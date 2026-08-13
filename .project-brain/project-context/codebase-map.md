# Codebase map

Where everything lives. Derived from the filesystem; generated, vendored, and gitignored paths are
excluded.

<br>

## Repository root

```
Advanced RAG System/
│
├── 📁 Backend/               Python — Flask API + the RAG pipeline package
├── 📁 Frontend/              JavaScript — Vue 3 single-page app
│
├── 📁 .project-brain/        This brain (junction to the Claude Home folder)
├── 📁 .claude/               ClaudeSH kit — agents, skills, hooks, policies (gitignored)
├── 📁 .readme-lib/           Doc assets — the CLAUDE.md icon + the README diagram sources/SVGs
│
├── 📄 dev.py                 Dev launcher — picks both ports, spawns both halves, tears both down
├── 📄 README.md              Human front door for the repository
└── 📄 .gitignore             One shared ignore file for both halves
```

There is no root `package.json`, `pyproject.toml`, `Makefile`, `Dockerfile`, or CI configuration — the two
halves are still installed and built independently. The one root-level script is `dev.py`, a developer
launcher that runs both halves together without coupling their builds; its contract and the alternatives
rejected are recorded in
[ADR-006](../decisions/ADRs/entries/006-dev-launcher-env-injected-ports.md).

The working tree **is** a git repository — branch `feature`, remote `origin` →
`git@github.com:Shohrab-Hossain/Advanced-RAG-System.git`, 74 tracked files.

<br>

## `Backend/`

```
Backend/
│
├── 📁 documentation/         Human engineering docs (separate layer — read, never link)
│   ├── 📄 api.md              Endpoints + SSE reference
│   ├── 📄 architecture.md     Config, persistence, ingestion, LLM layer
│   ├── 📄 rag-pipeline.md     Every node, store, and the retry loop
│   └── 📄 README.md           Setup + project structure
│
├── 📁 src/
│   ├── 📁 data/               Runtime stores + uploads — created at import (see the note below)
│   ├── 📁 rag_pipeline/       The pipeline package (below)
│   ├── 📄 app.py              create_app() — CORS + 8 routes + module-level `app`
│   ├── 📄 config.py           class Config — every env var, read at import
│   └── 📄 main.py             Entry point: quiet the loggers, app.run(threaded=True)
│
├── 📄 .env.example           Every backend variable, documented
├── 📄 requirements.txt       Pinned dependency floors
└── 📄 README.md              Quick start, stack, env table
```

### `Backend/src/rag_pipeline/`

```
rag_pipeline/
│
├── 📁 core/
│   └── 📄 events.py           SSE event bus: session_id → queue.Queue
│
├── 📁 encoding/
│   ├── 📄 embeddings.py       get_embedder() — one shared SentenceTransformer
│   └── 📄 llm.py              get_llm() + cache, safe_json_parse(), check_ollama()
│
├── 📁 generation/
│   ├── 📄 compressor.py       Node 6 — conditional LLM context compression
│   ├── 📄 planner.py          Node 1 — Self-RAG retrieve/external/type decision
│   ├── 📄 reasoning.py        Node 7 — cited answer generation
│   └── 📄 reflection.py       Node 8 — grounding verdict, retry, escalation
│
├── 📁 ingestion/
│   ├── 📄 loader.py           load_file(), chunking, file hashing, chunk ids
│   └── 📄 registry.py         kb_registry.json — register/get/list/remove/clear
│
├── 📁 ranking/
│   ├── 📄 aggregator.py       Node 4 — dedup by content MD5
│   └── 📄 reranker.py         Node 5 — CrossEncoder top-k
│
├── 📁 retrieval/
│   ├── 📁 graph/
│   │   └── 📄 graph_store.py   NetworkX entity graph + 2-hop search
│   ├── 📁 keyword/
│   │   └── 📄 bm25_store.py    BM25Okapi corpus + pickle persistence
│   ├── 📁 vector/
│   │   └── 📄 vector_store.py  ChromaVectorStore | FaissVectorStore
│   ├── 📄 node.py             Node 2 — fan-out to the three stores
│   └── 📄 web_node.py         Node 3 — DuckDuckGo external tools
│
├── 📄 graph.py               StateGraph assembly, routing fns, `rag_graph`
└── 📄 state.py               RAGState + Document TypedDicts
```

