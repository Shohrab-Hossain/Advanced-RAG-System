<div align="center">

# 📡 SSE Event Bus

### Fifty lines and one module-level dict that carry every pipeline event from a daemon thread to the browser — and stay silent when nobody is listening.

<br>

[![Transport](https://img.shields.io/badge/transport-text%2Fevent--stream-1c7ed6)](#52-the-wire-format-and-what-it-omits)
[![Module](https://img.shields.io/badge/events.py-50%20lines-7c5cff)](#-2-where-it-lives)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Event types](https://img.shields.io/badge/event%20types-10-f59e0b)](#-6-wire-shape-cross-boundary-contracts)
[![Timeout](https://img.shields.io/badge/per--event%20timeout-180s-f59e0b)](#42-the-180-second-timeout)
[![Workers](https://img.shields.io/badge/workers-exactly%201-ef4444)](#33-one-process-one-worker)

</div>

<br>

---

<br>

## Content Tree

<pre>
SSE Event Bus
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│   ├── <a href="#11-what-the-user-sees">1.1 What the user sees</a>
│   └── <a href="#12-what-happens-when-the-user-walks-away">1.2 What happens when the user walks away</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-the-five-functions">3.1 The five functions</a>
│   ├── <a href="#32-two-threads-one-queue">3.2 Two threads, one queue</a>
│   └── <a href="#33-one-process-one-worker">3.3 One process, one worker</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-the-six-phases-of-a-session">4.1 The six phases of a session</a>
│   ├── <a href="#42-the-180-second-timeout">4.2 The 180-second timeout</a>
│   └── <a href="#43-teardown-and-the-double-sentinel">4.3 Teardown, and the double sentinel</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-emit-and-why-the-no-op-is-load-bearing">5.1 emit(), and why the no-op is load-bearing</a>
│   ├── <a href="#52-the-wire-format-and-what-it-omits">5.2 The wire format, and what it omits</a>
│   ├── <a href="#53-the-consumer-is-fetch--readablestream-not-eventsource">5.3 The consumer is fetch + ReadableStream, not EventSource</a>
│   └── <a href="#54-the-stage-id-contract">5.4 The stage-id contract</a>
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

The event bus is how a query's progress reaches the browser. `POST /api/query` does not return an answer
— it returns an open `text/event-stream` response, starts the LangGraph pipeline on a **daemon thread**,
and forwards whatever that thread pushes into an in-memory queue. The pipeline's eight nodes call one
function, `emit()`, and know nothing about HTTP.

The whole bus is `custom_packages/rag_pipeline/events.py`: **50 lines, five functions, one module-level
dict.** It is the smallest module in the backend and the one every node depends on.

```python
# custom_packages/rag_pipeline/events.py:14
# session_id → Queue
_sessions: dict[str, queue.Queue] = {}
```

> [!IMPORTANT]
> **`emit()` must stay a no-op for an unknown session.** Its `if q:` guard (`events.py:36`) is not
> defensive tidiness — it is the guardrail the whole design rests on. The daemon thread keeps emitting
> for the full life of the run, and every one of those calls lands after `close_session` has already
> popped the queue for a browser that closed its tab. **Make `emit()` raise on an unknown session and a
> disconnected browser becomes a pipeline crash.** The corollary is just as important: a disconnect frees
> the socket, never the compute. The thread runs on.

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

### 1.1 What the user sees

The chat page's pipeline tracker shows eight rows — one per stage — that light up as the run progresses,
each carrying a live status message: *"Searching…"*, *"Vector: 10 | BM25: 7 | Graph: 3"*, *"Context
already within limit"*, *"Verifying grounding (attempt 1)"*. On a retry the tracker resets the seven
downstream rows and re-runs them. When the run ends, the answer and its source cards render from a final
`done` frame.

None of that is polling. Every one of those updates is a `data:` frame pushed the instant the node
produced it, which is why the tracker moves in real time on a run that takes thirty seconds.

### 1.2 What happens when the user walks away

Closing the tab aborts the `fetch`, which closes the socket. Flask's generator stops being consumed, and
its `finally` calls `close_session` (`query_routes.py:112-113`).

**The pipeline does not stop.** The daemon thread continues through every remaining node — every LLM
call, every retrieval, every rerank — writing into a queue nobody drains, and each `emit()` silently
no-ops once the session has been popped. The user sees nothing more; the machine does all the work
anyway, and pays for all the tokens.

---

## 📍 2. WHERE IT LIVES

Paths are relative to the package root, `Backend/src/adrag/`, except the last two.

| Concern | Path | Anchor |
|---|---|---|
| The bus | `custom_packages/rag_pipeline/events.py` | `_sessions`, `create_session`, `emit`, `close_session`, `format_sse` |
| The producer | `routes/query/query_routes.py:81` | `_run` — the daemon thread body |
| The consumer | `routes/query/query_routes.py:102` | `_generate` — the SSE generator |
| The timeout | `routes/query/query_routes.py:28` | `_EVENT_TIMEOUT_SECONDS = 180` |
| Every emitter | `custom_packages/rag_pipeline/{generation,retrieval,ranking}/*.py` | 31 `emit()` call sites across 8 nodes |
| Browser reader | `Frontend/src/services/ragApi.js:40` | `streamQuery` |
| Browser dispatch | `Frontend/src/store/ragStore.js:16` | `STAGES` + `_applyEvent` |

```text
custom_packages/rag_pipeline/
│
└── 📄 events.py               The whole bus — sessions, emit(), the sentinel, the frame formatter

routes/query/
│
└── 📄 query_routes.py         POST /api/query — validates, opens a session, forks the producer,
                               drains the queue, frames each item as an SSE data: line
```

---

## 🏗️ 3. ARCHITECTURE

### 3.1 The five functions

| Function | Line | Signature | Behaviour |
|---|---|---|---|
| `create_session` | `:18-24` | `(session_id: Optional[str] = None) -> Tuple[str, queue.Queue]` | mints a `uuid4` if none given, creates an **unbounded** `queue.Queue()`, registers it, returns `(id, q)` |
| `get_queue` | `:27-28` | `(session_id) -> Optional[queue.Queue]` | plain dict lookup |
| `emit` | `:31-37` | `(session_id: Optional[str], event_type: str, data: dict) -> None` | two guards, then `q.put({"type": …, "data": …})` |
| `close_session` | `:40-45` | `(session_id) -> None` | pushes the `None` sentinel, then pops the queue |
| `format_sse` | `:48-50` | `(payload: dict) -> str` | `f"data: {json.dumps(payload)}\n\n"` |

> [!NOTE]
> **Two of the five are effectively dead, and it is better to know that than to reason around them.**
> `get_queue` has **zero callers** anywhere in `Backend/` — it is unused public surface.
> `create_session`'s auto-uuid branch (`:20-21`) never runs either: its only caller mints its own id
> first and passes it in, discarding the returned one with `_,` (`query_routes.py:51-52`). The id is
> generated in the route because the route needs it for `close_session` in a `finally`, long after
> `create_session` has returned.

### 3.2 Two threads, one queue

The producer and the consumer of every session are **different threads in the same process**, joined by
nothing but a `queue.Queue`:

- **The producer** is the daemon thread running `rag_graph.invoke(initial_state)`. Nodes on it call
  `emit(session_id, type, data)`, which looks the session up in `_sessions` and puts a dict on its queue.
- **The consumer** is the Flask request thread running the `_generate()` generator, blocking on
  `event_queue.get(timeout=180)` and yielding each item as an SSE frame.

`_sessions` itself has **no lock**. Correctness relies on CPython's atomic dict get/set/pop under the
GIL — a session is registered once by the request thread before the producer starts, read by the
producer, and popped once by the request thread at teardown. There is no read-modify-write anywhere in
the module, which is why the absence of a lock is safe rather than merely lucky.

The queue is **unbounded**, so the pipeline never blocks on a slow reader, and it is FIFO with exactly
one producer — so **strict emission order is preserved end to end**. The thread also starts *before*
Flask begins consuming the generator (`query_routes.py:100` precedes the `Response(...)` return at
`:115`), so early events are buffered, never lost.

### 3.3 One process, one worker

`_sessions` is **process memory**. That single fact, plus two others, pins the entire backend to one
worker:

1. **Fork the process and the producer lands in one copy while the SSE generator serving that client may
   be in another.** `emit()` writes to a queue nobody drains; the browser sees an empty stream that
   eventually times out.
2. **Every store is a module singleton** (`vector_store.py:250-253`, `bm25_store.py:114`,
   `graph_store.py:185`). Two workers hold divergent in-memory BM25 corpora and graphs, each overwriting
   the other's pickle on write.
3. **The registry's lock is per-process** (`registry.py:22`) and protects nothing across a fork.

Hence `app.run(..., threaded=True)` for development (`main.py:51`) and gunicorn with **`-w 1`** plus the
gevent-websocket worker class for production — both documented in `main.py:15-20` and `app.py:17-19`.
The `prod` extra in `pyproject.toml` exists to install exactly those two dependencies.

**What *is* supported is concurrency across queries**: each run gets its own `uuid4` session and its own
queue, served by its own thread. The stores are shared and unsynchronised, so concurrent *ingest* is the
unsafe operation — concurrent *query* is read-only against them.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 The six phases of a session

<p align="center">
  <img src="../../../.readme-lib/documentation/sse-event-bus/diagrams/svg/sse-session-lifecycle.svg" alt="The SSE session lifecycle across four participants: Browser, Flask request thread, queue.Queue and Daemon thread. The browser POSTs /api/query; a blank query or an unknown provider returns 400, the only HTTP error status in the whole flow. The route calls create_session(uuid4()), registering an unbounded in-memory queue in _sessions, and seeds the 21-key initial_state carrying session_id. From there the run is parallel. The producer branch starts a daemon thread — Thread(target=_run, daemon=True).start() — whose nodes call emit(session_id, type, data), which is q.put from 31 call sites and a NO-OP for an unknown session: make it raise and a dead browser crashes the whole pipeline. The consumer branch returns 200 text/event-stream, after which the headers are committed and every later failure is in-band. If an item arrives within 180 seconds the generator does q.get(timeout=180) and yields a data frame — the timeout is per event, so the clock resets on every frame. If queue.Empty is raised instead, the generator yields a Stream timeout error event and close_session() pops the queue: that frees the SOCKET, never the COMPUTE — the daemon runs to completion and every later emit() no-ops into an orphaned queue. On the normal path the daemon puts done directly, bypassing emit(), then puts None as the sentinel; the generator turns the sentinel into a stream_end frame and close_session() pops the queue. done, error and stream_end are route-framed, not node-emitted, and close_session() pushes a second sentinel that nobody reads." width="780">
</p>

<sub>Diagram source: <a href="../../../.readme-lib/documentation/sse-event-bus/diagrams/mermaid-source/sse-session-lifecycle.mmd"><code>sse-session-lifecycle.mmd</code></a> — edit it, then regenerate the SVG (don't hand-edit the SVG).</sub>

**Phase 1 — validate, while it is still an ordinary JSON request.** `query_routes.py:40-49`. A missing
or blank `query` returns `400`; a `provider` outside `("openai", "ollama")` returns `400`. **These are
the only two error paths in the whole flow that produce an HTTP error status** — past this point the
response headers are committed and every failure is in-band.

**Phase 2 — open the session.**

```python
# routes/query/query_routes.py:51
session_id = str(uuid.uuid4())
_, event_queue = create_session(session_id)
```

The route keeps a **direct reference** to the queue object. That reference is what makes phase 6's
orphaned-queue behaviour possible.

**Phase 3 — seed the state.** All 22 `RAGState` keys are written here (`:54-79`), including
`session_id`, which is how every node reaches `emit()` without importing Flask. The key-by-key table is
in [`../rag-pipeline/state-model.md`](../rag-pipeline/state-model.md).

**Phase 4 — fork the producer.**

```python
# routes/query/query_routes.py:81
def _run():
    try:
        result = rag_graph.invoke(initial_state)
        event_queue.put({"type": "done", "data": {...}})
    except Exception as exc:
        event_queue.put({"type": "error", "data": {"message": str(exc), "stage": "pipeline"}})
    finally:
        event_queue.put(None)   # sentinel → close stream

threading.Thread(target=_run, daemon=True).start()
```

`_run` closes over `event_queue` and calls `.put()` **directly** — so `done` and `error` bypass `emit()`
entirely, which is why they carry no pipeline `stage` and are described here as *route-framed*. The
thread is `daemon=True`, so it does not keep the interpreter alive at shutdown: a `Ctrl-C` mid-pipeline
abandons the run with the stores possibly half-written.

**Phase 5 — drain, on the request thread.**

```python
# routes/query/query_routes.py:102
def _generate():
    try:
        while True:
            item = event_queue.get(timeout=_EVENT_TIMEOUT_SECONDS)
            if item is None:
                yield format_sse({"type": "stream_end"})
                break
            yield format_sse(item)
    except Exception:
        yield format_sse({"type": "error", "data": {"message": "Stream timeout"}})
    finally:
        close_session(session_id)
```

The response is returned with `mimetype="text/event-stream"` and three headers (`:115-123`):
`Cache-Control: no-cache`, `Connection: keep-alive`, and **`X-Accel-Buffering: no`** — the last tells
nginx not to buffer the response. Without it a reverse proxy holds frames until the response completes
and the live tracker appears frozen for the entire run.

**Phase 6 — teardown.** Covered in §4.3.

### 4.2 The 180-second timeout

`_EVENT_TIMEOUT_SECONDS = 180` is a **hardcoded module constant, not env-driven** (`query_routes.py:28`).
The comment above it is the fact to lead with:

```python
# routes/query/query_routes.py:26
# A disconnected browser frees the socket, never the compute — the daemon thread
# runs to completion regardless. This is the only bound on a wedged pipeline.
_EVENT_TIMEOUT_SECONDS = 180
```

Three properties, each of which is commonly assumed wrong:

- **It is per-event, not total.** The clock resets on every frame. A twenty-minute run that emits
  something every thirty seconds never trips it; a single stage that stalls for 181 seconds does.
- **It ends the HTTP response, not the pipeline.** After it fires, `close_session` pops the queue, every
  subsequent `emit()` hits the `if q:` guard and no-ops, and **the pipeline continues to completion —
  burning LLM calls, writing results nobody reads.**
- **`_run`'s final `event_queue.put({...done})` still succeeds**, because the closure holds the queue
  object even though `_sessions` no longer does. The answer is deposited into an orphaned queue which is
  then garbage-collected.

From the browser's perspective this is the practical bound on a wedged pipeline. From the machine's
perspective the compute is unbounded, and the only in-graph limit is the reflection retry budget
described in [`../rag-pipeline/README.md`](../rag-pipeline/README.md).

### 4.3 Teardown, and the double sentinel

On the normal path the `None` sentinel is enqueued **twice**: once by `_run`'s `finally`
(`query_routes.py:98`) and once by `close_session` (`events.py:44`) after the generator has already
broken out of its loop. The second is never read, and is discarded along with the queue by the
`_sessions.pop` on the next line.

It is harmless, but it looks like a bug to anyone tracing the code, so it is written down here rather
than left to be rediscovered. The two puts exist because `_run` cannot know whether the consumer is
still there, and `close_session` cannot know whether the producer already finished.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 `emit()`, and why the no-op is load-bearing

**The problem:** eight nodes running on a background thread must report progress to a consumer that may
have vanished at any moment, and none of them has any way to find out that it did.

```python
# custom_packages/rag_pipeline/events.py:31
def emit(session_id: Optional[str], event_type: str, data: dict) -> None:
    """Push a typed event into the session queue (no-op if session gone)."""
    if not session_id:
        return
    q = _sessions.get(session_id)
    if q:
        q.put({"type": event_type, "data": data})
```

**Two independent guards, and they cover different cases:**

- `if not session_id` covers a pipeline invoked with **no session at all**. `session_id` is `str | None`
  on `RAGState`, so `rag_graph.invoke()` works headless in a script or a smoke test with no HTTP
  anywhere in the picture.
- `if q` covers a session that **existed and has since been closed**. This is the common case, not the
  exotic one: every closed tab, every timeout, every aborted request produces a long tail of `emit()`
  calls into a session that is gone.

**`emit()` never signals failure.** It returns `None` on every path, so a node cannot tell whether its
event reached anyone — which is exactly why no node checks, and why no node needs a try/except around a
progress report.

### 5.2 The wire format, and what it omits

`format_sse` (`events.py:48-50`) produces one line, twice-newline-terminated:

```text
data: {"type": "stage_start", "data": {"stage": "retrieval", "message": "Searching..."}}

```

That is the entire protocol. **Everything the SSE specification offers beyond `data:` is absent, and
each omission has a consequence:**

| Absent field | Consequence |
|---|---|
| `event:` | Every frame arrives on the **default** channel. A browser cannot `addEventListener('stage_start', …)` — the type lives *inside* the JSON and must be dispatched in application code. |
| `id:` | No `Last-Event-ID`, therefore no resumable stream. |
| `retry:` | No server-controlled reconnect interval. |
| any heartbeat / comment keep-alive | A silent pipeline sends **nothing** for up to 180 seconds. Any intermediary with a shorter idle timeout cuts the connection first, and the client cannot distinguish that from a crash. |

### 5.3 The consumer is `fetch` + `ReadableStream`, not `EventSource`

The reason is stated in the client's own docstring (`ragApi.js:31-32`): *"Uses fetch + ReadableStream so
we can POST with a body."* `EventSource` is GET-only, and the query — with its `query`, `provider` and
optional `model` fields — is a POST.

```js
// Frontend/src/services/ragApi.js:62
const { done, value } = await reader.read()
if (done) break

buffer += decoder.decode(value, { stream: true })
const lines = buffer.split('\n')
buffer = lines.pop()   // last (possibly incomplete) line stays in buffer

for (const line of lines) {
  if (!line.startsWith('data: ')) continue
  ...
}
```

The client decodes with a `TextDecoder`, **keeps the last partial line in a buffer** across chunk
boundaries, drops anything not starting with `data: `, and `JSON.parse`s the remainder. Dispatch is four
branches (`ragApi.js:76-84`): `done` → `onDone`; `stream_end` → a **deliberate no-op**; `error` →
`onError`; **everything else** → `onEvent(type, data)`, which is where the eight stage ids get matched.
A malformed line is swallowed by a bare `catch` (`:85-87`).

> [!NOTE]
> **A consequence of not using `EventSource`: there is no automatic reconnection.** `EventSource`
> reconnects on its own; a `fetch` stream does not. A dropped stream is simply a dropped stream, and
> because the protocol carries no `id:` there would be nothing to resume from anyway.

### 5.4 The stage-id contract

Every progress frame carries a `stage` field **inside** its `data` payload, and that string — not the
LangGraph node name — is what the frontend matches.

**Five of the eight differ from their node name.** The emitted set, verified at every `emit()` call
site, is:

`planner` · `retrieval` · `external_tools` · `aggregator` · `reranker` · `compressor` · `reasoning` · `reflection`

while `workflow.py` registers the nodes as `planner` · `retrieval` · `external_tools` · `aggregate` ·
`rerank` · `compress` · `reason` · `reflect`. Only the first three coincide.

> [!WARNING]
> **The `emit()` call sites are the contract, not `workflow.py`.** Renaming a graph node breaks nothing.
> Changing a `stage` string inside an `emit()` payload silently stops the tracker updating that row —
> no error, no warning, just one row that never lights up — because `Frontend/src/store/ragStore.js:16-25`
> matches on the emitted value. The failure is invisible on the server and only shows in the UI. The
> per-node mapping is tabulated in [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md).

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

**Eleven distinct event types reach the browser. Seven originate in the pipeline via `emit()`; four are
framed by the route** and never pass through the bus at all:

| Event type | Framed by | Carries `stage`? | Origin |
|---|---|---|---|
| `stage_start` | node → `emit()` | ✅ | 8 call sites |
| `stage_complete` | node → `emit()` | ✅ | 11 call sites |
| `stage_skip` | node → `emit()` | ✅ | 2 call sites |
| `stage_error` | node → `emit()` | ✅ | 7 call sites |
| `retrieval_result` | node → `emit()` | ✅ | `hybrid_node.py:45` |
| `finalize` | node → `emit()` | ✅ | `reflection.py:150` |
| `retry` | node → `emit()` | ❌ **deliberately** | `reflection.py:129` |
| `done` | **route** — `event_queue.put` | ❌ | `query_routes.py:84` |
| `error` (pipeline) | **route** — `_run`'s `except` | ⚠️ `"stage": "pipeline"` | `query_routes.py:93` |
| `error` (stream) | **route** — the generator's `except` | ❌ | `query_routes.py:111` |
| `stream_end` | **route** — the generator, on the sentinel | ❌ | `query_routes.py:107` |

> [!NOTE]
> **`error` is two different shapes under one name.** The worker's version carries
> `{message, stage: "pipeline"}`; the generator's carries `{message}` only. The client treats both
> identically (`ragApi.js:80-81`), reading `data?.message` and ignoring the rest — so the distinction is
> invisible in the UI but very much present on the wire.

**HTTP framing** — `POST /api/query`:

| Direction | Channel | Payload | Notes |
|---|---|---|---|
| Client → server | HTTP POST, JSON | `{query, provider?, model?}` | `provider` defaults to `Config.DEFAULT_PROVIDER`; `model` overrides the chat model for **both** providers |
| Server → client | `text/event-stream` | a sequence of `data: {json}\n\n` frames | headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Connection: keep-alive` |
| Server → client | HTTP status | `400` only | Emitted before streaming begins; every later failure is an in-band `error` event on a `200` |

The full per-event payload reference lives in [`../api/query.md`](../api/query.md).

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **Errors are in-band by necessity, not preference.** The response headers are committed the moment
  streaming starts, so a node that fails at second 30 physically cannot become a `500`. A pipeline
  failure is therefore a `200` carrying an `error` event. Any client that treats HTTP status as the
  success signal will report every failed run as a success.

- **The queue is unbounded, so a slow reader costs memory, not throughput.** A client that opens the
  stream and reads nothing simply accumulates frames until the run ends. Nothing applies backpressure to
  the pipeline, and nothing bounds the queue.

- **`emit()` is fire-and-forget in both directions.** It cannot report delivery, and the node cannot ask.
  Progress reporting is therefore never a source of pipeline failure — which is deliberate, and worth
  preserving.

- **`stream_end` is deliberately ignored by the client.** `ragApi.js:78-79` matches it and does nothing.
  The stream ending is already observable from the `fetch` reader's `done`, so the frame exists as a
  protocol marker rather than a signal anyone acts on.

- **The `retry` event carries no `stage` on purpose.** It is not a per-stage update; it announces that
  the whole tracker is about to reset for another pass. The frontend handles it **before** its
  `data?.stage` guard for exactly that reason (`ragStore.js:87-99`).

- **The generator's `except` is bare and mislabels every failure as *"Stream timeout"*.**
  `except Exception` at `query_routes.py:110` catches `queue.Empty` — the expected case — but would
  equally catch a `json.dumps` failure inside `format_sse` on a non-serialisable payload, and report it
  with the same misleading message. Every payload built today is JSON-primitive, so this is a latent
  diagnostic trap rather than a live bug.

- **Nothing cleans up an abandoned session except the generator's `finally`.** There is no reaper, no
  TTL sweep and no maximum session count. If a request thread were killed without unwinding, its
  `_sessions` entry would leak for the life of the process. In practice Flask always runs the generator's
  `finally`, so this has no observed trigger — but it is the only thing standing between the design and
  an unbounded dict.

---

## 💥 8. FAILURE MODES

| Failure | Symptom | Behaviour |
|---|---|---|
| Missing / empty `query` | `400` JSON, no stream | The only pre-stream rejection alongside a bad `provider` |
| `provider` not `openai`/`ollama` | `400` JSON, no stream | Validated at `query_routes.py:45-46` |
| A node raises and does not catch it | `error` event with `{"message": …, "stage": "pipeline"}` on a `200` | `_run`'s `except`; the sentinel still follows from its `finally` |
| A node catches its own failure | `stage_error` on that row, run continues degraded | Per-node fallbacks — see [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md) |
| No frame for 180 s | `error` event `{"message": "Stream timeout"}`, stream closes | **Frees the browser only** — the daemon thread runs to completion |
| Browser disconnects | Stream closes; `close_session` pops the queue | Every later `emit()` no-ops; the compute is not freed |
| Reverse proxy buffers the response | Tracker appears frozen, then all frames arrive at once | `X-Accel-Buffering: no` prevents this on nginx; other proxies need their own equivalent |
| Malformed frame reaches the client | Silently dropped | Bare `catch` in the client's parse loop (`ragApi.js:85-87`) |
| More than one worker process | Empty stream that eventually times out | The producer and consumer land in different processes — see §3.3 |

> [!CAUTION]
> **A disconnect frees the socket and never the compute — and there is no way to cancel a run.** Nothing
> in the system can stop a pipeline once `rag_graph.invoke()` is underway: not closing the tab, not the
> 180-second timeout, not the client's `abort()`. The daemon thread completes every remaining node, makes
> every remaining LLM call, and then puts its result into a queue that no longer has a reader. On a paid
> provider that is real money spent on an answer nobody will ever see, and there is no counter anywhere
> that would show it happening.

---

## 🧩 9. EXTENSION POINTS

**Add an event type.** Call `emit(state.get("session_id"), "<type>", {...})` from the node, and add a
branch to the client's dispatch in `ragApi.js:76-84` — anything unrecognised currently falls through to
`onEvent`, so it will reach `ragStore._applyEvent` and be ignored there unless you handle it. Keep the
`Emits:` line in the node's module docstring current; it is the only inventory of what a node produces.

**Add a stage row.** The emitted `stage` string must be added to `STAGES` in
`Frontend/src/store/ragStore.js:16-25`. The node name is irrelevant (§5.4).

**Change the timeout.** `_EVENT_TIMEOUT_SECONDS` at `query_routes.py:28`. It is not env-driven; making
it so would mean adding a `Config` attribute and an `.env.example` line, per the convention in
[`../configuration.md`](../configuration.md). Remember it bounds the *gap between frames*, so lowering it
mostly punishes slow single stages, and raising it delays nothing except the browser's release.

**Add a keep-alive.** The natural place is inside `_generate`'s loop: catch `queue.Empty` on a shorter
timeout and yield an SSE comment line (`: ping\n\n`) rather than an error, tracking total elapsed time
separately. That would also fix the bare-`except` mislabelling noted in §7.

**What not to touch.** Do not make `emit()` raise or return a status — a disconnected browser would
become a pipeline crash. Do not bound the queue without deciding what a full queue should do; blocking
it would stall the pipeline on a slow client. Do not run more than one worker process (§3.3). Do not
make nodes import Flask or read the request; the whole reason the bus exists is that they cannot.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **Server-Sent Events instead of WebSockets.** The traffic is entirely one-directional — the server
  narrates, the client listens — and SSE is a plain HTTP response with no handshake, no protocol
  upgrade, no connection registry and no extra dependency in the request path. The cost is that the
  client cannot send anything back over the same channel, which is why cancellation does not exist
  (§8) and why the query itself has to be a separate POST body rather than a message.

- **A background thread instead of a task queue.** Running the graph on a daemon thread inside the
  request process keeps the whole system to one process with no broker, which is right for a
  single-machine tool. The price is that the run's lifetime is decoupled from the request's without
  anyone owning it: no cancellation, no persistence, no visibility, and no bound but the retry budget.

- **The type inside the payload rather than in an SSE `event:` field.** It makes the client's dispatch a
  plain `switch` over a JSON field instead of a set of `addEventListener` registrations, which suits a
  consumer that is already parsing JSON out of `fetch` chunks. It also means the transport carries no
  semantics at all — a frame is a frame — so adding an event type requires no protocol change.

- **One worker, always.** Not a performance decision but a correctness one: session queues are process
  memory and every store is a module singleton. This is the constraint that shapes the deployment
  command, and it is why the production recipe carries `-w 1` explicitly rather than relying on a
  default.

**Continue reading:**

- [`../rag-pipeline/README.md`](../rag-pipeline/README.md) — the eight-node pipeline that produces these events
- [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md) — every node's emits, node by node
- [`../rag-pipeline/state-model.md`](../rag-pipeline/state-model.md) — `session_id` on `RAGState`, and the 22 seeded keys
- [`../api/query.md`](../api/query.md) — `POST /api/query` and the full per-event payload reference
- [`../architecture/query-lifecycle.md`](../architecture/query-lifecycle.md) — the two threads and the queue in their end-to-end context
- [`../configuration.md`](../configuration.md) — the settings around the stream, and the ones that are hardcoded
- [`../../../Frontend/Documentation/api-clients/README.md`](../../../Frontend/Documentation/api-clients/README.md) — the browser-side reader: `streamQuery`, the partial-frame carry-over, the four-way dispatch
- [`../../../Frontend/Documentation/state/README.md`](../../../Frontend/Documentation/state/README.md) — `STAGES` and `_applyEvent`, where these frames become UI state
