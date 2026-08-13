# Backend architecture

Flask app + a `rag_pipeline` package. Entry point is `Backend/src/main.py`; the WSGI object is `app` in
`Backend/src/app.py`, built by the factory `create_app()`.

<br>

## Package layout

```
Backend/src/
├── main.py                  Entry point: silences noisy loggers, then app.run(threaded=True)
├── app.py                   create_app() — CORS, 8 routes, module-level `app`
├── config.py                class Config — every env var, read once at import
└── rag_pipeline/
    ├── state.py             RAGState + Document TypedDicts
    ├── graph.py             StateGraph assembly + routing functions + `rag_graph` singleton
    ├── core/events.py       session_id → Queue event bus
    ├── encoding/
    │   ├── llm.py           get_llm() factory + cache, safe_json_parse(), check_ollama()
    │   └── embeddings.py    get_embedder() — one shared SentenceTransformer
    ├── ingestion/
    │   ├── loader.py        load_file(), generate_chunk_ids(), _hash_file()
    │   └── registry.py      JSON KB registry with a threading.Lock
    ├── retrieval/
    │   ├── node.py          retrieval_node — fans out to the three stores
    │   ├── web_node.py      external_tools_node — DuckDuckGo
    │   ├── vector/vector_store.py   ChromaVectorStore | FaissVectorStore
    │   ├── keyword/bm25_store.py    BM25Store
    │   └── graph/graph_store.py     GraphStore
    ├── ranking/
    │   ├── aggregator.py    aggregator_node — dedup by content MD5
    │   └── reranker.py      reranker_node — CrossEncoder top-k
    └── generation/
        ├── planner.py       planner_node — Self-RAG routing decision
        ├── compressor.py    compressor_node — conditional LLM compression
        ├── reasoning.py     reasoning_node — cited answer generation
        └── reflection.py    reflection_node — grounding verdict + retry decision
```

**Import style note:** modules import `from config import Config` and `from rag_pipeline...` as if `src/`
were the root — because it is. `sys.path[0]` is the directory of the **script being run**, and `main.py`
lives in `src/`, so `src/` is on the path regardless of the working directory. `python src/main.py` from
`Backend/` and `python main.py` from `Backend/src/` produce an identical `sys.path[0]`.

**The working directory is a separate concern, and it is the one that bites.** It does not affect these
imports at all; it sets `Config.DATA_ROOT` (`config.py:44`, the relative literal `"./data"`), which decides
which corpus the store singletons open at import time. The backend must run with CWD `Backend/src` for
that reason — running it from elsewhere imports cleanly and silently opens an empty index. Full detail in
[`../runtime/backend-startup/README.md`](../runtime/backend-startup/README.md).

The gunicorn form `--chdir src main:app` satisfies both at once: it puts `src/` on the path as the import
base *and* lands the working directory in the right place.

<br>

## Responsibilities and boundaries

**`app.py`** owns everything HTTP: CORS configuration, upload validation, session creation, thread launch,
and SSE framing. It imports the three store singletons and the registry directly for the non-query routes.
It contains no retrieval or generation logic.

**`graph.py`** owns the topology and nothing else. Two routing functions decide the flow:

- `_route_planner(state)` → `"retrieval"` if `retrieve`, else `"external_tools"` if `use_external`, else
  `"aggregate"` (the direct-answer path that skips retrieval entirely).
- `_route_reflection(state)` → `END` if `final_answer` is set, else `"retrieval"`. Reflection signals
  "finish" purely by *writing* `final_answer`; there is no explicit done flag.

Fixed edges: `retrieval → external_tools → aggregate → rerank → compress → reason → reflect`. `retrieval`
always runs `external_tools` next; that node no-ops itself when `use_external` is false.

**Nodes** are plain functions `(state: RAGState) -> dict`. They read what they need, return only modified
keys, and never raise — every node wraps its risky work in `try/except`, emits a `stage_error` event, and
returns a usable fallback. This is why a broken reranker or a missing web-search package degrades the
answer rather than failing the request.

**Stores** are singletons enforced with a `__new__` + `_initialized` guard, and each exposes the same
surface: `add_document(s)`, `search(query, top_k) -> List[Document]`, `delete_by_file(file_hash)`,
`clear()`, plus `count()` (vector/BM25) or `get_stats()` (graph). Uniform shape is what lets `app.py`
fan out ingestion and deletion in three parallel lines.

<br>

## The three stores compared

| | Vector (Chroma default) | BM25 | Graph |
|---|---|---|---|
| Library | `chromadb.PersistentClient` | `rank_bm25.BM25Okapi` | `networkx.Graph` |
| Persistence | Chroma's own files under `CHROMA_PATH` | one pickle at `BM25_PATH` | one pickle at `GRAPH_PATH` |
| Written on | every `add_documents` (Chroma internal) | every mutation → `_save()` | every `add_document` → `_save()` |
| In-memory model | Chroma collection `rag_documents`, `hnsw:space=cosine` | `corpus: List[str]` + `metadatas: List[dict]`, index rebuilt on every change | bipartite graph + `doc_store: Dict[doc_id, {content, metadata}]` |
| Score semantics | `1.0 - distance` (cosine) | raw BM25 score, results with `score <= 0` dropped | `2.0 × edge weight` for 1-hop, `+0.5` per 2-hop path |
| top-k used | `RETRIEVAL_TOP_K` (10) | `RETRIEVAL_TOP_K` (10) | `max(TOP_K // 2, 3)` → 5 |

The FAISS alternative (`VECTOR_BACKEND=faiss`) uses `IndexFlatIP` over L2-normalised vectors (inner
product on unit vectors = cosine) and keeps ids/documents/metadatas in parallel Python lists pickled
alongside the index file. Its `delete_by_file` **rebuilds the whole index** by re-encoding every remaining
document — an O(corpus) operation, unlike Chroma's id-based delete.

<br>

## Concurrency model

- The SSE route starts a `threading.Thread(..., daemon=True)` per query and returns immediately.
- `main.py` runs Flask with `threaded=True`. The gunicorn command in its docstring uses `-w 1` — **one
  worker** — because the event-bus dict and the store singletons are per-process memory; forking workers
  would split sessions across processes that cannot see each other's queues.
- The KB registry serialises reads and writes with a module-level `threading.Lock`. The three stores do
  **not** lock; concurrent uploads mutating the same store are unsynchronised.
- `_llm_cache` in `encoding/llm.py` and `_embedder` in `encoding/embeddings.py` are unguarded module
  globals — benign to double-initialise, but not atomic.
