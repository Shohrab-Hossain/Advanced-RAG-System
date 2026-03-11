# RAG Pipeline — Deep Dive

This document explains every stage of the adRAG pipeline: how the LangGraph state machine is structured, what each node does, how the three retrieval stores work, and how the self-reflection retry loop operates.

---

## Overview

The pipeline is a **LangGraph state machine** — a directed graph where each node is a Python function that reads from and writes to a shared `RAGState` dictionary. Conditional edges route the flow based on decisions made by each node.

```
┌────────────┐
│   planner  │  ← Decides: retrieve KB? use web? query type?
└─────┬──────┘
      │
      ├── retrieve=True ──────────────────────────────────────┐
      │                                                        ▼
      ├── use_external only ──────────────┐          ┌─────────────────┐
      │                                  │          │    retrieval    │  ← Vector + BM25 + Graph (parallel)
      └── direct answer ──────────┐      │          └────────┬────────┘
                                  │      │                   │
                                  │      ▼                   ▼
                                  │  ┌──────────────────────────┐
                                  │  │     external_tools       │  ← DuckDuckGo (if use_external)
                                  │  └──────────┬───────────────┘
                                  │             │
                                  ▼             ▼
                            ┌──────────────────────┐
                            │      aggregator      │  ← Merge + deduplicate all docs
                            └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │       reranker       │  ← Cross-encoder scoring
                            └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │      compressor      │  ← Summarize if context too long
                            └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │       reasoning      │  ← Generate answer with citations
                            └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │      reflection      │  ← Verify grounding; retry or finalize
                            └──────────┬───────────┘
                                       │
                   ┌───────────────────┴───────────────────────┐
                   │                                           │
            final_answer set                        final_answer not set
                   │                                           │
                  END                              loop back → retrieval
                                                  (up to MAX_REFLECTION_RETRIES)
```

---

## Shared State (`RAGState`)

All nodes read from and write to a single `TypedDict` called `RAGState`. It flows through every node in sequence.

```python
class RAGState(TypedDict):
    # ── Input (set by Flask before invoking the graph) ──────────────────────
    query: str                    # User's question
    session_id: str               # Routes SSE events back to the correct HTTP stream
    provider: str                 # "openai" | "ollama"
    ollama_model: str | None      # Optional model override (Ollama only)

    # ── Planner outputs ──────────────────────────────────────────────────────
    retrieve: bool                # Should we search the knowledge base?
    use_external: bool            # Should we run web search?
    query_type: str               # "factual" | "analytical" | "conversational"

    # ── Retrieval outputs ────────────────────────────────────────────────────
    vector_docs: List[Document]   # Dense (ChromaDB) results
    bm25_docs:   List[Document]   # Sparse (BM25) results
    graph_docs:  List[Document]   # Knowledge graph traversal results
    web_docs:    List[Document]   # DuckDuckGo web search results

    # ── Post-retrieval ───────────────────────────────────────────────────────
    all_docs:           List[Document]  # Deduplicated union of all sources
    context:            List[Document]  # Top-k after cross-encoder reranking
    compressed_context: str             # LLM-compressed context string

    # ── Generation ───────────────────────────────────────────────────────────
    answer:  str         # Raw LLM answer
    sources: List[dict]  # Source metadata for citations

    # ── Reflection ───────────────────────────────────────────────────────────
    grounded:             bool  # Is the answer grounded in the retrieved context?
    reflection_feedback:  str   # Feedback from the reflection agent
    retry_count:          int   # How many retrieval retries have occurred

    # ── Final output ─────────────────────────────────────────────────────────
    final_answer:      str        # Finalized answer (may include caveats)
    final_sources:     List[dict] # Sources to show the user
    pipeline_metadata: dict       # Confidence, retry count, grounded flag, etc.
```

Each `Document` in the lists has:
```python
{
    "content":      str,   # Raw text of the passage
    "metadata":     dict,  # file_name, page, chunk_index, url, etc.
    "score":        float, # Initial retrieval score (0–1)
    "source":       str,   # "vector" | "bm25" | "graph" | "web"
    "rerank_score": float, # Cross-encoder score (set later by reranker)
}
```

---

## Node Reference

### 1. Planner (`generation/planner.py`)

**Purpose:** Self-RAG decision node. Classifies the query and decides whether to retrieve from the knowledge base, use web search, or answer directly.

**Inputs read:** `query`, `provider`, `ollama_model`

**Outputs written:** `retrieve`, `use_external`, `query_type`

**Mechanism:**
- Sends the query to an LLM with a structured prompt asking for a JSON decision:
  ```json
  { "retrieve": true, "use_external": false, "query_type": "factual" }
  ```
