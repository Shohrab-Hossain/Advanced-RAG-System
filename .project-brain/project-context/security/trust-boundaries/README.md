# Trust boundaries

<br>

## The boundaries

| # | Boundary | Untrusted side | Validation on the trusted side |
|---|---|---|---|
| 1 | Browser → Flask `/api/*` | any HTTP client that can reach the port | per-route body/param checks (below). **CORS headers are emitted and working, but CORS is not a trust boundary** — it is browser-enforced only, and the allowlist currently ends in `"*"` (see Invariant 4) |
| 2 | Uploaded file → parser | arbitrary file bytes | extension allowlist, `secure_filename`, 50 MB cap |
| 3 | Query text → LLM prompt | arbitrary user text | **none** — interpolated directly into the prompt template |
| 4 | Document text → LLM prompt | arbitrary document content | **none** — retrieved chunks are interpolated directly |
| 5 | Web results → LLM prompt | arbitrary internet content | **none** — DuckDuckGo titles/bodies are interpolated directly |
| 6 | LLM output → application logic | model output | `safe_json_parse()` with three fallbacks, then `bool()` / `float()` coercion and `.get()` defaults |
| 7 | LLM answer → DOM | model output | rendered as HTML by `marked.parse()` |
| 8 | Pickle files → process memory | files on disk | bare `except` → reset to empty on any load failure |

<br>

## What is actually validated

**`POST /api/query`** — body must be JSON with a non-empty `query` after `.strip()` (else `400`);
`provider` must be exactly `"openai"` or `"ollama"` after lowercase+strip (else `400`); `model` is passed
through unvalidated to the LLM factory.

**`POST /api/upload`** — a `file` field must exist and have a non-empty filename; the extension must be in
`Config.ALLOWED_EXTENSIONS`; the name goes through `secure_filename` before being joined to
`UPLOAD_FOLDER`; Flask enforces `MAX_CONTENT_LENGTH = 50 MB`. Content is **not** sniffed — the extension is
trusted to describe the bytes, and the corresponding loader is what actually rejects a malformed file (as a
`500`).

> [!IMPORTANT]
> **The route-level extension allowlist is 35 entries wide, not four** (`config.py:62-65`) — it accepts
> `py`, `sh`, `bat`, `pl`, `js`, `php` and other script types as indexable text. Nothing *executes* them,
> and `_get_loader()` remains the narrower second gate (Invariant 3): a suffix it has no loader for raises
> `ValueError`. The exposure is therefore content-driven, not execution-driven — a much wider set of file
> types can carry prompt-injection or HTML payloads into the corpus (see the accepted risks below). The
> full list is in [`../../operations/configuration/README.md`](../../operations/configuration/README.md).

**`DELETE /api/knowledge-bases/<file_hash>`** — the hash is used as a dict key and as a metadata filter
only; it is never joined into a path. The file that *is* deleted comes from the registry entry's stored
`name`, not from the URL.

**Everything else** takes no input.

<br>

## Invariants that must not break

1. **The API key stays server-side.** `/api/providers` must keep exposing availability as a boolean only.
2. **`secure_filename` runs before any `os.path.join` with user input.** It is the sole defence against
   path traversal in the upload route.
3. **The extension allowlist gates which loader runs.** `_get_loader()` raises `ValueError` on anything
   else — keep both checks; the route check gives a clean `400`, the loader check is the backstop.
4. **CORS stays an explicit origin list.** Widening it to `*` on a machine reachable from a network makes
   the whole API public. **⚠️ This invariant is currently BROKEN in the code — see below.**
5. **Nothing constructs an LLM outside `get_llm()`**, so provider selection and credential handling stay in
   one place.
6. **`emit()` stays failure-tolerant.** It must remain a no-op for an unknown session, or a disconnected
   client turns into a pipeline crash.

<br>

---

<br>

## Invariant 4 is breached today

CORS itself is configured and working — the resource pattern is `r"/api/*"` (`app.py:43`) and headers are
emitted for `/api/…` requests. **The defect is the opposite of a failure: the allowlist is too wide.**
`app.py:44` carries six entries, and the last one is a wildcard:

```python
"origins": [Config.FRONTEND_URL, "http://localhost:3000", "http://localhost:5000",
            "http://localhost:8080", "http://localhost:8081", "*"]
```

The `"*"` makes the five named origins decorative — **every** origin on the internet is permitted. Two
things make that serious rather than cosmetic:

| Multiplier | Detail |
|---|---|
| **No authentication on any route** | No decorator, no `before_request`, no token check anywhere in `app.py:36-311`. `DELETE /api/clear` wipes the entire index unauthenticated |
| **`FLASK_DEBUG` defaults to `true`** | `config.py:67` — the Werkzeug debugger is on unless explicitly disabled |

**This does not break anything today, and that is the trap.** Localhost binding is the only thing
containing it, so nothing fails, no error appears, and the misconfiguration is invisible while
development stays on one machine. It converts on deployment: a static frontend calling a separate API host
crosses origins, and this allowlist will let that call through — **from every other origin too**. The
deploy failure mode is over-permission, not a CORS error you would notice.

**To close it:** remove the `"*"` entry and let `FRONTEND_URL` carry the deployed origin, then add
authentication before the port is reachable off the machine. Do not "fix CORS" by widening anything — the
scoping half (`r"/api/*"`, the method list, `Content-Type`) is correct as written.

<br>

---

<br>

## Accepted risks (documented, not fixed)

These are consequences of the local-single-user scope. Each becomes a real vulnerability if the server is
exposed:

- **No authentication or authorisation on any route.** Anyone who can reach the API port — 5001 by default
  (`config.py:68`), and a floating port under `dev.py` — can upload, query, and wipe the entire index;
  `DELETE /api/clear` is unauthenticated and irreversible. The `"*"` CORS entry above means a browser on
  any site can do it too.
- **A single global corpus.** There is no tenancy; every query searches every uploaded document.
- **Prompt injection is unmitigated.** Query text, document chunks, and web-search results all flow
  unescaped into the planner, compressor, reasoning, and reflection prompts. A crafted document can
  instruct the model — including the reflection agent that judges grounding.
- **Rendered answers are not sanitised.** `ResultDisplay.vue` puts `marked.parse(store.answer)` into the
  DOM; `marked` v12 does not sanitise by default, so HTML that survives from a document into an answer
  renders as HTML. This is an XSS path from a malicious uploaded document.
- **Raw exception strings reach the client.** `/api/upload` and `/api/query` return `str(exc)`, which can
  leak absolute filesystem paths.
- **`FLASK_DEBUG` defaults to `true`**, so the Werkzeug debugger is on unless explicitly disabled — remote
  code execution if the port is reachable.
- **Pickle stores are loaded without integrity checks.** `pickle.load` on a tampered
  `bm25_store.pkl` / `graph_store.pkl` executes arbitrary code. The files are local-only, which is the
  entire mitigation.
- **No rate limiting anywhere.** Each query costs several LLM calls; an unauthenticated caller can spend
  the API budget freely.
- **Uploaded files persist in `UPLOAD_FOLDER`** after indexing and are only removed via the delete routes;
  a file with no registry entry is never cleaned up.
- **Outbound calls leak content by design** on the OpenAI path (chunks are sent to OpenAI) and the web
  path (the raw query is sent to DuckDuckGo). The Ollama path exists precisely to avoid the first.

TODO: no threat model, security review, or dependency-audit process is recorded in the repository. If the
project is ever exposed beyond localhost, the list above is the starting backlog — confirm scope with the
owner first.
