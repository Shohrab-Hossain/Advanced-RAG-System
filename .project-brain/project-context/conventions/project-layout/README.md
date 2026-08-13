# Project layout rules

Where a new file goes, and the layering that must not be broken.

<br>

## Top level

```
Advanced RAG System/
├── Backend/     Python: Flask API + rag_pipeline package + its own documentation/
├── Frontend/    JavaScript: Vue 3 SPA + its own Documentation/
├── dev.py       Root dev launcher — starts, wires, and tears down both halves
├── README.md    Human front door
├── .readme-lib/ Doc assets — diagram sources + rendered SVGs
└── .gitignore   One shared ignore file for both sides
```

The two halves remain independent projects that share only the HTTP contract. There is no root
`package.json`, no monorepo tool, no workspace config — each is still installed and built from its own
folder. `dev.py` does not change that: it *runs* both together without coupling their builds, and each half
still starts standalone. Each half owns its own `README.md` and its own docs folder — **`Backend/documentation/`
(lowercase) and `Frontend/Documentation/` (capital `D`)**. The casing genuinely differs on disk; match the
half you are in rather than normalising.

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

`Frontend/src/` is sorted by **ownership, not by kind**: a folder exists because something owns what is
inside it. There is no `components/`, `views/`, `services/`, or `stores/` bucket, and re-introducing one
re-opens the decision recorded in
[ADR-007](../../../decisions/ADRs/entries/007-ownership-based-frontend-tree.md). The question to answer
before creating any frontend file is therefore **"who owns this?"** — one page, one capability, or nobody.

| Adding… | Goes in |
|---|---|
| A new page | `src/pages/<page>/views/<Name>View.vue` + a lazily-imported entry in `src/router/index.js`. Give the page a `views/` folder **even for a single view** — every page has one, so a reader never has to know which kind of page it is before guessing where the view sits |
| A component owned by exactly one page | `src/pages/<page>/components/<Name>/<Name>.vue` |
| A component used by more than one page | `src/shared/components/<Name>/<Name>.vue` |
| A satellite used only by one component | inside that component's folder — `PipelineTracker/StageRow.vue`, `ResultDisplay/SourceCard.vue`. Do not promote it to `shared/` until a second owner actually exists |
| Pure logic pulled out of a `.vue` | a camelCase sibling module beside it — `<Name>.vue` → `<name>.js` (`chatView.js`, `knowledgeBaseView.js`, `chatHistorySidebar.js`) |
| Real CSS a component cannot express in Tailwind | a camelCase sibling `<name>.css`, attached as `<style scoped src="./<name>.css">` |
| A new API call | the owning subsystem's client — `src/subsystems/rag/ragApi.js` or `src/subsystems/knowledge-base/kbApi.js` — as an exported function returning `data` |
| New capability state | that capability's store — `src/subsystems/rag/ragStore.js` (provider, query, result, history) or `src/subsystems/knowledge-base/kbStore.js` (index stats, KB list, upload/indexing progress) |
| New state that **no** capability owns | `src/store/index.js` (the `'ui'` store — theme, global modal) |
| A whole new capability | `src/subsystems/<name>/` with a flat `<name>Store.js` + `<name>Api.js` pair inside |
| A shared style pattern | `@layer components` in `src/assets/main.css` |
| A design token | `tailwind.config.js` under `theme.extend` |

Layering rules:

- **Components do not call an API module** — they call store actions. (`NavBar.vue`'s `healthCheck` import
  from `subsystems/rag/ragApi` is the one accepted exception, `NavBar.vue:111`.)
- **An API module holds no state**; it only shapes requests and responses.
- **Subsystems never import each other.** `rag/` and `knowledge-base/` share nothing — not a store, not a
  client, not a helper. Where one screen needs both, the *component* imports both stores; there are exactly
  two such places (`ChatView.vue:118-119`, `NavBar.vue:108-111`), and a third is a signal that the boundary
  is drawn in the wrong place.
- **Each subsystem builds its own axios client** rather than importing a shared one, so
  `VUE_APP_API_URL` is read twice (`ragApi.js:12`, `kbApi.js:11`). Accepted duplication: it is what keeps
  the subsystems independent.
- **`store/` at the root means *state owned by no single capability*** — it is not "where stores go". Put
  capability state in that capability's subsystem, or the root store silently becomes the old global
  `rag.js` again.
- **A page-owned component never reaches back up into its page.** The view owns the data and hands each
  child a finished view-model; children are presentational and communicate upward by emitting. The rule is
  written into the source at `KnowledgeBaseView.vue:48-49`, and `IndexStats.vue` — which imports nothing at
  all — is the reference example.
