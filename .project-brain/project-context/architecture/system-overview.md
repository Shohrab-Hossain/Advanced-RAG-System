# System overview

adRAG is two independently-run processes that meet at exactly one place: HTTP calls to `/api/*` on the
Flask server. There is no shared database, no message broker, and no build-time coupling between them.

<br>

## The components

| Component | Lives in | Responsibility | Boundary |
|---|---|---|---|
| **Vue SPA** | `Frontend/src/` | All UI. Owns query input, live pipeline visualisation, result rendering, KB management screens, provider selection, and browser-local chat history. | Talks only to the Flask API. Holds no secrets. |
| **Flask API** | `Backend/src/app.py` | Seven REST routes + one SSE route (eight in all). Validates uploads, orchestrates ingestion into all three stores, launches pipeline runs, and streams their events. | The only network-facing surface. Owns all credentials. |
| **LangGraph pipeline** | `Backend/src/rag_pipeline/` | The eight-node RAG workflow. Pure functions over `RAGState`; emits events as a side effect. | Called only via `rag_graph.invoke(initial_state)`. |
| **Vector store** | `retrieval/vector/vector_store.py` | Dense semantic retrieval. Chroma `PersistentClient` (default) or FAISS `IndexFlatIP`. | Singleton module-level object `vector_store`. |
| **BM25 store** | `retrieval/keyword/bm25_store.py` | Sparse keyword retrieval over a tokenized corpus. | Singleton `bm25_store`. |
| **Graph store** | `retrieval/graph/graph_store.py` | Entity-graph retrieval over a NetworkX bipartite graph. | Singleton `graph_store`. |
| **KB registry** | `ingestion/registry.py` | Tracks which files are indexed and their per-file stats. A JSON file with a `threading.Lock`. | Module functions, not a class. |
| **Event bus** | `core/events.py` | Maps `session_id → queue.Queue`; nodes push, the SSE route drains. | In-memory only; dies with the process. |
| **LLM factory** | `encoding/llm.py` | Constructs and caches a LangChain chat model per `(provider, temperature, json_mode, model)`. | The only place a model is instantiated. |
| **Embedder** | `encoding/embeddings.py` | Lazily loads one shared `SentenceTransformer`. | Singleton via module-level `_embedder`. |

<br>

## End-to-end flow — a query

1. The user submits in `QueryInput.vue`; `ragStore.runQuery()` resets all stage statuses and calls
   `streamQuery()`.
2. `subsystems/rag/ragApi.js:42-50` POSTs to `/api/query` with `fetch` (a POST body rules out
   `EventSource`) — the body is `{query, provider}`, with `model` added **only when truthy** — then reads
   `res.body.getReader()` and splits the stream on `\n`, parsing every line that starts with `data: `.
3. The Flask route validates the body, mints a UUID `session_id`, creates that session's queue, builds the
   full `initial_state`, and starts a **daemon thread** running `rag_graph.invoke(initial_state)`.
4. The route's generator blocks on `event_queue.get(timeout=180)` and yields each event as
   `data: {json}\n\n`. Response headers set `Cache-Control: no-cache`, `X-Accel-Buffering: no`, and
   `Connection: keep-alive`.
5. Each pipeline node calls `emit(session_id, type, data)`; those land in the same queue and reach the
   browser within the same run.
6. When `invoke` returns, the thread pushes a `done` event carrying `{answer, sources, metadata}`, then a
   `None` sentinel that makes the generator emit `{"type": "stream_end"}` and close.
7. The store applies each event to `stageStatuses[stage]` (driving `PipelineTracker`), then on `done`
   writes `answer`, `sources`, `metadata` and pushes an entry onto `chatHistory`.

Failure paths: any exception inside the thread is caught and pushed as an `error` event with
`stage: "pipeline"`; a queue timeout yields an `error` event with `message: "Stream timeout"`. Either way
`close_session()` runs in the generator's `finally`.

<br>

## End-to-end flow — an upload

1. `uploadFile()` POSTs `multipart/form-data` via axios, reporting transfer percentage through
   `onUploadProgress`.
2. `/api/upload` checks the extension against `ALLOWED_EXTENSIONS` — **35 entries** (`config.py:62-65`),
   well beyond the four loader types — sanitises the name with `secure_filename`, and saves it under
   `UPLOAD_FOLDER`.
3. `load_file()` picks a loader by extension, splits the document into ~500-character chunks with 50
   characters of overlap, and returns parallel `texts` / `metadatas` lists. Every metadata dict carries the
   file's MD5 `file_hash`.
4. Any prior data for that `file_hash` is deleted from all three stores and the registry — so re-uploading
   the same file replaces rather than duplicates it.
5. The chunks are indexed into all three stores, and the registry records `chunks`, `vectors`, `entities`,
   and `edges` for the file.
6. The response returns the KB entry plus global index totals; the frontend then refreshes stats and the
   KB list.

<br>

## Boundary rules that hold everywhere

- **Secrets never cross to the browser.** `OPENAI_API_KEY` is read only in `Backend/src/config.py`.
  `/api/providers` exposes availability as a boolean, never the key.
- **The frontend never talks to Ollama, OpenAI, or DuckDuckGo directly.** Every model and search call is
  made server-side inside a pipeline node.
- **The pipeline never touches HTTP.** Nodes receive `RAGState` and emit events; they know nothing about
  Flask, requests, or responses.
- **`config.Config` is the only place environment variables are read for storage paths.** Individual store
  modules re-read a few knobs (`BM25_PATH`, `GRAPH_PATH`, `RETRIEVAL_TOP_K`, `RERANK_TOP_K`,
  `MAX_CONTEXT_CHARS`, `MAX_REFLECTION_RETRIES`) directly from `os.getenv` with the same defaults — a real
  duplication to be aware of when changing a default.