Every package has an `__init__.py`.

> [!IMPORTANT]
> **Runtime data lands in `Backend/src/data/`, not `Backend/data/` — and it is not ignored.**
> `Config.DATA_ROOT` is the relative literal `"./data"` (`config.py:44`), resolved against the **process
> working directory**, and the backend runs from `Backend/src`. `.gitignore:29-30` ignore
> `Backend/data/databases/` and `Backend/data/uploads/`, which match nothing — `Backend/data/` does not
> exist. The consequence is live:
> `Backend/src/data/databases/vector_db/chroma_db/chroma.sqlite3` is **tracked in git** and grows with
> every ingest. Why the directory is chosen at import time, and what `dev.py` does about it, is in
> [`runtime/backend-startup/`](runtime/backend-startup/README.md).

<br>

## `Frontend/`

```
Frontend/
│
├── 📁 documentation/         Human engineering docs (separate layer — read, never link)
│   ├── 📄 components.md       Every component — props, emits, behaviour
│   ├── 📄 state.md            Stores, API service, SSE, history
│   └── 📄 README.md           Views, structure, setup
│
├── 📁 public/
│   └── 📄 index.html          Title/meta/OG tags, Google Fonts links, #app mount
│
├── 📁 src/
│   ├── 📁 assets/
│   │   └── 📄 main.css         Tailwind entry + .card/.btn-*/.prose-rag layers
│   │
│   ├── 📁 components/          12 components (PipelineTracker, StageRow,
│   │                           ResultDisplay, SourceCard, LLMSelector…)
│   │
│   ├── 📁 router/
│   │   └── 📄 index.js         4 lazy routes, HTML5 history mode
│   │
│   ├── 📁 services/
│   │   └── 📄 api.js           All HTTP calls + the SSE stream reader
│   │
│   ├── 📁 stores/
│   │   ├── 📄 rag.js           STAGES, query lifecycle, index, result, history
│   │   └── 📄 ui.js            Theme + promise-based modal
│   │
│   ├── 📁 views/               HomeView, ChatView, KnowledgeBaseView, ConfigView
│   │
│   ├── 📄 App.vue             Shell: NavBar + RouterView transition + ModalDialog
│   └── 📄 main.js             createApp → Pinia → router → mount
│
├── 📄 .env.example           VUE_APP_API_URL=http://localhost:5001
├── 📄 package.json           Scripts + dependencies (name: rag-frontend, v1.0.0)
├── 📄 postcss.config.js      tailwindcss + autoprefixer
├── 📄 tailwind.config.js     darkMode class, warm palette, fonts, animations
├── 📄 vue.config.js          devServer port 8080 + /api proxy → `DEV_API_TARGET`, fallback :5000
└── 📄 README.md              Quick start, stack, docs index
```

<br>

## Quick lookup

| Looking for… | Go to |
|---|---|
| An HTTP route | `Backend/src/app.py` |
| The pipeline's shape or routing | `Backend/src/rag_pipeline/graph.py` |
| What a node does | `Backend/src/rag_pipeline/{generation,retrieval,ranking}/<name>.py` |
| A setting or default | `Backend/src/config.py` (plus the `os.getenv` reads in node modules) |
| How a store persists | `Backend/src/rag_pipeline/retrieval/<kind>/*_store.py` |
| The SSE event contract | `Backend/src/rag_pipeline/core/events.py` (producer) + `Frontend/src/services/api.js` (consumer) |
| Client state or the stage list | `Frontend/src/stores/rag.js` |
| A design token | `Frontend/tailwind.config.js` + `Frontend/src/assets/main.css` |
| A page | `Frontend/src/views/<Name>View.vue` |
| How dev ports are chosen and injected | `dev.py` (repository root) + `Frontend/vue.config.js` |
