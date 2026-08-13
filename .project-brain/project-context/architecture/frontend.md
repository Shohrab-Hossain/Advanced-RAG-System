# Frontend architecture

A Vue 3 single-page app built with Vue CLI (webpack). Composition API with `<script setup>` throughout;
no TypeScript, no component library, and no CSS beyond Tailwind, the `@layer components` classes in
`src/assets/main.css`, and three small `<style scoped>` blocks.

`Frontend/src/` is sorted by **ownership**, not by kind: a folder exists because something owns what is
inside it. There is no `components/`, `views/`, `services/`, or `stores/` bucket — the reasoning, the
measured import graph behind it, and the rejected kind-first alternative are recorded in
[ADR-007](../../decisions/ADRs/entries/007-ownership-based-frontend-tree.md).

<br>

## Layout

```
Frontend/src/                        30 files
├── main.js                          createApp → Pinia → router → mount('#app')
├── App.vue                          Shell: NavBar + <RouterView> with a "page" transition + ModalDialog
├── assets/main.css                  Tailwind entry + @layer components (.card, .btn-*, .prose-rag …)
├── router/index.js                  4 routes, lazy-imported, createWebHistory
│
├── store/index.js                   Cross-capability state ONLY — theme + the global modal ('ui')
│
├── subsystems/                      Capabilities: each owns its store + its own axios client
│   ├── rag/
│   │   ├── ragStore.js              'rag' — STAGES, provider, query lifecycle, result, chat history
│   │   └── ragApi.js                3 exports — /api/query (SSE), /api/providers, /api/health
│   └── knowledge-base/
│       ├── kbStore.js               'knowledgeBase' — index stats, KB list, upload/indexing progress
│       └── kbApi.js                 5 exports — upload, documents, clear, list KBs, delete KB
│
├── shared/components/               Used by more than one page — 3 components
│   ├── NavBar/NavBar.vue
│   ├── ModalDialog/ModalDialog.vue
│   └── FileTypeIcon/FileTypeIcon.vue
│
└── pages/                           One folder per route; every page has views/, most have components/
    ├── home/views/HomeView.vue
    ├── chat/
    │   ├── views/                   ChatView.vue + chatView.js (pure PIPELINE_STEPS teaser)
    │   └── components/              ChatHistorySidebar/ · PipelineTracker/ · QueryInput/ · ResultDisplay/
    ├── knowledge-base/
    │   ├── views/                   KnowledgeBaseView.vue + knowledgeBaseView.js (pure helpers)
    │   └── components/              UploadPanel/ · IndexStats/ · KnowledgeBaseList/
    └── configuration/
        ├── views/ConfigView.vue
        └── components/LLMSelector/
```

Three structural rules hold across that tree, and each is load-bearing rather than cosmetic — they are
specified with their do/don't in
[`../conventions/project-layout/README.md`](../conventions/project-layout/README.md):

- **One component = one folder** (`<Name>/<Name>.vue`), with a satellite used only by that component
  living inside it — `PipelineTracker/StageRow.vue`, `ResultDisplay/SourceCard.vue`.
- **Pure logic splits into a camelCase sibling module** beside the `.vue` — `chatView.js`,
  `knowledgeBaseView.js`, `chatHistorySidebar.js`. Each header states the contract: no store, no refs,
  no lifecycle.
- **Every page has a `views/` folder**, even `home/` and `configuration/`, which hold a single view each.

<br>

## Routes

All in HTML5 history mode, all lazily imported (`router/index.js`):

| Path | Name | View |
|---|---|---|
| `/` | `home` | `pages/home/views/HomeView.vue` |
| `/chat` | `chat` | `pages/chat/views/ChatView.vue` |
| `/knowledge-base` | `knowledge-base` | `pages/knowledge-base/views/KnowledgeBaseView.vue` |
| `/configuration` | `configuration` | `pages/configuration/views/ConfigView.vue` |

<br>

## Components — 13, split by owner

**3 shared · 6 chat · 3 knowledge-base · 1 configuration.** Counting components, not folders: the two
satellites (`StageRow.vue`, `SourceCard.vue`) live inside their parent's folder, so `pages/chat/` holds
six components across four folders.

**Shared** (`src/shared/components/<Name>/`) — imported by more than one page:

