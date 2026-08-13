# HTTP endpoints

All eight routes are registered in `create_app()` in `Backend/src/app.py` — one factory, one file.

The **client side is split by domain across two modules**, one per frontend subsystem, and every route
belongs to exactly one of them. There is no shared api module and neither imports the other:

| Client module | Owns | Routes |
|---|---|---|
| `Frontend/src/subsystems/rag/ragApi.js` | asking the pipeline a question, and what it needs to ask | 3 — `/api/query`, `/api/providers`, `/api/health` |
| `Frontend/src/subsystems/knowledge-base/kbApi.js` | the corpus the pipeline searches | 5 — `/api/upload`, `/api/documents`, `/api/clear`, `/api/knowledge-bases`, `/api/knowledge-bases/<file_hash>` |

`/api/providers` sits with the RAG client rather than a configuration one because the chosen provider
**rides the query itself** — it is a field of the `/api/query` body, not standalone settings state.

<br>

## Summary

| Method | Path | Purpose | Client fn | Client module |
|---|---|---|---|---|
| POST | `/api/query` | Run the pipeline, stream SSE | `streamQuery()` `:40` | `ragApi.js` |
| POST | `/api/upload` | Upload + index a document | `uploadFile()` `:17` | `kbApi.js` |
| GET | `/api/documents` | Global index statistics | `getDocuments()` `:33` | `kbApi.js` |
| DELETE | `/api/clear` | Wipe all indexed content | `clearDocuments()` `:38` | `kbApi.js` |
| GET | `/api/knowledge-bases` | List uploaded KBs | `getKnowledgeBases()` `:45` | `kbApi.js` |
| DELETE | `/api/knowledge-bases/<file_hash>` | Delete one KB | `deleteKnowledgeBase()` `:50` | `kbApi.js` |
| GET | `/api/providers` | LLM providers + availability | `getProviders()` `:23` | `ragApi.js` |
| GET | `/api/health` | Liveness check | `healthCheck()` `:18` | `ragApi.js` |

Eight routes, eight exports, 3 + 5. Each module builds its **own** axios client from its own read of
`VUE_APP_API_URL` (`ragApi.js:12-14`, `kbApi.js:11-13`) — the base-URL behaviour is identical, there are
simply two construction sites. Adding a route means adding it to the subsystem that owns the capability,
never to a shared client.

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
