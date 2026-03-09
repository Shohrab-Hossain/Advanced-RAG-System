# core/ — Shared Infrastructure

Low-level plumbing used by every node in the pipeline.

## Files

### `events.py` — SSE Event Bus

Each pipeline run gets a unique `session_id`. Nodes call `emit()` to push
typed events into the session's queue; the Flask SSE route drains the queue
and sends each event to the browser as `text/event-stream`.

```
Node                    Queue (per session)         Flask SSE route
 │                           │                            │
 ├─ emit(sid,"stage_start",…)─►  {"type":…,"data":…}  ──► browser
 ├─ emit(sid,"stage_complete",…)► {"type":…,"data":…}  ──► browser
 └─ emit(sid,"done",…)  ──────►  None (sentinel)       ──► stream close
```

**Public API:**

| Function | Description |
|----------|-------------|
| `create_session(session_id?)` | Create a new `queue.Queue` for a run |
| `emit(session_id, event_type, data)` | Push a typed event dict |
| `close_session(session_id)` | Push `None` sentinel and clean up |
| `format_sse(payload)` | Serialise dict as `data: {...}\n\n` |
| `get_queue(session_id)` | Return the queue (used by Flask route) |

**Thread safety:** Each session has its own `queue.Queue`. The pipeline runs
in a daemon thread; the Flask generator runs in the request thread. No locks
are needed — `queue.Queue` is thread-safe by design.