- **Component-scoped CSS is allowed but rationed.** Tailwind utilities first, shared patterns promoted to
  `@layer components` in `src/assets/main.css`; a `<style scoped>` block only where neither can express the
  rule. Three exist (`ChatHistorySidebar.vue:132`, `ResultDisplay.vue:128`, `ModalDialog.vue:36`) — see
  [`../code-style/README.md`](../code-style/README.md) for the exact form.
- **There is no path alias.** No `@/` or equivalent is configured in `vue.config.js` or anywhere else, and
  every import is relative — the deepest is `../../../../` from
  `pages/<page>/components/<Name>/`. Do not introduce one file-by-file: either configure it globally and
  convert every import, or keep writing relative paths.

<br>

## Naming

| Kind | Convention | Example |
|---|---|---|
| Python module | `snake_case.py` | `vector_store.py` |
| Store module | `<kind>_store.py` inside `retrieval/<kind>/` | `keyword/bm25_store.py` |
| Node module | named for the role, not the phase | `planner.py`, `reranker.py`, `reflection.py` |
| Vue component | `PascalCase.vue`, inside a folder of the same name | `PipelineTracker/PipelineTracker.vue` |
| Vue view | `PascalCaseView.vue` | `KnowledgeBaseView.vue` |
| Pure-logic sibling | `camelCase.js` — the `.vue` name with a lowercase initial | `KnowledgeBaseView.vue` → `knowledgeBaseView.js` |
| Split CSS sibling | `camelCase.css` — same rule. **Never** `<name>.style.css` | `ChatHistorySidebar.vue` → `chatHistorySidebar.css` |
| Subsystem folder | kebab-case, matching its page folder when one exists | `subsystems/knowledge-base/` |
| Subsystem module | `<abbrev>Store.js` / `<abbrev>Api.js`, flat inside the subsystem | `kbStore.js`, `kbApi.js` |
| Pinia store | `use<Name>Store` export; the **store id** is spelled out even where the file name abbreviates | `kbStore.js` → `useKbStore`, id `'knowledgeBase'` |
| Route path | kebab-case | `/knowledge-base` |
| API path | kebab-case under `/api/` | `/api/knowledge-bases` |
| Env var | `UPPER_SNAKE`. On the frontend the prefix is a **visibility marker**, not decoration — see below | `RETRIEVAL_TOP_K`, `VUE_APP_API_URL`, `DEV_API_TARGET` |
| SSE stage id | `snake_case`, matching the **emitted `data.stage` value** — *not* the graph node name (5 of 8 differ) | `reranker` (node `rerank`) |

**The stage id is the string in the `emit()` call, not the graph registration.** `planner`, `retrieval`,
and `external_tools` are spelled the same in both places, but the other five are not: nodes `aggregate`,
`rerank`, `compress`, `reason`, `reflect` emit `aggregator`, `reranker`, `compressor`, `reasoning`,
`reflection`. The emitted value is what `STAGES` (`subsystems/rag/ragStore.js:16-25`) must match; the node
name never reaches the wire. All eight are listed in
[`../../api/sse-events/README.md`](../../api/sse-events/README.md).

**The `VUE_APP_` prefix means "compiled into the browser bundle".** Vue CLI inlines every `VUE_APP_*`
variable at build time, so the prefix is a declaration that the value is public and permanent for that
build — `VUE_APP_API_URL` (read in both clients: `subsystems/rag/ragApi.js:12` and
`subsystems/knowledge-base/kbApi.js:11`) is one. A frontend-side variable that must **not** reach
the client is deliberately left **unprefixed**: `DEV_API_TARGET` is read by `vue.config.js:12` in the Node
dev-server process, never by the app, and `dev.py:243` sets it per-run. Choose the prefix by where the
value is consumed, not by which half of the repo the file sits in.

<br>

## Ignored paths

From the root `.gitignore` — these are runtime state, never source: `node_modules/`, `Frontend/dist/`,
`.env` and `*.env` (but **not** `.env.example`), virtualenvs (`my_venv/`, `venv/`, `.venv/`, `env/`),
`__pycache__/`, build artifacts, IDE folders, and `.claude`.

**The runtime data tree is ignored at both possible locations.** `.gitignore:32` ignores
`Backend/src/data/` — the real one, because `DATA_ROOT` is the CWD-relative literal `"./data"`
(`config.py:44`) and the backend runs from `Backend/src` — and `.gitignore:33` also ignores
`Backend/data/`, which is where the tree lands if anyone starts the process from `Backend/`. An
explanatory comment block at `.gitignore:29-31` records why both entries exist. Keep both: dropping the
second re-opens the case where a wrongly-started backend commits a vector database.
