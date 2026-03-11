# Backend Architecture

This document covers configuration, data persistence, the ingestion pipeline, the events/SSE system, and the LLM/embedding layer.

---

## Configuration Reference

All configuration is read from environment variables. Copy `.env.example` to `.env` in the `Backend/` directory before running.

`config.py` uses `load_dotenv()` with an explicit path (`Backend/.env`) so it works regardless of the working directory.

### LLM Settings

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | `""` | OpenAI secret key. Required if `DEFAULT_PROVIDER=openai`. |
| `LLM_MODEL` | `"gpt-4o-mini"` | OpenAI model to use for all generation nodes. |
| `OLLAMA_BASE_URL` | `"http://localhost:11434"` | Ollama server URL. |
| `OLLAMA_MODEL` | `"llama3.2"` | Default Ollama model when no override is specified. |
| `DEFAULT_PROVIDER` | `"openai"` | Which provider to use if the request doesn't specify one. |

### Retrieval Settings

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_MODEL` | `"all-MiniLM-L6-v2"` | SentenceTransformer model for embedding documents and queries. |
| `RERANKER_MODEL` | `"cross-encoder/ms-marco-MiniLM-L-6-v2"` | Cross-encoder model for reranking. |
| `VECTOR_BACKEND` | `"chroma"` | Vector store backend: `"chroma"` or `"faiss"`. |
| `RETRIEVAL_TOP_K` | `10` | Max results returned per retrieval strategy (before reranking). |
| `RERANK_TOP_K` | `5` | Max documents kept after cross-encoder reranking. |
| `MAX_CONTEXT_CHARS` | `4000` | Context length (chars) above which compression is triggered. |
| `MAX_REFLECTION_RETRIES` | `2` | Max retry loops the reflection node is allowed. |

### Chunking Settings

| Variable | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | `500` | Target chunk size in characters. |
| `CHUNK_OVERLAP` | `50` | Overlap between consecutive chunks (preserves context at boundaries). |

### Server & File Settings

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Flask server port. |
| `DEBUG` | `true` | Flask debug mode. Set to `false` in production. |
| `FRONTEND_URL` | `"http://localhost:5173"` | Frontend origin added to CORS allow-list. |
| `MAX_CONTENT_LENGTH` | `52428800` (50 MB) | Maximum file upload size. |
| `ALLOWED_EXTENSIONS` | `{pdf, txt, md, docx}` | Permitted upload file extensions. |

### Storage Paths

| Variable | Default | Description |
|---|---|---|
| `DATA_ROOT` | `"./data"` | Root for all runtime data. |
| `UPLOAD_FOLDER` | `"{DATA_ROOT}/uploads"` | Where uploaded files are saved. |
| `DATABASE_ROOT` | `"{DATA_ROOT}/databases"` | Root for all store data. |
| `CHROMA_PATH` | `"{DATABASE_ROOT}/vector_db/chroma_db"` | ChromaDB persistence directory. |
| `FAISS_PATH` | `"{DATABASE_ROOT}/vector_db/faiss_db"` | FAISS index storage (if `VECTOR_BACKEND=faiss`). |
| `BM25_PATH` | `"{DATABASE_ROOT}/keyword_db/bm25_store/bm25_store.pkl"` | BM25 pickle file. |
| `GRAPH_PATH` | `"{DATABASE_ROOT}/graph_db/graph_store/graph_store.pkl"` | Graph store pickle file. |

All paths are relative to the `Backend/` directory (the working directory when running `python src/main.py`).

---

## Data Persistence

The three retrieval stores and the KB registry all persist to disk automatically. They survive server restarts and are loaded as singletons on startup.

```
Backend/data/                       ← gitignored
  uploads/                          ← Raw uploaded files
  databases/
    vector_db/
      chroma_db/                    ← ChromaDB SQLite + binary index files
    keyword_db/
      bm25_store/
        bm25_store.pkl              ← Pickled BM25Okapi corpus + metadata
    graph_db/
      graph_store/
        graph_store.pkl             ← Pickled NetworkX graph + document store
    kb_registry.json                ← JSON manifest of all uploaded files
