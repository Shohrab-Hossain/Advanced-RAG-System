<div align="center">

# 🧬 adRAG — Backend

### A Flask REST + SSE API wrapped around an eight-node LangGraph pipeline that retrieves three ways, reranks, and grades its own answer.

<br>

[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](pyproject.toml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-8%20nodes-1c3c3c)](Documentation/rag-pipeline/README.md)

[![Routes](https://img.shields.io/badge/routes-8-1c7ed6)](Documentation/api/README.md)
[![Stores](https://img.shields.io/badge/stores-vector%20%C2%B7%20BM25%20%C2%B7%20graph-f59e0b)](Documentation/hybrid-retrieval/README.md)
[![Port](https://img.shields.io/badge/dev%20port-5000-7c5cff)](#%EF%B8%8F-5-configuration)
[![Auth](https://img.shields.io/badge/auth-none-ef4444)](Documentation/security.md)

</div>

<br>

---

<br>

## Content Tree

<pre>
adRAG — Backend
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-quick-start">🚀 1. Quick start</a>
│   ├── <a href="#11-install">1.1 Install</a>
│   ├── <a href="#12-configure">1.2 Configure</a>
│   └── <a href="#13-run">1.3 Run</a>
│
├── <a href="#-2-what-it-does">🧠 2. What it does</a>
│
├── <a href="#%EF%B8%8F-3-stack">🛠️ 3. Stack</a>
│
├── <a href="#-4-layout">📁 4. Layout</a>
│
├── <a href="#%EF%B8%8F-5-configuration">⚙️ 5. Configuration</a>
│
├── <a href="#-6-checking-it-still-works">🧪 6. Checking it still works</a>
│
└── <a href="#-7-documentation">📚 7. Documentation</a>
</pre>

<br>

---

<br>

## 📖 Overview

The backend is an installable Python package, **`adrag`**, that serves eight HTTP routes and runs a
multi-stage RAG pipeline behind one of them. It handles document ingestion into three stores, hybrid
retrieval across all three, cross-encoder reranking, cited answer generation, and a self-reflection
pass that can send the whole query round again — streaming every stage to the browser as it happens.

> [!IMPORTANT]
> **It runs as exactly one process with one worker, and that is a correctness constraint.** The SSE
> session registry is a plain module dict and every store is a module singleton, so forking splits the
> event producer from its consumer *and* gives each worker a divergent BM25 corpus and graph.

<br>

---

<br>

## 🚀 1. QUICK START

### 1.1 Install

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .                 # editable install; adds the `adrag` package
```

Dependencies live in [`pyproject.toml`](pyproject.toml); `requirements.txt` is a one-line `-e .`
pointer kept so `pip install -r requirements.txt` still works. Two optional groups exist, and **neither
is installed by default**:

```bash
pip install -e ".[faiss]"        # faiss-cpu — the alternative vector backend
pip install -e ".[prod]"         # gunicorn + gevent-websocket, for the command below
```

**Python 3.10+ is mandated by the code, not just the docs.** PEP 604 unions (`str | None`) are
evaluated at runtime in module and signature scope, and no file carries
`from __future__ import annotations`, so 3.9 fails at import.

### 1.2 Configure

```bash
cp .env.example .env
# then set, at minimum:
#   OPENAI_API_KEY=<YOUR_API_KEY>
```

`.env` is loaded by absolute path from the package location, so it is found no matter where you start
the process — and **the process environment wins over the file**, which is how `infra/dev.py` injects
the ports it picked.

### 1.3 Run

```bash
adrag-dev                        # API → http://localhost:5000
```

`adrag-dev` is the console script `pip` installs; `python -m adrag.main` does the same thing without it
on `PATH`. Confirm it is up:

```bash
curl http://localhost:5000/api/health
```

```json
{ "status": "healthy" }
```

> [!NOTE]
> **First boot takes about a minute cold and roughly ten seconds warm** — almost all of it
> `sentence-transformers` pulling in torch at import. `/api/health` answers *before* the models finish
> loading, deliberately: it is a liveness probe, not a readiness one, and `infra/dev.py` polls it to
> decide when to bring the frontend up.

**Production** — one worker, always. Both the `-w 1` and the worker class are part of the command:

```bash
gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         --bind 0.0.0.0:5000 adrag.app:app
```

**Both halves together** — `python infra/dev.py` from the repository root runs this API and the Vue dev
server, probes free ports, wires the frontend proxy to whichever port the backend actually got, and
waits on `/api/health`.

<br>

---

<br>

## 🧠 2. WHAT IT DOES

**The pipeline** is eight LangGraph nodes, compiled once into a module-level `rag_graph` singleton:

```text
planner → retrieval → external_tools → aggregate → rerank → compress → reason → reflect
```

`planner` and `reflect` are conditional. The planner branches three ways — search the corpus, go
straight to web search, or answer directly with no retrieval at all. `reflect` grades the answer for
grounding and either terminates or loops back to `retrieval`, at most `MAX_REFLECTION_RETRIES` (2)
extra times.

> [!WARNING]
> **An SSE `stage` id is not the graph node name — five of the eight differ.** The frames those nodes
> emit carry `aggregator`, `reranker`, `compressor`, `reasoning` and `reflection` where the graph
> registers `aggregate`, `rerank`, `compress`, `reason` and `reflect`. The `emit()` call sites are the
> contract; the frontend drops any event whose stage it does not recognise, silently.

**The API** is eight routes across four blueprints, all under `/api`:

| Resource folder | Routes |
|---|---|
| `query/` | `POST /api/query` — runs the pipeline, returns `text/event-stream` |
| `knowledge_base/` | `POST /api/upload` · `GET /api/documents` · `DELETE /api/clear` · `GET /api/knowledge-bases` · `DELETE /api/knowledge-bases/<file_hash>` |
| `provider/` | `GET /api/providers` |
| `health_check/` | `GET /api/health` |

`routes/__init__.py` exports one `BLUEPRINTS` tuple and the factory iterates it, so **`app.py` carries
no route decorator at all** and adding a resource is a folder plus one line.

> [!CAUTION]
> **There is no authentication on any route.** `DELETE /api/clear` wipes all three stores, the
> registry, and every uploaded file it names — in one unauthenticated request, with no confirmation and
> no undo. The CORS allowlist also ends in a literal `"*"`, and `FLASK_DEBUG` defaults to `true`. All
> three are documented, localhost-only choices; see
> [`Documentation/security.md`](Documentation/security.md) before exposing the port.

<br>

---

<br>

## 🛠️ 3. STACK

| Role | Library |
|---|---|
| Web API | **Flask** + Flask-CORS — REST plus the SSE stream |
| Pipeline | **LangGraph** — the eight-node state machine |
| LLM abstraction | **LangChain** — one factory over OpenAI and Ollama |
| Dense vector store | **ChromaDB** (default) · **FAISS** (opt-in, `faiss` extra) |
| Sparse retrieval | **rank-bm25** — Okapi BM25 over the same corpus |
| Knowledge graph | **NetworkX** — a bipartite document ↔ entity graph |
| Embeddings + reranking | **sentence-transformers** — the embedder and the cross-encoder |
| Document loaders | **pypdf** · **docx2txt** · **unstructured** and LangChain's text loaders |
| Web search | **ddgs** — DuckDuckGo, no API key |

<br>

---

<br>

## 📁 4. LAYOUT

```text
Backend/
│
├── 📁 Documentation/          The engineering cookbook — 18 pages
├── 📁 data/                   RUNTIME STATE — git-ignored; databases + uploads
├── 📁 src/                    The slot — exactly one package
│   └── 📁 adrag/              The package, and the import root
│       ├── 📁 custom_packages/  Capabilities nothing routes to (the pipeline)
│       ├── 📁 routes/           One folder per resource, each owning a Blueprint
│       ├── 📄 app.py            The factory — CORS + blueprints, NO routes
│       ├── 📄 config.py         Settings, anchored to the package not the cwd
│       └── 📄 main.py           Entry point — main() backs the adrag-dev script
│
├── 📄 .env.example            Env template — the storage block ships commented out
├── 📄 pyproject.toml          THE MANIFEST — deps, extras, script, packaging
└── 📄 requirements.txt        A `-e .` pointer, nothing more
```

**Two placement rules govern the package.** A **route** is something the router points at: it gets its
own folder under `routes/`, with `<resource>_routes.py` inside and a `services.py` beside it once there
is real work to hold. A **capability** is something nothing routes to: it lives under
`custom_packages/` and never imports upward into `routes/` or `app.py`.

The full tree, with every module, is in
[`Documentation/README.md`](Documentation/README.md#-4-package-structure).

<br>

---

<br>

## ⚙️ 5. CONFIGURATION

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | Required for the OpenAI provider. Empty means it reports itself unavailable |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama model |
| `DEFAULT_PROVIDER` | `openai` | Used when a request does not name one |
| `VECTOR_BACKEND` | `chroma` | `chroma` or `faiss`; switching **does not migrate data** |
| `PORT` | `5000` | Server port |
| `FRONTEND_URL` | `http://localhost:8080` | Added to the CORS origins list |
| `FLASK_DEBUG` | `true` | Turns on **both** the auto-reloader and the interactive debugger |
| `DATA_ROOT` | `Backend/data` | Runtime state. Computed from the package location — **a relative value set here is resolved against the working directory instead**, so use an absolute path |

Every setting, its real default, where it is cast, and the four ways the *"a setting is a `Config`
attribute **and** an `.env.example` line"* convention is broken are in
[`Documentation/configuration.md`](Documentation/configuration.md).

<br>

---

<br>

## 🧪 6. CHECKING IT STILL WORKS

```bash
.venv/Scripts/python ../infra/smoke.py     # POSIX: .venv/bin/python ../infra/smoke.py
```

It builds the app through `create_app()` and drives the four read-only routes over Flask's test
client — binding no port and writing nothing — then checks the registered URL map. Exit `0` means every
checked route answered with the keys it promises.

> [!IMPORTANT]
> **This is a dev tool, not a test suite, and it says so itself.** The project has **no test
> framework**: no runner in `pyproject.toml`, no `tests/` directory, no CI. `smoke.py` covers four of
> the eight routes and asserts key *presence*, never values — it deliberately skips `POST /api/query`
> and `POST /api/upload` because both would call an LLM or mutate the index. Run it after any
> structural change; do not call this project tested.

<br>

---

<br>

## 📚 7. DOCUMENTATION

The engineering cookbook is [`Documentation/`](Documentation/README.md) — eighteen pages, each written
to be understood without opening the source.

| Start with | For |
|---|---|
| [`Documentation/README.md`](Documentation/README.md) | The index, four read orders, and the package tree |
| [`Documentation/rag-pipeline/README.md`](Documentation/rag-pipeline/README.md) | The eight nodes, the two conditional edges, and the retry state machine |
| [`Documentation/hybrid-retrieval/README.md`](Documentation/hybrid-retrieval/README.md) | Three stores, three incomparable score scales, one cross-encoder |
| [`Documentation/api/README.md`](Documentation/api/README.md) | The eight routes, CORS, and the error contract |
| [`Documentation/architecture/query-lifecycle.md`](Documentation/architecture/query-lifecycle.md) | One request from `POST` to rendered answer, across every layer |
| [`Documentation/security.md`](Documentation/security.md) | The trust boundaries, and what to close before leaving localhost |

The project front door — the RAG system explained end to end, plus the frontend — is
[`../README.md`](../README.md).

<br>
