<div align="center">

# 🔒 Security

### Four trust boundaries, none of them enforced — and a CORS policy that hands the whole index to any page the user happens to be visiting.

<br>

[![Auth](https://img.shields.io/badge/authentication-none%20on%208%2F8%20routes-ef4444)](#-3-no-authentication-on-any-route)
[![CORS](https://img.shields.io/badge/CORS-any%20origin%20echoed-ef4444)](#-2-cors--what-the-wire-actually-does)
[![Debugger](https://img.shields.io/badge/werkzeug%20debugger-on%20by%20default-ef4444)](#-4-the-interactive-debugger-is-on)

[![Error handlers](https://img.shields.io/badge/error%20handlers-0%20registered-f59e0b)](#-5-the-error-contract)
[![Accepted risks](https://img.shields.io/badge/accepted%20risks-documented-f59e0b)](#-7-prompt-injection-and-document-to-dom-xss)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../pyproject.toml)

</div>

<br>

---

<br>

## Content Tree

<pre>
Security
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-trust-boundary-model">🧭 1. The trust-boundary model</a>
│
├── <a href="#-2-cors--what-the-wire-actually-does">🌐 2. CORS — what the wire actually does</a>
│
├── <a href="#-3-no-authentication-on-any-route">🔓 3. No authentication on any route</a>
│
├── <a href="#-4-the-interactive-debugger-is-on">🐛 4. The interactive debugger is on</a>
│
├── <a href="#-5-the-error-contract">💥 5. The error contract</a>
│
├── <a href="#-6-the-upload-surface">📤 6. The upload surface</a>
│   ├── <a href="#61-what-secure_filename-does-measured">6.1 What secure_filename does, measured</a>
│   ├── <a href="#62-two-reachable-defects">6.2 Two reachable defects</a>
│   └── <a href="#63-content-is-never-sniffed">6.3 Content is never sniffed</a>
│
├── <a href="#-7-prompt-injection-and-document-to-dom-xss">💉 7. Prompt injection and document-to-DOM XSS</a>
│   ├── <a href="#71-all-four-prompts-interpolate-untrusted-text">7.1 All four prompts interpolate untrusted text</a>
│   └── <a href="#72-the-answer-reaches-the-dom-unsanitised">7.2 The answer reaches the DOM unsanitised</a>
│
├── <a href="#-8-pickle-load-as-a-deserialisation-surface">🥒 8. Pickle load as a deserialisation surface</a>
│
├── <a href="#-9-data-integrity-risks">🧨 9. Data-integrity risks</a>
│
├── <a href="#-10-what-the-system-gets-right">✅ 10. What the system gets right</a>
│
├── <a href="#-11-before-this-leaves-localhost">🧯 11. Before this leaves localhost</a>
│
├── <a href="#-12-known-gaps">🚧 12. Known gaps</a>
│
└── <a href="#-13-related-reading">🔗 13. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

This page states the measured security posture of the backend. Other pages describe what the
configuration *says*; this one describes what the server *does* when a request arrives, verified against
the installed Flask, Werkzeug and flask-cors this run.

The short version: there is **no authentication on any of the eight routes**, and the CORS configuration
does not restrict origins in any meaningful way. Those two facts multiply.

> [!CAUTION]
> **Any web page a user visits while this server is running on their machine can wipe the entire
> index.** flask-cors **echoes the requesting origin back verbatim** — measured — so
> `OPTIONS /api/clear` from `https://evil.example` returns `200` with
> `Access-Control-Allow-Methods: DELETE, GET, OPTIONS, POST`, and `DELETE /api/clear` needs no
> credential of any kind. One request destroys all three stores, the registry, and every uploaded file
> the registry names. There is no confirmation parameter, no dry run, no backup and no undo. The
> confirmation dialog in the UI is client-side decoration.

Everything else on this page is a variation on the same theme: the mitigation is **deployment-shaped,
not code-shaped**. Bind this to localhost and the risks are contained; expose the port and every one of
them is remotely reachable. §11 is the ordered list of what to close first.

Two things this page is careful about. Several of the findings below are **accepted, documented
risks** — deliberate trade-offs, not oversights — and they are labelled as such. And the pickle
deserialisation surface (§8) is assessed honestly rather than sensationally: it is real, it is strictly
local, and the two things that raise it above zero are named.

---

## 🧭 1. THE TRUST-BOUNDARY MODEL

Four boundaries. Everything inside a boundary is trusted; everything crossing one should not be.

| # | Boundary | What crosses | Validated by | Trusted after? |
|---|---|---|---|---|
| 1 | **Browser → HTTP API** | JSON bodies, multipart uploads, path parameters | two `400` checks on `/api/query`; three `400` gates plus `secure_filename` on `/api/upload`; **nothing at all on the other six routes** | fully |
| 2 | **Uploaded bytes → the corpus** | document text extracted by six LangChain loaders | **extension only. Content is never sniffed.** | fully — and it becomes prompt input |
| 3 | **Corpus + web → the LLM prompts** | retrieved chunk text, DuckDuckGo titles and bodies, the user's query | **nothing — interpolation is unescaped by design** | fully |
| 4 | **Answer → the DOM** | the model's markdown | **nothing — `marked.parse()` with no sanitiser, into `v-html`** | fully |

**The compound shape is what matters.** Boundary 1 has no authentication, boundary 2 has no content
validation, boundary 3 has no escaping and boundary 4 has no sanitisation — so **a single
unauthenticated upload reaches the rendered DOM of every later reader.** No single link in that chain is
unusual on its own; the chain is what makes it consequential.

The mitigation for all four is the same one, and it is a deployment decision: **bind to localhost, and
treat every document you index as trusted input.**

---

## 🌐 2. CORS — WHAT THE WIRE ACTUALLY DOES

The origins list in the factory ends in a literal wildcard:

```python
# adrag/app.py:41
"origins": [Config.FRONTEND_URL, "http://localhost:3000", "http://localhost:5000",
            "http://localhost:8080", "http://localhost:8081", "*"],
"methods": ["GET", "POST", "DELETE", "OPTIONS"],   # :42
"allow_headers": ["Content-Type"],                 # :43
"expose_headers": ["Content-Type"],                # :44
```

[`api/README.md`](api/README.md#-5-cors) already notes that the five named origins are decorative. What
follows is the part no configuration file can tell you — the response headers, measured against
flask-cors 6.0.5 through Flask's test client this run:

```text
GET /api/health          Origin: https://evil.example
  → 200
    Access-Control-Allow-Origin: https://evil.example      ← the origin is ECHOED BACK
    Access-Control-Expose-Headers: Content-Type
    Vary: Origin

OPTIONS /api/clear       Origin: https://evil.example   Access-Control-Request-Method: DELETE
  → 200
    Access-Control-Allow-Origin: https://evil.example
    Access-Control-Allow-Methods: DELETE, GET, OPTIONS, POST

OPTIONS /api/query       Access-Control-Request-Headers: Authorization, Content-Type
  → 200
    Access-Control-Allow-Headers: Content-Type             ← Authorization is NOT echoed → dropped
```

**Three conclusions, none of which should be softened:**

1. **flask-cors reflects the requesting origin verbatim rather than emitting a bare `*`.** The response
   carries `Vary: Origin`, which is correct caching behaviour for a reflected policy — and it means the
   header will match whatever origin asked. **Any web page on the internet may read `/api/*` responses
   from this server.**
2. **The `DELETE /api/clear` preflight succeeds from an arbitrary origin.** Combined with §3, that is the
   concrete attack in the overview: a drive-by index wipe, no credential required, triggered by a page
   the user merely visited.
3. **Adding an `Authorization` header later is a two-file change.** `allow_headers` is `["Content-Type"]`
   only, and the measurement above shows `Authorization` is **not** echoed at preflight — so a browser
   would refuse to send it until the CORS config is widened alongside whatever guard is added.

`supports_credentials` is not set, so cookies are not sent cross-origin. **That mitigates nothing here**,
because the application uses no cookies and has no authentication for a cookie to carry.

---

## 🔓 3. NO AUTHENTICATION ON ANY ROUTE

Verified by exhaustive grep across `Backend/src/`: **no `@app.before_request`, no decorator of any kind
beyond the eight `@…route` lines, no key check, no session, no token, no rate limit, no CSRF token.** The
full route-by-route matrix is in [`api/README.md`](api/README.md#-4-authentication); the consequences are
here.

- **`DELETE /api/clear` wipes everything, unauthenticated** — all three stores, the registry, and every
  uploaded file named by a registry entry. **One request. No confirmation parameter, no dry run, no
  backup, no undo.** The modal the UI shows is client-side only; the API has no gate.
- **`DELETE /api/knowledge-bases/<file_hash>` deletes any knowledge base by id**, and the ids are
  enumerable through the equally unauthenticated `GET /api/knowledge-bases`.
- **`POST /api/upload` lets any caller write into `UPLOAD_FOLDER` and inject content into the corpus.**
  Upload is the entry point for the prompt-injection chain of §7.
- **`POST /api/query` spends real LLM budget per call**, with no quota, no accounting and — because a run
  cannot be cancelled — no way to stop one already in flight.
- **`GET /api/providers` discloses**, unauthenticated: which providers are configured, the configured
  model for each, the Ollama base URL, and **the name of every model pulled on the local machine.** That
  last item is a fingerprint of the host, not just of the app.

> [!IMPORTANT]
> **The gap is not that authentication is weak — it is that there is no place to put it.** Adding a guard
> means a `before_request` hook (or a decorator applied to all four blueprints) *and* widening
> `allow_headers` so the browser will send the header at all (§2, conclusion 3). Plan both changes
> together; either alone produces a system that appears to authenticate and does not.

---

## 🐛 4. THE INTERACTIVE DEBUGGER IS ON

```python
# adrag/config.py:76
DEBUG: bool = os.getenv("FLASK_DEBUG", "true").lower() == "true"
```

`main.py:48` passes `debug=Config.DEBUG` to `app.run`. Traced through the installed Flask and Werkzeug:

| Step | Measured |
|---|---|
| `Flask.run` | `options.setdefault("use_debugger", self.debug)` → `True` |
| `werkzeug.serving.run_simple` | `use_evalex` defaults to **`True`**; `main.py` overrides nothing |
| `run_simple` body | `application = DebuggedApplication(application, evalex=use_evalex)` |

**So an unhandled exception renders Werkzeug's traceback page with the interactive Python console
enabled.** Both halves of the following sentence are true and both belong in any description of it:

> The console is gated by Werkzeug's debugger **PIN** (`get_pin_and_cookie_name`, disabled entirely by
> `WERKZEUG_DEBUG_PIN=off`), which is printed to the server's own console at startup. **The traceback
> page itself is not gated at all** — it discloses source lines, local variable values and framework
> internals to anyone who can trigger an error. The PIN is derived from machine and user attributes and
> is not a security boundary this project should rely on.

**Two reachable ways to trigger it**, both established rather than hypothetical:

1. **A non-string `query` or `provider`.** `query_routes.py:41` and `:44` sit outside any `try`.
   Measured: a body of `{"query": 42}` raises `AttributeError: 'int' object has no attribute 'strip'`
   straight out of the route.
2. **Any store exception on `DELETE /api/clear` or `DELETE /api/knowledge-bases/<hash>`** — neither route
   has a `try` at all.

**The mitigation is one line:** `FLASK_DEBUG=false` in `Backend/.env`. `python infra/dev.py --no-reload`
sets exactly that (`dev.py:274-275`), making it the only one-flag mitigation the repo ships — at the cost
of also turning off the auto-reloader, since both are driven by the same setting
([`architecture/README.md`](architecture/README.md#44-the-reloader-and-flask_debugs-two-jobs)).

> [!NOTE]
> **The variable is `FLASK_DEBUG`, not `DEBUG`.** Setting `DEBUG=false` in `.env` changes nothing —
> `config.py:76` reads `FLASK_DEBUG` and the attribute it produces is called `DEBUG`, which is exactly
> how the mistake happens.

---

## 💥 5. THE ERROR CONTRACT

The application returns a JSON `{"error": …}` envelope for failures it raises deliberately. **The
framework's own errors are HTML**, because no error handler is registered anywhere.

**Programmatic proof, stronger than a grep:** on the built application object,
`app.error_handler_spec == defaultdict(<lambda>, {})` — completely empty. Not "we searched and found
none": the app has none.

Measured responses:

| Request | Status | `Content-Type` | Body starts |
|---|---|---|---|
| `GET /api/nope` | `404` | `text/html; charset=utf-8` | `<!doctype html> … <title>404 Not Found</title>` |
| `GET /api/clear` (wrong method) | `405` | `text/html; charset=utf-8` | `<!doctype html> … <title>405 Method Not Allowed` |
| `PUT /api/query` | `405` | `text/html; charset=utf-8` | same |
| `POST /api/upload`, body > 50 MB | `413` | `text/html; charset=utf-8` | `<!doctype html> … <title>413 Request Entity Too Large` |
| `POST /api/query {"query": ""}` | `400` | `application/json` | `{"error": "Missing or empty 'query' field"}` |

Two consequences:

- **A client cannot assume a JSON body on an error.** It has already shaped client code: `ragApi.js:53`
  parses defensively with `await res.json().catch(() => ({ message: res.statusText }))`.
- **With debug on, the `500` is not a plain HTML page but the interactive debugger** (§4). Registering
  handlers for `404`/`405`/`413`/`500` closes both the contract gap and the disclosure at once.

The application-raised side of the contract, endpoint by endpoint, is in
[`api/README.md`](api/README.md#-7-the-error-contract).

---

## 📤 6. THE UPLOAD SURFACE

```python
# routes/knowledge_base/knowledge_base_routes.py:56
# secure_filename runs BEFORE the join — it is the sole path-traversal defence here.
filename  = secure_filename(f.filename)                       # :57
file_path = os.path.join(Config.UPLOAD_FOLDER, filename)      # :58
f.save(file_path)                                             # :59
```

**Order is the whole defence.** Reverse those two lines and `../../etc/passwd.pdf` escapes the folder.
The in-code comment names the property explicitly, which is the right way to protect a line whose
correctness is invisible.

### 6.1 What `secure_filename` does, measured

Werkzeug 3.1.8, this run:

| Input | Result | Consequence |
|---|---|---|
| `../../etc/passwd` | `etc_passwd` | **traversal neutralised** |
| `..\..\windows\system32\x.txt` | `windows_system32_x.txt` | neutralised |
| `a/b/c.pdf` | `a_b_c.pdf` | neutralised |
| `.env` | `env` | leading dot stripped |
| `CON.txt` | `_CON.txt` | Windows reserved name escaped |
| `résumé.pdf` | `resume.pdf` | transliterated |
| `my report.pdf` | `my_report.pdf` | spaces collapsed |
| **`文件.pdf`** | **`pdf`** | ⚠️ the entire base name is stripped |
| **`テスト.md`** | **`md`** | ⚠️ same |
| **`документ.txt`** | **`txt`** | ⚠️ same |
| `文件-report.pdf` | `-report.pdf` | the ASCII part survives |
| `report_文件.pdf` | `report_.pdf` | ⚠️ two different names can collapse to one |

**It does its job.** Every traversal form tested is neutralised. The cost is everything below.

### 6.2 Two reachable defects

**1 — a fully non-ASCII base filename loses its extension, and the upload fails confusingly.** Traced end
to end this run:

```text
文件.pdf
  → _allowed() tests the RAW name, sees ".pdf", passes
  → secure_filename() yields 'pdf'
  → saved to UPLOAD_FOLDER/pdf
  → _get_loader() sees Path(".../pdf").suffix == ''
  → ValueError("Unsupported file type: ")  →  422 with a BLANK extension in the message
```

**The bytes are already on disk and nothing removes them.** `clear_everything()` only deletes files a
registry entry names, and a failed ingest never created one — so the orphan is never reclaimed by any
code path in the system.

**2 — sanitisation can collide two distinct uploads onto one path**, and `f.save` overwrites silently.
*Every* non-ASCII-named `.pdf` lands on `UPLOAD_FOLDER/pdf`; `a b.pdf` and `a_b.pdf` both land on
`a_b.pdf`. **The index stays correct** — dedup keys on content MD5, not on name — but the file on disk is
the later one, and `delete_upload` for **either** knowledge base removes the one shared file
(`knowledge_base_routes.py:95`).

### 6.3 Content is never sniffed

`knowledge_base_routes.py:30-32` says so verbatim. There is no magic-byte check, no MIME inspection, no
`python-magic`. **The extension is trusted to describe the bytes**: a `.txt` holding a PDF is read as
text, and a renamed executable is read as text.

- **35 extensions are accepted** (`config.py:70-73`), including 27 code and markup types.
  `ALLOWED_EXTENSIONS` is **not** env-tunable.
- **`MAX_CONTENT_LENGTH = 50 MB` is enforced by Flask** — measured on the built app — and produces the
  HTML `413` of §5.

Neither of those is a content check. What actually protects the corpus is that you chose to upload the
file — which is the assumption §7 examines.

---

## 💉 7. PROMPT INJECTION AND DOCUMENT-TO-DOM XSS

Both risks below are **accepted, documented risks** — deliberate trade-offs recorded so they are not
rediscovered as surprises. They are also the reason "treat every indexed document as trusted input" is a
real operational rule and not a platitude.

### 7.1 All four prompts interpolate untrusted text

| Node | Template / call | Untrusted input reaching the model |
|---|---|---|
| `planner` | `("human", "Query: {query}")` — `planner.py:45` | the **user query** |
| `compressor` | `("human", "Query: {query}\n\nDocuments:\n{documents}")` — `compressor.py:33` | query **+ retrieved chunk text + web results** |
| `reasoning` | `("human", "Query: {query}\n\nContext:\n{context}")` — `reasoning.py:39`, plus two **raw f-string prompts** with no template at all (`:75-76`, `:111`) | query **+ chunk text** |
| `reflection` | `("human", """Query: {query} … {context} … {answer}""")` — `reflection.py:43-49` | query **+ chunk text + the model's own answer** |

**No escaping, no delimiting and no instruction-hierarchy defence exists in any of the four.**

> [!CAUTION]
> **The same untrusted document text is interpolated into the reflection prompt — the agent whose job is
> to judge whether the answer is grounded.** A crafted document can therefore attack the critic that is
> supposed to catch it, which removes the one check that might otherwise have flagged a manipulated
> answer. This is an **accepted, documented risk**, not an oversight — and both halves of that sentence
> matter. Do not widen it, and do not describe the reflection node as a safety mechanism.

Web-search results reach the same prompts (`external_tools` feeds the aggregator), so the injection
surface is not limited to files you uploaded yourself.

### 7.2 The answer reaches the DOM unsanitised

There is **exactly one `v-html` in the entire frontend**
(`Frontend/src/pages/chat/components/ResultDisplay/ResultDisplay.vue:31`):

```vue
<div class="prose-rag" v-html="renderedAnswer" />
```

fed at `:118` by `try { return marked.parse(store.answer) } catch { return store.answer }`.

**`marked` 12.0.2 is installed** (`Frontend/package.json:12` declares `^12.0.0`), and marked v12 ships
**no sanitiser by default** — the `sanitize` option was removed in v5. A repo-wide grep for `DOMPurify`,
`sanitize` and `sanitise` across `Frontend/src/` and `package.json` returns nothing.

So raw HTML in the model's markdown reaches the DOM. Because the answer is derived from retrieved
document text (§7.1), **a crafted document is a stored-XSS vector against every later reader of that
knowledge base.** Accepted, documented risk. Do not imply a sanitiser exists; adding one is item 6 of
§11.

---

## 🥒 8. PICKLE LOAD AS A DESERIALISATION SURFACE

Three modules call `pickle.load` on files under `DATABASE_ROOT`: `bm25_store.py:57`,
`graph_store.py:177`, and `vector_store.py:142` (FAISS only).

`pickle.load` executes arbitrary code during deserialisation. The honest assessment:

> **These files are written only by this application, into a git-ignored directory under
> `Backend/data/`, and are never uploaded, never fetched, and never accepted from a request** — so there
> is no route through the HTTP API that plants a malicious pickle. **The surface is real but strictly
> local:** it becomes a code-execution path only if an attacker can already write to
> `Backend/data/databases/`, at which point they have filesystem access and the pickle is not the weakest
> link.
>
> **Two things do raise it above zero, and both are worth naming.** The store paths are **relocatable by
> environment variable** (`BM25_PATH`, `GRAPH_PATH`, `FAISS_PATH`), so a hostile `.env` or a hostile
> shell environment can point the loader at a file the attacker controls. And a **shared or synced
> `data/` directory** — a network drive, a cloud-sync folder, a backup restored from an untrusted
> source — is a plausible real-world delivery path.
>
> **Prefer JSON or a checked format if these stores are ever exchanged between machines.**

Both loads also sit under a bare `except`, which is a *separate* problem with the same code — see §9.

---

## 🧨 9. DATA-INTEGRITY RISKS

Not confidentiality issues, but failures that destroy or corrupt data with no signal. The storage
mechanics behind each are in
[`architecture/storage-model.md`](architecture/storage-model.md#-8-failure-modes).

| Risk | Mechanism | Blast radius |
|---|---|---|
| **A corrupt `kb_registry.json` wipes every other record** | `registry._load()` (`:25-32`) catches **every** exception and returns `{}`; `register()` then does `data = _load()` → `data[hash] = entry` → `_save(data)` (`:44-55`) | **One unreadable registry plus one subsequent upload permanently discards every other record**, while all three stores still hold their chunks. The corpus becomes searchable but unlistable and undeletable through the UI. |
| **A corrupt pickle silently empties a store** | bare `except` → reset to empty (`bm25_store.py:61-63`, `graph_store.py:180-182`, `vector_store.py:148-154`); the next write persists the emptiness | Total, silent loss of that store. **No log line, no exception, no warning.** Chroma — the default vector backend — is unaffected: it has no such handler and raises instead. |
| **Switching `VECTOR_BACKEND` does not migrate** | import-time class selection (`vector_store.py:250-253`) | Flipping it silently exposes a different, probably empty index. `.env.example:59` says so. |
| **No transaction across the four write targets** | `services.py:6-9`, verbatim | A crash between `bm25_store.add_documents` (`:64`) and the graph loop (`:65-66`) leaves a document searchable by keyword and vector, invisible to the graph, and **absent from the registry — so there is no UI path to delete it.** Only `DELETE /api/clear` recovers. |
| **A failed ingest orphans its file** | neither `except` branch removes `file_path` (`knowledge_base_routes.py:64-67`); `clear_everything` only deletes registry-named files (`services.py:103-104`) | Orphans accumulate in `UPLOAD_FOLDER` **permanently**. |

> [!WARNING]
> **The bare-`except` pattern is the common cause of three of those five rows.** It converts every
> corruption, version mismatch and permission error into an empty store with a successful startup. If one
> change were made to this file set, logging the swallowed exception would be it — the data would still
> be gone, but the operator would know.

---

## ✅ 10. WHAT THE SYSTEM GETS RIGHT

A security page that lists only failures is not a useful one. Four verified properties worth preserving:

**1 — the API key stays server-side, and it never enters a response.** `Config.OPENAI_API_KEY` has
exactly **one** consumer: `provider_routes.py:37`, `"available": bool(Config.OPENAI_API_KEY)`. It is
**never** passed to `ChatOpenAI` — `llm.py:61-64` passes only `model` and `temperature` — because the
credential travels `Backend/.env` → `load_dotenv` → `os.environ` → langchain's own read. **The key never
appears in any response, log line or error message.**

> [!IMPORTANT]
> **Keep availability a boolean.** A prefix, a length, or a masked form would each break the one security
> invariant this module has. `/api/providers` must keep answering *whether* a key exists and nothing
> more. (Measured aside: `Backend/` has **no `.env` today**, so `OPENAI_API_KEY` is `""` and
> `bool(...)` is `False` unless the variable is exported in the shell.)

**2 — `GET /api/health` leaks nothing.** `{"status": "healthy"}`, one hardcoded string: no version, no
environment, no paths, no dependency status (`health_check_routes.py:19`). Its minimalism is a security
property as much as a design one, and it is the reason a probe cannot be used to fingerprint the
deployment.

**3 — `secure_filename` runs before the join**, and it genuinely neutralises every traversal form tested
(§6.1). The ordering is documented in a comment at the call site, which is why it has survived
refactoring.

**4 — two independent extension checks exist.** `_allowed()` gives a clean `400`; `_get_loader()`'s
`ValueError` is the backstop that decides which loader actually runs. Measured,
`Config.ALLOWED_EXTENSIONS` and `loader.SUPPORTED_EXTENSIONS` are **exactly equal** (35 each, empty
difference in both directions) — so the backstop is redundant *today*, and drift between two files is
precisely what it exists to catch.

---

## 🧯 11. BEFORE THIS LEAVES LOCALHOST

An ordered list. Every item is a code or configuration change; none of them is optional if the port
becomes reachable from another machine.

| # | Close | Where | Why in this order |
|---|---|---|---|
| 1 | **Remove the literal `"*"`** from the origins list | `app.py:41` | The single change that stops any web page reading the API (§2) |
| 2 | **Set `FLASK_DEBUG=false`** | `Backend/.env`, or `python infra/dev.py --no-reload` | Turns off the interactive debugger *and* the traceback disclosure (§4) |
| 3 | **Add authentication** to all eight routes | a `before_request` guard, plus widening `allow_headers` to include `Authorization` | Without it, `DELETE /api/clear` is a drive-by wipe (§2 item 2, §3) |
| 4 | **Register `@app.errorhandler`s** for `404`/`405`/`413`/`500` | `app.py` | Restores the JSON error contract and stops the debugger rendering (§5) |
| 5 | **Bind to a loopback interface** | `main.py:50` currently passes `host="0.0.0.0"` | Until 1–4 land, the port must not be reachable off the machine |
| 6 | **Sanitise the rendered answer** | `ResultDisplay.vue:118` | Closes document-to-DOM XSS (§7.2) |
| 7 | **Consider a non-`pickle` format** if `data/` is ever shared | the three stores | §8 |

> [!NOTE]
> **This is not "development mode, where security is relaxed."** Nothing in the code distinguishes a
> development posture from a production one except `FLASK_DEBUG`, and the CORS and authentication
> defaults are identical in both. The mitigation is the network boundary you deploy behind — which is why
> item 5 exists and why it is listed as a stopgap rather than a fix.

---

## 🚧 12. KNOWN GAPS

Beyond the accepted risks of §7, **exactly two gaps survive**, both verified this run:

| # | Gap | Verified how |
|---|---|---|
| 1 | **No test framework.** No runner in `Backend/pyproject.toml` or `Frontend/package.json`; no `tests/` or `test/` directory; no `.github/`, `Makefile` or `justfile`. | directory listing plus both manifests |
| 2 | **No `LICENSE`.** `LICENSE*`, `LICENCE*` and `COPYING*` are all absent from the repo root — the terms under which this code may be used are formally undefined. | measured |

> [!CAUTION]
> **`infra/smoke.py` is not a test suite and this project is not tested.** Its own docstring says so:
> *"This is a DEV TOOL, not a test suite — the project has no test framework and this does not pretend to
> be one."* It drives **four of the eight routes** through Flask's test client, asserting key *presence*
> and never values, and deliberately excludes the two routes that would call an LLM or mutate the index.
> Run it after every structural change; never report it as coverage
> ([`architecture/README.md`](architecture/README.md#56-smokepy--a-dev-tool-and-it-says-so-itself)).

Everything else once listed as a gap has been closed: the production dependencies are declared in the
`prod` extra, the frontend lint script runs clean, the frontend documentation no longer describes a build
system this project does not use, `FRONTEND_URL` and `PORT` agree everywhere at `http://localhost:8080`
and `5000`, and `DATA_ROOT` is anchored to the package rather than the working directory.

---

## 🔗 13. RELATED READING

- **Why the risks are accepted rather than fixed.** This is a single-machine research tool whose corpus
  is documents you chose to index. Escaping prompt input would degrade retrieval quality for a threat
  that does not exist when the operator is the only uploader — and sanitising the answer would strip
  legitimate markdown rendering. The trade is defensible *only* under the localhost assumption, which is
  why that assumption is stated everywhere rather than implied.
- **Why the mitigation is deployment-shaped.** Every finding on this page becomes remote the moment the
  port is reachable and stays contained while it is not. One network decision moves the whole posture,
  which is a better lever than seven partial code fixes — but it is also a decision nothing in the code
  enforces, and `host="0.0.0.0"` actively works against it.
- **Why `bool(OPENAI_API_KEY)` is the strictest thing in the codebase.** It is the one place where a more
  "helpful" response — a masked key, a length, a prefix — would be a genuine leak. The invariant is
  narrow enough to hold, which is why it has.

**Continue reading:**

- [`api/README.md`](api/README.md) — the eight routes, the CORS block and the error contract as configured
- [`api/query.md`](api/query.md) — the query endpoint, including its two `400`s and the in-band error model
- [`api/knowledge-base.md`](api/knowledge-base.md) — upload validation, the two extension checks, and the unauthenticated wipe
- [`api/provider-and-health.md`](api/provider-and-health.md) — what `/api/providers` discloses, field by field
- [`configuration.md`](configuration.md) — every setting behind these defaults, and its real value
- [`architecture/README.md`](architecture/README.md) — the process model, the debugger wiring and `infra/`
- [`architecture/storage-model.md`](architecture/storage-model.md) — the persistence mechanics behind §8 and §9
- [`ingestion/README.md`](ingestion/README.md) — the write path an untrusted upload actually takes
- [`llm-providers/README.md`](llm-providers/README.md) — `get_llm()`, credential handling, and the JSON discipline
