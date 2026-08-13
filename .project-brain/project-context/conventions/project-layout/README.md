# Project layout rules

Where a new file goes, and the layering that must not be broken.

<br>

## Top level

```
Advanced RAG System/
├── Backend/     Python: Flask API + rag_pipeline package + its own documentation/
├── Frontend/    JavaScript: Vue 3 SPA + its own documentation/
├── dev.py       Root dev launcher — starts, wires, and tears down both halves
├── README.md    Human front door
├── .readme-lib/ Doc assets — diagram sources + rendered SVGs
└── .gitignore   One shared ignore file for both sides
```

The two halves remain independent projects that share only the HTTP contract. There is no root
`package.json`, no monorepo tool, no workspace config — each is still installed and built from its own
folder. `dev.py` does not change that: it *runs* both together without coupling their builds, and each half
still starts standalone. Each half owns its own `README.md` and `documentation/` folder.

**Where a root-level dev script goes:** flat at the repository root, as a single file — it belongs to
neither half, so it lives above both. It must be runnable **before** either half is installed: `dev.py`
resolves the backend interpreter itself (`Backend/.venv` → `venv` → `env`, else `sys.executable` with a
warning — `dev.py:92-100`) and locates `npm` via `shutil.which` (`dev.py:103-108`), rather than assuming
an environment. Hold any future sibling tool to the same rule, or it stops working at the moment it is
needed most.

<br>

## Backend — where a new file goes

`Backend/src/` is the import root, so a module refers to `config` and `rag_pipeline` as top-level names.
It is the import root because **`sys.path[0]` is the directory of the script being run** — `main.py` lives
in `src/`, so `src/` is on the path whatever the working directory is. The working directory is a separate
concern entirely: it decides `DATA_ROOT`, and it must be `Backend/src` for that reason (see
[`../../runtime/backend-startup/README.md`](../../runtime/backend-startup/README.md)). Do not conflate the
two — a module placed outside `src/` breaks imports no matter where you start the process, and starting
from the wrong directory breaks the data path without touching imports.

| Adding… | Goes in |
|---|---|
| A new pipeline node | `rag_pipeline/<phase>/<name>.py` where `<phase>` is `generation/`, `retrieval/`, or `ranking/`; then register it in `graph.py` |
| A new retrieval backend | `rag_pipeline/retrieval/<kind>/<name>_store.py`, matching the existing store surface (`add_documents`, `search`, `delete_by_file`, `count`/`get_stats`, `clear`) and exposing a module-level singleton |
| A new HTTP route | `app.py` inside `create_app()` — all routes live in that one factory |
| A new setting | `config.py` as a `Config` class attribute **and** a documented line in `.env.example` |
| A shared helper | `rag_pipeline/core/` for cross-cutting infrastructure, `rag_pipeline/encoding/` for model construction |

Layering rules that hold today and should keep holding:

- **`rag_pipeline/` never imports from `app.py`.** The dependency runs one way: routes → pipeline.
- **Nodes never touch Flask.** They receive `RAGState` and emit events; HTTP framing is `app.py`'s job.
- **Stores never import nodes.** Nodes import stores.
- **Only `config.py` and the store/node module constants read the environment.** A new setting gets a
  `Config` attribute; prefer reading it from `Config` rather than repeating an `os.getenv` default (the
  existing duplication for the top-k and retry knobs is a wart, not a pattern to copy).

<br>

## Frontend — where a new file goes

| Adding… | Goes in |
|---|---|
| A new page | `src/views/<Name>View.vue` + a lazily-imported entry in `src/router/index.js` |
| A reusable UI piece | `src/components/<Name>.vue` — flat, no sub-folders |
| A new API call | `src/services/api.js` as an exported function returning `data` |
| New shared state | an existing store in `src/stores/` — `rag.js` for anything about documents/queries/results, `ui.js` for presentation concerns |
| A shared style pattern | `@layer components` in `src/assets/main.css`, not a `<style>` block |
| A design token | `tailwind.config.js` under `theme.extend` |

Layering rules:

- **Components do not call `services/api.js`** — they call store actions. (`NavBar.vue`'s `healthCheck`
  import is the one accepted exception.)
- **`services/api.js` holds no state**; it only shapes requests and responses.
- **`stores/ui.js` knows nothing about RAG**; keep presentation concerns (theme, modal) out of `rag.js`.
- **No component-scoped CSS.** Styling is Tailwind utilities plus the shared component layer.

<br>

## Naming

| Kind | Convention | Example |
|---|---|---|
| Python module | `snake_case.py` | `vector_store.py` |
| Store module | `<kind>_store.py` inside `retrieval/<kind>/` | `keyword/bm25_store.py` |
| Node module | named for the role, not the phase | `planner.py`, `reranker.py`, `reflection.py` |
| Vue component | `PascalCase.vue` | `PipelineTracker.vue` |
| Vue view | `PascalCaseView.vue` | `KnowledgeBaseView.vue` |
| Pinia store | lowercase file, `use<Name>Store` export | `rag.js` → `useRagStore` |
| Route path | kebab-case | `/knowledge-base` |
| API path | kebab-case under `/api/` | `/api/knowledge-bases` |
| Env var | `UPPER_SNAKE`. On the frontend the prefix is a **visibility marker**, not decoration — see below | `RETRIEVAL_TOP_K`, `VUE_APP_API_URL`, `DEV_API_TARGET` |
| SSE stage id | `snake_case`, matching the node name | `external_tools` |

**The `VUE_APP_` prefix means "compiled into the browser bundle".** Vue CLI inlines every `VUE_APP_*`
variable at build time, so the prefix is a declaration that the value is public and permanent for that
build — `VUE_APP_API_URL` (`services/api.js:12`) is one. A frontend-side variable that must **not** reach
the client is deliberately left **unprefixed**: `DEV_API_TARGET` is read by `vue.config.js:12` in the Node
dev-server process, never by the app, and `dev.py:243` sets it per-run. Choose the prefix by where the
value is consumed, not by which half of the repo the file sits in.

<br>

## Ignored paths

From the root `.gitignore` — these are runtime state, never source: `node_modules/`, `Frontend/dist/`,
`.env` and `*.env` (but **not** `.env.example`), virtualenvs (`my_venv/`, `venv/`, `.venv/`, `env/`),
`__pycache__/`, build artifacts, IDE folders, and `.claude`.

> [!WARNING]
> **The two data ignores do not work.** `.gitignore:29-30` list `Backend/data/databases/` and
> `Backend/data/uploads/`, but `DATA_ROOT` is CWD-relative (`config.py:44`) and the backend runs from
> `Backend/src`, so the real tree is `Backend/src/data/` — unignored, and partially **tracked**
> (`chroma.sqlite3`). `Backend/data/` does not exist. Ignore `Backend/src/data/` instead, and untrack what
> is already committed.
