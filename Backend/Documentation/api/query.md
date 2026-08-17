<div align="center">

# 💬 Query Endpoint

### One POST, one open `text/event-stream`, ten event types — and every failure after the first byte is a `200`.

<br>

[![Endpoint](https://img.shields.io/badge/POST-%2Fapi%2Fquery-1c7ed6)](#-1-the-endpoint)
[![Response](https://img.shields.io/badge/response-text%2Fevent--stream-7c5cff)](#-4-success-response)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Event types](https://img.shields.io/badge/event%20types-10-f59e0b)](#-5-the-sse-event-catalogue)
[![HTTP errors](https://img.shields.io/badge/HTTP%20error%20statuses-2-f59e0b)](#%EF%B8%8F-6-error-responses)
[![Auth](https://img.shields.io/badge/auth-none-ef4444)](#-9-security-notes)

</div>

<br>

---

<br>

## Content Tree

<pre>
Query Endpoint
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-endpoint">🚀 1. The endpoint</a>
│
├── <a href="#-2-request">📥 2. Request</a>
│   ├── <a href="#21-headers">2.1 Headers</a>
│   ├── <a href="#22-body-fields">2.2 Body fields</a>
│   └── <a href="#23-the-model-field-is-not-ollama-only">2.3 The model field is not Ollama-only</a>
│
├── <a href="#-3-how-to-call">📞 3. How to call</a>
│   ├── <a href="#31-curl">3.1 cURL</a>
│   ├── <a href="#32-javascript-fetch--readablestream">3.2 JavaScript (fetch + ReadableStream)</a>
│   └── <a href="#33-python-requests">3.3 Python (requests)</a>
│
├── <a href="#-4-success-response">✅ 4. Success response</a>
│   ├── <a href="#41-status-media-type-and-headers">4.1 Status, media type and headers</a>
│   └── <a href="#42-the-frame-format-and-what-it-omits">4.2 The frame format, and what it omits</a>
│
├── <a href="#-5-the-sse-event-catalogue">📡 5. The SSE event catalogue</a>
│   ├── <a href="#51-the-stage-id-contract">5.1 The stage-id contract</a>
│   ├── <a href="#52-the-ten-types-at-a-glance">5.2 The ten types at a glance</a>
│   ├── <a href="#53-the-stage_start-event">5.3 The stage_start event</a>
│   ├── <a href="#54-the-stage_complete-event">5.4 The stage_complete event</a>
│   ├── <a href="#55-the-stage_skip-event">5.5 The stage_skip event</a>
│   ├── <a href="#56-the-stage_error-event">5.6 The stage_error event</a>
│   ├── <a href="#57-the-retrieval_result-event">5.7 The retrieval_result event</a>
│   ├── <a href="#58-the-finalize-event">5.8 The finalize event</a>
│   ├── <a href="#59-the-retry-event">5.9 The retry event</a>
│   ├── <a href="#510-the-three-route-framed-events">5.10 The three route-framed events</a>
│   ├── <a href="#511-the-done-payload">5.11 The done payload</a>
│   └── <a href="#512-a-representative-frame-sequence">5.12 A representative frame sequence</a>
│
├── <a href="#%EF%B8%8F-6-error-responses">⚠️ 6. Error responses</a>
│   ├── <a href="#61-the-two-http-error-statuses">6.1 The two HTTP error statuses</a>
│   ├── <a href="#62-errors-that-are-not-json">6.2 Errors that are not JSON</a>
│   └── <a href="#63-in-band-errors-on-a-200">6.3 In-band errors on a 200</a>
│
├── <a href="#-7-the-180-second-timeout">⏳ 7. The 180-second timeout</a>
│
├── <a href="#-8-sessions-and-cancellation">🧵 8. Sessions and cancellation</a>
│
├── <a href="#-9-security-notes">🔒 9. Security notes</a>
│
└── <a href="#-10-related-reading">🔗 10. Related reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

`POST /api/query` is the only route in this API that does not return an answer. It returns an **open
stream**. The route validates a small JSON body, mints a session, starts the eight-node LangGraph
pipeline on a **daemon thread**, and then does nothing but forward whatever that thread pushes onto an
in-memory queue, framed as Server-Sent Events, until a sentinel arrives.

The handler is 91 lines (`routes/query/query_routes.py:33-123`) and its module docstring is the sentence
to read first (`:6-8`):

> *"The pipeline runs on a daemon thread; this route only frames its events as HTTP. Errors are IN-BAND:
> a pipeline failure is a 200 carrying an `error` event, not an HTTP error status, because the stream has
> already begun by the time one can occur."*

> [!IMPORTANT]
> **Exactly two things about this endpoint break clients that assume a normal REST route.** First,
> **the HTTP status tells you almost nothing** — there are two `400`s, both raised before a single byte
> of the stream is written, and after that every outcome including total failure is a `200`. Second,
> **the event `stage` id is not the LangGraph node name** — five of the eight differ, and the emitted
> value is the contract (§5.1).

---

## 🚀 1. THE ENDPOINT

```text
POST /api/query
```

Runs one retrieval-augmented generation pass and streams its progress, then its answer.

| Aspect | Value |
|---|---|
| **Auth** | **None.** No key, no token, no session, no rate limit. Any caller can spend LLM budget. See §9. |
| Base URL (dev) | `http://localhost:5000` |
| Request `Content-Type` | `application/json` |
| Response `Content-Type` | `text/event-stream` |
| Success status | `200` — always, including for a failed pipeline (§6.3) |
| Error statuses | `400` only (two conditions, §6.1) |
| Blueprint / endpoint | `query` / `query.query` |
| Handler | `query()`, `routes/query/query_routes.py:33` |

---

## 📥 2. REQUEST

### 2.1 Headers

| Header | Value | Required |
|---|---|---|
| `Content-Type` | `application/json` | ✅ |
| `Accept` | `text/event-stream` | ❌ — not read; the response media type is fixed |

**A wrong `Content-Type` is a `400`, not a `415`.** The body is parsed with
`request.get_json(silent=True)` (`:40`), which returns `None` rather than raising — so a form-encoded or
plain-text body falls into the missing-`query` branch and is reported as such.

### 2.2 Body fields

| Field | Type | Required | Default | Normalisation |
|---|---|---|---|---|
| `query` | string | ✅ | — | `.strip()` before it reaches the pipeline state (`:55`) |
| `provider` | `"openai"` \| `"ollama"` | ❌ | `Config.DEFAULT_PROVIDER` = `"openai"` | `.lower().strip()` (`:44`) — so `"  OpenAI "` is accepted |
| `model` | string | ❌ | `null` → the provider's configured default | `body.get("model") or None` (`:49`) — an empty string becomes `null` |

```json
{
  "query": "What does the reflection node do when the answer is not grounded?",
  "provider": "openai",
  "model": "gpt-4o"
}
```

**No other field is read.** There is no schema validation, no `pydantic`, no marshmallow — extra keys in
the body are silently ignored.

### 2.3 The `model` field is not Ollama-only

> [!WARNING]
> **The code comment above this field is wrong, and the behaviour is the contract.**
> `query_routes.py:48` reads `# Optional model override (only meaningful for Ollama; ignored for
> OpenAI)`, and the value is stored on the pipeline state under the key **`ollama_model`** (`:58`) —
> the name reinforces the same misreading. **Both are stale.**

The override reaches `get_llm(provider, …, model=…)` from every node that calls an LLM, and the OpenAI
branch uses it exactly as the Ollama branch does:

```python
# custom_packages/rag_pipeline/models/llm.py:62
llm = ChatOpenAI(model=model or os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=temperature)
```

Three independent confirmations that this is intended behaviour rather than an accident:

- **The frontend depends on it.** `Frontend/src/store/ragStore.js:133-135` selects `openaiModel` when the
  provider is `openai` and `ollamaModel` when it is `ollama`, and puts whichever it picked on the request
  body (`ragApi.js:43`). Choosing `gpt-4o` on the Configuration page **works**; if the comment were true,
  that control would be inert.
- **`GET /api/providers` ships a four-item OpenAI model list** for that picker
  (`provider_routes.py:17-22`) — a list that would be pointless against an ignored field.
- The value is threaded through all four LLM call sites identically (`generation/reasoning.py:49` and
  `:86`, `generation/reflection.py:60` and `:82`).

**Write it as: `model` overrides the chat model for *either* provider.** The comment and the
`ollama_model` state-key name are the two things that need correcting, and correcting them is a code
change outside this document's scope. The provider layer itself is documented in
[`../llm-providers/README.md`](../llm-providers/README.md).

---

## 📞 3. HOW TO CALL

### 3.1 cURL

The only way to see the raw frames. **`-N` is required** — without it curl buffers the response and every
frame arrives in one block at the end, which hides the entire point of the endpoint.

```bash
curl -N -X POST http://localhost:5000/api/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is retrieval-augmented generation?","provider":"openai"}'
```

Output is a sequence of `data:` lines separated by blank lines:

```text
data: {"type": "stage_start", "data": {"stage": "planner", "message": "Analyzing query..."}}

data: {"type": "stage_complete", "data": {"stage": "planner", "retrieve": true, ...}}

...

data: {"type": "done", "data": {"answer": "...", "sources": [...], "metadata": {...}}}

data: {"type": "stream_end"}
```

### 3.2 JavaScript (fetch + ReadableStream)

> [!NOTE]
> **`EventSource` cannot be used here.** It is GET-only, and the query is a POST with a body. The
> application's own client says so in its docstring (`ragApi.js:31-32`): *"Uses fetch + ReadableStream so
> we can POST with a body."* The knock-on is that **there is no automatic reconnection** — `EventSource`
> reconnects on its own, a `fetch` stream does not — and since the protocol carries no `id:` field
> (§4.2) there would be nothing to resume from anyway.

This mirrors the real client at `Frontend/src/services/ragApi.js:40-96`:

```js
const res = await fetch('http://localhost:5000/api/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'What is RAG?', provider: 'openai' }),
})

// Only the two pre-stream 400s can land here. Everything after is in-band.
if (!res.ok) {
  const err = await res.json().catch(() => ({ error: res.statusText }))
  throw new Error(`${res.status}: ${err.error}`)
}

const reader = res.body.getReader()
const decoder = new TextDecoder()
let buffer = ''

for (;;) {
  const { done, value } = await reader.read()
  if (done) break

  buffer += decoder.decode(value, { stream: true })
  const lines = buffer.split('\n')
  buffer = lines.pop()               // keep the last, possibly partial, line

  for (const line of lines) {
    if (!line.startsWith('data: ')) continue
    const { type, data } = JSON.parse(line.slice(6))

    if (type === 'done')       console.log('ANSWER:', data.answer)
    else if (type === 'error') console.error('FAILED:', data.message)
    else if (type === 'stream_end') { /* no data key — do not read data.* here */ }
    else console.log(type, data?.stage ?? '(no stage)', data?.message ?? '')
  }
}
```

Three details in that loop are load-bearing rather than stylistic: **the partial line must be carried
across chunk boundaries** (a `data:` frame is routinely split by the network), **`stream_end` carries no
`data` key at all** so `data.anything` throws on it, and **`error` must be handled outside any
stage-based routing** because its payload is not a stage update.

### 3.3 Python (requests)

```python
import json
import requests

with requests.post(
    "http://localhost:5000/api/query",
    json = {"query": "What is retrieval-augmented generation?", "provider": "openai"},
    stream = True,          # required — without it requests buffers the whole body
    timeout = (5, None),    # connect timeout only; the read is open-ended by design
) as res:
    if res.status_code != 200:
        raise RuntimeError(f"{res.status_code}: {res.json()['error']}")

    for line in res.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        frame = json.loads(line[6:])
        if frame["type"] == "done":
            print(frame["data"]["answer"])
        elif frame["type"] == "error":
            raise RuntimeError(frame["data"]["message"])
        else:
            print(frame["type"], frame.get("data", {}).get("stage", ""))
```

`res.raise_for_status()` is deliberately **not** used: it would pass a failed pipeline straight through,
because a failed pipeline is a `200` (§6.3).

---

## ✅ 4. SUCCESS RESPONSE

### 4.1 Status, media type and headers

**`200 OK`**, with `mimetype="text/event-stream"` and three explicit headers (`:115-123`):

| Header | Value | Why it is there |
|---|---|---|
| `Content-Type` | `text/event-stream` | the SSE media type, set via `mimetype=` |
| `Cache-Control` | `no-cache` | stops any intermediary replaying a stream |
| `X-Accel-Buffering` | `no` | **nginx-specific** — without it a reverse proxy buffers the whole response and the live tracker appears frozen until the run completes |
| `Connection` | `keep-alive` | holds the socket open |

### 4.2 The frame format, and what it omits

`format_sse` (`custom_packages/rag_pipeline/events.py:48-50`) is one f-string, and it produces one line
followed by a blank line:

```text
data: {"type": "stage_start", "data": {"stage": "retrieval", "message": "Running hybrid retrieval..."}}

```

That is the entire protocol. **Everything the SSE specification offers beyond `data:` is absent**, and
each omission has a consequence a client must plan around:

| Absent field | Consequence |
|---|---|
| `event:` | Every frame arrives on the **default** channel. `addEventListener('stage_start', …)` cannot work — the type lives *inside* the JSON and must be dispatched in application code. |
| `id:` | No `Last-Event-ID`, therefore **no resumable stream**. |
| `retry:` | No server-controlled reconnect interval. |
| any heartbeat or comment keep-alive | A quiet pipeline sends **nothing** for up to 180 seconds. An intermediary with a shorter idle timeout cuts first, and the client cannot tell that from a crash. |

**Every frame is one line.** `json.dumps` produces no embedded newlines for the payloads built today, so
a `data:` frame is never continued across multiple `data:` lines — but a client that splits on `\n\n`
rather than parsing line-by-line is relying on that rather than on the protocol.

---

## 📡 5. THE SSE EVENT CATALOGUE

**Eleven distinct `type` values reach the browser. Seven originate in the pipeline through `emit()`;
four are framed by this route** and never pass through the event bus at all. That split explains most of
the payload asymmetries below.

### 5.1 The stage-id contract

`emit()` is `emit(session_id, event_type, data)`. **The `stage` id is a string literal *inside the `data`
dict*, not the event type** — which is precisely why it can drift from the graph node name unnoticed.

| `add_node` name (`workflow.py`) | Emitted `stage` id | Same? |
|---|---|---|
| `planner` | `planner` | ✅ |
| `retrieval` | `retrieval` | ✅ |
| `external_tools` | `external_tools` | ✅ |
| `aggregate` | **`aggregator`** | ❌ |
| `rerank` | **`reranker`** | ❌ |
| `compress` | **`compressor`** | ❌ |
| `reason` | **`reasoning`** | ❌ |
| `reflect` | **`reflection`** | ❌ |

> [!WARNING]
> **Five of the eight differ, and the `emit()` call sites are the contract — not `workflow.py`.**
> The emitted set matches `Frontend/src/store/ragStore.js:16-25` exactly, and the client's guard is
> `if (!stage || !(stage in stageStatuses)) return` (`ragStore.js:98-99`) — **an unrecognised stage id is
> silently dropped**, with no error and no console warning. Renaming a graph node breaks nothing.
> Changing an `emit(...)` `stage` literal silently stops that tracker row updating, forever, and the
> failure is invisible on the server.

### 5.2 The ten types at a glance

| Event type | Framed by | Carries `stage`? | Sites | Terminal? |
|---|---|---|---|---|
| `stage_start` | node → `emit()` | ✅ | 8 | no |
| `stage_complete` | node → `emit()` | ✅ | 11 | no |
| `stage_skip` | node → `emit()` | ✅ | 2 | no |
| `stage_error` | node → `emit()` | ✅ | 7 | **no** — see §5.6 |
| `retrieval_result` | node → `emit()` | ✅ | 1 | no |
| `finalize` | node → `emit()` | ✅ | 1 | last pipeline event |
| `retry` | node → `emit()` | ❌ **deliberately** | 1 | no |
| `done` | **route** | ❌ | 1 | yes |
| `error` (pipeline) | **route** | ⚠️ `"stage": "pipeline"` | 1 | yes |
| `error` (stream) | **route** | ❌ | 1 | yes |
| `stream_end` | **route** | ❌ (no `data` key at all) | 1 | yes — the last frame |

> [!NOTE]
> **A client that handles only the four `stage_*` types has an incomplete contract.** The retrieval row
> never receives a `stage_complete` — it is completed by `retrieval_result` alone (§5.7) — and both
> `retry` and `finalize` carry state no other event does.

### 5.3 The `stage_start` event

Eight call sites, one per node. `data` keys are `stage` and `message` on seven of them.

| Emitted by | Site | Extra `data` keys |
|---|---|---|
| `planner` | `generation/planner.py:55` | — |
| `retrieval` | `retrieval/hybrid_node.py:36` | — |
| `external_tools` | `retrieval/web_node.py:31` | — |
| `aggregator` | `ranking/aggregator.py:22` | — |
| `reranker` | `ranking/reranker.py:39` | — |
| `compressor` | `generation/compressor.py:44` | — |
| `reasoning` | `generation/reasoning.py:51` | — |
| `reflection` | `generation/reflection.py:62` | **`attempt`**, **`max_attempts`** |

```json
{"type": "stage_start", "data": {"stage": "retrieval", "message": "Running hybrid retrieval — Vector + BM25 + GraphRAG..."}}
```

**`reflection` is the only one carrying extra keys** — `attempt` is `retry_count + 1` and `max_attempts`
is `MAX_RETRIES + 1` (`3` at the defaults). It is a client's only signal, *at the start of a pass*, of
which pass it is on.

### 5.4 The `stage_complete` event

**Eleven call sites across six nodes, and the payload differs per node** — three nodes emit it from more
than one branch, with different keys each time.

| Emitted by | Site | Fires when | `data` keys beyond `stage` + `message` |
|---|---|---|---|
| `planner` | `planner.py:69` | decision parsed | `retrieve` (bool), `use_external` (bool), `query_type` (str), `reasoning` (str) |
| `external_tools` | `web_node.py:59` | search returned | `web_count` (int) |
| `aggregator` | `aggregator.py:48` | always | `before` (int), `after` (int), `sources` (object: source name → count) |
| `reranker` | `reranker.py:45` | there was nothing to rerank | *(none)* |
| `reranker` | `reranker.py:63` | cross-encoder scored | `top_k` (int), `scores` (float array, 4 dp), `sources` (string array) |
| `compressor` | `compressor.py:50` | no context at all | *(none)* |
| `compressor` | `compressor.py:66` | context already under the char limit | `original_chars`, `compressed_chars` — **equal** |
| `compressor` | `compressor.py:84` | LLM compression ran | `original_chars`, `compressed_chars`, `ratio` (2 dp) |
| `reasoning` | `reasoning.py:78` | no-context direct answer | `confidence` — the **literal `0.5`**, not a model output |
| `reasoning` | `reasoning.py:98` | JSON answer parsed | `confidence` (2 dp), `is_sufficient` (bool), `key_facts` (array) |
| `reflection` | `reflection.py:106` | verdict reached | `grounded` (bool), `confidence` (2 dp), `issues` (array), `will_retry` (bool), `escalate_external` (bool) |

```json
{"type": "stage_complete", "data": {"stage": "aggregator", "before": 20, "after": 17, "sources": {"vector": 10, "bm25": 4, "graph": 3}, "message": "17 unique docs (from 20 total, ...)"}}
```

Two reading notes that save a debugging session:

- **`compressor` emits `original_chars == compressed_chars` when it skips.** That equality is how a
  client distinguishes a skip from a real compression on the same event type. Compression is skipped
  whenever the assembled context is at or under `MAX_CONTEXT_CHARS` (4 000) — the common case at the
  defaults.
- **There is no `details` key on any payload.** `details` is the *frontend store's own* field
  (`ragStore.js:110` assigns `stageStatuses[stage].details = data`). It has never been on the wire.

### 5.5 The `stage_skip` event

Two call sites — and only the two conditional-branch nodes can be skipped. The other six always run.

| Emitted by | Site | Fires when | `data` keys |
|---|---|---|---|
| `retrieval` | `hybrid_node.py:30` | the planner set `retrieve=False` | `stage`, `message` |
| `external_tools` | `web_node.py:25` | `use_external=False` | `stage`, `message` |

```json
{"type": "stage_skip", "data": {"stage": "retrieval", "message": "Retrieval skipped — direct answer mode"}}
```

### 5.6 The `stage_error` event

> [!IMPORTANT]
> **A `stage_error` never ends the stream.** Every one of the seven sites is immediately followed by a
> fallback, and the pipeline continues to `done`. Treating this event as terminal is the most common way
> to mis-implement a client against this API. Only a `_run`-level exception produces the route-framed
> `error` event (§5.10).

**Note also that the payload key is `error`, not `message`** — this is the one progress event that breaks
that convention, and the frontend reads `data.error` for it specifically (`ragStore.js:118`).

| Emitted by | Site | Fires when | Fallback the node takes |
|---|---|---|---|
| `planner` | `planner.py:89` | any exception | defaults to `retrieve=True, use_external=False, query_type="factual"` |
| `external_tools` | `web_node.py:67` | `ImportError` — the search package is absent | `web_docs = []` |
| `external_tools` | `web_node.py:74` | any other exception | `web_docs = []` |
| `reranker` | `reranker.py:73` | model load or predict failed | sorts by the raw `score` and takes `RERANK_TOP_K` |
| `compressor` | `compressor.py:94` | compression failed | truncates to `MAX_CONTEXT_CHARS` |
| `reasoning` | `reasoning.py:108` | the JSON path failed | retries with a plain prompt, then `"Unable to generate an answer."` |
| `reflection` | `reflection.py:173` | any exception | **fails open** — `grounded=True`, and the current answer becomes final |

```json
{"type": "stage_error", "data": {"stage": "external_tools", "error": "duckduckgo-search not installed"}}
```

`aggregator` is the one node with **no error path at all** — it carries no `try`, so a failure there
becomes a route-framed `error` (§5.10) rather than a `stage_error`.

### 5.7 The `retrieval_result` event

One call site, `hybrid_node.py:45`. It is a `stage_complete` in all but name.

| `data` key | Type |
|---|---|
| `stage` | `"retrieval"` |
| `vector_count` | int |
| `bm25_count` | int |
| `graph_count` | int |
| `message` | string |

```json
{"type": "retrieval_result", "data": {"stage": "retrieval", "vector_count": 10, "bm25_count": 7, "graph_count": 3, "message": "Vector: 10 | BM25: 7 | Graph: 3"}}
```

**The retrieval node never emits `stage_complete`.** The frontend falls through for it —
`case 'stage_complete': case 'retrieval_result':` (`ragStore.js:106-107`) — so the retrieval row is
completed by this event alone.

**There is no `web_count` on this event.** `web_count` lives on the `external_tools` node's
`stage_complete` (`web_node.py:61`).

### 5.8 The `finalize` event

One call site, `reflection.py:150`. `data` keys are `stage` (`"reflection"`), `grounded` (bool) and
`message`.

```json
{"type": "finalize", "data": {"stage": "reflection", "grounded": true, "message": "Answer verified and finalized"}}
```

It is emitted **only** on the pass that sets the final answer, immediately before the reflection node
returns it — so its arrival is the reliable signal that no further retry is coming. It is the last
*pipeline* event of a run; `done` follows from the route.

### 5.9 The `retry` event

One call site, `reflection.py:129-135`. **It is the only pipeline event with no `stage` key, and that
omission is deliberate.**

| `data` key | Type | Value |
|---|---|---|
| `attempt` | int | `retry_count + 2` — the pass about to begin, 1-based |
| `max_attempts` | int | `MAX_RETRIES + 1` = `3` at the defaults |
| `reason` | string | why the answer was rejected |
| `escalate_external` | bool | true when the knowledge base produced nothing usable and web search was not already on |
| `message` | string | human-readable summary |

```json
{"type": "retry", "data": {"attempt": 2, "max_attempts": 3, "reason": "...", "escalate_external": false, "message": "Retrying with adjusted strategy (attempt 2/3)"}}
```

It fires when the reflection verdict is *not grounded*, the model asked for a retry, and the budget is
not exhausted — `(not grounded) and raw_retry and (retry_count < MAX_RETRIES)` (`reflection.py:97`).

> [!IMPORTANT]
> **`retry` is a pipeline-level event, not a per-stage update — so it must be dispatched *before* any
> stage-based routing.** It does not describe a stage; it announces that the whole tracker is about to
> reset and re-run. A client that reads `data.stage` first and returns when it is absent will drop this
> event and silently show a stale single-pass run. The reference client handles it at
> `ragStore.js:87-96`, ahead of its `const stage = data?.stage` guard at `:98`, with a comment naming
> exactly that reason.

### 5.10 The three route-framed events

These bypass `emit()` entirely. `_run` and `_generate` close over the queue object and call
`event_queue.put(...)` / `format_sse(...)` directly — which is why they carry no pipeline `stage`.

| Type | Framed at | `data` keys | Fires when |
|---|---|---|---|
| `done` | `query_routes.py:84-91` | `answer`, `sources`, `metadata` | `rag_graph.invoke()` returned normally |
| `error` (pipeline) | `query_routes.py:93-96` | `message`, **`stage: "pipeline"`** | `_run` caught any exception |
| `error` (stream) | `query_routes.py:110-111` | `message` — always `"Stream timeout"` | the generator's bare `except` fired |
| `stream_end` | `query_routes.py:106-108` | **none — the frame is `{"type": "stream_end"}`** | the `None` sentinel was dequeued |

> [!WARNING]
> **`error` is two different shapes under one name.** The worker's version carries
> `{message, stage: "pipeline"}`; the generator's carries `{message}` only. `"pipeline"` is **not** one of
> the eight stage ids, so it would be dropped by a stage guard — but a correct client never routes
> `error` through one. The reference client treats both identically (`ragApi.js:80-81`).
>
> **`stream_end` has no `data` key at all**, so `payload.data.anything` throws on it. The reference
> client matches it and deliberately does nothing (`ragApi.js:78-79`) — the stream ending is already
> observable from the reader's own `done`.

### 5.11 The `done` payload

```python
# routes/query/query_routes.py:84
event_queue.put({
    "type": "done",
    "data": {
        "answer":   result.get("final_answer") or result.get("answer", ""),
        "sources":  result.get("final_sources") or result.get("sources", []),
        "metadata": result.get("pipeline_metadata", {}),
    },
})
```

The `or` fallbacks are defensive: the reflection router only routes to `END` when a final answer is set,
so in practice the first branch always wins.

**`sources[]` — the exact eight keys**, built in `generation/reasoning.py:56-69`:

| Key | Type | Value |
|---|---|---|
| `index` | int | 1-based position |
| `file_name` | string | the chunk's `file_name`, else its `title`, else `"Unknown"` |
| `source_type` | string | `"vector"` \| `"bm25"` \| `"graph"` \| `"web"` |
| `url` | string | the source URL, or `""` — web results only |
| `page` | int \| string | the page number, or `""` — PDFs only |
| `rerank_score` | float | the cross-encoder score, else the raw store score, 4 dp — **can be negative** |
| `content_preview` | string | the first 250 characters |
| `content` | string | the full chunk |

> [!CAUTION]
> **The key is `source_type`, and the score key is `rerank_score`. There is no `source` key and no
> `score` key on a wire source.** The retired `api.md` claimed both, and it also omitted `url` and
> `content` entirely. A client written against that document reads `undefined` on every card.

**`sources` is filtered to what the model actually cited** — `reasoning.py:95-96` keeps only entries
whose `index` appears in the model's `cited_sources` array. Three consequences follow:

1. **An empty `sources` array on a non-empty answer is normal**, not a bug. It means the model answered
   from training knowledge without citing retrieved evidence.
2. On the no-context direct-answer path, `sources` is explicitly `[]` (`reasoning.py:83`).
3. On the reasoning **error** fallback path the filter is bypassed and **all** candidate sources are
   returned (`reasoning.py:113`, `:115`) — so a degraded run can be the one that returns *more* sources.

**`metadata` — the exact six keys**, built in `generation/reflection.py:162-169`:

| Key | Type | Value |
|---|---|---|
| `query_type` | string | the planner's classification; `"factual"` by default |
| `sources_used` | string array | the source of **every** context document — not only the cited ones |
| `retry_count` | int | passes *beyond* the first; `0` on a clean run |
| `grounded` | bool | the reflection verdict |
| `confidence` | float | 2 dp |
| `issues` | array | the reflection model's list of problems with the answer |

**On the reflection error path the shape collapses to `{"error": "<string>"}`** (`reflection.py:180`) —
one key, none of the six. **Treat `metadata` as best-effort** and read every key defensively.

A complete `done` frame:

```json
{
  "type": "done",
  "data": {
    "answer": "Retrieval-augmented generation combines a retriever with a generator [1][3]...",
    "sources": [
      {
        "index": 1,
        "file_name": "rag-survey.pdf",
        "source_type": "vector",
        "url": "",
        "page": 4,
        "rerank_score": 6.2841,
        "content_preview": "Retrieval-augmented generation (RAG) augments a language model with...",
        "content": "Retrieval-augmented generation (RAG) augments a language model with a non-parametric memory..."
      }
    ],
    "metadata": {
      "query_type": "factual",
      "sources_used": ["vector", "vector", "bm25", "graph"],
      "retry_count": 0,
      "grounded": true,
      "confidence": 0.91,
      "issues": []
    }
  }
}
```

### 5.12 A representative frame sequence

Ordering is guaranteed: one producer thread, one FIFO queue. A clean single-pass run with retrieval on
and web search off produces exactly this:

```text
stage_start(planner)          → stage_complete(planner)
stage_start(retrieval)        → retrieval_result(retrieval)
stage_skip(external_tools)
stage_start(aggregator)       → stage_complete(aggregator)
stage_start(reranker)         → stage_complete(reranker)
stage_start(compressor)       → stage_complete(compressor)
stage_start(reasoning)        → stage_complete(reasoning)
stage_start(reflection)       → stage_complete(reflection) → finalize(reflection)
done
stream_end
```

A retrying run inserts `retry` after `stage_complete(reflection)` and replays the block from
`stage_start(retrieval)` — up to `MAX_REFLECTION_RETRIES` (default `2`) additional times, so **three
passes maximum**.

Two ordering properties worth relying on: the queue is **unbounded** (`events.py:21`), so the pipeline
never blocks on a slow reader — a client that reads nothing simply accumulates frames in server memory;
and the producer thread starts *before* Flask begins consuming the generator, so early events are
buffered rather than lost.

---

## ⚠️ 6. ERROR RESPONSES

### 6.1 The two HTTP error statuses

Both are raised before a single byte of the stream is written, and both use the API's standard envelope
(`{"error": "<message>"}`). **There are no others.**

| Condition | Status | Body | Site |
|---|---|---|---|
| body absent, not JSON, or `query` missing/blank | `400` | `{"error": "Missing or empty 'query' field"}` | `:41-42` |
| `provider` outside `("openai", "ollama")` | `400` | `{"error": "provider must be 'openai' or 'ollama'"}` | `:45-46` |

**`400 Bad Request`** — missing query:

```json
{ "error": "Missing or empty 'query' field" }
```

**`400 Bad Request`** — unknown provider:

```json
{ "error": "provider must be 'openai' or 'ollama'" }
```

### 6.2 Errors that are not JSON

> [!WARNING]
> **There is no `@app.errorhandler` in this codebase**, so framework-generated failures return Werkzeug's
> default **HTML** page. `response.json()` will throw on all of them.

| Situation | Status | Body |
|---|---|---|
| `GET /api/query` (wrong method) | `405` | HTML |
| a path that does not exist | `404` | HTML |
| an exception outside the route's guarded region | `500` | HTML — or the **interactive Werkzeug debugger**, since `FLASK_DEBUG` defaults to `true` |

**One of those is reachable from an ordinary client mistake.** `body.get("query", "").strip()` (`:41`)
and `body.get("provider", …).lower()` (`:44`) both assume strings, and both sit **outside any `try`**.
So:

```json
{ "query": 42 }
```

raises `AttributeError: 'int' object has no attribute 'strip'`, falls through to Flask's unhandled path,
and produces an **HTML `500`** — where a `400` would be correct. `{"provider": null}` does the same.
This is a real defect in the validation surface, noted here rather than fixed; the correction belongs in
`query_routes.py`.

### 6.3 In-band errors on a `200`

**A pipeline failure is a `200 OK` carrying an `error` event. It is never an HTTP error status.**

The reason is structural, not a design preference: once `Response(...)` has been returned, the status
line is already on the wire and cannot be revised. A node that fails at second thirty physically cannot
become a `500`.

```text
data: {"type": "error", "data": {"message": "Connection error.", "stage": "pipeline"}}

data: {"type": "stream_end"}
```

**A client must therefore inspect the stream, not the status code, to know whether a query succeeded.**
The reference client does exactly that: `res.ok` gates only the two `400`s (`ragApi.js:52-56`), and
everything after is event dispatch. Any client that treats HTTP status as the success signal will report
every failed run as a success.

Note the distinction from §5.6: a **`stage_error`** is a node that failed and recovered — the run
continues. An **`error`** is the run itself ending.

---

## ⏳ 7. THE 180-SECOND TIMEOUT

```python
# routes/query/query_routes.py:26
# A disconnected browser frees the socket, never the compute — the daemon thread
# runs to completion regardless. This is the only bound on a wedged pipeline.
_EVENT_TIMEOUT_SECONDS = 180
```

It is a **hardcoded module constant, not environment-driven** — it appears nowhere in `config.py` or
`.env.example`. Three properties, each of which is commonly assumed wrong:

- **It is per event, not per run.** The clock resets on every frame. A twenty-minute run that emits
  something every thirty seconds never trips it; a single stage that stalls for 181 seconds does.
- **It ends the HTTP response, not the pipeline.** After it fires, the session is closed, every later
  `emit()` hits its no-op guard, and **the graph runs to completion — burning LLM calls nobody will
  read.**
- **The frame it emits is still on a `200`:** `{"type": "error", "data": {"message": "Stream timeout"}}`.

One caveat on that message. The `except` at `:110` is a bare `except Exception` and reports *every*
generator failure as `"Stream timeout"`. `queue.Empty` is the expected case, but a non-serialisable
payload inside `format_sse` would surface with the same misleading text. Every payload built today is
JSON-primitive, so this is a latent diagnostic trap rather than a live bug.

Changing the value means editing `query_routes.py:28`. Making it configurable would mean adding a
`Config` attribute **and** an `.env.example` line, per the convention in
[`../configuration.md`](../configuration.md).

---

## 🧵 8. SESSIONS AND CANCELLATION

What happens between validation and the first byte, in source order:

| Phase | Lines | What |
|---|---|---|
| 1 · validate | `:40-49` | the two `400`s; `model` normalised to a string or `null` |
| 2 · open session | `:51-52` | `session_id = str(uuid.uuid4())`; `create_session` returns the queue and the route keeps a **direct reference** to it |
| 3 · seed state | `:54-79` | all 21 pipeline-state keys written explicitly — see [`../rag-pipeline/state-model.md`](../rag-pipeline/state-model.md) |
| 4 · start producer | `:81-100` | `threading.Thread(target=_run, daemon=True).start()`; `_run` calls `rag_graph.invoke(initial_state)` |
| 5 · drain | `:102-113` | the generator loop, `event_queue.get(timeout=180)` |
| 6 · respond | `:115-123` | `Response(_generate(), mimetype="text/event-stream", headers=…)` |

> [!CAUTION]
> **The `session_id` never reaches the client, and there is no way to cancel a running pipeline.**
> It appears in no event payload and no response header. Closing the tab, calling `abort()`, or hitting
> the 180-second timeout all do the same thing: they **free the socket, never the compute.** The daemon
> thread completes every remaining node, makes every remaining LLM call, and deposits its answer into a
> queue that no longer has a reader. On a paid provider that is real money spent on an answer nobody will
> ever see, and no counter anywhere records it.

Adding cancellation would require a second route and a cooperative check inside the graph; neither
exists. The session mechanics are in [`../sse-event-bus/README.md`](../sse-event-bus/README.md).

---

## 🔒 9. SECURITY NOTES

- **No authentication.** Any caller who can reach the port can run queries and spend LLM budget. There is
  no key, no token, no quota and no rate limit. See [`README.md`](README.md) §4.
- **Query text is interpolated into prompts unescaped, by design.** The user's question, every retrieved
  chunk, and every web-search result flow straight into the planner, compressor, reasoning and reflection
  prompts. **Prompt injection is an accepted, documented risk** — including against the reflection agent
  that judges whether the answer is grounded, which is the one component nominally acting as a check.
- **The answer is rendered through `marked.parse()`** in the frontend (`ResultDisplay.vue`, marked v12,
  **no sanitiser by default**), so a crafted document can carry markup from the corpus into the DOM.
  Stored XSS is likewise an accepted, documented risk.
- **A `500` renders the interactive Werkzeug debugger** under the default `FLASK_DEBUG=true` (§6.2).

Neither risk is widened here and neither should be. The full trust-boundary treatment and the mitigation
(bind to localhost) is in [`../security.md`](../security.md#-7-prompt-injection-and-document-to-dom-xss).

---

## 🔗 10. RELATED READING

- [`README.md`](README.md) — the route index, blueprint registration, CORS, and the API-wide error contract
- [`../rag-pipeline/README.md`](../rag-pipeline/README.md) — what the eight nodes actually do, and the retry loop
- [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md) — per-node behaviour, including every `emit()` call site
- [`../rag-pipeline/state-model.md`](../rag-pipeline/state-model.md) — the 22 state keys this route seeds
- [`../sse-event-bus/README.md`](../sse-event-bus/README.md) — sessions, `emit()`, the queue, and the sentinel
- [`../architecture/query-lifecycle.md`](../architecture/query-lifecycle.md) — this request as one narrative, across every layer
- [`../llm-providers/README.md`](../llm-providers/README.md) — where `provider` and `model` end up
- [`provider-and-health.md`](provider-and-health.md) — how a client discovers which providers are usable
- [`../security.md`](../security.md) — trust boundaries and accepted risks
- [`../../../Frontend/Documentation/chat/pipeline-tracker.md`](../../../Frontend/Documentation/chat/pipeline-tracker.md) — the reference client's stage-id contract and the eight rows these events drive
- [`../../../Frontend/Documentation/api-clients/README.md`](../../../Frontend/Documentation/api-clients/README.md) — `ragApi.js` in full: the `res.ok` gate, the reader loop, and the three intercepted types
