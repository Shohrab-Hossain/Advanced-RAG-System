# adRAG — Frontend

The frontend is a Vue 3 single-page application built with Vite, Pinia, and Tailwind CSS. It provides a chat interface for querying the RAG pipeline, a knowledge base management page for uploading documents, a configuration page for selecting LLM providers, and real-time animated pipeline progress driven by Server-Sent Events from the backend.

---

## Table of Contents

- [Setup & Run](#setup--run)
- [Project Structure](#project-structure)
- [Views](#views)
- [Detailed Documentation](#detailed-documentation)

---

## Setup & Run

### Prerequisites

- Node.js 18+
- Backend running on `http://localhost:5000` (Vite proxies `/api/*` to it)

### Install & Run

```bash
cd Frontend
npm install
npm run dev       # dev server on http://localhost:5173
npm run build     # production build → dist/
```

---

## Project Structure

```
Frontend/
├── index.html                    # Entry HTML — title, meta tags, fonts
├── vite.config.js                # Vite config — Vue plugin, /api proxy → :5000
├── tailwind.config.js            # Tailwind theme extensions
├── package.json
└── src/
    ├── main.js                   # App bootstrap (Vue + Pinia + Router)
    ├── App.vue                   # Root layout (NavBar + RouterView + ModalDialog)
    ├── assets/
    │   └── main.css              # Tailwind layers, custom animations, page transitions
    ├── router/
    │   └── index.js              # Route definitions (/, /chat, /knowledge-base, /configuration)
    ├── stores/
    │   ├── rag.js                # Pinia: pipeline state, chat history, document index
    │   └── ui.js                 # Pinia: theme, modal dialog system
    ├── services/
    │   └── api.js                # All API calls + SSE streaming (fetch + ReadableStream)
    ├── views/
    │   ├── HomeView.vue          # Landing page with pipeline overview
    │   ├── ChatView.vue          # Main chat + history sidebar
    │   ├── KnowledgeBaseView.vue # File upload + index stats + KB management
    │   └── ConfigView.vue        # LLM provider/model selection
    └── components/
        ├── NavBar.vue            # Top navigation bar + connection status
        ├── ModalDialog.vue       # Reusable alert/confirm dialog (promise-based)
        ├── QueryInput.vue        # Query textarea + submit/cancel buttons
        ├── PipelineTracker.vue   # Animated pipeline stage progress
        ├── StageRow.vue          # Single pipeline stage row with status chips
        ├── ResultDisplay.vue     # Markdown answer + sources grid
        ├── SourceCard.vue        # Individual source card with rerank score
        ├── LLMSelector.vue       # Provider/model picker with availability status
        ├── FileTypeIcon.vue      # File extension or retrieval source icon
        ├── StatBadge.vue         # Simple value + label stat pill
        ├── FileUpload.vue        # Single-file upload widget (legacy)
        └── KnowledgeBases.vue    # Collapsible KB list widget (legacy)
```

---

## Views

### Home (`/`)
Landing page. Displays the adRAG hero section, three navigation cards (Chat, Knowledge Base, Configuration), and a grid of the 8 pipeline stages with descriptions. Purely informational — no interactive state.

### Chat (`/chat`)
Main interface. Contains the query input, real-time pipeline tracker (8 animated stage rows), the final answer rendered as Markdown, and a source cards grid. A collapsible left sidebar shows the full chat history (persisted to `localStorage`, max 50 items). Selecting a history item replays the full pipeline state snapshot.

### Knowledge Base (`/knowledge-base`)
Document management. Supports drag-and-drop or click-to-browse file upload (PDF, DOCX, TXT, Markdown) with multi-file batch support. Shows a unified progress bar with three phases: uploading (determinate), processing on server (indeterminate shimmer), and indexing (determinate). Displays three index stat cards (Vector Store, BM25, Knowledge Graph) and a grid of uploaded KB cards with per-file deletion.

### Configuration (`/configuration`)
LLM provider selection. Shows availability and API key status for OpenAI and Ollama. Allows selecting a specific model from each provider. Ollama availability is polled every 15 seconds.

---

## Detailed Documentation

| Document | Contents |
|---|---|
| [components.md](components.md) | Every component: props, emits, rendered output, behaviour |
| [state.md](state.md) | Pinia stores, API service, SSE streaming, chat history persistence |
