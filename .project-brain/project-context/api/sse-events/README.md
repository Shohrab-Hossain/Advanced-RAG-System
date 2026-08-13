# SSE event contract

Every frame streamed by `POST /api/query` is `data: {"type": "<type>", "data": {…}}\n\n`. There is no
`event:` or `id:` field — the type lives in the payload. Producers are the pipeline nodes via
`emit(session_id, type, data)`; the consumer is `streamQuery()` in `Frontend/src/services/api.js`, which
routes `done`, `stream_end`, and `error` specially and passes everything else to `_applyEvent`.

Every stage event carries **`data.stage`**, one of: `planner`, `retrieval`, `external_tools`,
`aggregator`, `reranker`, `compressor`, `reasoning`, `reflection`.

<br>

## Event types

| `type` | Emitted by | Meaning |
|---|---|---|
| `stage_start` | every node | the stage began |
| `stage_complete` | every node except retrieval | the stage finished successfully |
| `retrieval_result` | `retrieval` | retrieval finished (its completion event, with per-store counts) |
| `stage_skip` | `retrieval`, `external_tools` | the stage was bypassed for this run |
| `stage_error` | every node | the stage failed and fell back |
| `retry` | `reflection` | the pipeline is looping back to retrieval |
| `finalize` | `reflection` | the final answer is being produced |
| `done` | the `/api/query` background thread | terminal result payload |
| `error` | the thread or the SSE generator | pipeline exception or stream timeout |
| `stream_end` | the SSE generator | the stream is closing |

<br>

## Payloads

Every stage event includes `stage` and, except for `stage_error`, a human-readable `message`.

**`stage_start`** — `{stage, message}`. `reflection` additionally sends `attempt` and `max_attempts`
(`MAX_REFLECTION_RETRIES + 1`).

**`stage_complete`**, by stage:

| Stage | Extra fields |
|---|---|
| `planner` | `retrieve` (bool), `use_external` (bool), `query_type` (string), `reasoning` (string) |
| `external_tools` | `web_count` (int) |
| `aggregator` | `before` (int), `after` (int), `sources` (object: `{vector: n, bm25: n, graph: n, web: n}`) |
| `reranker` | `top_k` (int), `scores` (array of floats, 4 dp), `sources` (array of source tags) |
| `compressor` | `original_chars`, `compressed_chars`, and `ratio` (float, 2 dp) when compression actually ran |
| `reasoning` | `confidence` (float, 2 dp), `is_sufficient` (bool), `key_facts` (array of strings) |
| `reflection` | `grounded` (bool), `confidence` (float, 2 dp), `issues` (array of strings), `will_retry` (bool), `escalate_external` (bool) |

**`retrieval_result`** — `{stage: "retrieval", vector_count, bm25_count, graph_count, message}`.

**`stage_skip`** — `{stage, message}`. Sent by `retrieval` when `retrieve=false`
("Retrieval skipped — direct answer mode") and by `external_tools` when `use_external=false`
("Web search not needed").

**`stage_error`** — `{stage, error}`. Note: `error`, **not** `message`; `StageRow.vue` reads `data.error`.

**`retry`** — `{attempt, max_attempts, reason, escalate_external, message}`. `reason` is the reflection
model's `feedback`. Note this event has **no `stage` field**, so the frontend's stage switch ignores it —
`_applyEvent` handles `retry` before the stage lookup matters, resetting the seven post-planner stages to
`idle` and setting `retryCount = attempt - 1`.

**`finalize`** — `{stage: "reflection", grounded, message}`.

**`done`** — the terminal payload:

```json
{ "type": "done",
  "data": { "answer": "…markdown with [1] citations…",
            "sources": [ { "index": 1, "file_name": "report.pdf", "source_type": "vector",
                           "url": "", "page": 3, "rerank_score": 6.4213,
                           "content_preview": "first 250 chars…", "content": "full chunk text" } ],
            "metadata": { "query_type": "factual", "sources_used": ["vector", "bm25"],
                          "retry_count": 0, "grounded": true, "confidence": 0.92, "issues": [] } } }
```

**`error`** — `{message, stage?}`. `stage: "pipeline"` for an exception inside the graph; the stream
timeout variant carries only `{"message": "Stream timeout"}`.

**`stream_end`** — no `data` field at all; the frame is literally
`data: {"type": "stream_end"}\n\n`. The client ignores it.

<br>

## Ordering guarantees

Events arrive strictly in node execution order (one pipeline thread, one FIFO queue per session). A retry
therefore produces a second full run of `retrieval → … → reflection` events for the same stage ids, which
is why the client resets those stages rather than trying to distinguish attempts.

`done` is always followed by `stream_end`. An `error` from the thread is also followed by `stream_end`
(the `None` sentinel is pushed in the thread's `finally`); an `error` from the generator's timeout path is
not.