| Component | Props / emits | Job |
|---|---|---|
| `NavBar.vue` | — | Top bar: four nav links with icons, backend connectivity dot, active model label, theme toggle. Reads all three stores and is the one component allowed to import an API module directly — `healthCheck` from `subsystems/rag/ragApi` (`:111`). Its `onMounted` (`:140-148`) awaits `healthCheck()`, sets `connected`, then fans out `Promise.all([kb.refreshStats(), store.fetchProviders(), kb.fetchKnowledgeBases()])` — four calls across three sources, and the sharpest illustration of the cross-subsystem seam: one `Promise.all` touching both subsystems. |
| `ModalDialog.vue` | — | Single global dialog rendered in `App.vue`, driven by `ui.modal`. Carries a `<style scoped>` block (`:36`). |
| `FileTypeIcon.vue` | props `filename`, `type`, `size` | Dual mode. With a filename it renders an extension badge (`PDF` `#EF4444`, `DOC` `#3B82F6`, `TXT` `#6B7280`, `MD` `#8B5CF6`, else the first 4 chars in `#A8A29E`); otherwise an SVG glyph per retrieval source (`web` `#6366F1`, `vector` `#10B981`, `bm25` `#0EA5E9`, `graph` `#14B8A6`). |

**Chat page** (`src/pages/chat/components/<Name>/`):

| Component | Props / emits | Job |
|---|---|---|
| `QueryInput.vue` | — | Auto-growing textarea (grows only, capped at 400px), four example prompts, submit at `:103` → `ragStore.runQuery(localQuery)`. Mirrors `store.query` via a watcher so navigating away and back preserves the text. |
| `PipelineTracker.vue` | — | Renders one `StageRow` per entry of `STAGES` and a progress percentage: completed+skipped stages, plus 0.5 for an active one, over 8; forced to 100 once a result exists. |
| `StageRow.vue` | props `stage`, `status` | Satellite of `PipelineTracker`, imported only by it (`PipelineTracker.vue:60`). Maps `status.status` (`idle`/`active`/`complete`/`skipped`/`error`) to row, icon, label and message classes, and renders detail "chips" derived from the event payload (`N vector`, `N BM25`, `top K`, `NN% conf.`, `grounded ✓`, `NN% size`). |
| `ResultDisplay.vue` | — | Renders the answer through `marked.parse()` into `.prose-rag`, a copy-to-clipboard button with a 2s confirmation, a collapsible source list of `SourceCard`s, and an expandable full-text panel for the selected source. Clears the selection whenever `store.sources` changes. Carries a `<style scoped>` block (`:128`). |
| `SourceCard.vue` | props `source`, `selected`; emits `select` | Satellite of `ResultDisplay`, imported only by it (`ResultDisplay.vue:97`). One citation: file-type icon, label (`file_name` or `url`), source tag (`Vector`/`BM25`/`Graph`/`Web`), and `rerank_score` to 3 decimals (`—` when null). |
| `ChatHistorySidebar.vue` | props `open` (Boolean, default `false`, `:90-92`); emits `close` (`:94`) | Slide-over history list: a watcher (`:101-105`) reacts to the open state, and `ui.confirm()` guards its destructive actions (`:113-129`). Relative-time formatting is `formatTime()` in the sibling `chatHistorySidebar.js:8`; its CSS is the sibling `chatHistorySidebar.css`, attached as `<style scoped src="./chatHistorySidebar.css">` (`:132`). `ChatView.vue` owns only the `sidebarOpen` ref (`:129`) and the toggle button (`:24`). |

**Knowledge-base page** (`src/pages/knowledge-base/components/<Name>/`) — all three are presentational.
`KnowledgeBaseView.vue:48-49` states the contract in the source: *"The children are presentational — the
view owns the data and hands each one a finished view-model, so no component reaches back up into this
folder."*

| Component | Props / emits | Job |
|---|---|---|
| `UploadPanel.vue` | props `accept` (String, required, `:89-91`) | Drag-and-drop / click uploader. `handleFiles()` (`:125-147`) loops the whole drop, so multi-file upload lives here rather than in the view; a re-upload of an already-indexed file goes through a `ui.confirm()` (`:134-137`) before re-indexing. Clears the upload result **6 seconds** after it completes — `setTimeout(() => store.resetUploadResult(), 6000)` (`:146`). Its `accept` value is `ACCEPT_ATTR` from `knowledgeBaseView.js:13-20`. |
| `IndexStats.vue` | props `stats` (Array, required, `:39-41`) | The stat tiles. Imports **nothing** — the purest example of the view-model handoff above. |
| `KnowledgeBaseList.vue` | props `items` (Array, required, `:81-83`); emits `remove`, `clear` (`:85`) | Collapsible KB list with per-file icon, formatted upload date, and delete-one / clear-all buttons. It only emits; the two `ui.confirm()` flows and the store calls belong to `KnowledgeBaseView.vue:59-69`. |

