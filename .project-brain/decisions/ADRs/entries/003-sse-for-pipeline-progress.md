# ADR-003: Server-Sent Events for pipeline progress
Date: 2026-08-13 · Status: accepted

> Reconstructed from the code on 2026-08-13, not recorded at decision time. Grounded in
> `Backend/src/app.py` (`/api/query`), `rag_pipeline/core/events.py`, and
> `Frontend/src/services/api.js` (`streamQuery`).

## Context

A full pipeline run makes up to four LLM calls, three retrievals, and a cross-encoder pass — and may repeat
most of that twice more on reflection retries. A single request/response would leave the user staring at a
spinner for tens of seconds with no signal, and would hide the very thing the product is built to show:
*how* the answer was reached.

So progress has to be pushed from server to client while the request is still in flight. The traffic is
strictly **one-way** (server → client), typed, and short-lived — it ends when the query ends.

## Decision

Stream the run as Server-Sent Events from `POST /api/query`. The route mints a UUID `session_id`, creates a
`queue.Queue` for it, runs `rag_graph.invoke()` in a **daemon thread**, and returns a generator that drains
the queue into `data: {json}\n\n` frames on a `text/event-stream` response. Pipeline nodes push events with
`emit(session_id, type, data)`; a `None` sentinel closes the stream.

Because the request needs a JSON **body**, the browser cannot use `EventSource` — `streamQuery()` uses
`fetch` + `res.body.getReader()` and buffers partial lines itself.

## Alternatives considered

- **WebSockets** — TODO: not documented as considered. The traffic is one-way and per-request, so a
  full-duplex persistent connection would add a protocol and a connection lifecycle for no gain; that is
  the reasoning the design implies, not a recorded rejection.
- **Polling a status endpoint** — TODO: not documented. It would need server-side run state keyed by id,
  which is what the in-memory queue already provides more directly.
- **`EventSource`** — genuinely rejected, and visibly so: it cannot send a POST body, which is why the
  client hand-rolls the stream reader.

## Consequences

**Makes easy**

- Live, ordered, typed progress with no extra protocol — plain HTTP, no handshake, and it works through the
  Vue dev-server proxy unchanged.
- Node code stays ignorant of HTTP: it calls `emit()` and nothing else.
- Ordering is free — one pipeline thread and one FIFO queue per session guarantee events arrive in node
  order.

**Makes hard / watch out for**

- **Single worker only.** `_sessions` is process memory, so a forking server would put the producer and
  consumer in different processes. Hence `-w 1` in the documented gunicorn command, and `threaded=True` in
  `main.py`.
- **A disconnect does not cancel the work.** The daemon thread runs to completion; `emit()` simply no-ops
  once the session is gone. Aborting in the browser frees the socket, not the compute.
- **Buffering proxies break it** — hence the `X-Accel-Buffering: no` and `Cache-Control: no-cache` headers.
- **The 180-second `queue.get` timeout is per-event, not per-run.** A stage that stalls longer than three
  minutes kills the stream even though the pipeline continues.
- **The queue is unbounded** and there is no back-pressure.
- **The client must handle partial frames.** The reader keeps the last incomplete line in a buffer — remove
  that and JSON parsing breaks at arbitrary chunk boundaries.
- **Errors are in-band.** A pipeline failure is a `200` response containing an `error` event, not an HTTP
  error status.
