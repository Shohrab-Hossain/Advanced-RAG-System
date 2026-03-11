# adRAG — Frontend

Vue 3 single-page application. Chat interface, knowledge base management, real-time pipeline tracking via SSE, and LLM provider configuration.

## Quick Start

```bash
npm install
npm run serve     # dev server → http://localhost:8080
npm run build     # production build → dist/
```

Requires the Backend API running on `http://localhost:5000`. All `/api/*` requests are proxied automatically in development.

## Stack

- **Vue 3** + Vue Router 4 + Pinia
- **Tailwind CSS** (PostCSS)
- **Vue CLI** (webpack)
- **marked** — Markdown rendering
- **axios** — HTTP client

## Documentation

Detailed docs in [`documentation/`](documentation/):

| File | Contents |
|---|---|
| [documentation/README.md](documentation/README.md) | Views, project structure, setup |
| [documentation/components.md](documentation/components.md) | Every component — props, emits, behaviour |
| [documentation/state.md](documentation/state.md) | Pinia stores, API service, SSE streaming, history |