```

### Store Singletons

All three stores are module-level singletons, instantiated once on import:

```python
# In app.py:
from rag_pipeline.retrieval.vector.vector_store import vector_store
from rag_pipeline.retrieval.keyword.bm25_store  import bm25_store
from rag_pipeline.retrieval.graph.graph_store   import graph_store
```

Singletons are loaded from disk on first import and kept in memory for the lifetime of the server process. Writes are persisted to disk immediately (pickle/ChromaDB auto-persist).

---

## Knowledge Base Registry

The KB registry (`ingestion/registry.py`) is a thin JSON file that tracks metadata for every uploaded document. It is the source of truth for the `/api/knowledge-bases` endpoint and is consulted when deleting files to look up their original filenames.

**Registry file:** `data/databases/kb_registry.json`

**Entry format:**
```json
{
  "a3f8c2e1...": {
    "id":          "a3f8c2e1...",
    "name":        "my_document.pdf",
    "uploaded_at": "2024-01-15T10:30:00+00:00",
    "chunks":      42,
    "vectors":     42,
    "entities":    18,
    "edges":       27
  }
}
```

**Thread safety:** A `threading.Lock` wraps every read-modify-write operation to prevent corruption under concurrent uploads.

---

## Ingestion Pipeline

The upload flow (`POST /api/upload`) follows these steps:

### 1. File Validation & Save
```python
filename = secure_filename(f.filename)
file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
f.save(file_path)
```
`werkzeug.utils.secure_filename` strips path traversal characters.

### 2. Load & Chunk
```python
texts, metadatas = load_file(file_path)
```
`load_file()` in `ingestion/loader.py`:
1. Selects the appropriate LangChain loader based on file extension
2. Loads the document into LangChain `Document` objects
3. Splits using `RecursiveCharacterTextSplitter`:
   - `chunk_size = CHUNK_SIZE` (chars)
   - `chunk_overlap = CHUNK_OVERLAP` (chars)
   - `separators = ["\n\n", "\n", ".", " ", ""]`
4. Attaches per-chunk metadata: `file_name`, `file_hash`, `chunk_index`, `total_chunks`, `source_type`, `page` (PDF)

### 3. Deduplicate
```python
file_hash = metadatas[0]["file_hash"]  # MD5 of file content
# Remove existing data for this file
vector_store.delete_by_file(file_hash)
bm25_store.delete_by_file(file_hash)
graph_store.delete_by_file(file_hash)
kb_registry.remove(file_hash)
```
Using content MD5 as the identifier means re-uploading the same file always produces the same hash, enabling clean replacement.

### 4. Index into All Three Stores
```python
chunk_ids = generate_chunk_ids(file_hash, len(texts))  # "{file_hash}_{i}"
vector_store.add_documents(texts, metadatas, chunk_ids)
bm25_store.add_documents(texts, metadatas)
for i, (text, meta) in enumerate(zip(texts, metadatas)):
    graph_store.add_document(chunk_ids[i], text, meta)
```

### 5. Register
```python
kb_registry.register(file_hash, filename, {
    "chunks":   len(texts),
    "vectors":  len(texts),
    "entities": graph_store.count_entities_by_file(file_hash),
    "edges":    graph_store.get_stats().get("edges", 0),
})
```

---

## Events / SSE System

**File:** `core/events.py`

The SSE system uses an in-memory `dict` of `queue.Queue` objects, keyed by `session_id`. Each pipeline run gets its own isolated queue.

### Session Lifecycle

```
POST /api/query received
    │
    ├── create_session(session_id) → returns queue
    │
    ├── threading.Thread(target=_run).start()
    │       │
    │       └── rag_graph.invoke(state)
    │               │
    │               └── nodes call emit(session_id, type, data)
    │                         └── queue.put({type, data})
    │
    └── _generate() generator
            │
            └── while True:
                    item = queue.get(timeout=180)
                    if item is None: yield stream_end; break
                    yield format_sse(item)
            │
            finally: close_session(session_id)
```

### API

| Function | Purpose |
|---|---|
| `create_session(session_id)` | Create a new queue and register it. Returns `(session_id, queue)`. |
| `emit(session_id, event_type, data)` | Push an event into the session queue. No-op if session doesn't exist. |
| `close_session(session_id)` | Remove session and push `None` sentinel to end the stream. |
| `format_sse(payload)` | Serialize a dict as an SSE frame: `data: {json}\n\n` |

### SSE Frame Format

```
data: {"type": "stage_start", "data": {"stage": "retrieval", "message": "Searching KB..."}}\n\n
```

Each frame is a single line starting with `data: `, followed by two newlines to signal the end of the event to the browser's SSE parser.

### Timeout

The `_generate()` generator calls `queue.get(timeout=180)`. If the pipeline thread stalls for more than 3 minutes, the generator catches the timeout exception and emits a final error event before closing.

---

## LLM & Embedding Layer

### LLM Factory (`encoding/llm.py`)

`get_llm(provider, temperature, json_mode, model)` returns a cached LangChain chat model.

```python
# OpenAI
ChatOpenAI(model=LLM_MODEL, temperature=temperature, api_key=OPENAI_API_KEY)

# Ollama
ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=temperature,
           format="json" if json_mode else None)
```

**Caching key:** `(provider, temperature, json_mode, model)` — models are only instantiated once per unique configuration.

**`safe_json_parse(text)`** — Robustly extracts JSON from LLM output by trying:
1. Direct `json.loads(text)`
2. Strip markdown fences ` ```json ... ``` `
3. Extract first `{...}` block with regex
4. Raise `ValueError` if all fail

**`check_ollama()`** — Probes `{OLLAMA_BASE_URL}/api/tags` to get the list of installed models. Falls back to a root ping. Returns `{"available": bool, "models": [...]}`.

### Embedding Singleton (`encoding/embeddings.py`)

`get_embedder()` lazy-loads a `SentenceTransformer` model the first time it is called and returns the cached instance on subsequent calls.

The embedding model runs locally (no API call). Default: `all-MiniLM-L6-v2` — a fast, 384-dimensional model suitable for semantic similarity. Override with `EMBEDDING_MODEL` env var.

Used by:
- `vector_store.add_documents()` — encode chunks at index time
- `vector_store.search()` — encode queries at retrieval time
