# Frontend State & API

This document covers the two Pinia stores, the API service layer, SSE streaming, and chat history persistence.

---

## Pinia Store: `rag.js`

**File:** `src/stores/rag.js`

The central store for the entire application. Manages LLM provider selection, document index stats, the query lifecycle, pipeline stage statuses, the final answer, and chat history.

### State

#### LLM Provider

| Ref | Type | Description |
|---|---|---|
| `llmProvider` | `"openai" \| "ollama"` | Currently selected provider |
| `openaiModel` | string | Currently selected OpenAI model |
| `ollamaModel` | string | Currently selected Ollama model |
| `availableProviders` | object | Provider map fetched from `/api/providers`. Shape: `{ openai: { available, model, models }, ollama: { available, model, models, base_url } }` |

#### Document Index

| Ref | Type | Description |
|---|---|---|
| `indexStats` | object | `{ vector_count, bm25_count, graph: { documents, entities, edges } }` |
| `knowledgeBases` | array | List of KB objects from `/api/knowledge-bases` |
| `uploading` | boolean | `true` while the file is transferring (XHR in progress) |
| `uploadProgress` | number | 0–100 — file transfer percentage |
| `isIndexing` | boolean | `true` while the indexing animation is running |
| `indexingProgress` | number | 0–100 — indexing animation percentage |
| `uploadQueueCurrent` | number | Which file in a batch is currently being processed (1-based) |
| `uploadQueueTotal` | number | Total files in the current batch |
| `uploadResult` | object \| null | Last upload outcome: `{ file_name, chunks_indexed }` or `{ error: "..." }` |

#### Query State

| Ref | Type | Description |
|---|---|---|
| `query` | string | Current query text |
| `isRunning` | boolean | `true` while the SSE stream is active |
| `stageStatuses` | reactive object | Keyed by stage id: `{ status, message, details }` per stage |
| `events` | array | Raw event log: `[{ type, data, ts }]` for debugging |
| `retryCount` | number | How many reflection retries occurred in the current run |

#### Result

| Ref | Type | Description |
|---|---|---|
| `answer` | string | Markdown-formatted final answer |
| `sources` | array | Source objects to render in the sources grid |
| `metadata` | object | `{ grounded, confidence, retry_count, query_type }` |
| `error` | string | Error message if the pipeline failed |
| `isHistoryResult` | boolean | `true` when the displayed result was loaded from history (not a live run) |

#### Chat History

| Ref | Type | Description |
|---|---|---|
| `chatHistory` | array | Array of history items, newest first. Loaded from and persisted to `localStorage`. |

### Computed

| Name | Returns | Description |
|---|---|---|
| `hasResult` | boolean | `true` when `answer` is non-empty |
| `hasDocuments` | boolean | `true` when `indexStats.vector_count > 0` |

### Actions

#### Query Actions

**`runQuery(q: string)`**

Starts a new RAG pipeline run for query `q`.

1. Sets `isRunning = true`, calls `resetPipeline()`
2. Determines `model` from the selected provider
3. Calls `streamQuery(q, provider, model, callbacks)` from `api.js`
4. `onEvent` callback pipes each SSE event through `_applyEvent()`
5. `onDone` callback:
   - Sets `answer`, `sources`, `metadata`
   - Saves a snapshot to `chatHistory` (including `stageStatuses` and `retryCount`)
   - Calls `_persistHistory()`
6. `onError` callback sets `error` and clears `isRunning`

**`abortQuery()`**

Calls the abort function returned by `streamQuery()` (via `AbortController`). Sets `isRunning = false` and `error = "Query cancelled"`.

**`resetPipeline()`**

Clears all pipeline state: stage statuses back to `idle`, `answer`, `sources`, `metadata`, `error`, `retryCount`, `isHistoryResult`.

**`_applyEvent(type, data)`** *(internal)*

Processes a single SSE event and updates `stageStatuses`:

| Event type | Effect |
|---|---|
| `stage_start` | Sets stage to `active` |
| `stage_complete` / `retrieval_result` | Sets stage to `complete`, stores `details` |
| `stage_skip` | Sets stage to `skipped` |
| `stage_error` | Sets stage to `error` |
| `retry` | Increments `retryCount`; resets retrieval stages back to `idle` so they re-animate |
| `finalize` | Sets stage to `complete` |

All events are also appended to `events` for debugging.

---

#### Upload Actions

