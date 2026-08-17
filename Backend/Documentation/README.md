<div align="center">

# 📗 Backend Documentation

### Eighteen pages covering every subsystem behind the eight-node pipeline — how each one works, how they connect, and where each one will surprise you.

<br>

[![Pages](https://img.shields.io/badge/pages-18-7c5cff)](#-2-the-document-map)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../pyproject.toml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)

[![Nodes](https://img.shields.io/badge/pipeline-8%20nodes-1c3c3c)](rag-pipeline/README.md)
[![Routes](https://img.shields.io/badge/routes-8-1c7ed6)](api/README.md)
[![Stores](https://img.shields.io/badge/stores-3-f59e0b)](hybrid-retrieval/README.md)
[![Auth](https://img.shields.io/badge/auth-none-ef4444)](security.md)

</div>

<br>

---

<br>

## Content Tree

<pre>
Backend Documentation
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-how-to-read-this-set">🧭 1. How to read this set</a>
│
├── <a href="#-2-the-document-map">📚 2. The document map</a>
│   ├── <a href="#21-the-tree">2.1 The tree</a>
│   ├── <a href="#22-the-pipeline-and-retrieval">2.2 The pipeline and retrieval</a>
│   ├── <a href="#23-the-platform">2.3 The platform</a>
│   ├── <a href="#24-the-http-api">2.4 The HTTP API</a>
│   └── <a href="#25-cross-cutting">2.5 Cross-cutting</a>
│
├── <a href="#-3-setup-and-run">🚀 3. Setup and run</a>
│   ├── <a href="#31-install">3.1 Install</a>
│   ├── <a href="#32-configure">3.2 Configure</a>
│   ├── <a href="#33-run">3.3 Run</a>
│   └── <a href="#34-check-it-still-works">3.4 Check it still works</a>
│
├── <a href="#-4-package-structure">📁 4. Package structure</a>
│
├── <a href="#-5-where-a-new-file-goes">🧩 5. Where a new file goes</a>
│
├── <a href="#%EF%B8%8F-6-known-gaps">⚠️ 6. Known gaps</a>
│
└── <a href="#-7-related-reading">🔗 7. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

The backend is a Flask REST + Server-Sent Events API wrapped around an eight-node **LangGraph**
pipeline. It ingests documents into three stores, retrieves over all three on every pass, reranks with
a cross-encoder, generates a cited answer, and runs a second LLM as a critic before returning it.

This folder is the engineering cookbook for that system. Each page is written to be read on its own:
you should be able to explain the subsystem back from the page without opening the source.

> [!IMPORTANT]
> **Three facts recur across almost every page, and getting one wrong invalidates the rest.**
> **(1)** An SSE `stage` id is **not** the graph node name — five of the eight differ, and the `emit()`
> call sites are the contract. **(2)** `score` is not comparable across the three stores; only
> `rerank_score` is, and it is a raw logit whose sign is load-bearing. **(3)** The server runs as one
> process with one worker, because the session registry is process memory and every store is a module
> singleton.

<br>

---

<br>

## 🧭 1. HOW TO READ THIS SET

Four routes through the same eighteen pages, depending on why you are here.

| You are… | Read in this order |
|---|---|
| **New to the project** | [`rag-pipeline/README.md`](rag-pipeline/README.md) → [`architecture/query-lifecycle.md`](architecture/query-lifecycle.md) → [`hybrid-retrieval/README.md`](hybrid-retrieval/README.md) → [`api/README.md`](api/README.md) |
| **Improving answer quality** | [`hybrid-retrieval/README.md`](hybrid-retrieval/README.md) → [`hybrid-retrieval/stores.md`](hybrid-retrieval/stores.md) → [`rag-pipeline/nodes.md`](rag-pipeline/nodes.md) → [`ingestion/README.md`](ingestion/README.md) → [`llm-providers/README.md`](llm-providers/README.md) |
| **Writing a client** | [`api/README.md`](api/README.md) → [`api/query.md`](api/query.md) → [`sse-event-bus/README.md`](sse-event-bus/README.md) → [`api/knowledge-base.md`](api/knowledge-base.md) |
| **Running or deploying it** | [`architecture/README.md`](architecture/README.md) → [`configuration.md`](configuration.md) → [`architecture/storage-model.md`](architecture/storage-model.md) → [`security.md`](security.md) |

If you only ever read two pages, read [`rag-pipeline/README.md`](rag-pipeline/README.md) — the state
machine everything else serves — and [`architecture/query-lifecycle.md`](architecture/query-lifecycle.md),
which walks one request across every layer from the `POST` to the rendered answer.

<br>

---

<br>

## 📚 2. THE DOCUMENT MAP

### 2.1 The tree

```text
Backend/Documentation/
│
├── 📄 README.md                       You are here — index and read order
│
├── 📁 rag-pipeline/                   The eight-node LangGraph state machine
│   ├── 📄 README.md                   The deep dive — the centrepiece of this set
│   ├── 📄 nodes.md                    Per-node reference, all eight
│   └── 📄 state-model.md              RAGState, merge semantics, invariants
│
├── 📁 hybrid-retrieval/               Three stores, one query, one ranking
│   ├── 📄 README.md                   The subsystem — scales, merge, rerank
│   └── 📄 stores.md                   Chroma · FAISS · BM25 · graph internals
│
├── 📁 ingestion/                      Upload to indexed — load, chunk, fan out
│   └── 📄 README.md
│
├── 📁 sse-event-bus/                  Sessions, emit(), queues, the wire format
│   └── 📄 README.md
│
├── 📁 llm-providers/                  get_llm(), the two providers, JSON discipline
│   └── 📄 README.md
│
├── 📁 api/                            The eight HTTP routes
│   ├── 📄 README.md                   Index, registration, CORS, error contract
│   ├── 📄 query.md                    POST /api/query + the full SSE catalogue
│   ├── 📄 knowledge-base.md           The five knowledge-base routes
│   └── 📄 provider-and-health.md      GET /api/providers · GET /api/health
│
├── 📁 architecture/                   The whole-system view
│   ├── 📄 README.md                   Layers, boot, process model, infra/
│   ├── 📄 query-lifecycle.md          One request end to end, ten phases
│   └── 📄 storage-model.md            What is on disk and what survives a crash
│
├── 📄 configuration.md                Every setting, its real default, its caveats
└── 📄 security.md                     Trust boundaries, measured posture, checklist
```

### 2.2 The pipeline and retrieval

The core. Start here for anything about *how an answer is produced*.

| Page | What it covers | Diagram |
|---|---|---|
| [`rag-pipeline/README.md`](rag-pipeline/README.md) | The eight nodes, the two conditional edges, the retry state machine, the citation chain, the escalation heuristic, the JSON discipline that keeps the same prompts working on a frontier model and a small local one | ✅ ×2 |
| [`rag-pipeline/nodes.md`](rag-pipeline/nodes.md) | Every node in turn — what it reads, what it returns, what it emits, what its prompt says, and how it fails | — |
| [`rag-pipeline/state-model.md`](rag-pipeline/state-model.md) | `RAGState` key by key, who writes each field, why returned keys overwrite instead of accumulating, and the two write-only keys | — |
| [`hybrid-retrieval/README.md`](hybrid-retrieval/README.md) | Why three stores, the three incomparable score scales, dedup by content MD5, and the cross-encoder that resolves them into one ranking | ✅ |
| [`hybrid-retrieval/stores.md`](hybrid-retrieval/stores.md) | Chroma, FAISS, BM25 and the entity graph — how each indexes, searches, scores and persists, and where the shared "store interface" is not actually shared | — |

### 2.3 The platform

The machinery the pipeline runs on.

| Page | What it covers | Diagram |
|---|---|---|
| [`ingestion/README.md`](ingestion/README.md) | One file to N chunks to four destinations — the loaders, the splitter, the content hash, delete-then-write dedup, and the failure modes of a write with no transaction | ✅ |
| [`sse-event-bus/README.md`](sse-event-bus/README.md) | The session registry, `emit()` and why its silence is load-bearing, the wire format and its four omissions, and the 180-second per-event drain | ✅ |
| [`llm-providers/README.md`](llm-providers/README.md) | `get_llm()` as the single construction point, the never-invalidated cache, the asymmetric JSON mode, the salvage parser, and the Ollama liveness probe | — |
| [`configuration.md`](configuration.md) | Every `Config` attribute with its real default and cast, the `.env` precedence rules, and the four distinct ways the settings convention is broken | — |

### 2.4 The HTTP API

| Page | What it covers |
|---|---|
| [`api/README.md`](api/README.md) | The eight-route index, how a blueprint is registered, the route-versus-service split, CORS, content types and limits, the error contract, and how to add a resource |
| [`api/query.md`](api/query.md) | `POST /api/query` in full — the request fields, the two `400`s, the response headers, and the **complete SSE catalogue**: ten event types with every payload key |
| [`api/knowledge-base.md`](api/knowledge-base.md) | Upload, documents, clear, list, delete — request and response shapes, every error, the filename defences, and the limitations of each |
| [`api/provider-and-health.md`](api/provider-and-health.md) | The two smallest routes, the boolean-availability guarantee that keeps the API key server-side, and the ten-second worst case hiding behind one of them |

### 2.5 Cross-cutting

| Page | What it covers | Diagram |
|---|---|---|
| [`architecture/README.md`](architecture/README.md) | The four layers and the import invariants that hold them apart, the boot sequence and its import-time disk writes, the measured cold-start cost, the process model, and `infra/dev.py` + `infra/smoke.py` | — |
| [`architecture/query-lifecycle.md`](architecture/query-lifecycle.md) | One request from `POST` to rendered answer across every layer — ten phases, two threads, eight nodes, and where each phase can fail | ✅ |
| [`architecture/storage-model.md`](architecture/storage-model.md) | Path anchoring, the on-disk tree, four stores with four persistence models, and the operational answers — how to back up, reset, move, and what survives an interrupt | — |
| [`security.md`](security.md) | Four trust boundaries, the measured CORS behaviour, the debugger, the prompt-injection and XSS paths, the pickle assessment, and an ordered checklist for leaving localhost | — |

<br>

---

<br>

## 🚀 3. SETUP AND RUN

### 3.1 Install

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .                 # editable install of the `adrag` package
```

Dependencies are declared in [`../pyproject.toml`](../pyproject.toml); `requirements.txt` is a one-line
`-e .` pointer kept so `pip install -r requirements.txt` still works. Two optional groups exist and
neither is installed by default:

```bash
pip install -e ".[faiss]"        # faiss-cpu — only for VECTOR_BACKEND=faiss
pip install -e ".[prod]"         # gunicorn + gevent-websocket
```

> [!NOTE]
> **The `prod` extra is declared but not installed here.** The gunicorn command below needs
> `pip install -e ".[prod]"` first, or it fails at the shell.

### 3.2 Configure

```bash
cp .env.example .env
# then set, at minimum:
#   OPENAI_API_KEY=<YOUR_API_KEY>
```

Everything is environment-driven and everything but the key has a working default. **The process
environment wins over `.env`** — `load_dotenv` is called without `override`, which is exactly how
`infra/dev.py` injects the ports it picked. The full reference is
[`configuration.md`](configuration.md).

### 3.3 Run

```bash
# Development — either form
adrag-dev
python -m adrag.main

# Production — one worker, always
gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
         --bind 0.0.0.0:5000 adrag.app:app
```

The API is served at `http://localhost:5000`. To run **both halves**, use `python infra/dev.py` from
the repository root — it probes free ports, wires the frontend proxy to whichever the backend got, and
waits on `/api/health`.

> [!IMPORTANT]
> **`-w 1` is a correctness constraint, not a tuning choice.** The SSE session registry is process
> memory and every store is a module singleton, so a second worker splits the event producer from its
> consumer *and* gives each worker a divergent BM25 corpus and graph that overwrite each other's
> pickle. See [`architecture/README.md`](architecture/README.md).

> [!NOTE]
> **First boot takes about a minute cold and roughly ten seconds warm** — nearly all of it
> `sentence-transformers` at import. `/api/health` deliberately answers before the models are loaded:
> it is a liveness probe, not a readiness one.

### 3.4 Check it still works

```bash
.venv/Scripts/python ../infra/smoke.py     # POSIX: .venv/bin/python ../infra/smoke.py
```

It builds the app through `create_app()` and drives the four read-only routes over Flask's test
client, binding no port and writing nothing. **It is a dev tool, not a test suite** — this project has
no test framework — but it is the fastest way to confirm the import chain resolves and every blueprint
is still registered after a structural change.

<br>

---

<br>

## 📁 4. PACKAGE STRUCTURE

```text
Backend/
│
├── 📁 Documentation/                     This folder — 18 pages
│
├── 📁 data/                              RUNTIME STATE — git-ignored, never in src/
│   ├── 📁 databases/                     The three stores + kb_registry.json
│   └── 📁 uploads/                       The files users dropped, verbatim
│
├── 📁 src/                               The slot — exactly one package
│   └── 📁 adrag/                         The import root for every module
│       ├── 📁 routes/                    The ROUTED layer — one folder per resource
│       │   ├── 📄 __init__.py            Exports BLUEPRINTS — the tuple the factory reads
│       │   ├── 📁 query/                 query_routes.py — POST /api/query (SSE)
│       │   ├── 📁 knowledge_base/        <resource>_routes.py + services.py
│       │   ├── 📁 provider/              provider_routes.py — GET /api/providers
│       │   └── 📁 health_check/          health_check_routes.py — GET /api/health
│       │
│       ├── 📁 custom_packages/           Capabilities nothing routes to
│       │   └── 📁 rag_pipeline/          The eight-node pipeline
│       │       ├── 📁 generation/        planner · compressor · reasoning · reflection
│       │       ├── 📁 ingestion/         loader.py (chunking) + registry.py
│       │       ├── 📁 models/            llm.py factory + embeddings.py singleton
│       │       ├── 📁 ranking/           aggregator.py + reranker.py
│       │       ├── 📁 retrieval/         hybrid_node · web_node · stores/
│       │       ├── 📄 events.py          The SSE bus — sessions, emit(), format_sse()
│       │       ├── 📄 state.py           RAGState + Document TypedDicts
│       │       └── 📄 workflow.py        build_graph() and the rag_graph singleton
│       │
│       ├── 📄 app.py                     The factory — CORS + blueprints. NO routes
│       ├── 📄 config.py                  One Config class, resolved once at import
│       └── 📄 main.py                    Entry point — main() backs adrag-dev
│
├── 📄 .env.example                       Env template — the storage block ships commented
├── 📄 pyproject.toml                     THE MANIFEST — deps, extras, script, packaging
├── 📄 README.md                          Backend front door
└── 📄 requirements.txt                   A `-e .` pointer, nothing more
```

**Two placement rules govern this tree.** A **route** is something the router points at — it gets its
own folder under `routes/`, with `<resource>_routes.py` inside and a `services.py` beside it once there
is real work to hold. A **capability** is something nothing routes to — it lives under
`custom_packages/` and never imports upward into `routes/` or `app.py`.

<br>

---

<br>

## 🧩 5. WHERE A NEW FILE GOES

| Adding… | Goes to |
|---|---|
| an **HTTP route** | `routes/<resource>/<resource>_routes.py`, plus one import and one entry in `routes/__init__.py`'s `BLUEPRINTS`. Nothing in `app.py` changes |
| **work behind a route** | that resource's `services.py` — the routes do framing, the service owns the ordering |
| a **pipeline node** | `custom_packages/rag_pipeline/<phase>/<name>.py`, then register it in `workflow.py` |
| a **retrieval backend** | `custom_packages/rag_pipeline/retrieval/stores/<name>_store.py`, plus a module-level singleton and one more list on the state before the aggregator |
| a **setting** | a `Config` attribute **and** a documented line in `.env.example` |

Every node is `def <name>_node(state: RAGState) -> dict` and returns **only the keys it modifies**. Its
module docstring ends with an `Emits:` line naming the events it produces — never add a node without
one, because that line is the only place the event surface is written down beside the code.

> [!WARNING]
> **A new store's shape decides whether it drops in.** The three existing stores do *not* share one
> interface: the graph store indexes one chunk per call and reports `get_stats()` where the others take
> a batch and report `count()`, so the ingest path special-cases it. Copy the BM25 store's shape and
> the existing call sites accept it unchanged; copy the graph store's and they will not.
> [`hybrid-retrieval/stores.md`](hybrid-retrieval/stores.md) has the full method matrix.

<br>

---

<br>

## ⚠️ 6. KNOWN GAPS

- **No test framework.** No runner in [`../pyproject.toml`](../pyproject.toml), no `tests/`, no CI.
  `infra/smoke.py` is a dev tool covering four of the eight routes and asserting key *presence*, never
  values. **No page here describes this project as tested.**
- **No `LICENSE`** at the repository root, so the terms are formally undefined.
- **The security defaults are localhost-only and deliberate** — no authentication on any route, a CORS
  allowlist ending in a literal `"*"`, `FLASK_DEBUG` defaulting to `true`, unescaped prompt
  interpolation, and an unsanitised markdown render on the client. Every one is documented rather than
  hidden; [`security.md`](security.md) carries the trust-boundary model, the measurements, and an
  ordered checklist of what to close first.

Per-subsystem limitations — the silent pickle resets, the corrupt-registry path, the FAISS-only delete
bug, the quadratic graph writes — are documented on the page that owns them rather than collected here,
so they stay next to the mechanism that causes them.

<br>

---

<br>

## 🔗 7. RELATED READING

| Destination | Why |
|---|---|
| [`../README.md`](../README.md) | The backend front door — install, run, layout, at a glance |
| [`../../README.md`](../../README.md) | The project front door — the RAG system explained, both halves, getting started |
| [`../../Frontend/Documentation/README.md`](../../Frontend/Documentation/README.md) | The other half: the three Pinia stores, the API clients, and the tracker that consumes this API's stream |
| [`../.env.example`](../.env.example) | The annotated environment template these pages describe |
| [`../pyproject.toml`](../pyproject.toml) | The manifest — dependencies, the two extras, the `adrag-dev` script |

<br>