- Parses the response with `safe_json_parse()` (handles markdown fences and partial JSON)
- Falls back to `retrieve=True, use_external=False, query_type="factual"` on parse failure

**Query types:**
- `factual` — Specific fact lookups; prioritises precise retrieval
- `analytical` — Synthesis questions; benefits from broad context
- `conversational` — Casual exchanges; may skip retrieval entirely

**Routing after this node:**
```
retrieve=True          → retrieval node
retrieve=False,
use_external=True      → external_tools node
both False             → aggregator node (direct answer with empty docs)
```

**SSE events emitted:** `stage_start` → `stage_complete` (or `stage_error`)

---

### 2. Retrieval (`retrieval/node.py`)

**Purpose:** Hybrid retrieval — runs all three stores in parallel and collects their results.

**Inputs read:** `query`, `retrieve`

**Outputs written:** `vector_docs`, `bm25_docs`, `graph_docs`

**Mechanism:**
- Runs three searches **concurrently** using `ThreadPoolExecutor`:
  1. `vector_store.search(query, top_k=RETRIEVAL_TOP_K)` — dense cosine similarity
  2. `bm25_store.search(query, top_k=RETRIEVAL_TOP_K)` — sparse BM25 scoring
  3. `graph_store.search(query, top_k=RETRIEVAL_TOP_K)` — entity-graph traversal
- Each store returns up to `RETRIEVAL_TOP_K` (default 10) documents

**SSE events emitted:** `stage_start` → `retrieval_result` (with per-source counts)

---

### 3. External Tools (`retrieval/web_node.py`)

**Purpose:** Web search fallback for queries that require live or external data.

**Inputs read:** `query`, `use_external`

**Outputs written:** `web_docs`

**Mechanism:**
- If `use_external=False`: emits `stage_skip` and returns immediately
- If `use_external=True`: calls DuckDuckGo Search (`ddgs`) and returns the top results as `Document` objects with `source="web"` and the URL in metadata

**SSE events emitted:** `stage_start` → `stage_complete` or `stage_skip` or `stage_error`

---

### 4. Aggregator (`ranking/aggregator.py`)

**Purpose:** Merge the four document lists (vector, BM25, graph, web) into one deduplicated ranked list.

**Inputs read:** `vector_docs`, `bm25_docs`, `graph_docs`, `web_docs`

**Outputs written:** `all_docs`

**Mechanism:**
- Iterates all documents from all sources
- Deduplicates by an MD5 hash of the content text
- When duplicates exist (same passage retrieved by multiple stores), keeps the copy with the **highest score**
- This means a passage retrieved by both vector and BM25 is kept once, with the better score

**SSE events emitted:** `stage_start` → `stage_complete`

---

### 5. Reranker (`ranking/reranker.py`)

**Purpose:** Apply a cross-encoder model to re-score all documents against the query and select the best top-k.

**Inputs read:** `all_docs`, `query`

**Outputs written:** `context`