**Configuration page** (`src/pages/configuration/components/<Name>/`):

| Component | Props / emits | Job |
|---|---|---|
| `LLMSelector.vue` | — | Provider cards with model dropdowns; refresh button; polls `fetchProviders()` every 15s while Ollama is unavailable and stops on unmount. At 204 lines it is the largest component and is deliberately left whole: its script (`:167-204`) is computeds, `select()`, `refresh()` and the mount/unmount timer — reactive throughout, so there is no pure logic to split into a sibling module. |

> [!NOTE]
> **`ACCEPT_ATTR` is the frontend half of a two-sided contract.** The 35 extensions in
> `knowledgeBaseView.js:13-20` must stay identical to `Config.ALLOWED_EXTENSIONS`
> (`Backend/src/config.py:62-65`); the source carries the sync warning at `knowledgeBaseView.js:11-12`.
> The sets match today — 35 on both sides. Change one and you must change the other, or the picker
> offers a file the API rejects with a `400`.

<br>

## State — three Pinia stores

All setup style. The split follows the same ownership rule as the tree: **`store/` at the root holds only
state that no single capability owns**; capability state lives with its capability.

**`subsystems/rag/ragStore.js`** — id `'rag'`, `useRagStore` at `:30`, 244 lines:

| Group | Keys |
|---|---|
| Provider | `llmProvider`, `ollamaModel`, `openaiModel`, `availableProviders` (`:32-38`) |
| Query | `query`, `isRunning`, `stageStatuses` (a `reactive` map keyed by stage id), `events` (raw log), `retryCount` |
| Result | `answer`, `sources`, `metadata`, `error`, `isHistoryResult` |
| History | `chatHistory` (`:55-62`, `:170-198`), hydrated from `localStorage['rag-chat-history']` |

It also exports the `STAGES` constant (`:16-25`) — the eight stage descriptors (id, label, icon, desc)
that define the tracker's order and must stay in lockstep with the backend's `stage` values.

The event reducer `_applyEvent(type, data)` (`:84`) is the heart of the live UI: it appends to `events`,
then switches on the event type to set the stage's status. `retry` is the special case — it resets the
seven post-planner stages to `idle` so the tracker visibly re-animates the second attempt.

**`subsystems/knowledge-base/kbStore.js`** — id `'knowledgeBase'`, `useKbStore` at `:14`, 121 lines:

| Group | Keys |
|---|---|
| Index | `indexStats`, `knowledgeBases` |
| Upload / indexing | `uploading`, `uploadProgress`, `indexingProgress`, `isIndexing`, `uploadQueueCurrent`, `uploadQueueTotal`, `uploadResult` |

`_animateIndexing()` (`:62-76`) is the fake progress bar the backend cannot supply: it eases toward 95 in
`+5` steps every 80 ms and only jumps to 100 when the upload response actually lands.

> [!IMPORTANT]
> **The file name and the store id differ on purpose, and only here.** The module is `kbStore.js`
> (matching the `kbApi.js` sibling and the `useKbStore` export) while the id registered with Pinia is
> `'knowledgeBase'` (`:14`) — the id is what appears in devtools and in persisted keys, so it is spelled
> out in full. Do not "fix" either one to match the other.

**`store/index.js`** — id `'ui'`, `useUiStore` at `:8`, 49 lines. Owns the theme
(`localStorage['rag-theme']`, default `'dark'` at `:9`, applied by `applyTheme` at `:4-6` toggling the
`dark` class on `<html>`) and a promise-based modal: `ui.alert(msg)` and `ui.confirm(msg, opts)` return
promises that resolve when `ModalDialog` calls `close(result)`. Both concerns are used from every page and
belong to no capability, which is exactly why they sit at the root rather than in a subsystem.

<br>

## Data flow

