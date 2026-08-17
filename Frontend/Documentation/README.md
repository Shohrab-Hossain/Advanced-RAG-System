<div align="center">

# 📘 Frontend Documentation

### Eight pages covering the Vue 3 SPA that drives the pipeline — three stores, two HTTP clients, four pages, and a tracker whose eight row ids must match the server byte for byte.

<br>

[![Pages](https://img.shields.io/badge/pages-8-7c5cff)](#-2-the-document-map)
[![Version](https://img.shields.io/badge/version-1.0.0-3fb950)](../package.json)
[![Vue](https://img.shields.io/badge/Vue-3.4-42b883?logo=vuedotjs&logoColor=white)](https://vuejs.org/)

[![Build](https://img.shields.io/badge/build-Vue%20CLI%20%2F%20webpack-35495e?logo=webpack&logoColor=white)](../vue.config.js)
[![Dev server](https://img.shields.io/badge/dev%20server-localhost%3A8080-f59e0b)](#-3-setup-and-run)
[![State](https://img.shields.io/badge/Pinia-3%20stores-ffd859)](state/README.md)
[![Styling](https://img.shields.io/badge/Tailwind-3.4-06b6d4?logo=tailwindcss&logoColor=white)](design-system/README.md)

</div>

<br>

---

<br>

## Content Tree

<pre>
Frontend Documentation
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-how-to-read-this-set">🧭 1. How to read this set</a>
│
├── <a href="#-2-the-document-map">📚 2. The document map</a>
│   ├── <a href="#21-the-tree">2.1 The tree</a>
│   ├── <a href="#22-the-pages">2.2 The pages</a>
│   └── <a href="#23-two-files-this-set-supersedes">2.3 Two files this set supersedes</a>
│
├── <a href="#-3-setup-and-run">🚀 3. Setup and run</a>
│   ├── <a href="#31-install-and-run">3.1 Install and run</a>
│   └── <a href="#32-the-three-scripts">3.2 The three scripts</a>
│
├── <a href="#-4-project-structure">📁 4. Project structure</a>
│
├── <a href="#-5-the-four-routes">💡 5. The four routes</a>
│
├── <a href="#-6-where-a-new-file-goes">🧩 6. Where a new file goes</a>
│
└── <a href="#-7-related-reading">🔗 7. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

The frontend is a **Vue 3 single-page application built with Vue CLI (webpack)**, Pinia and Tailwind
CSS. It has four pages: a chat view that streams the pipeline live, a knowledge-base view for uploading
and managing documents, a configuration view for picking a provider and model, and a landing page.

Its one genuinely hard job is the chat page. A query is a `POST` that returns an open
`text/event-stream`, and the store turns that stream into eight animated rows, a Markdown answer, a
grid of expandable source cards, and a history entry that can replay the whole run later.

> [!IMPORTANT]
> **The eight stage ids in `store/ragStore.js` are a wire contract with the backend, not labels.** They
> must equal the ids the server *emits*, and five of those eight differ from the pipeline's own graph
> node names. An event whose `stage` is not in the list is dropped silently — no error, no console
> warning — so a mismatch shows up as one row that never updates.
> [`chat/pipeline-tracker.md`](chat/pipeline-tracker.md) owns that contract.

> [!NOTE]
> **The build is Vue CLI / webpack, not Vite.** There is no `vite.config.js`, no `npm run dev`, and no
> port 5173 anywhere in this project. The three scripts in [`../package.json`](../package.json) —
> `serve`, `build`, `lint` — are the only ones defined.

<br>

---

<br>

## 🧭 1. HOW TO READ THIS SET

| You are… | Read in this order |
|---|---|
| **New to the frontend** | [`state/README.md`](state/README.md) → [`api-clients/README.md`](api-clients/README.md) → [`chat/README.md`](chat/README.md) |
| **Working on the live tracker** | [`chat/pipeline-tracker.md`](chat/pipeline-tracker.md) → [`state/README.md`](state/README.md) → [`api-clients/README.md`](api-clients/README.md) |
| **Working on uploads** | [`knowledge-base/README.md`](knowledge-base/README.md) → [`state/README.md`](state/README.md) → [`api-clients/README.md`](api-clients/README.md) |
| **Changing how it looks** | [`design-system/README.md`](design-system/README.md) → the page you are restyling |

[`state/README.md`](state/README.md) is the natural first page: all three stores live there, and it
carries the ownership-and-layering map that shows how every other file relates to them.

<br>

---

<br>

## 📚 2. THE DOCUMENT MAP

### 2.1 The tree

```text
Frontend/Documentation/
│
├── 📄 README.md                       You are here — index and read order
│
├── 📁 state/                          The three Pinia stores
│   └── 📄 README.md
│
├── 📁 api-clients/                    Both axios modules + the SSE reader
│   └── 📄 README.md
│
├── 📁 chat/                           The chat page
│   ├── 📄 README.md                   The view and its six components
│   └── 📄 pipeline-tracker.md         The tracker and the stage-id contract
│
├── 📁 knowledge-base/                 The knowledge-base page
│   └── 📄 README.md
│
├── 📁 configuration-page/             The provider and model picker
│   └── 📄 README.md
│
├── 📁 design-system/                  main.css, dark mode, the font chain
│   └── 📄 README.md
│
├── 📄 components.md                   SUPERSEDED — see §2.3
└── 📄 state.md                        SUPERSEDED — see §2.3
```

### 2.2 The pages

| Page | What it covers | Diagram |
|---|---|---|
| [`state/README.md`](state/README.md) | All three Pinia stores in setup style — the `'ui'` shell with its promise-based modal, the `'rag'` store that turns the SSE stream into eight rows and persists chat history, and the `'knowledgeBase'` store with its two-phase upload. Also the verified layering invariants | ✅ |
| [`api-clients/README.md`](api-clients/README.md) | `ragApi.js` and `kbApi.js` — eight routes across two axios instances, and the hand-rolled `fetch` + `ReadableStream` SSE reader with its partial-line buffering, four-way dispatch, and abort handle | — |
| [`chat/README.md`](chat/README.md) | The chat view and its six components — the query input, the answer renderer and its source cards, the history sidebar — plus the sidecar `.js`/`.css` convention that keeps pure functions out of the SFC | — |
| [`chat/pipeline-tracker.md`](chat/pipeline-tracker.md) | The eight-row tracker, the five status values, the detail chips and where each one's payload comes from, and the **stage-id contract** end to end including the retry re-animation | — |
| [`knowledge-base/README.md`](knowledge-base/README.md) | The container-and-view-model split, the sequential upload queue, the three-state progress bar, and the duplicate check that asks a different question than the server's | — |
| [`configuration-page/README.md`](configuration-page/README.md) | Provider selection, the two deliberately different model-fallback chains, the 15-second liveness poll and what it actually costs, and one panel that can never render | — |
| [`design-system/README.md`](design-system/README.md) | `src/assets/main.css` layer by layer, the two font families and the chain that delivers them, dark mode by hand-written pairs, and why the `design/` folder is a lab rather than a source | — |

### 2.3 Two files this set supersedes

[`components.md`](components.md) and [`state.md`](state.md) are the previous generation of these docs.
They are **retained but not maintained**, and both are wrong in ways that matter:

- **`state.md`** documents `src/stores/rag.js`, `src/stores/ui.js`, a single `services/api.js`,
  `vite.config.js` and port 5173. None of those exist. It also merges the knowledge-base store into the
  RAG store, and describes the `retry` event as incrementing a counter it actually assigns.
- **`components.md`** documents three components that do not exist — `StatBadge.vue`, `FileUpload.vue`
  and `KnowledgeBases.vue` — under a `src/components/` directory that does not exist either, and omits
  four that do.

**Read [`state/README.md`](state/README.md) instead of `state.md`**, and the four page docs
([`chat/`](chat/README.md), [`chat/pipeline-tracker.md`](chat/pipeline-tracker.md),
[`knowledge-base/`](knowledge-base/README.md),
[`configuration-page/`](configuration-page/README.md)) instead of `components.md` — between them they
cover all thirteen components against the current tree.

<br>

---

<br>

## 🚀 3. SETUP AND RUN

### 3.1 Install and run

**Prerequisites:** Node.js 18+, and the backend running on `http://localhost:5000` — the dev server
proxies `/api/*` to it.

```bash
cd Frontend
npm install
npm run serve     # dev server → http://localhost:8080
```

The proxy target is `vue.config.js`'s `devServer.proxy`, with `changeOrigin: true`, so development
never makes a cross-origin request. The literal fallback is `http://localhost:5000`;
`python infra/dev.py` overrides it with `DEV_API_TARGET` when it picks a different backend port.

`vue.config.js` also sets `lintOnSave: 'warning'` — deliberately, because with the default a single
lint error is emitted as a *compile* error and the app refuses to render while you are working.

> [!WARNING]
> **`.env.example` ships `VUE_APP_API_URL` set, and its own comment says to leave it unset.** Copy it
> verbatim to `.env` and every call bypasses the dev proxy and goes cross-origin to `:5000` directly.
> Leave it unset for normal development — both clients then fall back to a relative base URL. Set it
> only when the SPA is genuinely served from a different origin than the API, and remember the value is
> baked in **at build time**: only `VUE_APP_`-prefixed variables reach the browser at all.

### 3.2 The three scripts

| Script | What it does |
|---|---|
| `npm run serve` | Dev server on `8080`, hot reload, `/api` proxied to the backend |
| `npm run build` | Production bundle into `dist/`. It passes, and it emits a **bundle-size advisory** — an entrypoint above webpack's recommended budget. That is a warning, not a failure |
| `npm run lint` | ESLint 8 over `src/`, via `.eslintrc.js` (eslintrc, not flat config — Vue CLI 5 ships ESLint 8) |

> [!TIP]
> **`npm run lint` runs with `--fix` on by default**, so invoking it to *check* the code silently
> rewrites it. Use `npm run lint -- --no-fix` when you want the report and nothing else. The lint is
> clean today.

<br>

---

<br>

## 📁 4. PROJECT STRUCTURE

Components are placed by **ownership**; state and HTTP clients are **flat, by kind**. The two rules are
deliberately different and both are load-bearing — see [§6](#-6-where-a-new-file-goes).

```text
Frontend/
│
├── 📁 Documentation/                  This folder
│
├── 📁 design/                         DESIGN SOURCE — never served, never imported
│   ├── 📁 brand/logo/                 The master to derivative chain, in full anatomy
│   └── 📁 theme-lab/                  THROWAWAY — git-ignored, read by nothing
│
├── 📁 public/                         Served VERBATIM — the build copies this and nothing else
│   ├── 📄 index.html                  The Vue CLI build TEMPLATE, incl. the Google Fonts link
│   ├── 📁 brand-logo/                 Consumed by this app — our path, our names
│   ├── 📁 favicon/                    Consumed by browsers — names they dictate
│   └── 📁 images/og/                  Consumed by other sites — cached for weeks
│
├── 📁 src/                            Application source
│   ├── 📁 assets/                     main.css — THE live design system
│   ├── 📁 pages/                      One folder per route, owning its own components
│   │   ├── 📁 home/                   views/HomeView.vue
│   │   ├── 📁 chat/                   views/ + 6 components (StageRow and SourceCard
│   │   │                              nest inside their parents' folders)
│   │   ├── 📁 knowledge-base/         views/ + UploadPanel · IndexStats
│   │   │                              · KnowledgeBaseList
│   │   └── 📁 configuration/          views/ + LLMSelector
│   ├── 📁 router/                     index.js — four lazily-imported routes
│   ├── 📁 services/                   BOTH clients, flat — ragApi.js · kbApi.js
│   ├── 📁 shared/components/          The 3 cross-page components — NavBar
│   │                                  · ModalDialog · FileTypeIcon
│   ├── 📁 store/                      ALL stores, flat — index.js ('ui')
│   │                                  · ragStore.js · kbStore.js
│   ├── 📄 App.vue                     Root layout — NavBar + RouterView + ModalDialog
│   └── 📄 main.js                     Bootstrap — Vue + Pinia + Router
│
├── 📄 .env.example                    VUE_APP_API_URL — leave it unset in dev
├── 📄 .eslintrc.js                    ESLint 8 config — what `npm run lint` reads
├── 📄 package.json                    Three scripts + dependencies
├── 📄 postcss.config.js               Tailwind + autoprefixer
├── 📄 README.md                       Frontend front door
├── 📄 tailwind.config.js              Two font families; reads nothing from design/
└── 📄 vue.config.js                   Dev server :8080 + /api proxy → :5000
```

**Eighteen `.vue` files: one root layout, four views, and thirteen components.** Five of the thirteen
import no store at all — they are presentational leaves that take props and emit events.

<br>

---

<br>

## 💡 5. THE FOUR ROUTES

All four are lazily imported in `src/router/index.js` and served in HTML5 history mode.

| Route | View | What happens there |
|---|---|---|
| `/` | `HomeView.vue` | The landing page — the pitch, three navigation cards, and a grid describing the eight pipeline stages. No interactive state |
| `/chat` | `ChatView.vue` | The query input, the eight-row live tracker, the Markdown answer with expandable source cards, and a history sidebar backed by `localStorage` |
| `/knowledge-base` | `KnowledgeBaseView.vue` | Drag-and-drop or click-to-browse upload with a sequential queue, three index-stat cards, and a grid of knowledge-base cards with per-file delete |
| `/configuration` | `ConfigView.vue` | Provider and model selection, availability pills, and a 15-second liveness poll while Ollama is down |

Two pieces of state outlive a reload, both in `localStorage`: the theme under `rag-theme` (**dark is
the default**) and chat history under `rag-chat-history`. Each history entry carries a deep clone of the
tracker's stage snapshot, which is what lets an old run be replayed in full rather than just re-read.

<br>

---

<br>

## 🧩 6. WHERE A NEW FILE GOES

| Adding… | Goes to |
|---|---|
| a **page** | `pages/<name>/views/<Name>View.vue` plus a lazily-imported router entry. Every page gets a `views/` folder, uniformly, even when it owns nothing else |
| a component used by **one page** | `pages/<page>/components/<Name>/<Name>.vue` — its own folder, never flat beside its siblings |
| a component used by a **second page** | it moves to `shared/components/<Name>/`. Three qualify today |
| a satellite used by **one component only** | inside that component's folder — `PipelineTracker/StageRow.vue`, `ResultDisplay/SourceCard.vue` |
| a **store** | `store/<abbrev>Store.js` — flat. The domain lives in the filename, not a directory |
| an **HTTP client** | `services/<abbrev>Api.js` — flat. It returns `data`, never the axios response |
| **pure helpers for one view** | a sidecar `.js` beside it, camelCase-named after the component (`chatView.js`, `knowledgeBaseView.js`). Anything touching a store, a ref or a lifecycle hook stays in the `.vue` |
| a **shared style** | `src/assets/main.css` under `@layer components` — **not** `design/` |

**A new capability adds two files, not two folders** — `store/<abbrev>Store.js` and
`services/<abbrev>Api.js`.

**Layering that must not invert** (verified by an exhaustive import scan):

- **Components call store actions, not services.** The one accepted exception is `NavBar.vue`, which
  imports `healthCheck` directly to drive its connection dot.
- **The two API clients never import each other**, and neither imports anything else local — each
  constructs its own axios instance.
- **`store/index.js` knows nothing about RAG or HTTP.** It is the app shell: theme and modal.
- `shared/` and `pages/` both consume `store/` and `services/`, never the reverse.

> [!CAUTION]
> **Do not add a design token to `design/theme-lab/` and expect it to reach the app.** That folder is
> throwaway scratch for trying a theme out, it is git-ignored, and **nothing reads it** —
> `tailwind.config.js` holds only the two font families. The live design system is
> `src/assets/main.css`. Adopting a theme means writing its values into `src/`, never pointing the build
> at the lab. The lab's own `tokens.json` still calls itself the single source; that header is stale.
> [`design-system/README.md`](design-system/README.md) has the evidence.

<br>

---

<br>

## 🔗 7. RELATED READING

| Destination | Why |
|---|---|
| [`../README.md`](../README.md) | The frontend front door — install, run, layout, `design/` versus `public/` |
| [`../../README.md`](../../README.md) | The project front door — the RAG system explained, both halves, getting started |
| [`../../Backend/Documentation/api/query.md`](../../Backend/Documentation/api/query.md) | The other side of the SSE stream: every event type and every payload key |
| [`../../Backend/Documentation/api/README.md`](../../Backend/Documentation/api/README.md) | The eight routes these two clients call, with their real error shapes |
| [`../design/README.md`](../design/README.md) | The design source — the brand workbench, and why the theme lab is not a source |

<br>
