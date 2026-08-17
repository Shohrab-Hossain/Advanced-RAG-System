<div align="center">

# 🧬 adRAG — Frontend

### A Vue 3 single-page app that drives the RAG pipeline and renders it working, live, from one Server-Sent Events stream.

<br>

[![Version](https://img.shields.io/badge/version-1.0.0-3fb950)](package.json)
[![Vue](https://img.shields.io/badge/Vue-3.4-42b883?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Build](https://img.shields.io/badge/build-Vue%20CLI%20%2F%20webpack-35495e?logo=webpack&logoColor=white)](vue.config.js)
[![Tailwind](https://img.shields.io/badge/Tailwind-3.4-06b6d4?logo=tailwindcss&logoColor=white)](tailwind.config.js)

[![Pinia](https://img.shields.io/badge/Pinia-3%20stores-ffd859)](Documentation/state/README.md)
[![Components](https://img.shields.io/badge/components-13-7c5cff)](Documentation/README.md#-4-project-structure)
[![Dev server](https://img.shields.io/badge/dev%20server-localhost%3A8080-f59e0b)](#-1-quick-start)
[![Needs](https://img.shields.io/badge/needs-API%20on%20%3A5000-1c7ed6)](../Backend/README.md)

</div>

<br>

---

<br>

## Content Tree

<pre>
adRAG — Frontend
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-quick-start">🚀 1. Quick start</a>
│
├── <a href="#-2-the-four-pages">💡 2. The four pages</a>
│
├── <a href="#%EF%B8%8F-3-stack">🛠️ 3. Stack</a>
│
├── <a href="#-4-layout">📁 4. Layout</a>
│   ├── <a href="#41-design-versus-public">4.1 design versus public</a>
│   └── <a href="#42-inside-src">4.2 Inside src</a>
│
├── <a href="#%EF%B8%8F-5-configuration">⚙️ 5. Configuration</a>
│
└── <a href="#-6-documentation">📚 6. Documentation</a>
</pre>

<br>

---

<br>

## 📖 Overview

Four pages — home, chat, knowledge base, configuration — over three Pinia stores and two axios
clients. The interesting one is chat: a query is a `POST` that returns an open `text/event-stream`, and
the RAG store turns that stream into eight animated pipeline rows, a Markdown answer, a grid of
expandable source cards, and a history entry that can replay the whole run later.

> [!NOTE]
> **The build is Vue CLI / webpack, not Vite.** There is no `vite.config.js`, no `npm run dev`, and no
> port 5173. The HTML entry is `public/index.html`, which Vue CLI treats as the build **template**
> rather than the app root.

<br>

---

<br>

## 🚀 1. QUICK START

```bash
cd Frontend
npm install
npm run serve     # dev server → http://localhost:8080
npm run build     # production bundle → dist/
npm run lint      # ESLint 8 over src/
```

Those three are the only scripts defined in [`package.json`](package.json).

The app needs the backend running on `http://localhost:5000`. It does not talk to it directly in
development: `vue.config.js` proxies `/api/*` there with `changeOrigin: true`, so there is no
cross-origin hop and no CORS setup to do. To bring both halves up at once, run `python infra/dev.py`
from the repository root — it picks free ports and points this proxy at whichever one the backend got.

> [!TIP]
> **`npm run lint` runs with `--fix` on by default**, so calling it to *check* the code silently
> rewrites it. Use `npm run lint -- --no-fix` for a read-only report. `npm run build` passes and emits
> one bundle-size advisory — a warning about an entrypoint above webpack's recommended budget, not a
> failure.

<br>

---

<br>

## 💡 2. THE FOUR PAGES

All four are lazily imported and served in HTML5 history mode.

| Route | What you do there |
|---|---|
| `/` | The landing page — the pitch, three navigation cards, and a description of the eight pipeline stages |
| `/chat` | Ask a question, watch the eight-row tracker update live, read the cited answer, open any source card, and replay anything from the history sidebar |
| `/knowledge-base` | Drag or browse files in (35 accepted extensions, up to 50 MB), watch the three-phase progress bar, review the index stats, delete one knowledge base or clear everything |
| `/configuration` | Pick OpenAI or Ollama and a model; see which providers are actually reachable, re-checked every 15 seconds while Ollama is down |

Two things survive a reload, both in `localStorage`: the theme under `rag-theme` (**dark is the
default**) and chat history under `rag-chat-history`, whose write is capped at the newest 50 entries.

<br>

---

<br>

## 🛠️ 3. STACK

| Role | Library |
|---|---|
| Framework | **Vue 3** with `<script setup>` Composition API throughout |
| Routing | **Vue Router 4** — four lazily-imported routes |
| State | **Pinia** — three stores, all setup style |
| HTTP | **axios** — two clients, each with its own instance |
| Markdown | **marked** — renders the answer body |
| Build | **Vue CLI 5** (webpack) with `@vue/cli-plugin-babel` |
| Styling | **Tailwind CSS** via PostCSS, `darkMode: 'class'` |
| Linting | **ESLint 8** with `eslint-plugin-vue`, configured by `.eslintrc.js` |

`@mermaid-js/mermaid-cli` and `svgo` also appear in `devDependencies`. They are **documentation
tooling**, used to render the diagram sources these docs embed — nothing in `src/` imports either.

<br>

---

<br>

## 📁 4. LAYOUT

```text
Frontend/
│
├── 📁 Documentation/     The engineering cookbook — 8 pages
├── 📁 design/            Design SOURCE you edit — never served, never imported
├── 📁 public/            Served VERBATIM — the build copies this folder and nothing else
├── 📁 src/               The application
└── 📁 dist/              Build output — git-ignored, never edited
```

### 4.1 design versus public

Two folders that are easy to confuse, and the difference is load-bearing:

| | `design/` | `public/` |
|---|---|---|
| **Holds** | the source you edit — brand masters, theme experiments | the promoted copies the server sends |
| **Edited by hand?** | ✅ this is the only place | ❌ never — edit the master and re-promote |
| **Served?** | ❌ never | ✅ verbatim |

**The same logo legitimately exists in both.** Deleting the `public/` copy breaks serving; deleting the
`design/` source loses the ability to regenerate it at a new size. Never symlink one to the other.

```text
design/
├── 📁 brand/logo/        The master → derivative chain: svg/ png/ artifacts/
└── 📁 theme-lab/         THROWAWAY theme scratch — git-ignored, read by NOTHING

public/
├── 📄 index.html         The Vue CLI build template — meta tags, fonts, mount point
├── 📁 brand-logo/        Consumed by THIS app — our path, our names
├── 📁 favicon/           Consumed by browsers and platforms — names THEY dictate
└── 📁 images/og/         Consumed by other people's sites — cached for weeks
```

> [!CAUTION]
> **`design/theme-lab/` is not a source, and nothing reads it.** It is scratch space for trying a theme
> out, it is git-ignored, and it may be deleted at any time. **The live design system is
> `src/assets/main.css`** — its `@layer components` classes and its animations — plus the two font
> families in `tailwind.config.js`, which is the only thing that file holds. Adopting a theme means
> writing the values into `src/`, never pointing the build at the lab. (An earlier arrangement did point
> the build at a `design/theme/` folder; the folder moved, the build broke, and the rule reversed.)

The three `public/` folders each carry a `README.md` naming what belongs in them and are otherwise
**empty** — no brand master exists yet, so there is nothing to promote, and `/favicon.ico` currently
404s. [`design/README.md`](design/README.md) is the workbench's own guide.

### 4.2 Inside src

**Components are placed by ownership; state and HTTP clients are flat by kind.** The two rules are
deliberately different, and both are load-bearing.

```text
src/
├── 📁 assets/            main.css — THE live design system
├── 📁 pages/             One folder per route, owning its own components
│   ├── 📁 home/          views/HomeView.vue
│   ├── 📁 chat/          views/ + 6 components — the tracker and the result
│   │                     display each nest one satellite of their own
│   ├── 📁 knowledge-base/  views/ + UploadPanel · IndexStats · KnowledgeBaseList
│   └── 📁 configuration/   views/ + LLMSelector
├── 📁 router/            index.js — four lazily-imported routes
├── 📁 services/          BOTH clients, flat — ragApi.js · kbApi.js
├── 📁 shared/components/ The 3 cross-page components — NavBar · ModalDialog
│                         · FileTypeIcon
├── 📁 store/             ALL stores, flat — index.js ('ui') · ragStore.js
│                         · kbStore.js
├── 📄 App.vue            Root layout — NavBar + RouterView + ModalDialog
└── 📄 main.js            Bootstrap — Vue + Pinia + Router
```

A component used by exactly one page lives under that page and moves to `shared/` only when a **second**
page imports it — three qualify today. A satellite used by one component only lives inside that
component's folder. Stores and clients get no subfolders at all: **a new capability adds two files, not
two folders.** The full placement table is in
[`Documentation/README.md`](Documentation/README.md#-6-where-a-new-file-goes).

<br>

---

<br>

## ⚙️ 5. CONFIGURATION

There is exactly one frontend environment variable, and the right value in development is *no value*.

| Variable | Default | Purpose |
|---|---|---|
| `VUE_APP_API_URL` | *(unset)* | The API base URL. Unset, both clients fall back to a relative base and the dev proxy handles `/api/*`. Set it only when the SPA is served from a different origin than the API |

Vue CLI exposes **only** `VUE_APP_`-prefixed variables to the browser, and the value is baked into the
bundle **at build time** — so a static deployment either sets it at build time or is served behind
something that proxies `/api`.

> [!WARNING]
> **`.env.example` ships this variable set, while its own comment tells you to leave it unset.** Copy
> the file verbatim to `.env` and every request bypasses the dev proxy and goes cross-origin to `:5000`
> directly. That happens to work today only because the backend's CORS allowlist ends in a literal
> `"*"` — which is a documented, localhost-only risk, not a feature to rely on.

<br>

---

<br>

## 📚 6. DOCUMENTATION

The engineering cookbook is [`Documentation/`](Documentation/README.md) — eight pages, each written to
be understood without opening the source.

| Start with | For |
|---|---|
| [`Documentation/README.md`](Documentation/README.md) | The index, four read orders, the project tree, and where a new file goes |
| [`Documentation/state/README.md`](Documentation/state/README.md) | All three Pinia stores, chat-history persistence, and the layering map |
| [`Documentation/api-clients/README.md`](Documentation/api-clients/README.md) | Both axios modules and the hand-rolled SSE reader |
| [`Documentation/chat/pipeline-tracker.md`](Documentation/chat/pipeline-tracker.md) | The eight-row tracker and the stage-id contract it depends on |
| [`Documentation/design-system/README.md`](Documentation/design-system/README.md) | `main.css`, dark mode, the font chain, and why `design/` is a lab |
| [`design/README.md`](design/README.md) | The design source itself — the brand workbench and the theme lab |

The other half of the system is [`../Backend/README.md`](../Backend/README.md); the project front door,
including how the RAG pipeline actually works, is [`../README.md`](../README.md).

<br>
