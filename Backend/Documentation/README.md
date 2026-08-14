# adRAG — Backend

The backend is a Python/Flask application that exposes a REST + Server-Sent Events (SSE) API over a multi-stage LangGraph RAG pipeline. It handles document ingestion, three-store hybrid retrieval, LLM-based reasoning, and streaming real-time progress events to the frontend.

---

## Table of Contents

- [Setup & Run](#setup--run)
- [Project Structure](#project-structure)
- [Detailed Documentation](#detailed-documentation)

---

## Setup & Run

### Prerequisites

- Python 3.10+
- An OpenAI API key **or** a running [Ollama](https://ollama.com) instance

### Install

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .                 # editable install of the `adrag` package
```

Dependencies are declared in `pyproject.toml`; `requirements.txt` is a one-line `-e .` pointer kept so
`pip install -r requirements.txt` still works. Two optional groups, neither installed by default:

```bash
pip install -e ".[faiss]"        # faiss-cpu — only needed for VECTOR_BACKEND=faiss
pip install -e ".[prod]"         # gunicorn + gevent-websocket
```

### Configure

```bash
cp .env.example .env
# Edit .env and set at minimum:
#   OPENAI_API_KEY=sk-...
```

All configuration is environment-driven. See the full reference in [architecture.md](architecture.md#configuration-reference).

### Run

```bash
# Development — either form
adrag-dev
python -m adrag.main

# Production (gunicorn — single worker required for SSE)
gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         --bind 0.0.0.0:5000 adrag.app:app
```

The API will be available at `http://localhost:5000`.

`-w 1` is not a tuning choice: the SSE session queues are process memory and every store is a module
singleton, so a second worker would split the event producer from its consumer and give each worker a
divergent copy of the BM25 and graph indexes.

To run **both halves** together, use `python infra/dev.py` from the repo root.

### Check it still works

```bash
.venv/Scripts/python ../infra/smoke.py     # POSIX: .venv/bin/python ../infra/smoke.py
```

Builds the app through `create_app()` and drives every read-only route over Flask's test client. It binds
no port and writes nothing. This is a **dev tool, not a test suite** — the project has no test framework —
but it is the fastest way to confirm the import chain resolves and every blueprint is registered after a
structural change.

---

## Project Structure

```
Backend/
├── src/
│   └── adrag/                             # the package — the import root for every module
│       ├── main.py                        # Entry point; main() backs the adrag-dev script
│       ├── app.py                         # Flask app factory — CORS + blueprints, NO routes
│       ├── config.py                      # Configuration, anchored to the package location
│       │
│       ├── routes/                        # the ROUTED layer — one folder per resource
│       │   ├── __init__.py                # exports BLUEPRINTS, the one list the factory reads
│       │   ├── query/
│       │   │   └── query_routes.py        # POST /api/query — the SSE pipeline stream
│       │   ├── knowledge_base/
│       │   │   ├── knowledge_base_routes.py   # upload · documents · clear · list · delete
│       │   │   └── services.py            # the three-store index/delete work
│       │   ├── provider/
│       │   │   └── provider_routes.py     # GET /api/providers
│       │   └── health_check/
│       │       └── health_check_routes.py # GET /api/health
│       │
│       └── custom_packages/               # capabilities nothing routes to
│           └── rag_pipeline/
│               ├── state.py               # RAGState TypedDict (shared pipeline state)
│               ├── workflow.py            # LangGraph workflow builder (rag_graph singleton)
│               ├── events.py              # SSE event bus (session queues + emit())
│               ├── models/
│               │   ├── llm.py             # LLM factory (OpenAI + Ollama, cached)
│               │   └── embeddings.py      # SentenceTransformer singleton
│               ├── ingestion/
│               │   ├── loader.py          # File loader + chunker (PDF/DOCX/TXT/MD)
│               │   └── registry.py        # Knowledge base registry (JSON persistence)
│               ├── retrieval/
│               │   ├── hybrid_node.py     # Hybrid retrieval node (vector + BM25 + graph)
│               │   ├── web_node.py        # DuckDuckGo web search node
│               │   └── stores/
│               │       ├── vector_store.py    # ChromaDB (or FAISS) dense vector store
│               │       ├── bm25_store.py      # BM25 sparse keyword store
│               │       └── graph_store.py     # NetworkX knowledge graph store
│               ├── ranking/
│               │   ├── aggregator.py      # Merge + deduplicate evidence
│               │   └── reranker.py        # Cross-encoder reranker (ms-marco-MiniLM)
│               └── generation/
│                   ├── planner.py         # Self-RAG decision node
│                   ├── compressor.py      # LLM context compressor
│                   ├── reasoning.py       # Answer generator with citations
│                   └── reflection.py      # Self-reflection + retry orchestration
├── data/                                  # RUNTIME STATE — never inside src/
│   ├── uploads/                           # Uploaded source files (gitignored)
│   └── databases/                         # All persistent store data (gitignored)
│       ├── vector_db/chroma_db/
│       ├── keyword_db/bm25_store/
│       └── graph_db/graph_store/
├── .env.example
├── pyproject.toml                         # the manifest — deps, extras, scripts, packaging
└── requirements.txt                       # a `-e .` pointer, nothing more
```

**Two placement rules govern this tree.** A **route** is something the router points at — it gets its own
folder under `routes/`, with `<resource>_routes.py` inside and a `services.py` beside it once there is real
work to hold. A **capability** is something nothing routes to — it lives under `custom_packages/` and never
imports upward into `routes/` or `app.py`. Adding an endpoint is a folder plus one line in
`routes/__init__.py`; nothing else changes.

---

## Detailed Documentation

| Document | Contents |
|---|---|
| [rag-pipeline.md](rag-pipeline.md) | How the RAG pipeline works: every node, the state machine, retry logic, retrieval stores |
| [api.md](api.md) | All HTTP endpoints, request/response shapes, SSE event reference |
| [architecture.md](architecture.md) | Configuration reference, data persistence, ingestion, events/SSE system |
