<div align="center">

# 🔌 API Clients

### Two axios modules, eight routes, and one hand-rolled SSE reader — because `EventSource` cannot POST.

<br>

[![Modules](https://img.shields.io/badge/modules-2-1c7ed6)](#-2-where-it-lives)
[![Exports](https://img.shields.io/badge/exports-3%20%2B%205-7c5cff)](#51-ragapijs--three-exports)
[![Manifest](https://img.shields.io/badge/manifest-package.json-3fb950)](../../package.json)

[![Routes covered](https://img.shields.io/badge/backend%20routes%20covered-8%2F8-3fb950)](#-6-wire-shape-cross-boundary-contracts)
[![Stream transport](https://img.shields.io/badge/SSE-fetch%20%2B%20ReadableStream-f59e0b)](#52-streamquery--the-stream-reader)
[![Dead functions](https://img.shields.io/badge/dead%20client%20functions-0-3fb950)](#-6-wire-shape-cross-boundary-contracts)

</div>

<br>

---

<br>

## Content Tree

<pre>
API Clients
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│   ├── <a href="#11-what-the-user-experiences">1.1 What the user experiences</a>
│   └── <a href="#12-the-one-rule-every-caller-relies-on">1.2 The one rule every caller relies on</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-two-modules-two-axios-instances">3.1 Two modules, two axios instances</a>
│   ├── <a href="#32-the-base-url-and-the-dev-proxy">3.2 The base URL and the dev proxy</a>
│   └── <a href="#33-who-is-allowed-to-call-these">3.3 Who is allowed to call these</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-a-plain-rest-call">4.1 A plain REST call</a>
│   └── <a href="#42-a-streaming-call">4.2 A streaming call</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-ragapijs--three-exports">5.1 ragApi.js — three exports</a>
│   ├── <a href="#52-streamquery--the-stream-reader">5.2 streamQuery — the stream reader</a>
│   ├── <a href="#53-the-partial-frame-carry-over">5.3 The partial-frame carry-over</a>
│   ├── <a href="#54-the-four-way-dispatch">5.4 The four-way dispatch</a>
│   └── <a href="#55-kbapijs--five-exports">5.5 kbApi.js — five exports</a>
│
├── <a href="#-6-wire-shape-cross-boundary-contracts">🔌 6. Wire shape (cross-boundary contracts)</a>
│
├── <a href="#%EF%B8%8F-7-edge-cases--gotchas">⚠️ 7. Edge cases &amp; gotchas</a>
│
├── <a href="#-8-failure-modes">💥 8. Failure modes</a>
│
├── <a href="#-9-extension-points">🧩 9. Extension points</a>
│
└── <a href="#-10-related-decisions--deeper-reading">🔗 10. Related decisions &amp; deeper reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

Every byte the frontend exchanges with the backend goes through one of **two** modules, both flat in
`Frontend/src/services/`:

- **`ragApi.js`** (96 lines) — three exports covering health, provider discovery, and the streaming
  query.
- **`kbApi.js`** (53 lines) — five exports covering upload, statistics, the knowledge-base list, and the
  two deletes.

They are peers, not layers. **Neither imports the other**, each constructs its own axios instance, and
neither imports anything from the app besides `axios` itself. There is no shared `api.js`, no
interceptor chain, and no request/response middleware — a deliberate absence, since the two halves have
genuinely different needs: one of them has to bypass axios entirely.

Seven of the eight functions are ordinary axios calls that unwrap and return `data`. The eighth,
`streamQuery`, is the interesting one: it uses **`fetch` and a `ReadableStream`** to read Server-Sent
Events by hand, because the query endpoint requires a POST body and the browser's `EventSource` can only
issue a GET.

**Where this fits:** the stores that wrap these functions are documented in
[`../state/README.md`](../state/README.md); the endpoints themselves are specified in
[`../../../Backend/Documentation/api/README.md`](../../../Backend/Documentation/api/README.md).

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

### 1.1 What the user experiences

| Observed behaviour | The client fact behind it |
|---|---|
| Pipeline rows update **while** the answer is still being generated | `streamQuery` dispatches each frame as it arrives off the reader, not after the response completes |
| The Cancel button stops the run instantly | An `AbortController` created at `ragApi.js:41` and handed back to the caller as `{ abort }` |
| Cancelling shows *"Query cancelled"*, not a network error | The outer catch suppresses `AbortError` specifically (`:91-93`) |
| The upload bar reaches 100 % well before the file is indexed | `onUploadProgress` measures the browser→server byte transfer only (`kbApi.js:22-26`) |
| A dev machine needs no CORS setup | `BASE` defaults to `''`, so requests are same-origin and the dev proxy handles them |

### 1.2 The one rule every caller relies on

**Every REST function returns `data`, never the axios response.** Both files destructure at the call
site — `const { data } = await http.get(...)` — at `ragApi.js:19` and `:24`, and `kbApi.js:20`, `:34`,
`:39`, `:46`, `:51`.

That single convention is what keeps `.data.data` out of the stores, and it means a store never touches
an axios-shaped object. The one place axios's response *does* leak is a **rejection**: `kbStore`'s
upload catch reads `err.response?.data?.error` (`kbStore.js:54`) to find the backend's JSON error
message before falling back to the axios message.

---

## 📍 2. WHERE IT LIVES

Paths are relative to `Frontend/src/`.

| Concern | Path | Anchor |
|---|---|---|
| Base URL + instance (query side) | `services/ragApi.js:12-14` | `BASE`, `http` |
| Health probe | `services/ragApi.js:18` | `healthCheck` |
| Provider discovery | `services/ragApi.js:23` | `getProviders` |
| The SSE reader | `services/ragApi.js:40` | `streamQuery` |
| Base URL + instance (corpus side) | `services/kbApi.js:11-13` | `BASE`, `http` |
| Multipart upload | `services/kbApi.js:17` | `uploadFile` |
| Corpus reads | `services/kbApi.js:33`, `:45` | `getDocuments`, `getKnowledgeBases` |
| Corpus deletes | `services/kbApi.js:38`, `:50` | `clearDocuments`, `deleteKnowledgeBase` |
| Dev proxy | `vue.config.js:15-22` | `devServer.proxy` |

```text
src/services/
│
├── 📄 ragApi.js    health · providers · the streaming query (fetch + ReadableStream)
└── 📄 kbApi.js     upload · documents · clear · KB list · KB delete (all axios)
```

---

## 🏗️ 3. ARCHITECTURE

### 3.1 Two modules, two axios instances

Both files open with the identical four lines:

```js
// src/services/ragApi.js:12   ·   src/services/kbApi.js:11
const BASE = process.env.VUE_APP_API_URL || ''
const http = axios.create({ baseURL: BASE })
```

Two instances rather than one shared client is a deliberate cost. It buys **independence**: neither
module can break the other by adding an interceptor, a default header, or a timeout, and either can be
deleted without touching the other. With eight routes and no shared auth, the duplication is four lines.

The split by *resource* rather than by *verb* is the same rule the backend uses for its blueprint
folders, so the two sides read alike: query concerns on one side, corpus concerns on the other.

### 3.2 The base URL and the dev proxy

`BASE` defaults to the **empty string**, which makes every request a relative path. That is what allows
the Vue CLI dev server to proxy `/api/*` to the backend on port 5000, so the browser only ever talks to
`localhost:8080` and no CORS negotiation happens at all.

**`VUE_APP_` is a required prefix, not a style choice** — Vue CLI only injects environment variables
carrying it into the client bundle. A variable named `API_URL` is invisible to `process.env` in a
component.

> [!IMPORTANT]
> **`.env.example` ships the variable SET, and its own comment says to leave it unset.** Lines `4-7`
> read *"Leave this UNSET (or empty) for normal development … setting an absolute URL only bypasses the
> proxy"* — and then line `9` is the **uncommented** `VUE_APP_API_URL=http://localhost:5000`.
>
> A developer who copies `.env.example` to `.env` verbatim therefore **bypasses the dev proxy** and turns
> every call into a direct cross-origin request to port 5000. It works today only because the backend's
> CORS allowlist contains a literal `"*"` — an accepted, localhost-only risk that is not something to
> build on. **For normal development, comment that line out or leave the value empty.** Set it only when
> you are genuinely pointing the SPA at a backend on another host.

### 3.3 Who is allowed to call these

**Components call store actions, not services.** All five `kbApi` functions and two of the three
`ragApi` functions are reached only through `kbStore` / `ragStore`.

There is **exactly one exception in the entire source tree**: `NavBar.vue:111` imports `healthCheck`
directly, because the health pill is a display concern with no state anyone else needs. It is the only
service import outside `store/`, and it is accepted rather than tolerated — but it is also the ceiling,
not a precedent to extend.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 A plain REST call

Seven of the eight functions are the same three lines: call, destructure, return.

```js
// src/services/kbApi.js:33
export async function getDocuments () {
  const { data } = await http.get('/api/documents')
  return data
}
```

There is no retry, no timeout, no cancellation and no response normalisation. A rejected promise
propagates to the store, which applies its own policy — reads swallow, writes propagate (see
[`../state/README.md`](../state/README.md)).

### 4.2 A streaming call

`streamQuery` has a different lifecycle from everything else in the frontend, because it is the only
call that produces many results over time instead of one:

```text
runQuery()  →  streamQuery(...)  ──returns──►  { abort }        (synchronous)
                     │
                     ├─ POST /api/query  (fetch, signal)
                     ├─ res.ok?  no  ──►  onError(...)  ──►  return
                     └─ reader loop
                          ├─ decode chunk  →  buffer  →  split '\n'  →  keep the tail
                          ├─ per complete "data: {...}" line → JSON.parse
                          │     ├─ done        → onDone(data)
                          │     ├─ stream_end  → (no-op)
                          │     ├─ error       → onError(msg)
                          │     └─ otherwise   → onEvent(type, data)
                          └─ reader reports done → loop exits
```

The three things to hold onto:

- **It returns a controller, not a promise.** `{ abort: () => controller.abort() }` (`:95`) is handed
  back immediately; results arrive through the three callbacks.
- **The loop terminates when the *reader* reports `done`** — that is, when the server closes the
  connection. It does **not** terminate on `stream_end`, which is informational only.
- **After the first byte, there are no HTTP failures.** The status is already `200`; every subsequent
  problem is an in-band `error` event.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 `ragApi.js` — three exports

| Export | Line | Method · Path | Returns |
|---|---|---|---|
| `healthCheck()` | `:18-21` | `GET /api/health` | `{ status: 'healthy' }` |
| `getProviders()` | `:23-26` | `GET /api/providers` | `{ providers: [ … ], default: 'openai' }` |
| `streamQuery(query, provider, model, callbacks)` | `:40-96` | `POST /api/query` (SSE) | **`{ abort }` — a controller, not a promise** |

`getProviders` is the one call that can be slow: the endpoint probes the Ollama server over the network
on every request and is the only route in the API that makes an outbound call. That matters for the
configuration page, which polls it — see
[`../configuration-page/README.md`](../configuration-page/README.md).

### 5.2 `streamQuery` — the stream reader

**The problem:** the query endpoint needs a POST with a JSON body and answers with an open
`text/event-stream`. `EventSource`, the browser's built-in SSE client, is GET-only. So the frames have
to be parsed by hand.

The signature is
`streamQuery(query, provider = 'openai', model = null, { onEvent, onDone, onError })`, and the body
divides into five parts:

**Cancellation** (`:41`, `:49`, `:95`) — an `AbortController` is created up front, passed to `fetch` as
`signal`, and its `abort` returned to the caller. That is the whole cancellation story; the Cancel
button reaches it through `ragStore.abortQuery`.

**The request body** (`:42-43`) is `{ query, provider }`, and **`model` is added only when truthy**:

```js
// src/services/ragApi.js:42
const body = { query, provider }
if (model) body.model = model
```

An empty string is therefore omitted rather than sent as `""`, which is what lets "use the server
default" be expressed by simply not choosing a model.

> [!NOTE]
> **`model` is honoured for both providers.** The JSDoc above this function calls it an *"Ollama model
> override"*, which is stale — the backend applies it to the OpenAI chat model too, and
> `GET /api/providers` ships a four-item OpenAI model list that would be pointless otherwise. Describe
> the behaviour, not the comment.

**The `res.ok` pre-check** (`:52-56`) — on a non-2xx, the body is parsed as JSON (falling back to
`{ message: res.statusText }` if it is not JSON), and `onError(err.error || err.message || 'Request failed')`
fires before any reading starts. **This path only ever runs for the two pre-stream `400`s** — a missing
or empty `query`. Once the stream opens the status is `200` for the rest of the run.

**The read loop** (`:58-89`) — §5.3.

**The outer catch** (`:91-93`):

```js
// src/services/ragApi.js:91
} catch (err) {
  if (err.name !== 'AbortError') onError(err.message || 'Network error')
}
```

A user-initiated abort is **not** an error. This is why `ragStore.abortQuery` sets its own
`'Query cancelled'` message: nothing else would.

### 5.3 The partial-frame carry-over

**The problem:** a `ReadableStream` chunk boundary has nothing to do with an SSE frame boundary. One
read can deliver two and a half events, and the next read delivers the remaining half.

```js
// src/services/ragApi.js:66
buffer += decoder.decode(value, { stream: true })
const lines = buffer.split('\n')
buffer = lines.pop()          // the last line may be incomplete — carry it forward
```

Two details, both load-bearing:

- **`{ stream: true }` is required.** A multi-byte UTF-8 character can straddle a chunk boundary; the
  flag tells `TextDecoder` to hold the incomplete sequence rather than emit a replacement character.
  Without it, non-ASCII text in an answer corrupts at unpredictable offsets.
- **`lines.pop()` is the partial-frame defence.** `split('\n')` always yields a final element that is
  whatever followed the last newline — either an empty string, or half a frame. Assigning it back to
  `buffer` carries it into the next iteration. Drop that line and every event split across a chunk
  boundary is lost, intermittently and unreproducibly.

Each surviving line is skipped unless it starts with `'data: '` (`:71`), then parsed with
`JSON.parse(line.slice(6))` (`:73`). **A malformed line is caught and silently ignored** (`:85-87`) —
one bad frame cannot kill the stream.

The `while (true)` loop with an inner `if (done) break` (`:62-64`) is why `.eslintrc.js:44` sets
`no-constant-condition: { checkLoops: false }`; the rule's comment names this exact loop.

### 5.4 The four-way dispatch

Once a frame is parsed, its `type` decides everything (`:76-84`):

| `payload.type` | Line | Action |
|---|---|---|
| `done` | `:76-77` | `onDone(data)` — terminal, carries `{ answer, sources, metadata }` |
| `stream_end` | `:78-79` | **explicit no-op** — it has no `data` key at all, so touching `data` would throw |
| `error` | `:80-81` | `onError(data?.message \|\| 'Unknown pipeline error')` — optional chaining, because the two `error` variants have different shapes |
| *anything else* | `:82-83` | `onEvent(type, data)` → straight into `ragStore._applyEvent` |

The `stream_end` branch existing at all is the point: it is there **to do nothing deliberately**, so the
frame does not fall through to `onEvent` and reach the store's stage guard with no payload.

This four-way split is the reason the store's dispatch table has no `done`, `error` or `stream_end`
handling — those three never reach it.

### 5.5 `kbApi.js` — five exports

| Export | Line | Method · Path | Notes |
|---|---|---|---|
| `uploadFile(file, onProgress)` | `:17-29` | `POST /api/upload` | `FormData` with the single field name **`'file'`** (`:19`); `Content-Type: multipart/form-data` (`:21`) |
| `getDocuments()` | `:33-36` | `GET /api/documents` | corpus-wide statistics |
| `clearDocuments()` | `:38-41` | `DELETE /api/clear` | wipes everything |
| `getKnowledgeBases()` | `:45-48` | `GET /api/knowledge-bases` | already sorted newest-first by the server |
| `deleteKnowledgeBase(fileHash)` | `:50-53` | `DELETE /api/knowledge-bases/${fileHash}` | template-interpolated, **not** URL-encoded |

The progress callback (`:22-26`) is the only non-trivial part:

```js
// src/services/kbApi.js:22
onUploadProgress: (evt) => {
  if (onProgress && evt.total) onProgress(Math.round((evt.loaded / evt.total) * 100))
}
```

The `evt.total` guard matters — it is `undefined` when the total size is unknown, and without the guard
the callback would emit `NaN` into a progress bar. **This measures the browser→server byte transfer and
nothing else.** It reaches 100 % while the server is still loading, chunking, embedding and indexing,
which is precisely why the store bolts a second, synthetic phase onto the end of it.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

**All eight backend routes are consumed, and there is no dead client function.**

| Route | Client function | Store action |
|---|---|---|
| `GET /api/health` | `ragApi.js:18` | **none — `NavBar.vue:142` calls it directly** |
| `GET /api/providers` | `ragApi.js:23` | `ragStore.js:207` `fetchProviders` |
| `POST /api/query` | `ragApi.js:40` | `ragStore.js:136` `runQuery` |
| `POST /api/upload` | `kbApi.js:17` | `kbStore.js:42` `uploadDocument` |
| `GET /api/documents` | `kbApi.js:33` | `kbStore.js:80` `refreshStats` |
| `DELETE /api/clear` | `kbApi.js:38` | `kbStore.js:100` `clearIndex` |
| `GET /api/knowledge-bases` | `kbApi.js:45` | `kbStore.js:86` `fetchKnowledgeBases` |
| `DELETE /api/knowledge-bases/<hash>` | `kbApi.js:50` | `kbStore.js:94` `removeKnowledgeBase` |

**The SSE frame format**, as this reader assumes it: newline-delimited lines, each event a single
`data: ` line carrying one JSON object with a `type` key. No `event:` field, no `id:`, no `retry:`, and
no multi-line data blocks. **Eleven wire types exist** — seven produced by the pipeline plus four framed
by the route — of which this file intercepts three (`done`, `error`, `stream_end`) and forwards the rest.

The full endpoint reference, including request bodies, status codes and every event payload, lives in:

- [`../../../Backend/Documentation/api/query.md`](../../../Backend/Documentation/api/query.md) — `POST /api/query` and the event catalogue
- [`../../../Backend/Documentation/api/knowledge-base.md`](../../../Backend/Documentation/api/knowledge-base.md) — the five corpus routes
- [`../../../Backend/Documentation/api/provider-and-health.md`](../../../Backend/Documentation/api/provider-and-health.md) — the remaining two

> [!NOTE]
> **The dev proxy is Vue CLI's, configured in `vue.config.js:15-22`.** The dev server listens on **8080**
> and forwards `/api/*` to **5000**. There is no Vite anywhere in this project and no `vite.config.js`;
> any instruction mentioning port 5173 or `npm run dev` predates the current build.

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **`deleteKnowledgeBase` interpolates the hash straight into the path** (`kbApi.js:52`) with no
  `encodeURIComponent`. It is safe today because the only values passed are 32-character MD5 hex strings
  minted by the server — but it is an assumption, not a guarantee, and any future non-hex id would need
  encoding.

- **`streamQuery` returns before the stream is finished.** The returned object is available
  synchronously; awaiting it gets you the controller, not the answer. Everything meaningful arrives
  through the callbacks.

- **A malformed SSE line is swallowed** (`:85-87`). Good for resilience, bad for debugging: a
  server-side serialisation bug produces silence, not a console error.

- **`stream_end` has no `data` key at all.** The explicit no-op branch is not defensive padding — reading
  `data.anything` there would throw and kill the loop.

- **There is no request timeout anywhere.** Neither axios instance sets one, and `fetch` has none by
  default. A hung backend leaves the UI waiting indefinitely; the only server-side ceiling is the
  180-second per-event timeout on the query stream, which does not apply to the seven REST calls.

- **A 50 MB upload rejection does not arrive as JSON.** The backend's size cap is enforced by the WSGI
  layer before any route runs, so the response is an HTML error page. `err.response?.data?.error` is
  `undefined` for that one case and the store falls back to the axios message.

- **`healthCheck` has no store wrapper by design** — it is the single accepted component→service call.

- **Both modules read `process.env.VUE_APP_API_URL` at module scope**, so the value is baked in at build
  time. Changing it requires a rebuild, not a reload.

---

## 💥 8. FAILURE MODES

| Failure | Where it surfaces | Behaviour |
|---|---|---|
| Backend not running | Any call | axios/fetch rejects; `getProviders` and the two KB reads are swallowed by their stores, the rest propagate |
| Empty or missing `query` | `streamQuery` | Pre-stream `400`; `res.ok` check fires `onError` and returns — no reader is created |
| Pipeline failure mid-run | `streamQuery` | HTTP **`200`** with an in-band `error` event → `onError` |
| User cancels | `streamQuery` | `AbortError` is suppressed (`:91-93`); the store supplies the message |
| Malformed SSE frame | `streamQuery` | Caught and ignored (`:85-87`); the stream continues |
| Multi-byte character split across chunks | `streamQuery` | Handled by `{ stream: true }` — nothing to see |
| Event split across chunks | `streamQuery` | Handled by the `lines.pop()` carry-over |
| Upload over 50 MB | `uploadFile` | **HTML** error page, not JSON; the store falls back to `err.message` |
| Unsupported file type | `uploadFile` | JSON `400` with an `error` key listing the accepted extensions |
| Server closes the stream early | `streamQuery` | The reader reports `done`, the loop exits, and **no callback fires** — the store is left with `isRunning` still true |

That last row is the sharpest edge in the file: a stream that ends without a `done` or `error` frame
leaves the UI mid-run with no terminal signal. Nothing in the client detects it.

---

## 🧩 9. EXTENSION POINTS

**Add an endpoint to an existing resource.** One exported `async function` in the matching file,
following the house shape exactly: `const { data } = await http.<verb>(path)` then `return data`. Add
its wrapper action to the owning store; do not import the client from a component.

**Add a new resource.** Two files, flat, no folders — `services/<abbrev>Api.js` beside these two and
`store/<abbrev>Store.js` beside the three stores. Give the new client its **own** `axios.create`; do not
export the instance from an existing module and do not have the two clients import each other.

**Add a header to every request of one resource.** Set it on that module's `axios.create` call. Because
the instances are separate, this cannot leak into the other resource — which is the whole reason there
are two.

**Consume a new SSE event type.** Nothing changes here. Anything that is not `done`, `stream_end` or
`error` already falls through to `onEvent`, so a new pipeline event reaches the store automatically; the
work is on the store side.

**What not to touch.** Do not remove `{ stream: true }` from the decoder or the `lines.pop()` carry-over
— both fix intermittent, unreproducible corruption, which is the worst class of bug to reintroduce. Do
not replace `fetch` with `EventSource`: it cannot POST. Do not delete the `stream_end` no-op branch on
the grounds that it does nothing.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **`fetch` + `ReadableStream` instead of `EventSource`.** The query endpoint takes a JSON body, and
  `EventSource` is GET-only. The cost is real: automatic reconnection, `Last-Event-ID` replay and frame
  parsing all have to be given up or hand-written. This implementation hand-writes the parsing and gives
  up reconnection entirely — appropriate for a pipeline run that is not resumable anyway, since the
  server's session queue is process memory.

- **Two clients rather than one.** Four duplicated lines against genuine independence. The tie-breaker
  is that one of the two modules does not use axios for its most important function, so a shared
  instance would only ever cover part of the surface.

- **Return `data`, always.** A one-line convention that keeps axios's shape out of every store and makes
  a future transport swap a change in eight functions rather than everywhere.

- **Cancellation as a returned controller.** The alternative — a module-level "current request" that
  `abort()` looks up — would be shorter and would make concurrent queries impossible to reason about.
  Handing the controller to the caller keeps the client stateless, which is why these two modules hold
  no state at all.

**Continue reading:**

- [`../state/README.md`](../state/README.md) — the stores that wrap all eight functions
- [`../chat/pipeline-tracker.md`](../chat/pipeline-tracker.md) — what the forwarded events become on screen
- [`../knowledge-base/README.md`](../knowledge-base/README.md) — the upload path, both progress phases
- [`../../../Backend/Documentation/api/query.md`](../../../Backend/Documentation/api/query.md) — the streaming endpoint in full
- [`../../../Backend/Documentation/sse-event-bus/README.md`](../../../Backend/Documentation/sse-event-bus/README.md) — how the frames are produced
