# API Reference

All endpoints are prefixed with `/api`. The server runs on `http://localhost:5000` by default.

CORS is configured to allow requests from `http://localhost:5173` (Vite dev), `http://localhost:3000`, `http://localhost:8080`, and the `FRONTEND_URL` env var.

---

## Endpoints

### `POST /api/query`

Run the RAG pipeline for a query. Returns a **Server-Sent Events (SSE)** stream.

Because the client needs to send a JSON body, the frontend uses `fetch` + `ReadableStream` instead of the browser's `EventSource` API (which only supports GET).

**Request body:**
```json
{
  "query":    "What is retrieval-augmented generation?",
  "provider": "openai",
  "model":    "gpt-4o"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | The user's question |
| `provider` | `"openai"` \| `"ollama"` | No | LLM provider (default: `DEFAULT_PROVIDER` env var) |
| `model` | string | No | Model name override. For Ollama: selects a specific local model. For OpenAI: selects a specific GPT model. |

**Response:** `Content-Type: text/event-stream`

The stream emits a series of JSON-encoded SSE frames, one per pipeline event. Each frame has the form:

```
data: {"type": "<event_type>", "data": {...}}\n\n
```

**SSE event reference:**

| `type` | Description | Key `data` fields |
|---|---|---|
| `stage_start` | A pipeline node has begun executing | `stage` (node id), `message` |
| `stage_complete` | A node completed successfully | `stage`, `message`, `details` (node-specific) |
| `stage_skip` | A node was intentionally skipped | `stage`, `message` |
| `stage_error` | A node failed (pipeline continues with fallback) | `stage`, `error` |
| `retrieval_result` | Retrieval node finished; document counts ready | `stage`, `vector_count`, `bm25_count`, `graph_count`, `web_count` |
| `retry` | Reflection rejected answer; pipeline looping back | `stage`, `attempt` (1-based) |
| `finalize` | Reflection accepted the answer | `stage`, `message` |
| `done` | Pipeline complete; final answer available | `answer` (string), `sources` (array), `metadata` (object) |
| `stream_end` | Stream is closing (sent before connection closes) | — |

**`done` event `data` shape:**
```json
{
  "answer": "Retrieval-Augmented Generation (RAG) is...",
  "sources": [
    {
      "index":         1,
      "file_name":     "rag_paper.pdf",
      "source":        "vector",
      "score":         0.87,
      "rerank_score":  3.21,
      "content_preview": "RAG combines retrieval...",
      "page":          4
    }
  ],
  "metadata": {
    "grounded":    true,
    "confidence":  0.91,
    "retry_count": 0,
    "query_type":  "factual"
  }
}
```

**Errors:**
- `400` — Missing or empty `query` field
- `400` — `provider` is not `"openai"` or `"ollama"`
- Stream `error` event — pipeline exception (non-fatal errors emit `stage_error` and continue)

**Stream timeout:** 3 minutes. If the pipeline hasn't produced output in 3 minutes, the stream closes with an `error` event.

---

### `POST /api/upload`

Upload a document, chunk it, and index it into all three retrieval stores.

**Request:** `multipart/form-data` with a single `file` field.

Accepted file types: `.pdf`, `.txt`, `.md`, `.docx` (up to 50 MB)

**Response `200`:**
```json
{
  "success":        true,
  "file_name":      "my_document.pdf",
  "file_hash":      "a3f8c2e1...",
  "chunks_indexed": 42,
  "kb": {
    "id":          "a3f8c2e1...",
    "name":        "my_document.pdf",
    "uploaded_at": "2024-01-15T10:30:00+00:00",
    "chunks":      42,
    "vectors":     42,
    "entities":    18,
    "edges":       27
  },
  "stats": {
    "vector_total": 142,
    "bm25_total":   142,
    "graph": {
      "documents": 42,
      "entities":  18,
      "edges":     27
    }
  }
}
```

**Note:** If the same file (by name) is uploaded again, the endpoint first removes all existing data for that `file_hash` from all three stores before re-indexing.

**Errors:**
- `400` — No `file` field in request
- `400` — Empty filename
- `400` — Unsupported file type
- `422` — File loaded but no text could be extracted
- `500` — Indexing error

---

### `GET /api/documents`

Return current index statistics across all three stores.

**Response `200`:**
```json
{
  "vector_count": 142,
  "bm25_count":   142,
  "graph": {
    "documents": 42,
    "entities":  18,
    "edges":     27
  }
}
```

---

### `GET /api/knowledge-bases`

Return all uploaded knowledge bases with per-file stats, sorted newest first.

**Response `200`:**
```json
{
  "knowledge_bases": [
    {
      "id":          "a3f8c2e1...",
      "name":        "my_document.pdf",
      "uploaded_at": "2024-01-15T10:30:00+00:00",
      "chunks":      42,
      "vectors":     42,
      "entities":    18,
      "edges":       27
    }
  ]
}
```

---

### `DELETE /api/knowledge-bases/<file_hash>`

Remove a specific knowledge base from all three stores and delete its physical file from disk.

**Path parameter:** `file_hash` — the `id` field from the KB listing

**Response `200`:**
```json
{
  "success": true,
  "stats": {
    "vector_total": 100,
    "bm25_total":   100,
    "graph": { "documents": 35, "entities": 14, "edges": 20 }
  }
}
```

---

### `DELETE /api/clear`

Wipe **all** indexed documents from all three stores, clear the KB registry, and delete all uploaded files from disk.

**Response `200`:**
```json
{
  "success": true,
  "message": "All documents cleared"
}
```

---

### `GET /api/providers`

Return available LLM providers, their availability status, and model lists.

**Response `200`:**
```json
{
  "providers": [
    {
      "id":        "openai",
      "label":     "OpenAI",
      "model":     "gpt-4o-mini",
      "available": true,
      "models":    ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    },
    {
      "id":        "ollama",
      "label":     "Local (Ollama)",
      "model":     "llama3.2",
      "base_url":  "http://localhost:11434",
      "available": true,
      "models":    ["llama3.2", "mistral", "phi3"]
    }
  ],
  "default": "openai"
}
```

- `available` for OpenAI is `true` only if `OPENAI_API_KEY` is set in environment
- `available` for Ollama is `true` if the Ollama server responded to a health probe
- `models` for Ollama is populated by querying `/api/tags` on the Ollama server

---

### `GET /api/health`

Health check endpoint. Used by the frontend NavBar to display connection status.

**Response `200`:**
```json
{
  "status":  "ok",
  "version": "1.0.0"
}
```

---

## Error Responses

All non-streaming endpoints return errors in this format:

```json
{ "error": "Human-readable error description" }
```

Standard HTTP status codes:
- `400` — Bad request (validation failed, missing fields)
- `422` — Unprocessable entity (file loaded but unusable)
- `500` — Internal server error
