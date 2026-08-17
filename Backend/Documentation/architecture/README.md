<div align="center">

# 🧱 Backend Architecture

### Four layers, one process, exactly one worker — and an import that writes to disk before a single request arrives.

<br>

[![Layers](https://img.shields.io/badge/layers-4-1c7ed6)](#-1-the-four-layers)
[![Workers](https://img.shields.io/badge/workers-exactly%201-ef4444)](#-4-the-process-model)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Cold boot](https://img.shields.io/badge/cold%20boot-60.89s-f59e0b)](#34-the-measured-cost-and-the-three-choices-it-explains)
[![Package](https://img.shields.io/badge/import%20root-adrag-7c5cff)](#-2-the-module-map)
[![Tooling](https://img.shields.io/badge/infra-dev.py%20%C2%B7%20smoke.py-7c5cff)](#-5-the-infra-tooling)

</div>

<br>

---

<br>

## Content Tree

<pre>
Backend Architecture
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-four-layers">🧱 1. The four layers</a>
│   ├── <a href="#11-who-knows-about-whom">1.1 Who knows about whom</a>
│   ├── <a href="#12-the-four-invariants-and-the-grep-that-proves-each">1.2 The four invariants, and the grep that proves each</a>
│   ├── <a href="#13-the-one-accepted-exception">1.3 The one accepted exception</a>
│   └── <a href="#14-absolute-versus-relative-imports">1.4 Absolute versus relative imports</a>
│
├── <a href="#-2-the-module-map">📂 2. The module map</a>
│
├── <a href="#-3-boot">🚀 3. Boot</a>
│   ├── <a href="#31-the-import-chain">3.1 The import chain</a>
│   ├── <a href="#32-importing-the-package-writes-to-disk">3.2 Importing the package writes to disk</a>
│   ├── <a href="#33-what-create_app-actually-does">3.3 What create_app() actually does</a>
│   └── <a href="#34-the-measured-cost-and-the-three-choices-it-explains">3.4 The measured cost, and the three choices it explains</a>
│
├── <a href="#-4-the-process-model">🧵 4. The process model</a>
│   ├── <a href="#41-two-supported-ways-to-run-one-process">4.1 Two supported ways to run one process</a>
│   ├── <a href="#42-why-exactly-one-worker">4.2 Why exactly one worker</a>
│   ├── <a href="#43-three-kinds-of-thread">4.3 Three kinds of thread</a>
│   └── <a href="#44-the-reloader-and-flask_debugs-two-jobs">4.4 The reloader, and FLASK_DEBUG's two jobs</a>
│
├── <a href="#-5-the-infra-tooling">🧰 5. The infra/ tooling</a>
│   ├── <a href="#51-devpy--the-dual-process-launcher">5.1 dev.py — the dual-process launcher</a>
│   ├── <a href="#52-port-probing">5.2 Port probing</a>
│   ├── <a href="#53-environment-injection-and-why-it-beats-env">5.3 Environment injection, and why it beats .env</a>
│   ├── <a href="#54-wiring-the-frontend-two-modes">5.4 Wiring the frontend, two modes</a>
│   ├── <a href="#55-readiness-interpreters-and-shutdown">5.5 Readiness, interpreters and shutdown</a>
│   └── <a href="#56-smokepy--a-dev-tool-and-it-says-so-itself">5.6 smoke.py — a dev tool, and it says so itself</a>
│
├── <a href="#-6-how-the-two-halves-connect">🔌 6. How the two halves connect</a>
│
├── <a href="#%EF%B8%8F-7-edge-cases--gotchas">⚠️ 7. Edge cases &amp; gotchas</a>
│
├── <a href="#-8-extension-points">🧩 8. Extension points</a>
│
└── <a href="#-9-related-reading">🔗 9. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

The backend is one Flask application wrapped around one LangGraph pipeline, and it runs in **one
process**. That is not a simplification for the sake of a diagram — it is a correctness constraint that
shows up in the deployment command as a literal `-w 1`, and §4.2 explains why breaking it produces an
empty SSE stream and two divergent copies of the corpus.

Everything is organised into four layers with a single import direction: an entry point imports a
factory, the factory imports a tuple of blueprints, the blueprints import a capability package, and the
capability package imports nothing above itself. `app.py` is **61 lines and carries zero route
decorators** — every route lives in its own resource folder, and the factory only iterates a tuple.

```python
# adrag/app.py:51
for blueprint in BLUEPRINTS:
    app.register_blueprint(blueprint)
```

> [!IMPORTANT]
> **Importing this package is not free and is not side-effect-free.** `import adrag.app` creates four
> directories, opens a Chroma client, unpickles two stores, and loads `sentence_transformers` —
> **measured at 60.89 seconds on a cold filesystem** and roughly ten warm. That single fact explains the
> 240-second health timeout in `infra/dev.py`, why `GET /api/health` is deliberately shallow, and why a
> `--no-reload` flag exists at all (§3.4).

---

## 🧱 1. THE FOUR LAYERS

### 1.1 Who knows about whom

Paths below are relative to the package root, `Backend/src/adrag/`.

| Layer | Directory | Knows about | Is known by |
|---|---|---|---|
| **Entry** | `main.py` | `app.py`, `config.py` | nothing |
| **Factory** | `app.py` | `config.py`, `routes/` (as one tuple) | `main.py`, gunicorn |
| **Routed** | `routes/<resource>/` | `config.py`, the pipeline package, its own `services.py` | `app.py`, via `BLUEPRINTS` |
| **Capability** | `custom_packages/rag_pipeline/` | `config.py`, third-party libraries | `routes/` |

The direction never reverses. A capability is something nothing routes to; the moment it needs an HTTP
verb, a blueprint under `routes/` grows to call it, and the capability itself stays unaware that HTTP
exists.

### 1.2 The four invariants, and the grep that proves each

These were verified by exhaustive search across `Backend/src/` rather than asserted from the design.

| # | Invariant | Verification | Result |
|---|---|---|---|
| 1 | **The pipeline never imports upward.** No file under `custom_packages/` imports Flask, `app.py` or `routes/`. | `grep -rn "^from flask\|^import flask\|from adrag.app\|adrag\.routes" custom_packages/` | **zero matches** |
| 2 | **`app.py` knows only two things.** Its whole import list is `os`, `Flask`, `CORS`, `adrag.config.Config`, `adrag.routes.BLUEPRINTS` (`app.py:22-28`). No store, no node, no service. | read + grep | confirmed |
| 3 | **Only `services.py` touches the stores.** `routes/knowledge_base/services.py:15-17` is the sole importer of `vector_store` / `bm25_store` / `graph_store` anywhere under `routes/`. | grep across `routes/` | confirmed |
| 4 | **Stores never import nodes.** The three store modules import stdlib, their backend library and `adrag.config.Config` only (`bm25_store.py:8-15`, `graph_store.py:9-17`, `vector_store.py:8-14`); `vector_store.py:14` adds `...models.embeddings`. | grep | confirmed |

Invariant 1 is the load-bearing one. It is what lets the eight pipeline nodes run on a background thread
with no request context, and it is why progress reporting had to become a queue (`emit()`) rather than a
direct write to a response — see [`../sse-event-bus/README.md`](../sse-event-bus/README.md).

### 1.3 The one accepted exception

`routes/knowledge_base/knowledge_base_routes.py:20` imports the registry module directly and calls
`kb_registry.get(file_hash)` at `:92`. It needs the stored filename **before** it deletes the knowledge
base that names it, and a service call would have returned after the record was gone.

**It is a read, and every write still goes through `services`.** The route-versus-service split and the
reasoning behind that one exception are documented in
[`../api/README.md`](../api/README.md#-3-route-versus-service).

### 1.4 Absolute versus relative imports

The tree follows one rule consistently, and it is worth knowing which side of the boundary you are on
before adding a file:

- **Across the package boundary → absolute.** `from adrag.config import Config` appears exactly four
  times inside the pipeline package: `ingestion/registry.py:13`,
  `retrieval/stores/bm25_store.py:15`, `graph_store.py:17`, `vector_store.py:13`. Those are the only
  absolute imports in there.
- **Within the pipeline → relative.** `workflow.py:23-31` pulls all eight node functions in as
  `from .generation.planner import planner_node` and siblings; `vector_store.py:14` reaches back up with
  `from ...models.embeddings import get_embedder`.
- **Everything under `routes/` is absolute `adrag.…`** — `routes/__init__.py:10-13`,
  `query_routes.py:16-22`, `services.py:14-19`.

**Why it matters:** `Backend/src/` is a *src-layout* package (`pyproject.toml:75-76`, `where = ["src"]`),
so the name `adrag` does not exist until `pip install -e .` has run. Nothing works from a bare checkout,
and `infra/dev.py:124-126` probes for exactly that failure with `python -c "import adrag, flask"` so the
error arrives as an actionable message rather than a buried traceback.

---

## 📂 2. THE MODULE MAP

Re-derived from the live filesystem. The pipeline package is **25 Python files and about 1 900 lines**;
`adrag/` proper adds fourteen more, counting every `.py` outside `custom_packages/` — the eight modules
named below plus the six `__init__.py` files that make the package and its route folders importable.

```text
Backend/
├── 📄 pyproject.toml            THE MANIFEST — deps, the two extras, adrag-dev, src-layout packaging
├── 📄 requirements.txt          a one-line `-e .` pointer, nothing more
├── 📄 .env.example              66 lines, 6 sections — the storage block ships commented out
├── 📁 data/                     RUNTIME STATE — gitignored (.gitignore:33-34); see storage-model.md
└── 📁 src/
    ├── 📁 adrag_backend.egg-info/   editable-install metadata; ignored by .gitignore:7
    └── 📁 adrag/                the package; the import root for every module
        ├── 📄 main.py           56 ln — entry point; main() backs the adrag-dev script
        ├── 📄 app.py            61 ln — the factory: CORS + blueprint loop. ZERO route decorators
        ├── 📄 config.py         77 ln — one Config class, evaluated once at import
        ├── 📁 routes/           the ROUTED layer — one folder per resource
        │   ├── 📄 __init__.py   exports BLUEPRINTS — the one tuple create_app() iterates
        │   ├── 📁 query/        query_routes.py            123 ln — POST /api/query (SSE)
        │   ├── 📁 knowledge_base/  knowledge_base_routes.py 96 ln + services.py 114 ln
        │   ├── 📁 provider/     provider_routes.py          50 ln — GET /api/providers
        │   └── 📁 health_check/ health_check_routes.py      19 ln — GET /api/health
        └── 📁 custom_packages/  capabilities nothing routes to
            └── 📁 rag_pipeline/ 25 files · ~1 900 lines
                ├── 📄 workflow.py   107 ln — build_graph() + the rag_graph singleton
                ├── 📄 state.py       59 ln — RAGState + Document TypedDicts
                ├── 📄 events.py      50 ln — the SSE bus: _sessions, emit(), format_sse()
                ├── 📁 generation/    planner 90 · compressor 95 · reasoning 115 · reflection 181
                ├── 📁 ingestion/     loader 116 · registry 87
                ├── 📁 models/        llm 136 · embeddings 21
                ├── 📁 ranking/       aggregator 60 · reranker 75
                └── 📁 retrieval/     hybrid_node 61 · web_node 75
                    └── 📁 stores/    vector 253 · bm25 114 · graph 185
```

Two entries in that tree are easy to misread:

- **`custom_packages/` is not a vendor directory.** It holds first-party capabilities that no route
  points at directly. `rag_pipeline/` is the only occupant today.
- **`retrieval/stores/` is flat on purpose.** The per-kind folders `retrieval/vector/`,
  `retrieval/keyword/` and `retrieval/graph/` were retired in the package refactor; a new backend goes in
  `retrieval/stores/<name>_store.py` and nowhere else. The retrieval *node* is `retrieval/hybrid_node.py`.

The `infra/` folder sits at the **repo root**, not under `Backend/` — it drives both halves, so it
belongs to neither (§5).

---

## 🚀 3. BOOT

### 3.1 The import chain

```text
adrag-dev  /  python -m adrag.main   (or gunicorn adrag.app:app)
  └─ main.py:35   from adrag.app import app
       └─ app.py:27   from adrag.config import Config   ← load_dotenv(Backend/.env); all 29 attrs resolved
       └─ app.py:28   from adrag.routes import BLUEPRINTS
            ├─ routes/__init__.py:10  query_routes
            │    └─ rag_pipeline/workflow.py → all 8 nodes → retrieval/stores/*
            │                                → sentence_transformers, chromadb
            ├─ routes/__init__.py:11  knowledge_base_routes → services.py → the three stores (cached)
            ├─ routes/__init__.py:12  provider_routes       → rag_pipeline/models/llm.check_ollama
            └─ routes/__init__.py:13  health_check_routes   → Flask only
       └─ app.py:61   app = create_app()   ← module scope: runs at import, not at first request
```

**Config resolves first, and it resolves against the package rather than the shell.** `config.py:12-17`
computes `_BACKEND_ROOT` from `__file__` (`adrag/` → `src/` → `Backend/`), loads `Backend/.env` from
there, and defaults every data path against it — so **where you started the process no longer decides
where the databases land.** All 29 attributes are evaluated once, at import, and never re-read
([`storage-model.md`](storage-model.md#-1-anchoring--the-bug-this-design-prevents)).

**`app = create_app()` at module scope is deliberate**, and the comment at `app.py:57-59` says so:
`main.py` imports the object and the gunicorn command names it directly as `adrag.app:app`. There is
**no `__main__` block in `app.py`** — `main.py` is the one entry point.

### 3.2 Importing the package writes to disk

Five side effects fire during import, before any request exists:

| # | Effect | Where |
|---|---|---|
| 1 | `os.makedirs(Config.VECTOR_ROOT, exist_ok=True)` at module scope | `vector_store.py:18` |
| 2 | `ChromaVectorStore()` constructed at module scope → `os.makedirs(CHROMA_PATH)` + `chromadb.PersistentClient` + `get_or_create_collection` | `vector_store.py:253` → `:49-55` |
| 3 | `BM25Store()` constructed → `os.makedirs(dirname(BM25_PATH))` + `_load()` unpickles the corpus | `bm25_store.py:114` → `:32-36` |
| 4 | `GraphStore()` constructed → `os.makedirs(dirname(GRAPH_PATH))` + `_load()` unpickles the graph | `graph_store.py:185` → `:41-44` |
| 5 | `os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)` inside the factory | `app.py:49` |

There is also a **legacy migration at import**: `registry.py:18-21` moves `./data/kb_registry.json` to
the configured registry path when the old path exists and the new one does not. It is resolved against
the *process working directory*, making it the last cwd-dependent behaviour in the backend — see
[`storage-model.md`](storage-model.md#-1-anchoring--the-bug-this-design-prevents).

> [!WARNING]
> **`VECTOR_BACKEND=faiss` without `faiss-cpu` installed raises `RuntimeError` at import**
> (`vector_store.py:23-28`). **The application fails to start; it does not fall back to Chroma and it
> does not degrade.** Install the extra first: `pip install -e ".[faiss]"`.

### 3.3 What `create_app()` actually does

Four steps, `app.py:33-54`:

```python
app = Flask(__name__)
app.config.from_object(Config)                     # :35
CORS(app, resources={r"/api/*": {...}})            # :37-47
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)   # :49
for blueprint in BLUEPRINTS:                       # :51-52
    app.register_blueprint(blueprint)
return app
```

Measured on the built application object:

| Probe | Result |
|---|---|
| `app.url_map` rule count | **9** — the eight `/api/*` routes plus Flask's implicit `/static/<path:filename>` |
| `app.blueprints` | `['health_check', 'knowledge_base', 'provider', 'query']` |
| `app.config["MAX_CONTENT_LENGTH"]` | `52428800` — `from_object` really does arm Flask's 50 MB body limit |
| `app.config["SECRET_KEY"]` | `None` — never set; nothing uses sessions or flashing |
| `app.error_handler_spec` | **`defaultdict(<lambda>, {})` — completely empty.** No error handler of any kind is registered. |

That last row matters beyond curiosity: it is the reason `404`, `405`, `413` and `500` come back as
Werkzeug **HTML**, not as the JSON `{"error": …}` envelope the application's own failures use. The
measured bodies and the consequence are in [`../security.md`](../security.md#-5-the-error-contract).

### 3.4 The measured cost, and the three choices it explains

| Measurement | Result |
|---|---|
| `import adrag.config` | **0.06 s** |
| `import adrag.app`, cold filesystem | **60.89 s** |
| `import sentence_transformers` alone, warm | **7.09 s** (it pulls in `torch` and `transformers`) |
| `import chromadb` alone, warm | 0.69 s |
| `import langgraph.graph` alone, warm | 0.78 s |
| `import adrag.app`, warm, with the three above cached | **0.91 s** |

**The whole of the backend's own code imports in under a second.** Everything else is third-party model
tooling — and it lands at import time only because `models/embeddings.py:9` imports `SentenceTransformer`
at module scope, unlike `ranking/reranker.py:23-31`, which defers `CrossEncoder` into a function.

Three design choices follow directly from that number, and each looks arbitrary until you know it:

1. **`infra/dev.py` allows 240 seconds for the health check.** `HEALTH_TIMEOUT = 240` at `dev.py:46`,
   with the comment *"Boot is slow: sentence-transformers and chroma load their models on import."*
2. **`GET /api/health` is deliberately shallow** — one hardcoded string, no dependency probe. Its own
   docstring (`health_check_routes.py:5-7`) says `infra/dev.py` polls it *while the embedding and
   reranker models are still loading*, so it must answer before the pipeline is usable. **It is a
   liveness check and must never become a readiness check.**
3. **`python infra/dev.py --no-reload` exists** because Flask's reloader forks a child and **both
   processes pay the import cost.** The flag's own help text: *"models load once instead of twice"*
   (`dev.py:233-234`).

---

## 🧵 4. THE PROCESS MODEL

### 4.1 Two supported ways to run one process

| | Development | Production |
|---|---|---|
| Command | `adrag-dev` · `python -m adrag.main` · `python src/adrag/main.py` | `gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker --bind 0.0.0.0:5000 adrag.app:app` |
| Declared at | `pyproject.toml:69` — `adrag-dev = "adrag.main:main"` | `main.py:15-16`, in the module docstring |
| Server | Werkzeug — `app.run(debug=Config.DEBUG, host="0.0.0.0", port=Config.PORT, threaded=True)` (`main.py:47-52`) | gunicorn, **exactly one worker** |
| Extra deps | none beyond the base install | the **`prod`** extra: `gunicorn>=21.0.0`, `gevent-websocket>=0.10.1` (`pyproject.toml:65`) |

> [!IMPORTANT]
> **The production command does not run in this checkout yet.** `gunicorn` and `gevent-websocket` are
> **declared but not installed** in `Backend/.venv` — verified this run. Run
> `pip install -e ".[prod]"` before the documented command, or it fails at `gunicorn: command not found`.

### 4.2 Why exactly one worker

`-w 1` is a **correctness constraint, not a tuning choice**, and there are three independent reasons —
any one of which is sufficient:

1. **Session queues are process memory.** `_sessions` is a plain module-level dict (`events.py:15`).
   Fork, and the daemon thread producing events can land in one process while the SSE generator serving
   that same browser sits in another. The browser gets an empty stream that eventually times out.
2. **Every store is a module singleton** (`vector_store.py:250-253`, `bm25_store.py:114`,
   `graph_store.py:185`). Two workers hold divergent in-memory BM25 corpora and graphs, and each
   overwrites the other's pickle on the next write.
3. **The registry's lock is per-process** (`registry.py:22`). It protects nothing across a fork.

This is why development runs `threaded=True` rather than multi-process, and why the production recipe
spells `-w 1` out explicitly instead of relying on a default that could change.

**What *is* supported is concurrency across queries.** Each run gets its own `uuid4` session, its own
unbounded queue and its own daemon thread, and the three stores are read-only for the duration of a
query. Concurrent **ingest** is the unsafe operation — the stores are unsynchronised singletons with no
transaction between them ([`storage-model.md`](storage-model.md#-5-store-lifecycle)).

### 4.3 Three kinds of thread

| Thread | Created by | Lifetime | Purpose |
|---|---|---|---|
| The WSGI request thread | Werkzeug (`threaded=True`, `main.py:51`) or gunicorn | one request | runs the route — and for `/api/query`, runs the SSE generator |
| The pipeline daemon thread | `threading.Thread(target=_run, daemon=True).start()` (`query_routes.py:100`) | one query, **to completion regardless of the client** | runs `rag_graph.invoke()` and pushes events onto the queue |
| The registry lock's critical section | `registry.py:22`, held at `:43`, `:61`, `:67`, `:76`, `:86` | microseconds | the **only** explicit synchronisation anywhere in the backend |

`daemon=True` has a cost worth stating plainly: **a `Ctrl-C` mid-pipeline abandons the run.** Because
there is no transaction across the four write targets (`services.py:6-9`), an interrupted *ingest* can
leave the corpus inconsistent — a document present in two stores, missing from the third and absent from
the registry, with no UI path to remove it.

### 4.4 The reloader, and `FLASK_DEBUG`'s two jobs

Traced through the installed Flask and Werkzeug this run:

- `Flask.run` does `options.setdefault("use_reloader", self.debug)` **and**
  `options.setdefault("use_debugger", self.debug)`.
- `main.py:48` passes `debug=Config.DEBUG`, and `Config.DEBUG` defaults to **`True`** (`config.py:76`,
  read from `FLASK_DEBUG`).

**So one setting turns on both the auto-reloader and the interactive debugger.** Two consequences:

- **The reloader forks a child that holds the port.** `infra/dev.py:181-187` documents exactly this —
  *"killing only the PID we spawned would leave the real server running and the port occupied"* — which
  is why its `_terminate` uses `taskkill /F /T` on Windows and `os.killpg` on POSIX.
- **`--no-reload` also turns the debugger off**, because it works by setting `FLASK_DEBUG=false`
  (`dev.py:274-275`). That makes it the only one-flag mitigation the repo ships for the debug-console
  exposure described in [`../security.md`](../security.md#-4-the-interactive-debugger-is-on).

---

## 🧰 5. THE `infra/` TOOLING

Two files at the repo root, no `__init__.py`, not a package. They are the pieces of this project most
often used and least often read, so this section is their reference.

```text
infra/
├── 📄 dev.py     321 ln — runs both halves: probes ports, wires the proxy, waits on /api/health
└── 📄 smoke.py    96 ln — drives four read-only routes through Flask's test client, in-process
```

### 5.1 `dev.py` — the dual-process launcher

Run it from the repo root:

```bash
python infra/dev.py
```

It starts the backend and the frontend, chooses each one's port at launch, points the frontend's dev
proxy at whichever port the backend actually got, waits until the API answers, and shuts both down the
moment either exits.

**The four flags — complete** (`dev.py:229-237`):

| Flag | Type | Default | Help text, verbatim |
|---|---|---|---|
| `--direct` | `store_true` | off | *"frontend calls the backend cross-origin instead of via the dev proxy"* |
| `--no-reload` | `store_true` | off | *"disable the Flask reloader — models load once instead of twice"* |
| `--api-port` | `int` | `None` → probe | *"pin the backend port"* |
| `--ui-port` | `int` | `None` → probe | *"pin the frontend port"* |

> [!NOTE]
> **The module docstring lists only three of them.** `dev.py:8-11` shows `--direct`, `--no-reload` and
> `--api-port`; `--ui-port` is missing from the prose but defined at `:236`. **The argparse definition is
> the contract** — the flag works.

### 5.2 Port probing

Bases are `API_PORT_BASE = 5000` and `UI_PORT_BASE = 8080`, scanning up to `PORT_SCAN_SPAN = 40`
candidates (`dev.py:37-42`). `_find_free_port` (`:72-91`) binds a socket to test each one and
**deliberately does not set `SO_REUSEADDR`** — the comment at `:76` is *"a port in TIME_WAIT is not free
enough."*

The base-and-walk-up strategy is explained at `:38-39`: *"a normal run keeps landing on the same port
(curl / Postman / bookmarks keep working) and only floats on collision."* A **pinned** port that looks
busy prints a warning and **starts anyway** (`_pick`, `:240-245`) — the assumption being that you pinned
it for a reason.

### 5.3 Environment injection, and why it beats `.env`

```python
# infra/dev.py:264
# config.py calls load_dotenv() with override=False, so what we set here
# wins over Backend/.env — no file needs editing.
api_env = {**os.environ, "PORT": str(api_port), "FRONTEND_URL": ui_url,
           "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
```

`PORT` and `FRONTEND_URL` are **exported into the child process environment**, and they win over
`Backend/.env` because `load_dotenv`'s `override` parameter defaults to `False` and `config.py:19` does
not pass it. The full precedence, top wins:

```text
process environment  →  Backend/.env  →  the literal default in config.py
```

That ordering is easy to get backwards, and getting it backwards makes `dev.py` look broken. It is the
same mechanism the OpenAI credential travels on — see
[`../configuration.md`](../configuration.md#11-precedence-top-wins).

### 5.4 Wiring the frontend, two modes

| Mode | Env set for the frontend | What the browser does |
|---|---|---|
| proxied (default) | `DEV_API_TARGET = http://localhost:<api_port>` | `Frontend/vue.config.js:19` targets it; calls stay **relative** because `VUE_APP_API_URL` is unset and both clients fall back to `''` (`ragApi.js:12`, `kbApi.js:11`) |
| `--direct` | also `VUE_APP_API_URL = http://localhost:<api_port>` | axios gets an absolute `baseURL`, so every call goes **cross-origin** — which is what actually exercises the CORS configuration |

`--direct` is therefore the mode to use when you want to test CORS behaviour rather than assume it.

> [!NOTE]
> **One comment in that block names a file that no longer exists.** `dev.py:279-280` says *"api.js falls
> back to `''`"*. There is no `services/api.js`; the two clients are `ragApi.js` and `kbApi.js`. The
> **behaviour** the comment describes is correct — only the filename is stale.

### 5.5 Readiness, interpreters and shutdown

- **Readiness** (`dev.py:210-224`) — a background thread polls
  `http://127.0.0.1:<api_port>/api/health` every `HEALTH_INTERVAL = 1.0` s for up to
  `HEALTH_TIMEOUT = 240` s, prints `backend healthy after <n>s`, and **warns rather than fails** if the
  deadline passes. The generous budget is the boot cost of §3.4.
- **Interpreter resolution** (`dev.py:94-137`) — prefers `Backend/{.venv,venv,env}` and picks
  `Scripts/python.exe` or `bin/python` by platform. A venv built for the *other* platform is reported
  explicitly (*"built for the other platform … you are running on Windows/POSIX"*), which is the
  WSL-against-a-Windows-venv case. `_check_backend_deps` runs `python -c "import adrag, flask"` and, on
  failure, prints the exact `cd Backend && python -m venv .venv && … && pip install -e .` fix.
- **Process management** (`dev.py:150-206`) — each child gets merged stdout/stderr pipes and a
  colour-prefixed pump thread (`[api]` cyan, `[ui]` magenta), spawned with `CREATE_NEW_PROCESS_GROUP` on
  Windows and `start_new_session` on POSIX. A supervisor loop shuts everything down the moment either
  child exits (`:304-309`). The backend is launched as `[python, "-m", "adrag.main"]` with
  `cwd=Backend/` (`:294`); the frontend as `npm run serve -- --port <ui_port>` with `cwd=Frontend/`
  (`:297`). `sys.stdout.reconfigure(encoding="utf-8")` at `:55-56` exists because *"Vue CLI emits
  box-drawing and ✔/✖ glyphs; a cp1252 console would mangle them."*

### 5.6 `smoke.py` — a dev tool, and it says so itself

```bash
Backend/.venv/Scripts/python infra/smoke.py     # or: python infra/smoke.py, with the venv on PATH
```

It builds the app through `create_app()`, drives Flask's **test client**, **binds no port and writes
nothing**, and holds four read-only routes to a `(method, path, status, required-keys)` contract
(`smoke.py:25-30`):

| Method | Path | Expects | Body keys asserted |
|---|---|---|---|
| `GET` | `/api/health` | `200` | `status` |
| `GET` | `/api/providers` | `200` | `providers`, `default` |
| `GET` | `/api/documents` | `200` | `vector_count`, `bm25_count`, `graph` |
| `GET` | `/api/knowledge-bases` | `200` | `knowledge_bases` |

It also prints `len(registered) - 1` route rules — the `-1` discounting Flask's `/static` rule, which is
how the nine rules of §3.3 report as eight. Exit `0` means all four passed; exit `1` names the first
failure.

Its own docstring explains why it exists (`smoke.py:9-13`): *"a file-existence check cannot prove that an
import chain resolves or that a blueprint is still registered, which is exactly what a large refactor
breaks."* It **deliberately excludes** `POST /api/query` and `POST /api/upload` — *"both would call an
LLM or mutate the index, and a check with side effects is one people stop running"* (`:15-16`).

> [!CAUTION]
> **`infra/smoke.py` is not a test suite, and this project is not tested.** Its docstring says so
> outright (`smoke.py:9-10`): *"This is a DEV TOOL, not a test suite — the project has no test framework
> and this does not pretend to be one."* It covers **four of the eight routes** and asserts key
> *presence*, never values. Run it after any structural change; do not report it as coverage.

---

## 🔌 6. HOW THE TWO HALVES CONNECT

Four ways a browser's `/api/*` call reaches Flask, all verified end to end:

| How you started it | Frontend origin | How `/api/*` resolves | Set by |
|---|---|---|---|
| `npm run serve` alone | `http://localhost:8080` | webpack dev-server proxies `/api` → `http://localhost:5000` | `vue.config.js:19`'s literal fallback |
| `python infra/dev.py` | `http://localhost:<probed 8080+>` | proxy → `http://localhost:<probed 5000+>` | `DEV_API_TARGET` (`dev.py:281`) |
| `python infra/dev.py --direct` | same | axios `baseURL` is the absolute API URL — **cross-origin, CORS engaged** | `VUE_APP_API_URL` (`dev.py:283`) |
| `npm run build` → static hosting | wherever `Frontend/dist/` is served | `VUE_APP_API_URL` is baked in **at build time** (Vue CLI only exposes `VUE_APP_`-prefixed vars); absent → relative, so the host must proxy | `ragApi.js:12`, `kbApi.js:11` |

`vue.config.js` also sets `changeOrigin: true` (`:20`) and `lintOnSave: 'warning'` (`:11`) — the latter
with a comment noting that a compile-blocking lint error *"takes the whole UI down while you are
working."*

**One contract crosses the boundary in the other direction**, and it is the easiest thing in this repo to
break silently: the SSE `stage` ids the backend emits must equal `STAGES` in
`Frontend/src/store/ragStore.js:16-25` exactly. **Five of the eight differ from their graph node name** —
the emitted set is `planner` · `retrieval` · `external_tools` · `aggregator` · `reranker` · `compressor`
· `reasoning` · `reflection`. Renaming a node breaks nothing; changing an `emit()` `stage` string stops
one tracker row updating, with no error anywhere. Never present node names as stage ids
([`../sse-event-bus/README.md`](../sse-event-bus/README.md#54-the-stage-id-contract)).

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **The app object exists before any server does.** `app = create_app()` runs at import (`app.py:61`),
  so merely importing `adrag.app` in a REPL creates directories, opens Chroma and loads models. There is
  no lazy path and no application-factory-per-test seam.

- **A bare checkout imports nothing.** `adrag` only exists after `pip install -e .` because `src/` is a
  src-layout root. `python src/adrag/main.py` happens to work from `Backend/`, but the supported entry
  points are `adrag-dev` and `python -m adrag.main`.

- **`main.py` binds `host="0.0.0.0"`** (`main.py:50`) — every interface, not loopback. Combined with the
  CORS and authentication posture in [`../security.md`](../security.md), that is the single most
  consequential default in the file.

- **The reloader doubles the boot cost and the memory.** Two processes each load
  `sentence_transformers` and open Chroma. On a slow machine the second load is the reason the first
  request seems to hang; `--no-reload` removes it.

- **`FLASK_DEBUG` is the variable name, not `DEBUG`.** `config.py:76` reads `FLASK_DEBUG`. Setting
  `DEBUG=false` in `.env` changes nothing.

- **`infra/` is not importable.** No `__init__.py`, and both files are scripts meant to be run by path.
  Nothing in `Backend/src/` imports either, and nothing should.

- **`src/adrag_backend.egg-info/` is generated, not authored.** It is editable-install metadata,
  ignored by `.gitignore:7`, and safe to delete — `pip install -e .` recreates it.

---

## 🧩 8. EXTENSION POINTS

**Add an HTTP resource.** Create `routes/<resource>/<resource>_routes.py` with its own `Blueprint`, add
one line to the `BLUEPRINTS` tuple in `routes/__init__.py`, and put the work in that folder's
`services.py`. `app.py` is not edited — the full recipe, including the no-`url_prefix` convention, is in
[`../api/README.md`](../api/README.md#-10-adding-a-resource).

**Add a pipeline node.** Write it under `custom_packages/rag_pipeline/<phase>/<name>.py` as
`def <name>_node(state: RAGState) -> dict`, returning only the keys it modifies, and register it in
`workflow.py`. Give its module docstring an `Emits:` line — that line is the only inventory of what a
node produces ([`../rag-pipeline/README.md`](../rag-pipeline/README.md#-9-extension-points)).

**Add a retrieval backend.** `retrieval/stores/<name>_store.py`, implementing the existing store surface
(`add_documents`, `search`, `delete_by_file`, a count accessor, `clear`, plus a module-level singleton),
then append its result list before the aggregator
([`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md#-9-extension-points)).

**Add a setting.** A `Config` attribute **and** a documented line in `.env.example` — both halves, or it
is undiscoverable ([`../configuration.md`](../configuration.md#-8-changing-a-setting-safely)).

**What not to touch.** Do not import Flask anywhere under `custom_packages/` — that inversion is what
the event bus exists to avoid. Do not add a route decorator to `app.py`. Do not run more than one worker
(§4.2). Do not make `/api/health` probe a dependency; `infra/dev.py` polls it during boot on purpose.

---

## 🔗 9. RELATED READING

- **Why the factory holds no routes.** Registration is a loop over a tuple, so adding a resource is a
  folder plus one line and never a merge conflict in `app.py`. The cost is one level of indirection
  between the URL and the handler, which `smoke.py` compensates for by asserting the rule count.
- **Why the pipeline is a package, not a service.** Keeping it in-process removes a broker, a
  serialisation format and a deployment target — appropriate for a single-machine tool, and the reason
  the one-worker rule exists at all.
- **Why boot is slow and nothing hides it.** Models load at import rather than on first use, so the
  first request is fast and the *startup* is honest about the cost. The health check is shaped around
  that trade.

**Continue reading:**

- [`query-lifecycle.md`](query-lifecycle.md) — one request from `POST` to rendered answer, across every layer
- [`storage-model.md`](storage-model.md) — what lands on disk, who writes it, and what survives a crash
- [`../api/README.md`](../api/README.md) — the eight routes, the registration recipe, CORS and the error contract
- [`../rag-pipeline/README.md`](../rag-pipeline/README.md) — the eight-node graph the routed layer calls
- [`../sse-event-bus/README.md`](../sse-event-bus/README.md) — `emit()`, the queues, and the 180-second bound
- [`../configuration.md`](../configuration.md) — every `Config` attribute and its real default
- [`../security.md`](../security.md) — the posture this process model creates, measured on the wire
- [`../../../Frontend/Documentation/README.md`](../../../Frontend/Documentation/README.md) — the other half of the system