**Mechanism:**
- Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` (a sentence-transformer cross-encoder)
- Creates `(query, document_content)` pairs for every document in `all_docs`
- Runs the cross-encoder to get a relevance score for each pair
- The cross-encoder is more accurate than cosine similarity because it jointly encodes the query and document
- Returns the top `RERANK_TOP_K` (default 5) documents sorted by `rerank_score` descending
- On failure, falls back to sorting `all_docs` by the original retrieval score

**Why cross-encoder reranking matters:**
- Bi-encoder similarity (used in vector search) encodes query and document independently, which is fast but less accurate
- A cross-encoder reads both together and can model fine-grained relevance interactions
- The trade-off: cross-encoders are too slow to run over the entire corpus, so they run only on the top candidates already retrieved

**SSE events emitted:** `stage_start` → `stage_complete` (with `top_k` count)

---

### 6. Compressor (`generation/compressor.py`)

**Purpose:** If the total context length exceeds the LLM's practical window, summarise each document to retain only query-relevant passages.

**Inputs read:** `context`, `query`, `provider`, `ollama_model`

**Outputs written:** `compressed_context`

**Mechanism:**
- Concatenates all context documents into a string
- If the total length is ≤ `MAX_CONTEXT_CHARS` (default 4000): returns as-is (no LLM call)
- If longer: sends each document to the LLM with a prompt: *"Extract only the sentences relevant to: [query]"*
- Reconstructs a compact context string from the extracted passages
- Falls back to truncation if LLM fails

**SSE events emitted:** `stage_start` → `stage_complete` (with compression ratio if applied)

---

### 7. Reasoning (`generation/reasoning.py`)

**Purpose:** Generate the final answer from the compressed context, with inline numbered citations.

**Inputs read:** `compressed_context`, `context`, `query`, `provider`, `ollama_model`

**Outputs written:** `answer`, `sources`

**Mechanism:**
- Sends a structured prompt to the LLM:
  - System: *"Answer using only the provided context. Cite sources as [1], [2], etc."*
  - User: context passages + the query
- Expects a JSON response:
  ```json
  {
    "answer": "The answer text with [1] citations...",
    "cited_sources": [0, 1],
    "confidence": 0.87,
    "key_facts": ["fact 1", "fact 2"],
    "is_sufficient": true
  }
  ```
- Parses sources from the `cited_sources` array, mapping indices to the context documents
- Falls back to a plain-text answer if JSON parsing fails
- Sets `is_sufficient` in pipeline metadata for the reflection node

**SSE events emitted:** `stage_start` → `stage_complete` (with confidence score)

---

### 8. Reflection (`generation/reflection.py`)

**Purpose:** Self-verification agent. Checks whether the answer is actually grounded in the retrieved context and decides whether to accept it or loop back for another retrieval attempt.

**Inputs read:** `answer`, `context`, `query`, `retry_count`, `provider`, `ollama_model`

**Outputs written:** `grounded`, `reflection_feedback`, `final_answer`, `final_sources`, `pipeline_metadata`

**Mechanism:**
- Sends a structured prompt:
  - *"You are a fact-checker. Given the context and the answer, determine: is every claim in the answer supported by the context?"*
  - Expects: `{ "grounded": true/false, "feedback": "...", "confidence": 0.9 }`
- **If grounded:** Sets `final_answer` and `final_sources` → pipeline ends
- **If not grounded and retry budget remains:**
  - Increments `retry_count`
  - On the first retry: if `graph_docs` was empty (KB had nothing relevant), sets `use_external=True` to escalate to web search
  - Leaves `final_answer` empty → graph routes back to retrieval
- **If budget exhausted** (`retry_count >= MAX_REFLECTION_RETRIES`): Sets `final_answer` anyway (with a caveat appended about limited grounding) and exits the loop

**Retry budget:** Default `MAX_REFLECTION_RETRIES = 2` (configurable via env)

**SSE events emitted:** `stage_start` → `stage_complete` or `retry` or `finalize`

---

## Three Retrieval Stores

### Vector Store — Dense Semantic Search

**File:** `retrieval/vector/vector_store.py`
**Backend:** ChromaDB (default) or FAISS (set `VECTOR_BACKEND=faiss`)
**Persistence:** `data/databases/vector_db/chroma_db/`

Each document chunk is encoded by `all-MiniLM-L6-v2` (384-dimensional embedding) when uploaded. At query time, the query is embedded the same way, and the nearest neighbours are retrieved by cosine similarity.

```
Upload:  text chunk → SentenceTransformer → 384-dim vector → ChromaDB collection
Query:   user query → SentenceTransformer → 384-dim vector → top-k cosine neighbours
```

**Score:** `1.0 - cosine_distance` (0 = unrelated, 1 = identical)

**Key methods:**
| Method | Purpose |
|---|---|
| `add_documents(texts, metadatas, ids)` | Embed and store chunks |
| `search(query, top_k)` | Return top-k by cosine similarity |
| `delete_by_file(file_hash)` | Remove all chunks for a file |
| `count()` | Total stored vectors |
| `clear()` | Wipe the collection |

---

### BM25 Store — Sparse Keyword Search

**File:** `retrieval/keyword/bm25_store.py`
**Library:** `rank-bm25` (BM25Okapi)
**Persistence:** `data/databases/keyword_db/bm25_store/bm25_store.pkl`

BM25 (Best Matching 25) is a classical information retrieval algorithm based on term frequency and inverse document frequency. It excels at exact keyword matching — complementing the semantic vector search, which can miss precise technical terms.

```
Upload:  text chunk → tokenise (lowercase word boundaries) → BM25 corpus
Query:   user query → tokenise → BM25 score each document → top-k
```

**Tokenisation:** Regex `\b\w+\b` — alphanumeric word boundaries, lowercased.

**Score:** Raw BM25 score (≥ 0). Normalised to 0–1 range relative to the top result.

**Key methods:**
| Method | Purpose |
|---|---|
| `add_documents(texts, metadatas)` | Tokenise and rebuild BM25 index |
| `search(query, top_k)` | Return top-k by BM25 score |
| `delete_by_file(file_hash)` | Remove file's chunks and rebuild index |
| `count()` | Total documents in corpus |

---

### Graph Store — Entity-Aware Knowledge Graph

**File:** `retrieval/graph/graph_store.py`
**Library:** NetworkX (in-memory bipartite graph)
**Persistence:** `data/databases/graph_db/graph_store/graph_store.pkl`

The knowledge graph connects document chunks to the named entities (people, organisations, acronyms, technical terms) they mention. This enables entity-aware retrieval: if you ask about "LLM", the graph finds all chunks that mention it, plus chunks that mention related entities.

**Graph structure:**
```
[Document node]  ──── mentions ──── [Entity node]
      │                                    │
      └─── chunk_id, content_preview ──┐  └─── entity name (e.g. "GPT-4", "LLM")
                                        │