**`uploadDocument(file, { queueCurrent, queueTotal })`**

Two-phase upload with seamless progress:

```
Phase 1 (uploading):
  uploading = true
  uploadProgress → 0–100 via XHR onUploadProgress callback

  When XHR hits 100%:  ← server still processing
    isIndexing = true    ← set BEFORE uploading = false
    uploading  = false   ← Vue batches both; no flash-of-empty

Phase 2 (indexing animation):
  indexingProgress → 0–95 quickly, holds at 95 until server responds
  Server responds → isIndexing = false, indexingProgress = 100
  refreshStats() + fetchKnowledgeBases() update the UI
  uploadResult = server response
```

Setting `isIndexing = true` before `uploading = false` in the same synchronous tick causes Vue to batch both DOM updates together, eliminating the blank gap between the two phases.

**`refreshStats()`** — `GET /api/documents` → updates `indexStats`

**`fetchKnowledgeBases()`** — `GET /api/knowledge-bases` → updates `knowledgeBases`

**`removeKnowledgeBase(fileHash)`** — `DELETE /api/knowledge-bases/{fileHash}` → refreshes list and stats

**`clearIndex()`** — `DELETE /api/clear` → clears `knowledgeBases`, refreshes stats

**`resetUploadResult()`** — Sets `uploadResult = null`

---

#### Provider Actions

**`fetchProviders()`**

Calls `GET /api/providers` and:
1. Populates `availableProviders` map
2. Auto-selects the server's default provider (if available)
3. Falls back to OpenAI, then Ollama
4. Pre-fills `openaiModel` with the server default if not already set

**`setOllamaModel(model)`** — Updates `ollamaModel`

**`setOpenaiModel(model)`** — Updates `openaiModel`

---

#### History Actions

**`loadHistoryItem(item)`**

Restores a full history snapshot into the store:
- Sets `query`, `answer`, `sources`, `metadata`, `retryCount`, `isHistoryResult = true`
- Restores `stageStatuses` from the saved snapshot (if the item has one; old items default all stages to `complete`)

**`deleteHistoryItem(id)`** — Removes one item from `chatHistory` and persists

**`clearChatHistory()`** — Empties `chatHistory` and persists

---

### Pipeline Stages Constant

`STAGES` is an exported constant (array) defining the 8 pipeline stages in display order:

```js
export const STAGES = [
  { id: 'planner',        label: 'Self-RAG Planner',      icon: '🧠', desc: '...' },
  { id: 'retrieval',      label: 'Hybrid Retrieval',       icon: '🔍', desc: '...' },
  { id: 'external_tools', label: 'External Tools',         icon: '🌐', desc: '...' },
  { id: 'aggregator',     label: 'Evidence Aggregator',    icon: '📚', desc: '...' },
  { id: 'reranker',       label: 'Cross-Encoder Reranker', icon: '🎯', desc: '...' },
  { id: 'compressor',     label: 'Context Compressor',     icon: '✂️',  desc: '...' },
  { id: 'reasoning',      label: 'Reasoning Agent',        icon: '💡', desc: '...' },
  { id: 'reflection',     label: 'Self-Reflection Agent',  icon: '🔮', desc: '...' },
]
```

The stage `id` values must match the `stage` field in the SSE events emitted by the backend nodes.

---

### Chat History Persistence

History is stored in `localStorage` under the key `rag-chat-history`.

**Write:** `_persistHistory()` serialises `chatHistory.value.slice(0, 50)` to JSON and saves it. This caps storage at 50 items.

**Read:** `_loadHistory()` is called once at store initialisation via `const chatHistory = ref(_loadHistory())`.

**History item shape:**
```js
{
  id:           "1705316200000",    // Date.now() string
  query:        "What is RAG?",
  answer:       "RAG stands for...",
  sources:      [ ...source objects ],
  metadata:     { grounded: true, confidence: 0.91, ... },
  stageStatuses: { planner: { status: "complete", ... }, ... },
  retryCount:   0,
  timestamp:    1705316200000,
}
```

`stageStatuses` is a deep clone (`JSON.parse(JSON.stringify(...))`) taken at the moment the `onDone` callback fires, so it captures the final state of every stage for that run.

---

## Pinia Store: `ui.js`

**File:** `src/stores/ui.js`

Manages theme preference and the centralised modal dialog system.

### State