```
                      ┌── ragStore ──► subsystems/rag/ragApi.js ──HTTP──► Flask
component ──action────┤       ▲                    │
                      │       └─── SSE events ◄────┘   (onEvent → _applyEvent → stageStatuses)
                      │
                      └── kbStore ──► subsystems/knowledge-base/kbApi.js ──HTTP──► Flask

                          uiStore (store/index.js) — no network at all
```

Components never call an API module directly except `NavBar.vue`, which imports `healthCheck` for the
connectivity dot (`:111`). Everything else goes through a store action.

**The subsystems do not know about each other** — neither store nor either API module imports across the
boundary. Where a screen needs both capabilities, the *component* consumes both stores, and there are
exactly two such places:

| Consumer | Imports | Why |
|---|---|---|
| `pages/chat/views/ChatView.vue` (`:118-119`) | `ragStore` + `kbStore` | The query lifecycle is RAG's; `hasDocuments` for the "no documents indexed" warning (`:41`) is the knowledge base's. |
| `shared/components/NavBar/NavBar.vue` (`:108-111`) | `ragStore` + `kbStore` + `uiStore` + `ragApi` | The provider/model badge, the theme toggle, the health dot, and a single mount-time `Promise.all` (`:140-148`) that refreshes providers from `ragStore` **and** index stats + the KB list from `kbStore` — one bar showing four things owned by four different places. |

That is the whole cross-subsystem surface the split created. A third such consumer is a signal to
re-check whether the boundary is in the right place.

<br>

## Build-time coupling — the two API seams

Each subsystem builds its own axios client, so `VUE_APP_API_URL` is read **twice**:

```js
const BASE = process.env.VUE_APP_API_URL || ''   // ragApi.js:12  and  kbApi.js:11
```

| Module | Client | Owns |
|---|---|---|
| `subsystems/rag/ragApi.js` | `:14` | `healthCheck` (`:18`) · `getProviders` (`:23`) · `streamQuery` (`:40`, fetch + `ReadableStream`, returns `{ abort }`) |
| `subsystems/knowledge-base/kbApi.js` | `:13` | `uploadFile` (`:17`) · `getDocuments` (`:33`) · `clearDocuments` (`:38`) · `getKnowledgeBases` (`:45`) · `deleteKnowledgeBase` (`:50`) |

The duplication is deliberate and the seam **behaviour** is unchanged — both modules read the same
variable and resolve to the same origin. What doubled is the number of construction sites, so a change to
how the base URL is derived must be made in both files.

Everything downstream follows from whether that variable is set at **build** time, which produces two
different network topologies:

| Seam | When | How calls travel | CORS involved? |
|---|---|---|---|
| **Proxied** (default) | `VUE_APP_API_URL` unset → `BASE = ''` | Relative `/api/*` → the Vue dev server → `process.env.DEV_API_TARGET \|\| 'http://localhost:5000'` (`vue.config.js:12`) | No — same origin from the browser's point of view |
| **Direct** | `VUE_APP_API_URL` set — e.g. `dev.py --direct` (`dev.py:243-245`), or any production build | The browser calls the API origin itself | Yes — the `app.py:43-46` configuration is what permits it |

Both work today. The direct seam is the one a deployed topology (a static host in front of a separate API
box) necessarily uses, so it is worth exercising with `--direct` before shipping.

- **`DEV_API_TARGET` makes the proxy target movable.** `dev.py:243` always exports it, so the dev server
  follows whichever API port the launcher picked; the `:5000` literal is an additive fallback that keeps a
  bare `npm run serve` working. `devServer.port` is still `8080` in `vue.config.js:7`, but `dev.py:259`
  overrides it with `npm run serve -- --port <n>`.
- **`VUE_APP_API_URL` is baked in at build time.** Vue CLI only exposes variables prefixed `VUE_APP_`, and
  it inlines them into the bundle — a production build needs the API origin known before `npm run build`.
  `DEV_API_TARGET` deliberately carries **no** prefix because it is read in the Node dev-server process and
  must not reach the client.
- **The origin mismatch to know about:** the dev server runs on **8080** while the backend's
  `FRONTEND_URL` default is `http://localhost:5173`. On the direct seam that gap is covered by the other
  entries in the `app.py:44` allowlist — six of them, including a literal `"*"` that permits **every**
  origin (see [`../security/trust-boundaries/README.md`](../security/trust-boundaries/README.md)). Under
  `dev.py` the gap does not open: `FRONTEND_URL` is injected as the real UI URL (`dev.py:232`).
</content>
</invoke>