[Another Document] ── also mentions ────┘  (shared entity = related docs)
```

**Entity extraction (regex-based, at index time):**
- Multi-word proper nouns: `[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*` → e.g. "Google Cloud"
- Acronyms: `[A-Z]{2,6}` → e.g. "LLM", "RAG", "API"
- camelCase technical terms: `[a-z]+(?:[A-Z][a-z]+)+` → e.g. "langChain"
- Common stop-words (The, This, For, ...) are filtered out

**Query mechanism:**
1. Extract entities from the query using the same regex
2. **1-hop:** Find all documents directly connected to matching entity nodes (weight × 2.0)
3. **2-hop:** Find documents that share entities with the 1-hop documents (weight × 0.5)
4. Sum weights per document and return top-k

**Key methods:**
| Method | Purpose |
|---|---|
| `add_document(doc_id, content, metadata)` | Extract entities, build graph links |
| `search(query, top_k)` | Entity-graph traversal |
| `delete_by_file(file_hash)` | Remove document nodes + orphaned entities |
| `count_entities_by_file(file_hash)` | Stats for KB registry |
| `get_stats()` | `{documents, entities, edges}` |

---

## Document Ingestion

When a file is uploaded via `POST /api/upload`:

1. **Load** — The appropriate LangChain loader reads the file:
   - `.pdf` → `PyPDFLoader`
   - `.docx` → `Docx2txtLoader`
   - `.txt` → `TextLoader`
   - `.md` → `UnstructuredMarkdownLoader`

2. **Hash** — MD5 hash of file content becomes `file_hash` (stable unique ID)

3. **Chunk** — `RecursiveCharacterTextSplitter` splits into overlapping passages:
   - `CHUNK_SIZE = 500` characters
   - `CHUNK_OVERLAP = 50` characters
   - Separators tried in order: `\n\n`, `\n`, `.`, ` `, `""`

4. **Metadata** attached to each chunk:
   ```python
   {
       "file_name": str, "file_hash": str,
       "chunk_index": int, "total_chunks": int,
       "source_type": "pdf"|"text"|"markdown"|"docx",
       "page": int  # (PDF only)
   }
   ```

5. **Index** — All three stores are populated:
   ```python
   vector_store.add_documents(texts, metadatas, chunk_ids)
   bm25_store.add_documents(texts, metadatas)
   for chunk in chunks:
       graph_store.add_document(chunk_id, text, metadata)
   ```

6. **Register** — KB registry records the file with stats (chunks, vectors, entities, edges)

---

## SSE Streaming

Each pipeline run streams real-time events to the frontend via Server-Sent Events.

**Flow:**
```
Flask route creates session queue
         │
         ├── Background thread: rag_graph.invoke(state)
         │       │
         │       └── Nodes call emit(session_id, event_type, data)
         │               │
         │               └── Pushed into session queue
         │
         └── SSE generator reads queue → formats as SSE frame → streams to browser
```

**Event types:**

| Type | When | Key data fields |
|---|---|---|
| `stage_start` | Node begins | `stage`, `message` |
| `stage_complete` | Node finishes | `stage`, `message`, `details` |
| `stage_skip` | Node intentionally skipped | `stage`, `message` |
| `stage_error` | Node failed (non-fatal) | `stage`, `error` |
| `retrieval_result` | Retrieval counts ready | `stage`, `vector_count`, `bm25_count`, `graph_count` |
| `retry` | Reflection triggers retry | `stage`, `attempt` |
| `finalize` | Reflection accepts answer | `stage`, `message` |
| `done` | Pipeline complete | `answer`, `sources`, `metadata` |
| `stream_end` | Stream closing | — |

**SSE frame format:**
```
data: {"type": "stage_start", "data": {"stage": "retrieval", "message": "Searching..."}}\n\n
```
