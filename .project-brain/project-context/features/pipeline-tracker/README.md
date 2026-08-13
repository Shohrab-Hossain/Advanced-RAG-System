# Feature: Pipeline tracker

**Purpose:** make the RAG pipeline legible while it runs — every stage's state, message, and key numbers,
live, instead of a spinner.

**Entry point:** rendered by `ChatView.vue:92` (whenever the run is active, has a result, or errored);
driven entirely by SSE events reduced into `ragStore.stageStatuses`.

**Implemented in:**

| Concern | File |
|---|---|
| Stage definitions | `Frontend/src/subsystems/rag/ragStore.js:16` → exported `STAGES` |
| Event reducer | `Frontend/src/subsystems/rag/ragStore.js:84` → `_applyEvent(type, data)` |
| Container + progress | `Frontend/src/pages/chat/components/PipelineTracker/PipelineTracker.vue` |
| Per-stage row | `Frontend/src/pages/chat/components/PipelineTracker/StageRow.vue` |
| Event source | `Frontend/src/subsystems/rag/ragApi.js:40` → `streamQuery()` |

`StageRow.vue` is a **satellite of the container**, not a shared component: it sits inside the
`PipelineTracker/` folder and is imported only by `PipelineTracker.vue:60`. The container pulls both the
store and the `STAGES` constant from one import (`:59`), so the display order and the reducer's key set can
never drift apart.

**Inputs:** SSE events carrying `data.stage`.
**Outputs:** a reactive map `stageStatuses[stageId] = {status, message, details}` and a progress
percentage.

**The eight stages** (order is display order, ids match the backend's `stage` values exactly):

| id | Label | Icon | Description shown |
|---|---|---|---|
| `planner` | Self-RAG Planner | 🧠 | Decides if retrieval is needed |
| `retrieval` | Hybrid Retrieval | 🔍 | Vector + BM25 + GraphRAG |
| `external_tools` | External Tools | 🌐 | Web search for live data |
| `aggregator` | Evidence Aggregator | 📚 | Merge & deduplicate sources |
| `reranker` | Cross-Encoder Reranker | 🎯 | Score & rank by relevance |
| `compressor` | Context Compressor | ✂️ | Summarize to fit LLM window |
| `reasoning` | Reasoning Agent | 💡 | Generate cited answer |
| `reflection` | Self-Reflection Agent | 🔮 | Verify grounding & citations |

**Event → status mapping** (`_applyEvent`):

| Event type | Resulting status | Also sets |
|---|---|---|
| `stage_start` | `active` | `message` |
| `stage_complete`, `retrieval_result` | `complete` | `message`, `details` = full payload |
| `stage_skip` | `skipped` | `message` (default `"Skipped"`) |
| `stage_error` | `error` | `message` = `data.error` |
| `finalize` | `complete` | `message` (default `"Done"`) |
| `retry` | — | sets `retryCount = attempt - 1` and **resets the seven post-planner stages to `idle`** so they visibly re-run |

Events without a recognised `data.stage` are logged to `events` and otherwise ignored.

**Progress percentage** (`PipelineTracker.vue:68-73`): `(completed + skipped + 0.5 if any stage is active)
/ 8`, rounded — and forced to `100` as soon as `store.hasResult` is true.

**Detail chips** (`StageRow.vue:69-82`) are derived from `status.details`, showing only the keys present:
`N vector`, `N BM25`, `N graph`, `N web`, `top K`, `NN% conf.`, `grounded ✓` / `ungrounded`, `NN% size`.

**Visual states:** `active` and `complete` both use emerald tints (active slightly stronger), `skipped`
drops to `opacity-35` with muted text, `error` uses red tints, `idle` is neutral stone.

**Depends on:** the SSE contract in [`../../api/sse-events/README.md`](../../api/sse-events/README.md) and
the stage ids emitted by the pipeline. It writes nothing back to the server.

**Gotchas:**

- **`STAGES` is a hardcoded mirror of the backend's *emitted* `data.stage` values — not of its graph node
  names.** Five of the eight differ: nodes `aggregate`, `rerank`, `compress`, `reason`, `reflect` emit
  `aggregator`, `reranker`, `compressor`, `reasoning`, `reflection`; only `planner`, `retrieval`, and
  `external_tools` are spelled the same in both places. The authority is therefore the `emit(...)` call
  site, not `graph.py`: renaming a node changes nothing here, while changing an emitted `stage` string
  without updating this array silently drops that stage's events on the floor — per the event-mapping
  section above, an unrecognised `data.stage` is logged to `events` and otherwise ignored.
- **A skipped stage still renders**, greyed — the tracker shows the full pipeline shape, not just the path
  taken.
- **`events` grows unbounded** for the life of a query; it is a raw debugging log, reset only by
  `resetPipeline()`.
- **The percentage is a display heuristic**, not real progress — stages are weighted equally though their
  durations differ by an order of magnitude.
