<div align="center">

# 📚 Knowledge Base API

### Five routes that write to three stores and a registry with no transaction, no lock, and no authentication.

<br>

[![Routes](https://img.shields.io/badge/routes-5-1c7ed6)](#-1-the-five-routes)
[![Upload cap](https://img.shields.io/badge/upload%20cap-50%20MB-7c5cff)](#24-error-responses)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Extensions](https://img.shields.io/badge/accepted%20extensions-35-f59e0b)](#27-the-two-extension-checks)
[![Dedup](https://img.shields.io/badge/dedup-content%20MD5-f59e0b)](#25-what-happens-behind-the-route)
[![Auth](https://img.shields.io/badge/auth-none-ef4444)](#-9-security-notes)

</div>

<br>

---

<br>

## Content Tree

<pre>
Knowledge Base API
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-five-routes">🧭 1. The five routes</a>
│
├── <a href="#-2-upload-a-document">📤 2. Upload a document</a>
│   ├── <a href="#21-request">2.1 Request</a>
│   ├── <a href="#22-how-to-call">2.2 How to call</a>
│   ├── <a href="#23-success-response">2.3 Success response</a>
│   ├── <a href="#24-error-responses">2.4 Error responses</a>
│   ├── <a href="#25-what-happens-behind-the-route">2.5 What happens behind the route</a>
│   ├── <a href="#26-filename-sanitisation-and-what-it-costs">2.6 Filename sanitisation, and what it costs</a>
│   └── <a href="#27-the-two-extension-checks">2.7 The two extension checks</a>
│
├── <a href="#-3-read-index-statistics">📊 3. Read index statistics</a>
│
├── <a href="#-4-list-knowledge-bases">📚 4. List knowledge bases</a>
│
├── <a href="#-5-delete-one-knowledge-base">❌ 5. Delete one knowledge base</a>
│
├── <a href="#-6-clear-everything">🧹 6. Clear everything</a>
│
├── <a href="#-7-the-two-statistics-shapes">🧮 7. The two statistics shapes</a>
│
├── <a href="#%EF%B8%8F-8-limitations-and-failure-modes">⚠️ 8. Limitations and failure modes</a>
│
├── <a href="#-9-security-notes">🔒 9. Security notes</a>
│
└── <a href="#-10-related-reading">🔗 10. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

Five routes manage the corpus: one writes to it, two read it, two delete from it. All five live in
`routes/knowledge_base/knowledge_base_routes.py` (96 lines of pure HTTP framing) and delegate every
store operation to `routes/knowledge_base/services.py` (114 lines that import no Flask).

That split exists because of one property of the system, stated in the service module's own docstring
(`services.py:6-9`):

> *"Every ingest and every delete must touch ALL THREE stores AND the registry. There are no transactions
> and no cross-store lock, so a partial write leaves the corpus inconsistent with nothing surfaced —
> which is why the ordering here is fixed and why the routes call these functions rather than reaching
> into a store."*

> [!CAUTION]
> **None of these routes is authenticated.** `DELETE /api/clear` wipes all three stores, the registry,
> and every uploaded file named by a registry entry — in one unauthenticated request, with no
> confirmation parameter, no dry run, no backup and no undo. The confirmation modal the UI shows is
> **client-side only**; the API has no such gate. `DELETE /api/knowledge-bases/<file_hash>` deletes any
> knowledge base by id, and the ids are enumerable through the equally unauthenticated
> `GET /api/knowledge-bases`. See [`../security.md`](../security.md#-3-no-authentication-on-any-route).

---

## 🧭 1. THE FIVE ROUTES

Base URL in development: `http://localhost:5000`.

| # | Method | Path | Purpose | Success | Error statuses |
|---|---|---|---|---|---|
| 1 | `POST` | `/api/upload` | index one document into all three stores | `200` | `400` · `422` · `500` · `413` |
| 2 | `GET` | `/api/documents` | current totals across the three stores | `200` | none |
| 3 | `GET` | `/api/knowledge-bases` | the registry, newest first | `200` | none |
| 4 | `DELETE` | `/api/knowledge-bases/<file_hash>` | remove one knowledge base | `200` | none — see §5 |
| 5 | `DELETE` | `/api/clear` | wipe everything | `200` | none |

**Only `POST /api/upload` can return an error status at all.** The other four have no `try` and no
validation branch; every one of them answers `200` on every reachable input, including inputs that did
nothing.

Two cross-cutting facts before the per-route detail:

- **Ingestion is fully synchronous and has no progress channel.** `POST /api/upload` blocks for the
  entire load → chunk → embed → index cycle. There is no job id, no polling endpoint and no SSE stream
  for ingestion. The only genuine progress signal is the browser's own byte-transfer callback
  (`Frontend/src/services/kbApi.js:22-26`); the "indexing" bar in the UI is a **client-side animation**
  easing to 95% (`kbStore.js:61-75`).
- **Two different response shapes report the same three numbers** — `vector_count`/`bm25_count` on
  `GET /api/documents`, and `vector_total`/`bm25_total` on upload and delete. §7 covers it.

---

## 📤 2. UPLOAD A DOCUMENT

```text
POST /api/upload
```

Loads, chunks, embeds and indexes one file into the vector store, the BM25 store and the knowledge
graph, then records it in the registry.

**Auth:** none required — and none possible.

### 2.1 Request

`Content-Type: multipart/form-data`, with **exactly one field**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file part | ✅ | the field name is literally `"file"` (`:45`, `:48`) |

No other form field is read — no title, no tags, no knowledge-base selector, no overwrite flag. The
frontend matches exactly (`kbApi.js:18-19`: `form.append('file', file)`).

### 2.2 How to call

**cURL**

```bash
curl -X POST http://localhost:5000/api/upload \
  -F 'file=@./rag-survey.pdf'
```

**JavaScript (fetch)**

```js
const form = new FormData()
form.append('file', file)          // 'file' is the exact field name the route reads

const res = await fetch('http://localhost:5000/api/upload', {
  method: 'POST',
  body: form,                      // do NOT set Content-Type — the browser sets the boundary
})

if (!res.ok) {
  // 400/422/500 are JSON; a 413 is HTML, so parse defensively
  const err = await res.json().catch(() => ({ error: res.statusText }))
  throw new Error(`${res.status}: ${err.error}`)
}

const { file_hash, chunks_indexed, kb, stats } = await res.json()
console.log(`indexed ${chunks_indexed} chunks as ${file_hash}`)
```

**Python (requests)**

```python
import requests

with open("rag-survey.pdf", "rb") as fh:
    res = requests.post(
        "http://localhost:5000/api/upload",
        files = {"file": ("rag-survey.pdf", fh)},
        timeout = (5, 600),   # indexing is synchronous — allow a generous read timeout
    )

if res.status_code != 200:
    # 400/422/500 carry {"error": "..."}; a 413 carries HTML
    try:
        raise RuntimeError(f"{res.status_code}: {res.json()['error']}")
    except ValueError:
        raise RuntimeError(f"{res.status_code}: {res.text[:200]}")

payload = res.json()
print(payload["chunks_indexed"], payload["file_hash"])
```

The read timeout matters. A large PDF is loaded, split, embedded chunk by chunk and written to three
stores before the response is produced — there is no early acknowledgement.

### 2.3 Success response

**`200 OK`** (`jsonify(payload)` with no explicit status, `:63`). Body built at `services.py:76-83`:

| Key | Type | Value |
|---|---|---|
| `success` | bool | always `true` |
| `file_name` | string | the **sanitised** filename (§2.6) — not necessarily what was uploaded |
| `file_hash` | string | MD5 of the file **content** (`ingestion/loader.py:48-54`) |
| `chunks_indexed` | int | the number of chunks written |
| `kb` | object | the registry entry — `id`, `name`, `uploaded_at`, `chunks`, `vectors`, `entities`, `edges` |
| `stats` | object | post-write totals — `vector_total`, `bm25_total`, `graph{documents,entities,edges}` |

```json
{
  "success": true,
  "file_name": "rag-survey.pdf",
  "file_hash": "9f2b1c4e8a7d3056b1e2f4a9c8d70b13",
  "chunks_indexed": 42,
  "kb": {
    "id": "9f2b1c4e8a7d3056b1e2f4a9c8d70b13",
    "name": "rag-survey.pdf",
    "uploaded_at": "2026-08-16T10:53:45.812004+00:00",
    "chunks": 42,
    "vectors": 42,
    "entities": 18,
    "edges": 27
  },
  "stats": {
    "vector_total": 142,
    "bm25_total": 142,
    "graph": { "documents": 142, "entities": 61, "edges": 88 }
  }
}
```

Three notes on those numbers:

- **`kb.chunks` and `kb.vectors` are always equal.** `vectors` is set to `len(texts)` with the comment
  *"1 chunk → 1 embedding"* (`services.py:71`).
- **`kb.entities` and `kb.edges` are at different scopes, and nothing in the response says so.**
  `entities` is `count_entities_by_file(file_hash)` — entities from **this file**. `edges` is
  `graph_stats["edges"]` — edges across the **whole graph**. Reading them as a matched pair overstates
  what this upload contributed.
- **`uploaded_at` is UTC ISO-8601**, from `datetime.now(timezone.utc).isoformat()` (`registry.py:47`).

### 2.4 Error responses

Deliberate errors use the API-wide envelope, `{"error": "<message>"}`.

| Status | Condition | Body | Site |
|---|---|---|---|
| `400` | no `file` part in the request | `{"error": "No file field in request"}` | `:45-46` |
| `400` | the file part has an empty filename | `{"error": "Empty filename"}` | `:49-50` |
| `400` | extension not in the allow-list | `{"error": "Unsupported file type. Allowed: bat, c, cpp, …"}` — all 35, alphabetical | `:51-54` |
| `422` | any `ValueError` raised below the route | `{"error": "<the exception text>"}` | `:64-65` |
| `500` | any other exception raised below the route | `{"error": "<the exception text>"}` | `:66-67` |
| `413` | request body over `MAX_CONTENT_LENGTH` | **HTML** — Flask rejects it before the route runs | `config.py:69` |

**`400 Bad Request`** — no file part:

```json
{ "error": "No file field in request" }
```

**`400 Bad Request`** — unsupported extension. The message enumerates the entire allow-list:

```json
{ "error": "Unsupported file type. Allowed: bat, c, cpp, cs, css, csv, dart, docx, go, htm, html, java, js, json, jsx, kt, lua, m, md, pdf, php, pl, py, r, rb, rs, scala, scss, sh, sql, swift, ts, tsx, txt, vb" }
```

**`422 Unprocessable Entity`** — the intended case, from `services.py:53-54`:

```json
{ "error": "No text could be extracted from this file" }
```

Its docstring gives the reason (`services.py:48-50`): an empty index write *"would otherwise register a
knowledge base nothing can retrieve."*

> [!WARNING]
> **The `422` is broader than it looks, and its message is not a closed set.** `except ValueError` at
> `:64` is **type-based, not message-based**, so *any* `ValueError` raised anywhere beneath the route
> becomes a `422` carrying that exception's text verbatim. Three distinct causes reach it today:
>
> 1. **The intended one** — no text could be extracted.
> 2. **The loader backstop** — `ingestion/loader.py:71` raises `ValueError(f"Unsupported file type:
>    {ext}")`. It is reachable in practice through the filename-sanitisation path (§2.6), and it surfaces
>    as a **`422`, not the `400` a reader would expect**, sometimes with a blank extension in the message.
> 3. **A FAISS-only internal error** — see §8.
>
> Read the `422` as *"the server accepted the request but could not turn this file into indexable
> text."*

**`500 Internal Server Error`** — anything else, with the exception's text passed straight through:

```json
{ "error": "[Errno 13] Permission denied: '.../data/databases/chroma_db'" }
```

**`413 Payload Too Large`** returns **HTML**, not JSON. `MAX_CONTENT_LENGTH` is enforced by Flask itself
because `create_app()` copies `Config` into `app.config` (`app.py:35`), so the route never runs and the
JSON envelope never applies. The cap is `50 * 1024 * 1024` = **52 428 800 bytes**, hardcoded with no
environment override.

### 2.5 What happens behind the route

`index_document` (`services.py:44-83`), in source order:

1. **`load_file(file_path)`** — pick a loader by extension, read, then split at `CHUNK_SIZE=500` with
   `CHUNK_OVERLAP=50`.
2. **`if not texts: raise ValueError(...)`** → the `422`.
3. **`file_hash = metadatas[0]["file_hash"]`** — the **content MD5** computed at `loader.py:48-54`. The
   `fallback_hash` the route passes (`str(uuid.uuid4())`, `:62`) is unreachable in practice, because
   `load_file` always sets the key.
4. **`generate_chunk_ids(file_hash, len(texts))`** → `f"{file_hash}_{i}"`, deterministic
   (`loader.py:114-116`).
5. **`remove_document(file_hash)`** (`services.py:60`) — **delete before write, unconditionally.**
6. **Write to all three stores** — `vector_store.add_documents(texts, metadatas, chunk_ids)`, then
   `bm25_store.add_documents(texts, metadatas)`, then a per-chunk `graph_store.add_document(...)` loop.
7. **`kb_registry.register(...)`** — last.

> [!IMPORTANT]
> **Dedup is keyed on file *content*, not filename.** Step 5 is the whole mechanism. Re-uploading the
> same bytes under a different name produces the same MD5, so the previous copy is removed and the file
> is re-indexed: **the corpus never doubles, and the registry entry is replaced** (same `id`, new
> `uploaded_at`).
>
> The converse case is the one to watch: uploading *different* bytes under the *same* name creates a
> **second** registry entry with a different hash, while the file on disk is overwritten by the newer
> one. Deleting either entry then removes the one shared file.

**There are no transactions.** Steps 5 through 7 are four independent mutations against four independent
stores. A crash between any two leaves the corpus inconsistent with **nothing surfaced to the caller**.
The ordering is fixed precisely to make that window as small as possible; the full write path is in
[`../ingestion/README.md`](../ingestion/README.md).

### 2.6 Filename sanitisation, and what it costs

```python
# knowledge_base_routes.py:56
# secure_filename runs BEFORE the join — it is the sole path-traversal defence here.
filename  = secure_filename(f.filename)
file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
f.save(file_path)
```

**Order is the entire defence.** Sanitise, *then* join. Reverse those two lines and
`../../etc/passwd.pdf` escapes the upload folder. The comment above them says so outright, and it should
stay there.

Measured against Werkzeug 3.1.8, the version installed in the backend environment:

| Input filename | `secure_filename()` produces |
|---|---|
| `../etc/passwd.pdf` | `etc_passwd.pdf` — **traversal neutralised** |
| `C:\x.pdf` | `C_x.pdf` |
| `a b.pdf` | `a_b.pdf` |
| `.env.pdf` | `env.pdf` |
| `my_doc.PDF` | `my_doc.PDF` — case preserved |
| `..pdf` | `pdf` |
| `文件.pdf` | **`pdf`** — the entire base name is non-ASCII and is stripped |
| `рус.md` | **`md`** |

Two real consequences follow, and both are reachable:

> [!WARNING]
> **A file whose base name is entirely non-ASCII loses its extension.** `文件.pdf` passes the `400` gate
> (the *raw* name still ends in `pdf`), is saved as `uploads/pdf` with **no suffix at all**, and then the
> loader sees `Path("pdf").suffix == ""` and raises `ValueError("Unsupported file type: ")` — producing a
> **`422` whose message ends in a blank extension.** A user uploading a Chinese, Cyrillic, Arabic or
> Japanese filename hits this with a valid PDF.

**Sanitisation can also collide two distinct uploads onto one path.** `a b.pdf` and `a_b.pdf` both become
`a_b.pdf`; every non-ASCII `.pdf` becomes `pdf` — and `f.save` overwrites without warning. The *index*
stays correct, because dedup keys on content MD5 rather than name, but the file on disk under the upload
folder is whichever arrived last.

One structural note: `f.save()` at `:59` sits **outside** the route's `try`, which begins at `:61`. The
empty-name case (`..` → `''`) is not reachable through this route, because the `400` gate requires the
segment after the last dot to be one of the 35 allowed extensions and `""` is not — so this is not a live
crash path today. It is a fragile arrangement, though: any future save failure becomes an HTML `500`
rather than a JSON error.

### 2.7 The two extension checks

| Check | Where | On failure | Status |
|---|---|---|---|
| 1 · `_allowed(filename)` | `knowledge_base_routes.py:28-37` | returns `False` | clean **`400`** listing all 35 |
| 2 · `_get_loader(file_path)` | `ingestion/loader.py:57-71` | raises `ValueError` | **`422`** via the route's `except ValueError` |

`_allowed`'s own docstring names the relationship (`:30-32`): *"First of two extension checks. This one
gives a clean 400; `_get_loader()`'s ValueError is the backstop that decides which loader actually runs.
Content is never sniffed — the extension is trusted to describe the bytes."*

**Measured this run: the two sets agree exactly.** `Config.ALLOWED_EXTENSIONS` has 35 entries,
`loader.SUPPORTED_EXTENSIONS` has 35, and the set difference is empty in **both** directions. So the
backstop never fires for a correctly-preserved filename today. It fires in exactly two situations — when
sanitisation destroys the suffix (§2.6), and when somebody adds an extension to `Config` without adding a
loader branch. **That second case is precisely the drift the backstop exists to catch**, which is why
removing either check is a mistake even though one currently looks redundant.

The 35 extensions map to six loaders:

| Extension(s) | Loader |
|---|---|
| `.pdf` | `PyPDFLoader` |
| `.docx` | `Docx2txtLoader` |
| `.md` | `UnstructuredMarkdownLoader` |
| `.html` · `.htm` | `BSHTMLLoader(open_encoding="utf-8")` |
| `.csv` | `CSVLoader(encoding="utf-8")` |
| the other 29 — `.txt`, `.json`, and 27 code extensions | `TextLoader(encoding="utf-8")` |

> [!CAUTION]
> **Content is never sniffed.** There is no magic-byte check, no MIME validation, no `python-magic`. A
> `.txt` file containing a PDF is read as text; a renamed executable is read as text. This is a
> deliberate, documented trade — and it is part of the prompt-injection surface, because whatever the
> loader extracts becomes prompt input on a later query. See [`../security.md`](../security.md#63-content-is-never-sniffed).

---

## 📊 3. READ INDEX STATISTICS

```text
GET /api/documents
```

Current totals across the three stores. **Auth:** none.

**Request:** no parameters, no headers, no body.

**How to call**

```bash
curl http://localhost:5000/api/documents
```

```js
const stats = await fetch('http://localhost:5000/api/documents').then(r => r.json())
console.log(stats.vector_count, stats.bm25_count, stats.graph.documents)
```

```python
import requests
stats = requests.get("http://localhost:5000/api/documents", timeout=10).json()
print(stats["vector_count"], stats["bm25_count"], stats["graph"])
```

**Success — `200 OK`.** The body is `services.index_stats()` (`services.py:24-30`):

```json
{
  "vector_count": 142,
  "bm25_count": 142,
  "graph": { "documents": 142, "entities": 61, "edges": 88 }
}
```

**Error responses: none.** The handler has no validation, no `try` and no parameters. It answers `200` on
every call, including against a completely empty index (all zeros).

Two things about those numbers:

- **`graph.documents` counts chunk nodes, not files** (`graph_store.py:154`). A 42-chunk PDF reports
  `documents: 42`. The *file* count lives on `GET /api/knowledge-bases`.
- **This route is O(number of graph nodes).** `get_stats()` iterates every node twice
  (`graph_store.py:154-155`). Cheap at today's corpus sizes, linear forever.

**Note the key spelling.** This route returns `vector_count` / `bm25_count`. Upload and delete return
`vector_total` / `bm25_total` for the same numbers — §7.

---

## 📚 4. LIST KNOWLEDGE BASES

```text
GET /api/knowledge-bases
```

Every uploaded knowledge base with its per-file statistics. **Auth:** none.

**Request:** no parameters. **There is no pagination, no filtering and no limit** — the full registry is
returned on every call.

**How to call**

```bash
curl http://localhost:5000/api/knowledge-bases
```

```python
import requests
kbs = requests.get("http://localhost:5000/api/knowledge-bases", timeout=10).json()["knowledge_bases"]
for kb in kbs:
    print(kb["id"], kb["name"], kb["chunks"])
```

**Success — `200 OK`.** `{"knowledge_bases": [...]}`, from `kb_registry.list_all()`
(`ingestion/registry.py:65-72`), **sorted by `uploaded_at` descending — newest first**.

```json
{
  "knowledge_bases": [
    {
      "id": "9f2b1c4e8a7d3056b1e2f4a9c8d70b13",
      "name": "rag-survey.pdf",
      "uploaded_at": "2026-08-16T10:53:45.812004+00:00",
      "chunks": 42,
      "vectors": 42,
      "entities": 18,
      "edges": 27
    }
  ]
}
```

Each entry has exactly those **seven keys** (`registry.py:45-53`). `id` is the content MD5 and is the
value to pass to the delete route.

**Error responses: none.**

Two implementation facts that show through the API:

- **The registry is re-read from disk on every call** (`registry.py:25-32`, under a lock), so the cost is
  proportional to the file size, per request.
- **The registry is the only component in the backend with explicit thread synchronisation** —
  `_lock = threading.Lock()` (`registry.py:22`), held by all five of its public functions. Neither the
  event bus nor any of the three data stores has one.

> [!WARNING]
> **A corrupt registry file returns an empty list with a `200`.** `_load()` swallows every exception
> under a bare `except: pass` (`registry.py:30-31`) and returns `{}`. So an unreadable or truncated
> `kb_registry.json` makes this route report *no knowledge bases* while the three stores still hold every
> chunk — the list looks empty, but queries still retrieve. There is no error, no log line, and no way to
> tell this apart from a genuinely empty corpus from the API alone.

---

## ❌ 5. DELETE ONE KNOWLEDGE BASE

```text
DELETE /api/knowledge-bases/<file_hash>
```

Removes one knowledge base from all three stores and the registry, and deletes its uploaded file.
**Auth:** none.

**Request**

| Parameter | In | Type | Required | Notes |
|---|---|---|---|---|
| `file_hash` | path | string | ✅ | the `id` from `GET /api/knowledge-bases`. **No format validation anywhere** — Flask's default `string` converter matches any non-slash segment |

**How to call**

```bash
curl -X DELETE http://localhost:5000/api/knowledge-bases/9f2b1c4e8a7d3056b1e2f4a9c8d70b13
```

```js
const { stats } = await fetch(
  `http://localhost:5000/api/knowledge-bases/${fileHash}`,
  { method: 'DELETE' },
).then(r => r.json())
```

**Success — `200 OK`:**

```json
{
  "success": true,
  "stats": {
    "vector_total": 100,
    "bm25_total": 100,
    "graph": { "documents": 100, "entities": 43, "edges": 61 }
  }
}
```

**Error responses: none — including no `404`.**

> [!CAUTION]
> **This route can never report "not found."** An unknown, malformed or already-deleted hash returns
> `200 {"success": true}` with unchanged statistics. Every underlying call reports its outcome and every
> one of those reports is discarded — `services.remove_document` (`services.py:88-91`) calls
> `vector_store.delete_by_file`, `bm25_store.delete_by_file`, `graph_store.delete_by_file` and
> `kb_registry.remove` **for effect only**, keeping none of the four return values, two of which are
> counts and one of which is a boolean.
>
> The route is therefore **idempotent by construction**. That is a legitimate design, but a client must
> know it: a `200` here proves the request was processed, **not** that anything was deleted. To confirm a
> deletion, compare the returned `stats` against the previous totals, or re-fetch
> `GET /api/knowledge-bases`.

**There is no `try` in this handler**, so any store exception becomes an HTML `500` mid-delete, with the
earlier stores already modified. The one known trigger is FAISS-only — §8.

The handler is four steps (`:89-96`): read the registry entry (to learn the filename), call
`services.remove_document(file_hash)`, and — **only if the entry existed** — call
`services.delete_upload(kb_entry["name"])`. So an unknown hash also skips the file deletion, silently.

`remove_document`'s ordering is fixed and commented *"Order is deliberate"* (`services.py:87`): vector →
BM25 → graph → **registry last**. Registry-last means a crash mid-delete leaves a registry entry pointing
at partially-deleted content, rather than orphaned content with no entry to find it by.

`delete_upload` (`services.py:107-114`) is deliberately forgiving: a missing file is not an error, and an
`OSError` on `os.remove` is swallowed (`:113-114`) — so a Windows file lock silently leaves the upload on
disk while the index entry is gone.

---

## 🧹 6. CLEAR EVERYTHING

```text
DELETE /api/clear
```

Wipes all three stores, the registry, and every uploaded file the registry names. **Auth: none.**

**Request:** no parameters, no body, no confirmation token.

```bash
curl -X DELETE http://localhost:5000/api/clear
```

**Success — `200 OK`** (`:80`):

```json
{ "success": true, "message": "All documents cleared" }
```

**Error responses: none declared.**

`services.clear_everything()` (`services.py:94-104`) runs in this order: snapshot `list_all()` → clear the
vector store → clear BM25 → clear the graph → `kb_registry.clear_all()` → delete each snapshotted file
from the upload folder.

> [!CAUTION]
> **Everything about this route deserves to be stated bluntly.** No authentication. No confirmation
> parameter. No dry run. No backup. No undo. It returns `200` **even if a store's `clear()` silently did
> nothing**, because no return value is checked. And there is no `try` in the handler, so a store
> exception surfaces as an **HTML `500` mid-wipe** with the earlier stores already emptied and the
> registry possibly still full — the worst inconsistency this API can produce, reported as a generic
> server error.
>
> The snapshot-then-delete ordering also means the file cleanup only covers files **named by registry
> entries**. An upload that failed after `f.save()` is not in the registry, so this route will not remove
> it either — §8.

---

## 🧮 7. THE TWO STATISTICS SHAPES

The same three numbers are reported under two different key sets, by two different functions, and no
route reconciles them:

| Function | Site | Returned by | Keys |
|---|---|---|---|
| `index_stats()` | `services.py:24-30` | `GET /api/documents` | **`vector_count`**, **`bm25_count`**, `graph` |
| `totals()` | `services.py:33-39` | `POST /api/upload`, `DELETE /api/knowledge-bases/<hash>` | **`vector_total`**, **`bm25_total`**, `graph` |

The `graph` sub-object is **identical** in both — `{documents, entities, edges}`, from
`graph_store.get_stats()`.

`totals()`'s docstring frames the distinction as intentional (`:34`): *"The post-write shape the upload
and delete responses report."* So the naming carries a meaning — `_total` is a value **after** a
mutation, `_count` is a value **read on request** — but nothing enforces it and no client can discover it
from the payload alone.

**A client must read both spellings.** A shared normaliser that reads only `vector_count` silently
reports `undefined` after every upload. `infra/smoke.py:28` asserts the `_count` spelling specifically.

---

## ⚠️ 8. LIMITATIONS AND FAILURE MODES

**Failed uploads orphan their file permanently.**

Neither `except` branch on the upload route (`:64-67`) removes `file_path`, and `f.save()` has already
run by then. So every `422` and every `500` leaves the uploaded bytes sitting in the upload folder with
no registry entry pointing at them. Because `clear_everything()` deletes only files **named by registry
entries** (`services.py:103-104`), `DELETE /api/clear` will not reclaim them either. **There is no code
path that ever removes an orphan** — the only remedy is deleting the file by hand.

**A FAISS-only crash on deleting the last file.**

With `VECTOR_BACKEND=faiss` (opt-in; Chroma is the default and is unaffected), `delete_by_file` reaches
`zip(*kept)` on an empty list (`retrieval/stores/vector_store.py:227`) and raises
`ValueError: not enough values to unpack (expected 3, got 0)` when the removal empties the index. Two
routes surface it differently, because one has a `try` and one does not:

| Route | Result |
|---|---|
| `DELETE /api/knowledge-bases/<hash>` on the last file | **HTML `500`** — no `try` in the handler |
| `POST /api/upload` re-uploading the only indexed file | **`422`** — `index_document` calls `remove_document` first (`services.py:60`), and the route's `except ValueError` catches it, so the message is a raw Python unpacking error |

**Other reachable limitations, collected:**

| Limitation | Effect | Evidence |
|---|---|---|
| A fully non-ASCII base filename loses its extension | valid file → `422 "Unsupported file type: "` | §2.6 |
| Sanitisation collides distinct uploads onto one disk path | the index stays correct; the file on disk is the later one | §2.6 |
| A corrupt `kb_registry.json` is swallowed | `GET /api/knowledge-bases` returns `[]` on a `200` while queries still retrieve | `registry.py:30-31` |
| `DELETE /api/knowledge-bases/<hash>` cannot report "not found" | `200 {"success": true}` for any hash | `services.py:88-91` |
| Content is never sniffed | a renamed file is read as whatever its extension claims | `knowledge_base_routes.py:30-32` |
| No transactions across the four write targets | a mid-write crash leaves the corpus inconsistent, silently | `services.py:6-9` |
| Concurrent ingest is unsafe | the three stores are unsynchronised module singletons; only the registry has a lock | `registry.py:22` |
| Ingestion is synchronous with no progress channel | a large file holds the HTTP connection open for the whole index cycle | §1 |
| `413` and `405` return HTML | `response.json()` throws | [`README.md`](README.md) §7.2 |

---

## 🔒 9. SECURITY NOTES

- **No authentication on any of the five routes** — see §1 and [`README.md`](README.md) §4. Both delete
  routes are destructive and unauthenticated.
- **`secure_filename` is the sole path-traversal defence**, and it works only because it runs **before**
  `os.path.join` (§2.6). Reversing those two lines reintroduces directory traversal on an unauthenticated
  write endpoint.
- **Content is never sniffed** (§2.7). The extension is trusted to describe the bytes.
- **Upload is the prompt-injection entry point.** Whatever the loader extracts becomes a retrieved chunk,
  and retrieved chunks are interpolated into the planner, compressor, reasoning and reflection prompts
  **unescaped, by design** — including into the reflection prompt that is supposed to judge whether the
  answer is grounded. The answer is then rendered through `marked.parse()` with no sanitiser, so a
  crafted document can also carry markup into the DOM. Both are **accepted, documented risks.**

Neither is widened here. The trust boundaries and the mitigation (bind to localhost) are in
[`../security.md`](../security.md#-7-prompt-injection-and-document-to-dom-xss).

---

## 🔗 10. RELATED READING

- [`README.md`](README.md) — the route index, blueprint registration, CORS, limits, and the API-wide error contract
- [`../ingestion/README.md`](../ingestion/README.md) — the write path in full: load → chunk → dedup → three stores → registry
- [`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md) — what `vector_count`, `bm25_count` and `graph` actually count
- [`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md) — how the indexed corpus is searched
- [`query.md`](query.md) — how an indexed document becomes a cited source
- [`../configuration.md`](../configuration.md) — `DATA_ROOT`, `UPLOAD_FOLDER`, `CHUNK_SIZE`, `VECTOR_BACKEND`
- [`../security.md`](../security.md) — trust boundaries and accepted risks
- [`../../../Frontend/Documentation/knowledge-base/README.md`](../../../Frontend/Documentation/knowledge-base/README.md) — the page that drives these five routes, its upload queue, and the filename-vs-content dedup mismatch
