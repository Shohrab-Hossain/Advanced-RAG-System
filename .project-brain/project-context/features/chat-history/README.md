# Feature: Chat history

**Purpose:** keep a browser-local record of past queries so a user can revisit an answer — including the
pipeline visualisation it produced — without re-running it.

**Entry point:** the history sidebar in `ChatView.vue`.

**Implemented in:** `Frontend/src/stores/rag.js` (`chatHistory`, `loadHistoryItem`, `deleteHistoryItem`,
`clearChatHistory`, `_loadHistory`, `_persistHistory`) and `Frontend/src/views/ChatView.vue` (sidebar,
relative-time formatting, active-item highlighting).

**Storage:** `localStorage` key **`rag-chat-history`**, a JSON array, **newest first**, capped at **50
entries** on every write (`chatHistory.value.slice(0, 50)`). Loading is fault-tolerant: a parse failure
yields `[]` rather than throwing.

**Entry shape** — written in `runQuery`'s `onDone` handler, only when `result.answer` is truthy:

| Field | Type | Notes |
|---|---|---|
| `id` | string | `Date.now().toString()` |
| `query` | string | the submitted query |
| `answer` | string | the final answer markdown |
| `sources` | array | the cited sources as returned |
| `metadata` | object | `pipeline_metadata` from the run |
| `stageStatuses` | object | a deep clone (`JSON.parse(JSON.stringify(...))`) of the whole stage map |
| `retryCount` | number | retries in that run |
| `timestamp` | number | epoch ms |

**Behaviour:**

- `loadHistoryItem(item)` restores query, answer, sources, metadata, and retry count, clears any error,
  sets `isHistoryResult = true`, and replays the saved `stageStatuses` into the tracker. For an older entry
  with no `stageStatuses` snapshot, every stage is set to `complete` with the message
  `"Pipeline completed"` so the tracker is not blank.
- `ChatView.vue` formats timestamps relatively — `Just now`, `Nm ago`, `Nh ago`, then a locale
  month/day — and highlights the newest entry automatically when a fresh (non-history) query completes,
  via a watcher on `chatHistory[0]?.id`.
- `isHistoryResult` distinguishes a replayed result from a live one so the UI can label it.

**Depends on:** the browser's `localStorage` and the result/stage state produced by
[`self-rag-pipeline`](../self-rag-pipeline/README.md) and rendered by
[`pipeline-tracker`](../pipeline-tracker/README.md). Nothing server-side is involved.

**Gotchas:**

- **History is not conversation context.** Nothing from a past entry is sent back to the model; each query
  is independent.
- **Per-browser, per-origin, and lost on a storage clear.** There is no server-side copy and no export.
- **Full answers and full source `content` are stored**, so a long session can approach the ~5 MB
  `localStorage` quota; a quota error on write is not caught.
- **`id` is a millisecond timestamp** — two entries created in the same millisecond would collide, and
  `deleteHistoryItem` filters by `id`.
