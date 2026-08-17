<div align="center">

# 🔌 HTTP API

### Eight routes, four blueprints, one registration tuple — and no authentication of any kind.

<br>

[![Routes](https://img.shields.io/badge/routes-8-1c7ed6)](#-1-the-eight-routes)
[![Blueprints](https://img.shields.io/badge/blueprints-4-7c5cff)](#-2-how-a-route-is-registered)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Base URL](https://img.shields.io/badge/dev%20base%20URL-localhost%3A5000-f59e0b)](#-1-the-eight-routes)
[![Auth](https://img.shields.io/badge/auth-none-ef4444)](#-4-authentication)
[![Upload cap](https://img.shields.io/badge/upload%20cap-50%20MB-f59e0b)](#-6-content-types-and-limits)

</div>

<br>

---

<br>

## Content Tree

<pre>
HTTP API
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-eight-routes">🧭 1. The eight routes</a>
│   ├── <a href="#11-the-index">1.1 The index</a>
│   └── <a href="#12-where-each-one-is-documented">1.2 Where each one is documented</a>
│
├── <a href="#-2-how-a-route-is-registered">🧩 2. How a route is registered</a>
│   ├── <a href="#21-the-factory-does-four-things">2.1 The factory does four things</a>
│   ├── <a href="#22-the-blueprints-tuple">2.2 The BLUEPRINTS tuple</a>
│   └── <a href="#23-no-url_prefix-anywhere">2.3 No url_prefix anywhere</a>
│
├── <a href="#-3-route-versus-service">🧱 3. Route versus service</a>
│
├── <a href="#-4-authentication">🔓 4. Authentication</a>
│
├── <a href="#-5-cors">🌐 5. CORS</a>
│
├── <a href="#-6-content-types-and-limits">📦 6. Content types and limits</a>
│
├── <a href="#-7-the-error-contract">💥 7. The error contract</a>
│   ├── <a href="#71-what-the-application-raises">7.1 What the application raises</a>
│   └── <a href="#72-what-the-framework-raises">7.2 What the framework raises</a>
│
├── <a href="#-8-concurrency-and-the-one-worker-rule">🧵 8. Concurrency and the one-worker rule</a>
│
├── <a href="#-9-what-is-actually-verified">🧪 9. What is actually verified</a>
│
├── <a href="#-10-adding-a-resource">🧬 10. Adding a resource</a>
│
└── <a href="#-11-related-reading">🔗 11. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

The backend exposes **eight HTTP routes**, all under an `/api` prefix, all served by one Flask process on
port **5000** by default. Seven of them are ordinary JSON request/response endpoints. The eighth,
`POST /api/query`, returns an open `text/event-stream` and narrates a multi-minute pipeline run frame by
frame.

Every route lives in `Backend/src/adrag/routes/<resource>/<resource>_routes.py` and is attached to a
Flask `Blueprint`. The application factory registers them by iterating a single tuple — it does not know
what any of them do.

```python
# adrag/app.py:51
for blueprint in BLUEPRINTS:
    app.register_blueprint(blueprint)
```

> [!CAUTION]
> **There is no authentication on any route.** No API key, no session, no token, no rate limit, no CSRF
> protection — verified by an exhaustive grep across `Backend/src/`, which finds no `@app.before_request`
> and no decorator of any kind beyond the eight `@…route` lines. The most direct consequence:
> **`DELETE /api/clear` wipes the entire index — all three stores, the registry, and every uploaded file
> on disk — in one unauthenticated request, with no confirmation and no undo.** The mitigation is
> deployment-shaped, not code-shaped: **bind to localhost.** See [§4](#-4-authentication) and
> [`../security.md`](../security.md#-11-before-this-leaves-localhost).

---

## 🧭 1. THE EIGHT ROUTES

### 1.1 The index

Base URL in development: **`http://localhost:5000`** (`Config.PORT`, `config.py:77`). Paths are absolute
and written out in full on every decorator.

| # | Method | Path | Handler | Declared at | Response type |
|---|---|---|---|---|---|
| 1 | `POST` | `/api/query` | `query()` | `routes/query/query_routes.py:33` | `text/event-stream` |
| 2 | `POST` | `/api/upload` | `upload()` | `routes/knowledge_base/knowledge_base_routes.py:42` | JSON |
| 3 | `GET` | `/api/documents` | `documents()` | `routes/knowledge_base/knowledge_base_routes.py:70` | JSON |
| 4 | `DELETE` | `/api/clear` | `clear()` | `routes/knowledge_base/knowledge_base_routes.py:76` | JSON |
| 5 | `GET` | `/api/knowledge-bases` | `list_knowledge_bases()` | `routes/knowledge_base/knowledge_base_routes.py:83` | JSON |
| 6 | `DELETE` | `/api/knowledge-bases/<file_hash>` | `delete_knowledge_base()` | `routes/knowledge_base/knowledge_base_routes.py:89` | JSON |
| 7 | `GET` | `/api/providers` | `providers()` | `routes/provider/provider_routes.py:27` | JSON |
| 8 | `GET` | `/api/health` | `health()` | `routes/health_check/health_check_routes.py:17` | JSON |

`<file_hash>` uses Flask's **default `string` converter** — no `<uuid:…>`, no regex. Any non-slash
segment matches, and nothing validates its format anywhere in the stack.

### 1.2 Where each one is documented

| Page | Routes | What it covers |
|---|---|---|
| [`query.md`](query.md) | `POST /api/query` | the request body, the SSE wire format, all **ten** event types with every payload key, the 180-second timeout, in-band errors |
| [`knowledge-base.md`](knowledge-base.md) | the five KB routes | upload validation and defences, the two statistics shapes, dedup by content hash, the delete paths and their idempotency |
| [`provider-and-health.md`](provider-and-health.md) | `GET /api/providers` · `GET /api/health` | the boolean-availability guarantee, the live Ollama probe and its latency, liveness-not-readiness |

---

## 🧩 2. HOW A ROUTE IS REGISTERED

### 2.1 The factory does four things

`create_app()` is 22 lines (`app.py:33-54`) and does exactly four things, in this order:

1. **`Flask(__name__)` + `app.config.from_object(Config)`** (`:34-35`). This is how every **uppercase**
   `Config` attribute reaches `app.config` — including `MAX_CONTENT_LENGTH`, which is why Flask itself
   enforces the 50 MB upload cap without any route touching it (§6).
2. **`CORS(...)` on `r"/api/*"`** (`:37-47`) — §5.
3. **`os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)`** (`:49`). The upload directory is created at
   factory time, so `f.save()` on the upload route never fails for a missing directory.
4. **The blueprint loop** (`:51-52`).

Then `app = create_app()` at module level (`:61`). There is **deliberately no `__main__` block** —
`main.py` is the single entry point and the gunicorn command names `adrag.app:app` directly, both stated
in the comment at `:58-59`.

> [!IMPORTANT]
> **`app.py` carries zero route decorators.** Not "almost none" — zero. If you are looking for a
> handler, it is in `routes/<resource>/`, always. A change to the routing surface touches
> `routes/__init__.py` and nothing else in the application core.

### 2.2 The `BLUEPRINTS` tuple

`routes/__init__.py` is **20 lines total**: four imports and one tuple.

```python
# adrag/routes/__init__.py:15
BLUEPRINTS = (
    query_bp,
    knowledge_base_bp,
    provider_bp,
    health_check_bp,
)
```

Its module docstring states the design rule verbatim (`:6-7`): *"BLUEPRINTS is the single list
create_app() registers. Adding a resource means adding a folder and one line here; nothing else in the
application changes."*

| Blueprint object | Declared at | Blueprint name | Folder | Routes |
|---|---|---|---|---|
| `query_bp` | `query/query_routes.py:24` | `"query"` | `routes/query/` | 1 |
| `knowledge_base_bp` | `knowledge_base/knowledge_base_routes.py:23` | `"knowledge_base"` | `routes/knowledge_base/` | 5 |
| `provider_bp` | `provider/provider_routes.py:15` | `"provider"` | `routes/provider/` | 1 |
| `health_check_bp` | `health_check/health_check_routes.py:12` | `"health_check"` | `routes/health_check/` | 1 |

Flask endpoint names follow from the blueprint name and the function name — `query.query`,
`knowledge_base.upload`, `knowledge_base.delete_knowledge_base`, `provider.providers`,
`health_check.health`. Those are the strings `url_for()` and `app.url_map` speak.

The folder shape:

```text
routes/
│
├── 📄 __init__.py                       Four imports + the BLUEPRINTS tuple. 20 lines.
│
├── 📁 query/
│   └── 📄 query_routes.py               POST /api/query — validate, fork a daemon thread, stream SSE
│
├── 📁 knowledge_base/
│   ├── 📄 knowledge_base_routes.py      5 routes — validation, secure_filename, status codes, JSON
│   └── 📄 services.py                   The three-store + registry work. Imports no Flask.
│
├── 📁 provider/
│   └── 📄 provider_routes.py            GET /api/providers — the only route making an outbound call
│
└── 📁 health_check/
    └── 📄 health_check_routes.py        GET /api/health — 19 lines, the smallest file in the backend
```

Each resource folder also carries an `__init__.py`, empty in all four — a package marker only.

### 2.3 No `url_prefix` anywhere

**Not one blueprint declares a `url_prefix`.** Every decorator carries the full absolute path:
`"/api/query"`, `"/api/upload"`, `"/api/health"`, and so on.

The consequence is worth internalising: **the `/api` prefix is a convention repeated eight times, not a
structural guarantee.** A new route written as `@my_bp.route("/thing")` would register perfectly happily
at `/thing` — and would then fall **outside** the CORS `r"/api/*"` resource matcher (§5), which is the
kind of failure that only shows up from a browser and never from `curl`.

---

## 🧱 3. ROUTE VERSUS SERVICE

`routes/knowledge_base/` is the only resource folder with a second file, and that split is the concrete
illustration of the layering convention:

| File | Lines | Owns | Never does |
|---|---|---|---|
| `knowledge_base_routes.py` | 97 | validation, `secure_filename`, status codes, JSON framing | touch a store directly |
| `services.py` | 115 | the fixed order in which three stores and the registry are written | import Flask |

`services.py`'s docstring gives the reason (`:6-9`): *"Every ingest and every delete must touch ALL THREE
stores AND the registry. There are no transactions and no cross-store lock, so a partial write leaves the
corpus inconsistent with nothing surfaced — which is why the ordering here is fixed and why the routes
call these functions rather than reaching into a store."*

The rule is not absolute in one place, and it is better stated honestly than overstated:
`knowledge_base_routes.py` **does** import `kb_registry` directly (`:20`), for a single **read** at `:92`
— it needs the stored filename before it deletes the knowledge base that names it. Every **write** still
goes through `services`.

The other three route files import nothing from a store at all. `query_routes.py` imports `rag_graph` and
three functions from the event bus; `provider_routes.py` imports `Config` and `check_ollama`;
`health_check_routes.py` imports only Flask.

---

## 🔓 4. AUTHENTICATION

**There is none.** This section exists to say so unambiguously, because an API reference that omits the
subject reads as though the answer were "the usual."

What was checked, and what was found across `Backend/src/`:

| Mechanism | Present? |
|---|---|
| API key / bearer token check | ❌ none |
| Session or cookie auth | ❌ none |
| `@app.before_request` guard | ❌ none |
| Rate limiting | ❌ none |
| CSRF protection | ❌ none |
| Per-route authorisation | ❌ none |

The direct consequences, stated rather than softened:

- **`DELETE /api/clear` wipes everything, unauthenticated.** All three stores, the registry, and every
  uploaded file named by a registry entry. One request. No confirmation parameter, no dry run, no backup.
  The confirmation modal the UI shows is **client-side only** — the API has no such gate.
- **`DELETE /api/knowledge-bases/<file_hash>` deletes any knowledge base by id, unauthenticated** — and
  the ids are enumerable through the equally unauthenticated `GET /api/knowledge-bases`.
- **`POST /api/upload` lets any caller write files into the upload folder** and inject content into the
  corpus that later becomes prompt input. Upload is the prompt-injection entry point.
- **`POST /api/query` spends real LLM budget per call**, with no quota and no accounting.

> [!CAUTION]
> **Every one of these is a remote compromise the moment the port is reachable off the machine.** Two
> further defaults compound it: the CORS allowlist ends in a literal `"*"` (§5), and `FLASK_DEBUG`
> defaults to `true` (`config.py:76`), so an unhandled exception renders the **interactive Werkzeug
> debugger** — a remote code execution surface — instead of an error page (§7.2). The trust boundaries and
> the accepted-risk register are in [`../security.md`](../security.md#-1-the-trust-boundary-model).

**Adding auth later is not free**, and the obstacle is small but real: the CORS configuration permits
exactly one request header, `Content-Type`. An `Authorization` header would be rejected at the preflight
until that list is widened (§5).

---

## 🌐 5. CORS

The whole configuration is eight lines in the factory:

```python
# adrag/app.py:39
resources={
    r"/api/*": {
        "origins": [Config.FRONTEND_URL, "http://localhost:3000", "http://localhost:5000",
                    "http://localhost:8080", "http://localhost:8081", "*"],
        "methods": ["GET", "POST", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "expose_headers": ["Content-Type"],
    }
}
```

Four facts follow from it, all verifiable from those lines alone:

1. **The list ends in a literal `"*"`, which subsumes every named origin.** The five named entries are
   decorative — **any** origin is accepted. This is a documented, accepted risk, not an oversight to
   "discover"; it is also the single thing to close first before this is exposed beyond localhost.
2. **`PUT` and `PATCH` are not permitted** — consistent with an API that defines neither.
3. **`allow_headers` is `["Content-Type"]` only**, which is why bolting on an `Authorization` header is a
   two-file change rather than a one-file one (§4).
4. **`supports_credentials` is not set**, so cookies are not sent cross-origin.

`Config.FRONTEND_URL` defaults to **`http://localhost:8080`** (`config.py:75`) — the port
`Frontend/vue.config.js` actually serves, whose `/api` proxy targets **5000**.

---

## 📦 6. CONTENT TYPES AND LIMITS

**Request and response media types**, per route:

| Route | Request `Content-Type` | Response `Content-Type` |
|---|---|---|
| `POST /api/query` | `application/json` | **`text/event-stream`** |
| `POST /api/upload` | `multipart/form-data` | `application/json` |
| the other six | — (no body) | `application/json` |

**Two limits govern the upload surface, and both are hardcoded:**

| Limit | Value | Where | In `.env.example`? |
|---|---|---|---|
| `MAX_CONTENT_LENGTH` | `50 * 1024 * 1024` = **52 428 800 bytes** | `config.py:69` | **No** |
| `ALLOWED_EXTENSIONS` | a **35-entry** `set` | `config.py:70-73` | **No** |

Both are plain class attributes with **no `os.getenv` wrapper** — unlike every other `Config` entry.
They are the only two settings on the API surface a deployment cannot change without editing Python.
`MAX_CONTENT_LENGTH` is enforced by Flask itself, because `from_object(Config)` copies it into
`app.config` (`app.py:35`); exceeding it produces a `413` that the application never sees, and therefore
an **HTML** body (§7.2).

The full extension list, with the loader each one maps to, is in
[`knowledge-base.md`](knowledge-base.md); the environment surface as a whole is in
[`../configuration.md`](../configuration.md).

---

## 💥 7. THE ERROR CONTRACT

### 7.1 What the application raises

Every error the application code raises **deliberately** is JSON, and always this exact envelope:

```json
{ "error": "Human-readable description" }
```

It is produced by `jsonify({"error": …}), <status>` at six call sites — `query_routes.py:42` and `:46`,
and `knowledge_base_routes.py:46`, `:50`, `:52-54`, `:65`, `:67`. There is no error **code**, no
`details` array, and no request id. The string is the whole payload.

| Status | Raised by | Meaning |
|---|---|---|
| `400` | `/api/query`, `/api/upload` | the request was rejected before any work started |
| `422` | `/api/upload` | the file was accepted but could not be turned into indexable text |
| `500` | `/api/upload` | anything else that raised inside that route's `try` |

### 7.2 What the framework raises

> [!WARNING]
> **There is no `@app.errorhandler` anywhere in the codebase**, so every framework-generated error is
> Werkzeug's **default HTML page, not JSON**. A client cannot assume `response.json().error` exists.

| Situation | Status | Body |
|---|---|---|
| unknown path | `404` | **HTML** |
| wrong method on a known path (e.g. `GET /api/clear`) | `405` | **HTML** |
| upload body over `MAX_CONTENT_LENGTH` | `413` | **HTML** |
| an unhandled exception outside a route's `try` | `500` | **HTML** — or the **interactive Werkzeug debugger**, because `Config.DEBUG` defaults to `true` (`config.py:76`) |

This is a genuine gap in the API contract rather than a documentation nicety, and it has already shaped
client code: the frontend's stream reader parses errors defensively —
`await res.json().catch(() => ({ message: res.statusText }))` (`Frontend/src/services/ragApi.js:53`) —
precisely because the body may not be JSON.

**Two reachable paths turn what looks like a client mistake into an HTML `500`** rather than a `400`:

- A non-string `query` or `provider` on `POST /api/query`. `body.get("query", "").strip()` and
  `body.get("provider", …).lower()` sit **outside any `try`**, so `{"query": 42}` raises `AttributeError`
  and falls through to Flask's unhandled-exception path ([`query.md`](query.md) §6.2).
- Any store exception on `DELETE /api/clear` or `DELETE /api/knowledge-bases/<hash>`, neither of which
  has a `try` at all ([`knowledge-base.md`](knowledge-base.md) §8).

> [!NOTE]
> **`POST /api/query` is a special case and does not belong in either table.** Once the response has
> begun streaming, the status line is already `200` and cannot be revised — so a pipeline failure is
> reported as an **in-band `error` event on a `200`**, never as an HTTP error status. A client that reads
> the status code to decide whether a query succeeded will report every failed run as a success.
> [`query.md`](query.md) §6.3 covers it.

---

## 🧵 8. CONCURRENCY AND THE ONE-WORKER RULE

**The server must run as a single process.** Development uses `app.run(threaded=True)` (`main.py:51`);
production uses gunicorn with **`-w 1`** and the gevent-websocket worker class. The `-w 1` is not a
tuning choice, it is a correctness constraint: SSE session queues are process memory and every store is a
module-level singleton, so forking splits an event producer from its consumer and gives each worker a
divergent BM25 corpus and graph. The mechanism is in
[`../sse-event-bus/README.md`](../sse-event-bus/README.md).

What that means for a caller:

- **Concurrent queries are supported.** Each run gets its own `uuid4` session, its own unbounded queue,
  and its own daemon thread; the stores are read-only during a query.
- **Concurrent ingest is not safe.** The three stores are unsynchronised module singletons. The registry
  is the only component in the backend with an explicit lock (`ingestion/registry.py:22`) — neither the
  event bus nor any store has one.

---

## 🧪 9. WHAT IS ACTUALLY VERIFIED

> [!IMPORTANT]
> **This project has no test framework, and `infra/smoke.py` is not one.** It self-declares as much
> (`smoke.py:9-10`): *"This is a DEV TOOL, not a test suite — the project has no test framework and this
> does not pretend to be one."* No page here may present these routes as tested.

What `infra/smoke.py` does cover is still worth knowing, because it is the closest thing to an executable
contract. It builds the app through `create_app()`, drives Flask's test client, binds no port and writes
nothing — and touches **four of the eight** routes (`smoke.py:25-30`):

| Method | Path | Expected | Keys asserted |
|---|---|---|---|
| `GET` | `/api/health` | `200` | `status` |
| `GET` | `/api/providers` | `200` | `providers`, `default` |
| `GET` | `/api/documents` | `200` | `vector_count`, `bm25_count`, `graph` |
| `GET` | `/api/knowledge-bases` | `200` | `knowledge_bases` |

It also asserts each path is present in `app.url_map` (`:56`, `:62`). It **deliberately excludes**
`POST /api/query` and `POST /api/upload` — both would call an LLM or mutate the index, and the docstring
gives the reason (`:15-16`): *"a check with side effects is one people stop running."*

```bash
Backend/.venv/Scripts/python infra/smoke.py
```

Exit `0` means every checked route answered and every path is registered. Run it after any structural
change to `routes/`.

---

## 🧬 10. ADDING A RESOURCE

The claim this page exists to make is that adding a resource is a folder plus one line, and it is true.
Grounded in what the four existing folders actually contain:

1. **`routes/<resource>/__init__.py`** — empty. A package marker, nothing more.
2. **`routes/<resource>/<resource>_routes.py`** — `Blueprint("<resource>", __name__)` plus the route
   decorators. Write the path in full, **including the `/api` prefix** (§2.3), or the route escapes the
   CORS matcher.
3. **`routes/<resource>/services.py`** — only if the route touches state. Everything that reads or writes
   a store goes here; this file must not import Flask.
4. **One import line and one tuple entry in `routes/__init__.py`.**

**Nothing in `app.py` changes.** Then run `infra/smoke.py` (§9) to confirm the blueprint registered and
the import chain still resolves.

Match the conventions the four existing files share: a module docstring listing the routes the file owns,
`# ── Routes ──` section rules dividing the file, private helpers prefixed with `_`, and a JSON error
envelope of `{"error": "<message>"}` for every deliberate rejection (§7.1).

---

## 🔗 11. RELATED READING

- [`query.md`](query.md) — `POST /api/query`, the SSE wire format, and all ten event types
- [`knowledge-base.md`](knowledge-base.md) — the five knowledge-base routes in full
- [`provider-and-health.md`](provider-and-health.md) — `GET /api/providers` and `GET /api/health`
- [`../architecture/README.md`](../architecture/README.md) — blueprint registration inside the wider process model
- [`../sse-event-bus/README.md`](../sse-event-bus/README.md) — why one worker, and how the stream is produced
- [`../ingestion/README.md`](../ingestion/README.md) — the write path behind `POST /api/upload`
- [`../configuration.md`](../configuration.md) — every `Config` attribute and environment variable
- [`../security.md`](../security.md) — trust boundaries, accepted risks, and what to close before exposing a port
