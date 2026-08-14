# adRAG — Frontend

Vue 3 single-page application. Chat interface, knowledge base management, real-time pipeline tracking via SSE, and LLM provider configuration.

## Quick Start

```bash
npm install
npm run serve     # dev server → http://localhost:8080
npm run build     # production build → dist/
npm run lint      # ESLint over src/
```

Requires the Backend API running on `http://localhost:5000`. All `/api/*` requests are proxied automatically in development.

## Stack

- **Vue 3** + Vue Router 4 + Pinia
- **Tailwind CSS** (PostCSS)
- **Vue CLI** (webpack)
- **marked** — Markdown rendering
- **axios** — HTTP client

## Layout

```
Frontend/
├── src/           the application — components by OWNERSHIP, state + HTTP FLAT by kind
├── public/        served VERBATIM — the build copies this folder and nothing else
├── design/        design SOURCE you edit — never served, never imported by the app
├── Documentation/ in-depth docs
└── dist/          build output — git-ignored, never edited
```

Two folders are easy to confuse, and the difference is load-bearing:

| | `design/` | `public/` |
|---|---|---|
| **Holds** | the source you edit — brand masters, design tokens | the promoted copies the server sends |
| **Edited by hand?** | ✅ this is the only place | ❌ never — edit the master and re-promote |
| **Served?** | ❌ never | ✅ verbatim |

**The same logo legitimately exists in both.** Deleting the `public/` copy breaks serving; deleting the
`design/` source loses the ability to regenerate it at a new size. Never symlink one to the other.

### `design/` — the design source

```
design/
├── brand/logo/    the master → derivative chain: svg/ png/ artifacts/{meta,scripts,source,reference}
└── theme/         tokens.json — THE single source of the design tokens, read by tailwind.config.js
```

A design token goes in `design/theme/tokens.json`, **not** in `tailwind.config.js` — that file only reads
it. See [`design/README.md`](design/README.md) and [`design/theme/contract.md`](design/theme/contract.md).

### `public/` — the shipped tree

```
public/
├── index.html     the Vue CLI build template (not a root index.html — that is the Vite convention)
├── brand-logo/    consumed by THIS app — our path, our names
├── favicon/       consumed by browsers + platforms — names THEY dictate
└── images/og/     consumed by other people's sites — crawlers cache these for weeks
```

Three consumers, three folders, and they must not be merged. Each carries a README naming what belongs in
it. **They are empty today** — no brand master exists yet, so there is nothing to promote, and
`/favicon.ico` currently 404s. The next steps are tracked in
[`design/AGENT-NOTES.md`](design/AGENT-NOTES.md).

## Documentation

Detailed docs in [`Documentation/`](Documentation/):

| File | Contents |
|---|---|
| [Documentation/README.md](Documentation/README.md) | Views, project structure, where a new file goes, setup |
| [Documentation/components.md](Documentation/components.md) | Every component — props, emits, behaviour |
| [Documentation/state.md](Documentation/state.md) | Pinia stores, API service, SSE streaming, history |
| [design/README.md](design/README.md) | The design source — brand workbench + theme tokens |