| Ref | Type | Description |
|---|---|---|
| `theme` | `"dark" \| "light"` | Current colour theme. Persisted to `localStorage` under `"rag-theme"`. |
| `modal` | object \| null | Current modal config or `null` when no dialog is open. |

### Actions

**`setTheme(t)`** — Sets `theme`, saves to localStorage, and toggles the `dark` class on `document.documentElement` (Tailwind's dark mode selector).

**`toggleTheme()`** — Flips between `"dark"` and `"light"`.

**`alert(message)`** — Opens an alert dialog. Returns a Promise that resolves when the user clicks OK.

**`confirm(message, options)`** — Opens a confirm dialog. Returns a Promise that resolves to `true` (confirmed) or `false` (cancelled).

Options:
```js
{
  danger:      false,     // Makes confirm button red
  confirmText: "OK",
  cancelText:  "Cancel",
}
```

**`close(result)`** — Called by `ModalDialog` component when the user clicks a button. Resolves the pending promise with `result` and clears `modal`.

**Usage pattern** (any component):
```js
const ui = useUiStore()

// Confirmation with danger styling
const ok = await ui.confirm('Delete all documents?', {
  danger: true,
  confirmText: 'Yes, delete',
  cancelText: 'No, keep them',
})
if (ok) await store.clearIndex()
```

---

## API Service (`services/api.js`)

All communication with the Flask backend goes through this module.

### Base URL

Set to `""` (empty string), meaning all requests go to the same origin. Vite proxies `/api/*` to `http://localhost:5000` in development.

### Standard REST Functions

All use `axios` and return the `response.data` directly.

| Function | Method | Path | Description |
|---|---|---|---|
| `uploadFile(file, onProgress)` | POST | `/api/upload` | Multipart upload with XHR progress callback |
| `getDocuments()` | GET | `/api/documents` | Index statistics |
| `clearDocuments()` | DELETE | `/api/clear` | Wipe all stores |
| `healthCheck()` | GET | `/api/health` | Backend connectivity check |
| `getProviders()` | GET | `/api/providers` | LLM provider availability |
| `getKnowledgeBases()` | GET | `/api/knowledge-bases` | List uploaded KBs |
| `deleteKnowledgeBase(fileHash)` | DELETE | `/api/knowledge-bases/{fileHash}` | Remove one KB |

**`uploadFile` detail:**
```js
uploadFile(file, onProgress)
```
Uses `axios` with a `FormData` payload and `onUploadProgress` callback. The callback fires as the browser transfers bytes to the server — it reaches 100% when the transfer is complete, but **before** the server finishes indexing. This is why the upload → indexing transition needs the two-phase progress approach in the store.

### SSE Streaming

**`streamQuery(query, provider, model, { onEvent, onDone, onError })`**

Uses the Fetch API + `ReadableStream` instead of the browser's `EventSource` because `EventSource` only supports GET requests, but the query endpoint requires a POST with a JSON body.

```js
const controller = new AbortController()
const response = await fetch('/api/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query, provider, model }),
  signal: controller.signal,
})

const reader = response.body.getReader()
const decoder = new TextDecoder()

// Read chunks from the stream
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  const text = decoder.decode(value)
  // Parse SSE lines: "data: {json}\n\n"
  for (const line of text.split('\n')) {
    if (!line.startsWith('data: ')) continue
    const { type, data } = JSON.parse(line.slice(6))
    if (type === 'done') onDone(data)
    else if (type === 'error') onError(data.message)
    else onEvent(type, data)
  }
}
```

**Returns:** `{ abort: () => void }` — calling `abort()` triggers the `AbortController` signal, which cancels the fetch and closes the stream.

---

## Router (`router/index.js`)

Uses Vue Router 4 with HTML5 history mode (`createWebHistory`).

| Path | Component | Page |
|---|---|---|
| `/` | `HomeView` | Landing page |
| `/chat` | `ChatView` | Query interface |
| `/knowledge-base` | `KnowledgeBaseView` | Document management |
| `/configuration` | `ConfigView` | LLM provider settings |

---

## Vite Configuration (`vite.config.js`)

**Dev server port:** 5173

**API proxy:**
```js
proxy: {
  '/api': {
    target:       'http://localhost:5000',
    changeOrigin: true,
  }
}
```

All requests to `/api/*` in development are forwarded to the Flask backend. In production builds, the frontend is served as static files and a reverse proxy (nginx, etc.) should handle the `/api` routing.
