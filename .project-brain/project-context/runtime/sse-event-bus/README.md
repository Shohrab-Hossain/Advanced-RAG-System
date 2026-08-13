# Runtime: the SSE event bus

How pipeline progress reaches the browser. Implemented in `Backend/src/rag_pipeline/core/events.py` and
the `/api/query` route in `Backend/src/app.py`; consumed by `streamQuery()` in
`Frontend/src/subsystems/rag/ragApi.js:40` — the RAG subsystem's own axios/`fetch` client, which is the
only frontend module that reads this stream.

<br>

## The mechanism

A module-global dict maps a session to a queue:

```python
_sessions: dict[str, queue.Queue] = {}
```

Five functions make up the whole API: `create_session(id)` → `(id, queue)`, `get_queue(id)`,
`emit(session_id, event_type, data)`, `close_session(id)`, and `format_sse(payload)` →
`f"data: {json.dumps(payload)}\n\n"`.

`emit()` is a **silent no-op** when `session_id` is falsy or the session has already been removed. That is
deliberate: a node that outlives its client must not crash.

<br>

## Producer / consumer split

Two threads share one queue per query:

| | Producer | Consumer |
|---|---|---|
| Who | the daemon thread running `rag_graph.invoke(initial_state)` | the Flask response generator `_generate()` |
| Does | pipeline nodes call `emit(...)` → `q.put({"type", "data"})` | `q.get(timeout=180)` in a loop, yields `format_sse(item)` |
| Ends by | pushing a `done` event, then `None` in a `finally` | seeing `None` → yields `{"type": "stream_end"}` → breaks |

The `None` **sentinel** is the close protocol. `close_session()` also pushes `None` before removing the
queue, so either side can terminate the stream.

Ordering is FIFO per session, and since the pipeline runs in a single thread, events arrive in exact node
order. Nothing correlates events across sessions — the `session_id` never leaves the server; the client
simply reads its own response body.

<br>

## Response framing

```python
Response(_generate(), mimetype="text/event-stream", headers={
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",     # stops nginx buffering the stream
    "Connection": "keep-alive",
})
```

Each frame is a single `data: ` line followed by a blank line. No `event:` field and no `id:` field are
used — the event type lives inside the JSON payload as `type`.

<br>

## Client side

`streamQuery()` cannot use `EventSource` because the request is a **POST with a JSON body**. Instead it
uses `fetch` with an `AbortController` signal, then:

1. `res.body.getReader()` + `TextDecoder`.
2. Accumulates into a `buffer`, splits on `\n`, and **keeps the last (possibly partial) line in the
   buffer** — the essential detail that makes chunk boundaries safe.
3. For each line starting with `data: `, parses the JSON and dispatches:
   `done` → `onDone(data)`, `stream_end` → ignored, `error` → `onError(message)`, anything else →
   `onEvent(type, data)`.
4. Malformed lines are swallowed silently.
5. An `AbortError` is not reported as an error — that is the user cancelling.

`streamQuery` returns `{ abort }`, which the store keeps in `_abortFn` for `abortQuery()`.

<br>

## Failure and timeout behaviour

- **Pipeline exception** → the thread's `except` pushes `{"type": "error", "data": {message, stage:
  "pipeline"}}`, then `None`.
- **180-second queue starvation** → `_generate()`'s `except` yields
  `{"type": "error", "data": {"message": "Stream timeout"}}` and exits. This is a *hard* per-event timeout,
  not a total run budget: it fires only if no event arrives for three minutes.
- **`finally: close_session(session_id)`** always runs, so a session is never leaked from the normal path.

<br>

## Gotchas

- **Single worker only.** `_sessions` is per-process. Forking gunicorn workers would put the pipeline
  thread and the SSE generator in different processes with different dicts. Hence the `-w 1` guidance in
  `Backend/src/main.py`.
- **Client disconnect does not stop the pipeline.** The daemon thread keeps running to completion; its
  `emit` calls simply no-op once the session is gone. Aborting in the browser frees the socket, not the
  compute.
- **The queue is unbounded.** A pathological run could grow it without limit; nothing back-pressures the
  producer.
- **`get_queue()` is defined but unused** by the current code paths.
