# adRAG — Frontend

The frontend is a Vue 3 single-page application built with **Vue CLI (webpack)**, Pinia, and Tailwind CSS.
It provides a chat interface for querying the RAG pipeline, a knowledge base management page for uploading
documents, a configuration page for selecting LLM providers, and real-time animated pipeline progress
driven by Server-Sent Events from the backend.

---

## Table of Contents

- [Setup & Run](#setup--run)
- [Project Structure](#project-structure)
- [Where a new file goes](#where-a-new-file-goes)
- [Views](#views)
- [Detailed Documentation](#detailed-documentation)

---

## Setup & Run

### Prerequisites

- Node.js 18+
- Backend running on `http://localhost:5000` (the dev server proxies `/api/*` to it — see `vue.config.js`)

### Install & Run

```bash
cd Frontend
npm install
npm run serve     # dev server on http://localhost:8080
npm run build     # production build → dist/
npm run lint      # ESLint over src/
```

> **The build is Vue CLI / webpack, not Vite.** There is no `vite.config.js` and no `npm run dev` script;
> the three scripts above are the only ones defined in `package.json`. The HTML entry lives at
> `public/index.html` (Vue CLI treats it as the build **template**), not at the project root.

---

## Project Structure

Components are placed by **ownership**; state and HTTP clients are **flat, by kind**. The two rules are
deliberately different and both are load-bearing — see [Where a new file goes](#where-a-new-file-goes).

```
Frontend/
├── public/                       # Served VERBATIM
│   ├── index.html                #   Build template — title, meta tags, fonts, mount point
│   ├── brand-logo/               #   The mark as this app's UI uses it
│   ├── favicon/                  #   The icon set — names the platforms dictate
│   └── images/og/                #   Social share image
├── design/                       # DESIGN SOURCE — never served, never imported
│   ├── brand/                    #   The brand workbench: masters → derivatives
│   └── theme/                    #   tokens.json — the single source of the design tokens
├── Documentation/                # This folder
├── vue.config.js                 # Dev server :8080 + /api proxy → :5000
├── tailwind.config.js            # Reads design/theme/tokens.json — defines nothing itself
├── postcss.config.js
├── .eslintrc.js
├── .env.example
├── package.json
└── src/
    ├── main.js                   # App bootstrap (Vue + Pinia + Router)
    ├── App.vue                   # Root layout (NavBar + RouterView)
    ├── assets/
    │   └── main.css              # Tailwind layers, @layer components, animations
    ├── router/
    │   └── index.js              # Route definitions (/, /chat, /knowledge-base, /configuration)
    │
    ├── store/                    # ALL Pinia stores, FLAT — no per-capability subfolders
    │   ├── index.js              #   'ui' — modal dialog system, theme
    │   ├── ragStore.js           #   Pipeline state, chat history
    │   └── kbStore.js            #   Knowledge base documents + index stats
    │
    ├── services/                 # BOTH HTTP clients, FLAT — each builds its own axios instance
    │   ├── ragApi.js             #   query (SSE), providers, health
    │   └── kbApi.js              #   upload, documents, clear, KB list, delete
    │
    ├── shared/components/        # The 3 genuinely cross-page components
    │   ├── NavBar/               #   Top navigation + connection status
    │   ├── ModalDialog/          #   Promise-based alert/confirm
    │   └── FileTypeIcon/         #   File extension / retrieval source icon
    │
    └── pages/                    # One folder per route, owning its own components
        ├── home/views/HomeView.vue
        ├── chat/
        │   ├── views/ChatView.vue + chatView.js
        │   └── components/
        │       ├── ChatHistorySidebar/    # .vue + .js + .css
        │       ├── QueryInput/
        │       ├── PipelineTracker/       # + StageRow.vue (its satellite)
        │       └── ResultDisplay/         # + SourceCard.vue (its satellite)
        ├── knowledge-base/
        │   ├── views/KnowledgeBaseView.vue + knowledgeBaseView.js
        │   └── components/{UploadPanel,IndexStats,KnowledgeBaseList}/
        └── configuration/
            ├── views/ConfigView.vue
            └── components/LLMSelector/
```

---

## Where a new file goes

| Adding… | Goes to |
|---|---|
| a **page** | `pages/<name>/views/<Name>View.vue` + a lazily-imported router entry. Every page gets a `views/` folder, uniformly, even when it owns nothing else |
| a component used by **one page** | `pages/<page>/components/<Name>/<Name>.vue` — its own folder, never flat beside its siblings |
| a component used by a **second page** | it moves to `shared/components/<Name>/`. Three qualify today |
| a satellite used by **one component only** | inside that component's folder — `PipelineTracker/StageRow.vue`, `ResultDisplay/SourceCard.vue` |
| a **store** | `store/<abbrev>Store.js` — flat. The domain lives in the filename, not a directory |
| an **HTTP client** | `services/<abbrev>Api.js` — flat. It returns `data`, never the axios response |
| a **design token** | `design/theme/tokens.json` — **not** `tailwind.config.js`, which only reads it |

**A new capability adds two files, not two folders** — `store/<abbrev>Store.js` and `services/<abbrev>Api.js`.

### Layering that must not invert

- **Components call store actions, not the service.** (`NavBar.vue`'s `healthCheck` import is the one
  accepted exception.)
- **The two API clients never import each other** — each constructs its own axios instance.
- **`store/index.js` knows nothing about RAG.** It is the app shell: modal + theme.
- `shared/` and `pages/` both consume `store/` and `services/`, never the reverse.

### Styling

Tailwind utilities inline, with shared patterns promoted to `@layer components` in `assets/main.css`.
**No `<style>` blocks in components**, and every colour utility is written as a light/`dark:` pair —
the app runs `darkMode: 'class'`. The full rules are in
[`../design/theme/contract.md`](../design/theme/contract.md).

---

## Views

### Home (`/`)
Landing page. Displays the adRAG hero section, three navigation cards (Chat, Knowledge Base,
Configuration), and a grid of the 8 pipeline stages with descriptions. Purely informational — no
interactive state.

### Chat (`/chat`)
Main interface. Contains the query input, real-time pipeline tracker (8 animated stage rows), the final
answer rendered as Markdown, and a source cards grid. A collapsible left sidebar shows the full chat
history (persisted to `localStorage`, max 50 items). Selecting a history item replays the full pipeline
state snapshot.

### Knowledge Base (`/knowledge-base`)
Document management. Supports drag-and-drop or click-to-browse file upload (PDF, DOCX, TXT, Markdown)
with multi-file batch support. Shows a unified progress bar with three phases: uploading (determinate),
processing on server (indeterminate shimmer), and indexing (determinate). Displays three index stat cards
(Vector Store, BM25, Knowledge Graph) and a grid of uploaded KB cards with per-file deletion.

### Configuration (`/configuration`)
LLM provider selection. Shows availability and API key status for OpenAI and Ollama. Allows selecting a
specific model from each provider. Ollama availability is polled every 15 seconds.

---

## Detailed Documentation

| Document | Contents |
|---|---|
| [components.md](components.md) | Every component: props, emits, rendered output, behaviour |
| [state.md](state.md) | Pinia stores, API service, SSE streaming, chat history persistence |
| [../design/README.md](../design/README.md) | The design source — brand workbench and theme tokens |
