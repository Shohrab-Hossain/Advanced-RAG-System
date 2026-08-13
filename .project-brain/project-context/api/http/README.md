# HTTP endpoints

All routes are registered in `create_app()` in `Backend/src/app.py`. Client wrappers live in
`Frontend/src/services/api.js`.

<br>

## Summary

| Method | Path | Purpose | Client fn |
|---|---|---|---|
| POST | `/api/query` | Run the pipeline, stream SSE | `streamQuery()` |
| POST | `/api/upload` | Upload + index a document | `uploadFile()` |
| GET | `/api/documents` | Global index statistics | `getDocuments()` |
| DELETE | `/api/clear` | Wipe all indexed content | `clearDocuments()` |
| GET | `/api/knowledge-bases` | List uploaded KBs | `getKnowledgeBases()` |
| DELETE | `/api/knowledge-bases/<file_hash>` | Delete one KB | `deleteKnowledgeBase()` |
| GET | `/api/providers` | LLM providers + availability | `getProviders()` |
| GET | `/api/health` | Liveness check | `healthCheck()` |

<br>

---

<br>

### POST /api/query

Auth: none. Response is **not JSON** — it is `text/event-stream`.

Request:

```json
{ "query": "string (required, non-empty after strip)",
  "provider": "openai" | "ollama",
  "model": "string (optional; overrides the provider's default model)" }
```

`provider` defaults to `Config.DEFAULT_PROVIDER`, is lowercased and stripped.

Response `200`: an SSE stream. Response headers `Cache-Control: no-cache`,
`X-Accel-Buffering: no`, `Connection: keep-alive`. Frames are `data: {json}\n\n`. See
[`../sse-events/README.md`](../sse-events/README.md) for every event type. The terminal frames are:

```
data: {"type": "done", "data": {"answer": "...", "sources": [...], "metadata": {...}}}

data: {"type": "stream_end"}
```

`answer` falls back from `final_answer` to `answer`, and `sources` from `final_sources` to `sources`, if
the pipeline ended without the final pass writing them.

Errors: `400 {"error": "Missing or empty 'query' field"}` · `400 {"error": "provider must be 'openai' or
'ollama'"}`. Pipeline failures are **not** HTTP errors — they arrive as an in-stream `error` event.

<br>

---

<br>

### POST /api/upload

Auth: none. `multipart/form-data` with a single field **`file`**.

Response `200`:

```json
{
  "success": true,
  "file_name": "report.pdf",
  "file_hash": "<md5 hex>",
  "chunks_indexed": 42,
  "kb": { "id": "<md5>", "name": "report.pdf", "uploaded_at": "<ISO-8601 UTC>",
          "chunks": 42, "vectors": 42, "entities": 137, "edges": 980 },
  "stats": { "vector_total": 42, "bm25_total": 42,
             "graph": { "documents": 42, "entities": 137, "edges": 980 } }
}
```

Errors: `400 "No file field in request"` · `400 "Empty filename"` ·
`400 "Unsupported file type. Allowed: <list>"` ·
`422 "No text could be extracted from this file"` · `500 <exception string>`.

> [!NOTE]
> **The unsupported-type body is generated, not a fixed string.** `app.py:168-170` builds it as
> `f"Unsupported file type. Allowed: {', '.join(sorted(Config.ALLOWED_EXTENSIONS))}"`, so `<list>` is
> **every** extension in `Config.ALLOWED_EXTENSIONS` (35 of them, `config.py:62-65`), comma-separated in
> alphabetical order. Do not assert against a hardcoded four-item list — add an extension to the config
> and this response body changes with it.

<br>

---

<br>

### GET /api/documents

Response `200`:

```json
{ "vector_count": 42, "bm25_count": 42,
  "graph": { "documents": 42, "entities": 137, "edges": 980 } }
```

<br>

---

<br>

### DELETE /api/clear

Clears all three stores and the registry, and deletes every registered file from `UPLOAD_FOLDER`
(`OSError` on a file delete is swallowed).

Response `200`: `{ "success": true, "message": "All documents cleared" }`

<br>

---

<br>

### GET /api/knowledge-bases

Response `200`: `{ "knowledge_bases": [ <kb entry>, … ] }` — newest first, sorted by `uploaded_at`
descending. Entry shape as in the upload response's `kb`.

<br>

---

<br>

### DELETE /api/knowledge-bases/&lt;file_hash&gt;

Removes the file's chunks from all three stores, drops the registry entry, and deletes the uploaded file.
Returns `200` with post-deletion totals even when `file_hash` is unknown — there is no `404`:

```json
{ "success": true,
  "stats": { "vector_total": 0, "bm25_total": 0,
             "graph": { "documents": 0, "entities": 0, "edges": 0 } } }
```

<br>

---

<br>

### GET /api/providers

Response `200`:

```json
{
  "providers": [
    { "id": "openai", "label": "OpenAI", "model": "gpt-4o-mini",
      "available": true,
      "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"] },
    { "id": "ollama", "label": "Local (Ollama)", "model": "llama3.2",
      "base_url": "http://localhost:11434",
      "available": false, "models": [] }
  ],
  "default": "openai"
}
```

`openai.available` is `bool(Config.OPENAI_API_KEY)`. The `openai.models` list is hardcoded. The Ollama
entry is populated from `check_ollama()`, which may additionally carry `error` (probe failed) or
`warning: "Connected but could not list models"`. **The API key itself is never returned.**

<br>

---

<br>

### GET /api/health

Response `200`: `{ "status": "healthy" }` — one key, and that is the whole body (`app.py:307-309`). There
is **no** `version` field; nothing in the API reports a version. Used by `NavBar.vue` on mount to light the
connectivity indicator, and by `dev.py:173-187` as the launcher's readiness probe.
