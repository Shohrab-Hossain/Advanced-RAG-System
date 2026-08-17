<div align="center">

# 🔄 Query Lifecycle

### One request from `POST` to rendered answer — ten phases, two threads, eight nodes, and a status line that is fixed at `200` before any of the work begins.

<br>

[![Phases](https://img.shields.io/badge/phases-10-1c7ed6)](#-1-the-path-at-a-glance)
[![Nodes](https://img.shields.io/badge/graph%20nodes-8-7c5cff)](#-3-phase-7--the-graph-runs)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![LLM calls](https://img.shields.io/badge/LLM%20calls%20per%20pass-3%E2%80%934-f59e0b)](#34-three-or-four-llm-calls-per-pass)
[![Max passes](https://img.shields.io/badge/max%20passes-3-f59e0b)](#33-the-retry-loop)
[![HTTP errors](https://img.shields.io/badge/HTTP%20error%20statuses-2-ef4444)](#-6-failure-at-each-phase)

</div>

<br>

---

<br>

## Content Tree

<pre>
Query Lifecycle
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-path-at-a-glance">🧭 1. The path at a glance</a>
│
├── <a href="#-2-phases-16--from-post-to-committed-headers">🔌 2. Phases 1–6 — from POST to committed headers</a>
│   ├── <a href="#21-the-client-sends">2.1 The client sends</a>
│   ├── <a href="#22-validate">2.2 Validate</a>
│   ├── <a href="#23-open-the-session">2.3 Open the session</a>
│   ├── <a href="#24-seed-the-state">2.4 Seed the state</a>
│   ├── <a href="#25-fork-the-producer">2.5 Fork the producer</a>
│   └── <a href="#26-return-the-response">2.6 Return the response</a>
│
├── <a href="#-3-phase-7--the-graph-runs">🧬 3. Phase 7 — the graph runs</a>
│   ├── <a href="#31-the-eight-nodes-in-order">3.1 The eight nodes, in order</a>
│   ├── <a href="#32-the-three-shapes-a-request-can-take">3.2 The three shapes a request can take</a>
│   ├── <a href="#33-the-retry-loop">3.3 The retry loop</a>
│   └── <a href="#34-three-or-four-llm-calls-per-pass">3.4 Three or four LLM calls per pass</a>
│
├── <a href="#-4-phases-810--drain-terminate-tear-down">📤 4. Phases 8–10 — drain, terminate, tear down</a>
│
├── <a href="#-5-where-the-time-goes">⏳ 5. Where the time goes</a>
│
├── <a href="#-6-failure-at-each-phase">💥 6. Failure at each phase</a>
│
├── <a href="#%EF%B8%8F-7-edge-cases--gotchas">⚠️ 7. Edge cases &amp; gotchas</a>
│
└── <a href="#-8-related-reading">🔗 8. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

`POST /api/query` does not return an answer. It returns an **open `text/event-stream` response** and
starts the LangGraph pipeline on a background daemon thread, which pushes progress events into an
in-memory queue that the still-open response drains frame by frame. The answer arrives near the end, as
one more frame.

Everything that makes this endpoint unusual follows from one moment: **the response headers go out before
the work starts.** Two validation checks run while it is still an ordinary JSON request and can still
return `400`. After that the status line reads `200` and cannot be revised — so a node that fails at
second thirty cannot become a `500`, and the failure is delivered as an `error` event inside a
successful response.

> [!IMPORTANT]
> **A client that reads the HTTP status to decide whether a query succeeded will report every failed run
> as a success.** The status is decided at second zero. The outcome is in the frames.

This page is the narrative spine: it follows one request across every layer, in order. The deep detail
lives elsewhere and is linked at each step — per-node behaviour in
[`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md), per-event payloads in
[`../api/query.md`](../api/query.md), queue mechanics in
[`../sse-event-bus/README.md`](../sse-event-bus/README.md).

---

## 🧭 1. THE PATH AT A GLANCE

<p align="center">
  <img src="../../../.readme-lib/documentation/architecture/diagrams/svg/query-lifecycle.svg" alt="The full query lifecycle across four participants: Browser, Flask route + generator, queue.Queue and the LangGraph daemon thread. The browser POSTs /api/query with query, provider and an optional model, using fetch + ReadableStream and NOT EventSource, because the query is a POST that carries a body. A blank query or an unknown provider returns 400 — the only HTTP error status in the run. The route calls create_session(uuid4()), then starts Thread(target=_run, daemon=True): that hand-off is the point of no return, because a disconnect frees the SOCKET, never the COMPUTE. The route replies 200 text/event-stream, after which the headers are committed and every later failure is an in-band error delivered on a 200. The daemon runs node 1, planner, and emits stage &quot;planner&quot; carrying retrieve, use_external and query_type; the generator does q.get(timeout=180) and yields a data frame — shown once, because it drains continuously in strict FIFO order and the 180-second timeout is per event, so the clock resets on every frame. The planner router then branches three ways: retrieve is true, the default path, entering the graph at node 2 retrieval with every node 2 through 8 running; retrieve false but use_external true, entering at node 3 external_tools with node 2 skipped so the corpus is never searched; or neither, entering at node 4 aggregate with nodes 2 and 3 skipped and no evidence gathered at all. The five emits marked with an asterisk carry a stage id that DIFFERS from the graph node name — the emit() call site is the contract, never workflow.py, and changing an emitted id silently stops the frontend tracker updating that row. Inside a loop labelled retry, max 2 so 3 passes, the eight nodes run in order: node 2 retrieval emits stage &quot;retrieval&quot; with vector 10, BM25 10 and graph 5 fetched in series; node 3 external_tools emits stage &quot;external_tools&quot; with DuckDuckGo 5 results or a stage_skip; node 4 aggregate emits stage &quot;aggregator&quot;, deduplicating by MD5 of content; node 5 rerank emits stage &quot;reranker&quot;, cross-encoding to a top 5; node 6 compress emits stage &quot;compressor&quot;, skipped below 4000 characters; node 7 reason emits stage &quot;reasoning&quot; with the cited answer; and node 8 reflect emits stage &quot;reflection&quot; as both critic and terminator. A retry happens only when the answer is NOT grounded AND should_retry is set AND retry_count is below 2 — it emits retry and re-enters the graph at node 2, while _route_reflection tests final_answer alone and nothing else. Finally the daemon puts done with answer, sources and metadata directly on the queue, bypassing emit(), then puts the None sentinel; the generator yields stream_end and close_session() pops the queue. done, error and stream_end are route-framed, not node-emitted — no node writes them, and a pipeline failure is a 200 carrying an error event, never an HTTP error status." width="820">
</p>

<sub>Diagram source: <a href="../../../.readme-lib/documentation/architecture/diagrams/mermaid-source/query-lifecycle.mmd"><code>query-lifecycle.mmd</code></a> — edit it, then regenerate the SVG (don't hand-edit the SVG).</sub>

Ten phases. Phases 1–6 are HTTP framing and take milliseconds; phase 7 is the entire pipeline; phases
8–10 run concurrently with it and outlive nothing.

| # | Phase | Where | The one thing that matters |
|---|---|---|---|
| 1 | **Client sends** | `ragApi.js:45-58` | `fetch` + `ReadableStream`, **not `EventSource`** — the query is a POST with a body. Consequence: no automatic reconnection. |
| 2 | **Validate** | `query_routes.py:40-49` | Two `400`s — blank `query`, unknown `provider`. **The only HTTP error statuses in the entire flow.** |
| 3 | **Open the session** | `:51-52` | `uuid4()` + an **unbounded** `queue.Queue` registered in `_sessions`; the route keeps a direct reference to the queue object. |
| 4 | **Seed state** | `:54-79` | **All 22 `RAGState` keys are written before invocation.** Nothing appears mid-run. |
| 5 | **Fork the producer** | `:81-100` | `threading.Thread(target=_run, daemon=True).start()` — started *before* Flask consumes the generator, so no early event is lost. |
| 6 | **Return the response** | `:115-123` | `text/event-stream` + three headers. **Once these are on the wire the status is `200` forever.** |
| 7 | **The graph runs** | `workflow.py:107` → the eight nodes | `rag_graph.invoke(initial_state)` with **no `config`** — no `recursion_limit`, no `thread_id`, no checkpointer. |
| 8 | **Drain** | `:102-113` | `q.get(timeout=180)` → `yield format_sse(item)`. **The timeout is per event; the clock resets on every frame.** |
| 9 | **Terminate** | `:84-98`, `:106-108` | `_run` puts `done` (or `error`) **directly on the queue, bypassing `emit()`**, then always puts the `None` sentinel. |
| 10 | **Teardown** | `:112-113` | `finally: close_session()` pops the queue and pushes a second sentinel nobody reads. |

---

## 🔌 2. PHASES 1–6 — FROM POST TO COMMITTED HEADERS

### 2.1 The client sends

The browser does not use `EventSource`, and the client's own docstring says why (`ragApi.js:31-32`):
*"Uses fetch + ReadableStream so we can POST with a body."* `EventSource` is GET-only, and the request
carries `query`, an optional `provider` and an optional `model`.

```json
{ "query": "How does the reranker score documents?", "provider": "openai" }
```

**The cost of that choice is reconnection.** `EventSource` reconnects on its own; a `fetch` stream does
not. A dropped stream is simply dropped, and since the wire protocol carries no `id:` field there would
be nothing to resume from anyway.

### 2.2 Validate

```python
# routes/query/query_routes.py:41
query = (body.get("query") or "").strip()
```

Two checks, both returning `400` with a JSON `{"error": …}` body:

| Check | Condition | Line |
|---|---|---|
| Blank query | `query` missing or empty after `.strip()` | `:41-42` |
| Unknown provider | `provider` not in `("openai", "ollama")` | `:44-46` |

`provider` defaults to `Config.DEFAULT_PROVIDER` when the body omits it, and
`ollama_model = body.get("model") or None` — the `or None` turning an empty string into an absent value.

> [!WARNING]
> **A non-string `query` is a `500`, not a `400`.** Both checks sit outside any `try`, so a body of
> `{"query": 42}` raises `AttributeError: 'int' object has no attribute 'strip'` straight out of the
> route — reproduced this run. With the default `FLASK_DEBUG=true` that renders Werkzeug's interactive
> debugger rather than an error page. See [`../security.md`](../security.md#-4-the-interactive-debugger-is-on).

### 2.3 Open the session

```python
# routes/query/query_routes.py:51
session_id = str(uuid.uuid4())
_, event_queue = create_session(session_id)
```

`create_session` registers an **unbounded** `queue.Queue` in the module-level `_sessions` dict. Two
details shape everything downstream:

- **The route keeps a direct reference to the queue object**, not just its key. That reference is why a
  timed-out stream's `done` frame still lands somewhere — the producer's closure holds the queue even
  after `_sessions` has dropped it.
- **The id is minted in the route, not by `create_session`.** The route needs it for `close_session` in a
  `finally`, long after `create_session` returned, so it passes its own and discards the returned one.

### 2.4 Seed the state

All **22 `RAGState` keys are written before the graph is invoked** (`:54-79`). Nothing appears mid-run;
no node has to guard against a missing key.

```python
# routes/query/query_routes.py:59
# Planner will overwrite these:
"retrieve": True,
"use_external": False,
"query_type": "factual",
```

`session_id` rides on the state — **that is how a node reaches `emit()` without importing Flask.** The
key-by-key writer/reader matrix is in
[`../rag-pipeline/state-model.md`](../rag-pipeline/state-model.md#-2-the-22-state-keys).

### 2.5 Fork the producer

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

**The thread starts before Flask begins consuming the generator** — `:100` precedes the `Response(...)`
return at `:115` — so events produced in the first milliseconds are buffered by the queue, never lost.

`daemon=True` means the thread does not keep the interpreter alive at shutdown: a `Ctrl-C` mid-pipeline
abandons the run wherever it stands.

### 2.6 Return the response

```python
# routes/query/query_routes.py:115
Response(_generate(), mimetype="text/event-stream", headers={
    "Cache-Control":     "no-cache",
    "X-Accel-Buffering": "no",
    "Connection":        "keep-alive",
})
```

`X-Accel-Buffering: no` is the one that is easy to omit and expensive to debug: it tells nginx not to
buffer the response. Without it a reverse proxy holds every frame until the response completes, and the
live tracker appears frozen for the whole run before all eight rows light up at once.

**This is the commitment point.** From here the status line is `200` and every subsequent failure is an
in-band `error` event.

---

## 🧬 3. PHASE 7 — THE GRAPH RUNS

`rag_graph.invoke(initial_state)` runs the compiled LangGraph workflow on the daemon thread. **No
`config` is passed** — no `recursion_limit`, no `thread_id`, no checkpointer — so the graph is stateless
between requests and its only loop bound is the reflection retry budget (§3.3).

### 3.1 The eight nodes, in order

Each node's full behaviour is in [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md). What this page
owes is the one-line contribution of each to *this* request, and the `stage` id it puts on the wire.

| # | Graph node | Emitted `stage` id | Contribution | LLM? |
|---|---|---|---|---|
| 1 | `planner` | `planner` | Self-RAG decision — `retrieve` / `use_external` / `query_type`. **Fails toward retrieval.** | ✅ |
| 2 | `retrieval` | `retrieval` | Three **sequential** store searches: vector `top_k=10`, BM25 `top_k=10`, graph `top_k=5`. | ❌ |
| 3 | `external_tools` | `external_tools` | DuckDuckGo, `WEB_RESULTS = 5`, hardcoded. Self-skips when `use_external=False`. **Always non-fatal.** | ❌ |
| 4 | `aggregate` | ⚠️ **`aggregator`** | Concatenate vector + BM25 + graph + web, dedup by **MD5 of `content`**, sort by the incomparable raw `score`. | ❌ |
| 5 | `rerank` | ⚠️ **`reranker`** | Cross-encoder scores **every** candidate on one comparable scale; slice to `RERANK_TOP_K = 5` → `context`. **The dominant local compute.** | ❌ (a local model) |
| 6 | `compress` | ⚠️ **`compressor`** | **Usually a no-op** — the LLM only runs above `MAX_CONTEXT_CHARS = 4000`, and five chunks of ~500 chars is about 2 500. | conditional |
| 7 | `reason` | ⚠️ **`reasoning`** | Builds the 1-based source list first, then the cited answer. **Only sources the model lists in `cited_sources` survive.** | ✅ |
| 8 | `reflect` | ⚠️ **`reflection`** | Critic, loop controller and terminator. **Only this node writes `final_answer`, and writing it is what ends the graph.** | ✅ |

> [!WARNING]
> **Five of those eight stage ids differ from the node name, and the `emit()` call site is the
> contract.** `workflow.py` registers `aggregate` · `rerank` · `compress` · `reason` · `reflect`; the
> frames those nodes put on the wire carry `aggregator` · `reranker` · `compressor` · `reasoning` ·
> `reflection`, and it is the emitted value that `Frontend/src/store/ragStore.js:16-25` matches.
> Renaming a graph node breaks nothing. Changing an `emit()` `stage` string silently stops one tracker
> row from ever lighting up.

### 3.2 The three shapes a request can take

The planner's decision is a conditional edge, so not every request visits every node.

| Shape | Planner returns | Route through the graph | LLM calls |
|---|---|---|---|
| **Full RAG** (the common case) | `retrieve=True` | `planner → retrieval → external_tools → aggregate → rerank → compress → reason → reflect` | 3–4 |
| **Web-only** | `retrieve=False, use_external=True` | `planner → external_tools → aggregate → …` — the knowledge base is skipped entirely | 3–4 |
| **Direct answer** | `retrieve=False, use_external=False` | `planner → aggregate → …`; `all_docs=[]` → `context=[]` → reasoning takes its **no-context** branch and returns `sources: []` | 2 |

### 3.3 The retry loop

`reflect → retrieval` is the graph's **only loop edge**. The reflection node judges whether the answer is
grounded in the retrieved context; when it is not, and the retry budget allows, it emits a `retry` event
and sends the run back to retrieval for another full pass.

- `MAX_REFLECTION_RETRIES = 2`, so **three total passes maximum**.
- The router `_route_reflection` (`workflow.py:47-53`) tests **`final_answer` alone** — it returns `END`
  if and only if that key is set. **Any node that writes `final_answer` silently terminates the graph.**
- The budget check lives at `reflection.py:97`, **not** in the router. `workflow.py:33`'s `MAX_RETRIES`
  is dead code and reading it as the live bound is a common mistake.
- A retry **replaces** the previous pass's documents rather than adding to them — returned keys overwrite
  in `RAGState`, they never accumulate.

The state machine, the escalation heuristic and the grounding critic are documented in
[`../rag-pipeline/README.md`](../rag-pipeline/README.md#42-the-reflection-retry-state-machine).

### 3.4 Three or four LLM calls per pass

Per pass: planner, reasoning, reflection — plus compression **only** when the assembled context exceeds
4 000 characters. All run at `temperature=0`, and **all use the provider pinned once by the route**;
there is no per-node routing and the provider cannot change mid-run
([`../llm-providers/README.md`](../llm-providers/README.md#42-what-is-fixed-for-a-whole-run)).

On a three-pass run that is up to twelve LLM round trips for one question — worth knowing before
pointing this at a paid provider, because nothing counts them and nothing can cancel them (§7).

---

## 📤 4. PHASES 8–10 — DRAIN, TERMINATE, TEAR DOWN

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

**Phase 8 — drain.** The request thread blocks on `event_queue.get(timeout=180)` and yields each item as
one `data: {json}\n\n` frame. The queue is FIFO with exactly one producer, so **emission order is
preserved end to end**. `_EVENT_TIMEOUT_SECONDS = 180` is a hardcoded module constant
(`query_routes.py:28`) and it is **per event** — the clock resets on every frame, so a twenty-minute run
that emits something every thirty seconds never trips it, while one stage stalling for 181 seconds does.

**Phase 9 — terminate.** `_run` puts `done` (or, on an unhandled exception, `error`) **directly on the
queue, bypassing `emit()`** — which is why neither carries a pipeline `stage` and why both are described
as *route-framed* rather than emitted. Its `finally` then always puts the `None` sentinel, and the
generator turns that sentinel into a `stream_end` frame and breaks out of its loop.

**Phase 10 — teardown.** The generator's `finally` calls `close_session(session_id)`, which pushes a
**second sentinel nobody reads** and then pops the queue from `_sessions`. The second put is harmless and
is written down here so it does not look like a bug: `_run` cannot know whether the consumer is still
there, and `close_session` cannot know whether the producer already finished.

> [!CAUTION]
> **The 180-second timeout ends the HTTP response, never the pipeline.** After it fires, `close_session`
> pops the queue, every subsequent `emit()` hits its `if q:` guard and no-ops, and the daemon thread runs
> to completion — making every remaining LLM call and depositing its answer into an orphaned queue that
> is then garbage-collected. **There is no way to cancel a run:** not closing the tab, not the timeout,
> not the client's `abort()`.

---

## ⏳ 5. WHERE THE TIME GOES

| Cost | Magnitude | Where it comes from |
|---|---|---|
| First-ever boot (models download and load) | **~61 s cold, ~10 s warm** — dominated by `sentence_transformers` at 7.09 s | measured; see [`README.md`](README.md#34-the-measured-cost-and-the-three-choices-it-explains) |
| Reranker weights | loaded lazily on the **first query only** | `reranker.py:23-31` |
| Embedder weights | loaded lazily on the **first index or search** | `embeddings.py:16-21` |
| Cross-encoder forward passes | **O(candidates)** — up to 30 query/document pairs at the defaults | `reranker.py:53-61` |
| LLM round trips | 3 per pass, 4 when compression fires | §3.4 |
| Retrieval | three sequential store searches, no parallelism | `hybrid_node.py:41-45` |

Two of those are worth internalising. **The reranker is the pipeline's dominant local compute** — it
scores every surviving candidate, not just the top few, which is exactly what makes its scores
comparable. And **boot cost is paid once per process**, which is why the reloader (two processes, two
loads) is the thing to turn off first on a slow machine.

For reference, `/api/providers` can take up to ~10 s when Ollama is unreachable (two 5-second timeouts in
series) — a different route, but the first thing the UI calls, so it is often mistaken for query latency
([`../api/provider-and-health.md`](../api/provider-and-health.md#-4-performance)).

---

## 💥 6. FAILURE AT EACH PHASE

| Phase | What can fail | What the client sees |
|---|---|---|
| 2 | Blank query, unknown provider | **`400` JSON** `{"error": …}` — the only HTTP error statuses in the flow |
| 2 | **Non-string** `query` or `provider` | `AttributeError` outside any `try` → **HTML `500`**, or the interactive debugger |
| 7 | A node raises and catches it itself | that node's `stage_error` frame plus a fallback; **the run continues degraded** |
| 7 | A store raises inside `retrieval` | that node has **no `try` at all** — it propagates to `_run`'s `except` → in-band `error` on a `200` |
| 7 | Any other node raises uncaught | `error` event with `{"message": …, "stage": "pipeline"}` on a `200`; the sentinel still follows |
| 8 | 181 seconds of silence | in-band `error` `"Stream timeout"`, then `close_session` — **the pipeline keeps running** |
| 8 | Any other generator exception | the bare `except` at `:110` reports it as `"Stream timeout"` too — a latent diagnostic trap |
| 9 | Reflection itself raises | it **fails open**: sets `grounded: True` and `final_answer = answer`, terminating rather than looping |

> [!IMPORTANT]
> **Once the response headers are on the wire the status line cannot be revised, so every
> post-validation failure is an in-band `error` event on a `200`.** That is not a shortcut — it is a
> property of streaming responses. Clients must dispatch on the frame's `type`, and the browser client
> does exactly that (`ragApi.js:76-84`).

The per-event payload shapes, including both `error` variants, are catalogued in
[`../api/query.md`](../api/query.md#-5-the-sse-event-catalogue).

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **A disconnect frees the socket, never the compute.** Closing the tab aborts the `fetch`, Flask stops
  consuming the generator, and its `finally` pops the session — after which every `emit()` no-ops. The
  daemon thread finishes the run and pays for every token.

- **The queue is unbounded, so a slow reader costs memory, not throughput.** Nothing applies backpressure
  to the pipeline and nothing bounds the queue; a client that opens the stream and never reads simply
  accumulates frames until the run ends.

- **`done` and `error` never pass through `emit()`.** They are put on the queue directly by the route's
  worker, which is why they carry no pipeline `stage` and why they still arrive after the session has
  been closed — the closure holds the queue object.

- **The graph is invoked with no `config`.** No `recursion_limit` means LangGraph's own loop protection
  is at its default and plays no part here; the retry budget in `reflection.py` is the real bound.

- **A retry resets the tracker, not just one row.** The `retry` event deliberately carries **no**
  `stage`, because it announces that the whole downstream tracker is about to re-run
  ([`../sse-event-bus/README.md`](../sse-event-bus/README.md#-6-wire-shape-cross-boundary-contracts)).

- **Nothing in the flow is persisted.** No checkpointer, no run log, no request id in any store. Once the
  stream ends the only record of a run is whatever the browser kept in `localStorage`.

- **Concurrent queries are fine; concurrent ingest is not.** Each query gets its own session, queue and
  thread, and the stores are read-only for its duration. Writes have no lock between them — see
  [`storage-model.md`](storage-model.md#-5-store-lifecycle).

---

## 🔗 8. RELATED READING

- **Why the pipeline runs on a thread rather than a task queue.** Keeping the run inside the request
  process removes a broker, a serialisation format and a second deployment target — right for a
  single-machine tool. The price is that the run's lifetime is decoupled from the request's with nobody
  owning it: no cancellation, no persistence, no visibility.
- **Why validation is only two checks.** Everything past the headers is unreportable as an HTTP status,
  so the route front-loads exactly the two failures it can still express cleanly and lets the pipeline
  narrate the rest. The gap that leaves — a non-string `query` — is a real defect rather than a design.
- **Why the answer is a frame and not a return value.** The endpoint's product is the *progress*, not
  just the result; the tracker is the feature. Delivering the answer as one more frame keeps a single
  channel and a single parser on the client.

**Continue reading:**

- [`README.md`](README.md) — the layers, the boot sequence and the one-worker rule this flow depends on
- [`../rag-pipeline/README.md`](../rag-pipeline/README.md) — the eight-node graph in full
- [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md) — per-node reads, returns, emits and failure behaviour
- [`../rag-pipeline/state-model.md`](../rag-pipeline/state-model.md) — the 22 keys and their merge semantics
- [`../sse-event-bus/README.md`](../sse-event-bus/README.md) — sessions, `emit()`, the queue and the sentinel
- [`../api/query.md`](../api/query.md) — the endpoint reference and the full event catalogue
- [`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md) — what phase 7's retrieval and rerank steps actually do
- [`../llm-providers/README.md`](../llm-providers/README.md) — how the provider is chosen and pinned for the run
- [`../security.md`](../security.md) — the debugger exposure behind the non-string-`query` `500`
