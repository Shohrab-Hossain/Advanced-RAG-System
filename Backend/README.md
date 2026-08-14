# adRAG — Backend

Flask REST + SSE API over a LangGraph multi-stage RAG pipeline. Handles document ingestion, three-store hybrid retrieval (vector + BM25 + graph), LLM reasoning, and real-time streaming progress events.

## Quick Start

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .                 # editable install; adds the `adrag` package
cp .env.example .env             # add OPENAI_API_KEY
adrag-dev                        # API → http://localhost:5000
```

`adrag-dev` is the console script `pip` installs; `python -m adrag.main` does the same thing without it
on `PATH`. Two optional dependency groups exist and neither is installed by default:

```bash
pip install -e ".[faiss]"        # the alternative vector backend (VECTOR_BACKEND=faiss)
pip install -e ".[prod]"         # gunicorn + gevent-websocket, for the command below
```

**Production** — one worker, always. The SSE stream depends on threading, and forking additional workers
splits the event producer from its consumer:

```bash
gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         --bind 0.0.0.0:5000 adrag.app:app
```

**Both halves together** — `python infra/dev.py` from the repo root runs the backend and the Vue dev
server, wiring the frontend proxy to whichever port the backend got.

## Stack

- **Flask** + Flask-CORS — REST API + SSE streaming
- **LangGraph** — Pipeline state machine
- **LangChain** — LLM abstraction (OpenAI + Ollama)
- **ChromaDB** — Dense vector store
- **rank-bm25** — Sparse keyword retrieval
- **NetworkX** — Knowledge graph (GraphRAG)
- **SentenceTransformers** — Embeddings + cross-encoder reranking

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for OpenAI provider |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama model |
| `DEFAULT_PROVIDER` | `openai` | `openai` or `ollama` |
| `PORT` | `5000` | Server port |
| `DATA_ROOT` | `Backend/data` | Runtime state. Computed from the package location — **a relative value here is resolved against the working directory instead**, so use an absolute path if you set one |

See [`Documentation/architecture.md`](Documentation/architecture.md) for the full config reference.

## Layout

```
Backend/
├── data/                  runtime state — git-ignored; databases + uploads
├── pyproject.toml         the manifest — dependencies, extras, scripts
└── src/adrag/             the package, and the import root
    ├── app.py               the factory — CORS + blueprint registration, no routes
    ├── config.py            settings, anchored to the package not the CWD
    ├── main.py              entry point
    ├── routes/              one folder per resource, each owning a Blueprint
    └── custom_packages/     capabilities nothing routes to (the RAG pipeline)
```

Adding an endpoint means a folder under `routes/` and one line in `routes/__init__.py`'s `BLUEPRINTS`.
The full placement rules live in the project's `flask-file-tree` preference.

## Documentation

Detailed docs in [`Documentation/`](Documentation/):

| File | Contents |
|---|---|
| [Documentation/README.md](Documentation/README.md) | Setup, project structure |
| [Documentation/rag-pipeline.md](Documentation/rag-pipeline.md) | Every pipeline node, retrieval stores, retry loop |
| [Documentation/api.md](Documentation/api.md) | All API endpoints + SSE event reference |
| [Documentation/architecture.md](Documentation/architecture.md) | Config reference, persistence, ingestion, LLM layer |
