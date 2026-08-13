# Frontend architecture

A Vue 3 single-page app built with Vue CLI (webpack). Composition API with `<script setup>` throughout;
no TypeScript, no component library, no global CSS beyond Tailwind and the component classes in
`src/assets/main.css`.

<br>

## Layout

```
Frontend/src/
├── main.js                  createApp → Pinia → router → mount('#app')
├── App.vue                  Shell: NavBar + <RouterView> with a "page" transition + ModalDialog
├── assets/main.css          Tailwind entry + @layer components (.card, .btn-*, .prose-rag …)
├── router/index.js          4 routes, lazy-imported, createWebHistory
├── services/api.js          Every HTTP call + the SSE stream reader
├── stores/
│   ├── rag.js               The application store: docs, query lifecycle, stages, result, history
│   └── ui.js                Theme (dark/light) + a promise-based modal
├── views/                   One per route
│   ├── HomeView.vue         Hero, 8 feature cards, nav tiles
│   ├── ChatView.vue         Query + live tracker + result + history sidebar
│   ├── KnowledgeBaseView.vue  Drag-drop upload, per-KB cards, index stats
│   └── ConfigView.vue       Provider comparison + LLMSelector
└── components/              12 components (see the table below)
```

<br>

## Routes

All in HTML5 history mode, all lazily imported (`router/index.js`):

| Path | Name | View |
|---|---|---|
| `/` | `home` | `HomeView.vue` |
| `/chat` | `chat` | `ChatView.vue` |
| `/knowledge-base` | `knowledge-base` | `KnowledgeBaseView.vue` |
| `/configuration` | `configuration` | `ConfigView.vue` |

<br>

## Components

| Component | Props / emits | Job |
|---|---|---|
| `NavBar.vue` | — | Top bar: four nav links with icons, backend connectivity dot (from `healthCheck()` on mount), active model label, theme toggle. On mount also fires `refreshStats`, `fetchProviders`, `fetchKnowledgeBases`. |
| `QueryInput.vue` | — | Auto-growing textarea (grows only, capped at 400px), four example prompts, submit. Mirrors `store.query` via a watcher so navigating away and back preserves the text. |
| `PipelineTracker.vue` | — | Renders one `StageRow` per entry of `STAGES` and a progress percentage: completed+skipped stages, plus 0.5 for an active one, over 8; forced to 100 once a result exists. |
| `StageRow.vue` | props `stage`, `status` | One stage row. Maps `status.status` (`idle`/`active`/`complete`/`skipped`/`error`) to row, icon, label and message classes, and renders detail "chips" derived from the event payload (`N vector`, `N BM25`, `top K`, `NN% conf.`, `grounded ✓`, `NN% size`). |
| `ResultDisplay.vue` | — | Renders the answer through `marked.parse()` into `.prose-rag`, a copy-to-clipboard button with a 2s confirmation, a collapsible source list of `SourceCard`s, and an expandable full-text panel for the selected source. Clears the selection whenever `store.sources` changes. |
| `SourceCard.vue` | props `source`, `selected`; emits `select` | One citation: file-type icon, label (`file_name` or `url`), source tag (`Vector`/`BM25`/`Graph`/`Web`), and `rerank_score` to 3 decimals (`—` when null). |
| `FileTypeIcon.vue` | props `filename`, `type`, `size` | Dual mode. With a filename it renders an extension badge (`PDF` `#EF4444`, `DOC` `#3B82F6`, `TXT` `#6B7280`, `MD` `#8B5CF6`, else the first 4 chars in `#A8A29E`); otherwise an SVG glyph per retrieval source (`web` `#6366F1`, `vector` `#10B981`, `bm25` `#0EA5E9`, `graph` `#14B8A6`). |
| `FileUpload.vue` | — | Drag-and-drop / click uploader. Its `accept` list is **35 extensions** (`FileUpload.vue:77-84`), mirroring `Config.ALLOWED_EXTENSIONS` (`config.py:62-65`) exactly — the two must stay in sync. Clears the upload result after 5s. |
| `KnowledgeBases.vue` | — | Collapsible KB list with per-file emoji icon, formatted upload date, delete-one and clear-all — both behind `ui.confirm()`. |
| `LLMSelector.vue` | — | Provider cards with model dropdowns; refresh button; polls `fetchProviders()` every 15s while Ollama is unavailable and stops on unmount. |
| `ModalDialog.vue` | — | Single global dialog rendered in `App.vue`, driven by `ui.modal`. |
| `StatBadge.vue` | props `label`, `value` | A label/value pill. |

<br>

## State — two Pinia stores

**`stores/rag.js`** (setup style) holds five groups of state and is the single source of truth for the UI:

| Group | Keys |
|---|---|
| Provider | `llmProvider`, `ollamaModel`, `openaiModel`, `availableProviders` |
| Index | `indexStats`, `knowledgeBases`, `uploading`, `uploadProgress`, `indexingProgress`, `isIndexing`, `uploadQueueCurrent`, `uploadQueueTotal`, `uploadResult` |
| Query | `query`, `isRunning`, `stageStatuses` (a `reactive` map keyed by stage id), `events` (raw log), `retryCount` |
| Result | `answer`, `sources`, `metadata`, `error`, `isHistoryResult` |
| History | `chatHistory` (hydrated from `localStorage['rag-chat-history']`) |

It also exports the `STAGES` constant — the eight stage descriptors (id, label, icon, desc) that define
the tracker's order and must stay in lockstep with the backend's `stage` values.

The event reducer `_applyEvent(type, data)` is the heart of the live UI: it appends to `events`, then
switches on the event type to set the stage's status. `retry` is the special case — it resets the seven
post-planner stages to `idle` so the tracker visibly re-animates the second attempt.

**`stores/ui.js`** owns the theme (`localStorage['rag-theme']`, default `'dark'`, applied by toggling the
`dark` class on `<html>`) and a promise-based modal: `ui.alert(msg)` and `ui.confirm(msg, opts)` return
promises that resolve when `ModalDialog` calls `close(result)`.

<br>

## Data flow

```
component  ──action──►  rag store  ──►  services/api.js  ──HTTP──►  Flask
                             ▲                  │
                             └──── SSE events ◄─┘   (onEvent → _applyEvent → stageStatuses)
```

Components never call `services/api.js` directly except `NavBar.vue`, which imports `healthCheck` for the
connectivity dot. Everything else goes through a store action.

<br>

## Build-time coupling — the two API seams

`services/api.js:12` is the switch:

```js
const BASE = process.env.VUE_APP_API_URL || ''
```

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
