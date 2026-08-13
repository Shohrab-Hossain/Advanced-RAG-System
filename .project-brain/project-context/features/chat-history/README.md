# Feature: Chat history

**Purpose:** keep a browser-local record of past queries so a user can revisit an answer — including the
pipeline visualisation it produced — without re-running it.

**Entry point:** the `ChatHistorySidebar` overlay, mounted by `ChatView.vue:4` and toggled from the
header button at `:24`.

**Implemented in:**

| Concern | File |
|---|---|
| State + persistence | `Frontend/src/subsystems/rag/ragStore.js:55-62` (`HISTORY_KEY`, `_loadHistory`, `chatHistory`, `_persistHistory`) |
| Entry write | `Frontend/src/subsystems/rag/ragStore.js:141-153` — inside `runQuery`'s `onDone` |
| Load / delete / clear | `Frontend/src/subsystems/rag/ragStore.js:170-198` (`loadHistoryItem`, `deleteHistoryItem`, `clearChatHistory`) |
| Sidebar UI + confirms | `Frontend/src/pages/chat/components/ChatHistorySidebar/ChatHistorySidebar.vue` |
| Relative-time formatting (pure) | `Frontend/src/pages/chat/components/ChatHistorySidebar/chatHistorySidebar.js:8` — `formatTime` |
| Overlay transitions | `Frontend/src/pages/chat/components/ChatHistorySidebar/chatHistorySidebar.css` |

The sidebar is the brain's clearest example of the **component-folder triple** — `.vue` + a camelCase
pure-logic sibling + a split CSS file pulled in as `<style scoped src="./chatHistorySidebar.css">`
(`ChatHistorySidebar.vue:132`). The view keeps only what it owns: the `sidebarOpen` ref
(`ChatView.vue:129`), the toggle button with its entry-count badge (`:24-37`), and the `:open` / `@close`
wiring (`:4`). Everything else — the list, the highlight, the confirmations — belongs to the component.

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
- `formatTime()` (`chatHistorySidebar.js:8`) renders each entry's age relatively — `Just now`, `Nm ago`,
  `Nh ago`, then a locale month/day.
- The sidebar highlights the newest entry automatically when a fresh (non-history) query completes, via a
  watcher on `store.chatHistory[0]?.id` guarded by `!store.isHistoryResult`
  (`ChatHistorySidebar.vue:101-105`); `activeHistoryId` is component-local state, not store state.
  Clicking an entry loads it and closes the overlay (`:107-111`).
- Both destructive actions are gated behind `ui.confirm()` inside the sidebar (`:113-129`): *"Delete this
  chat from history?"* per entry, and *"Delete all chat history? This cannot be undone."* for the header's
  "Clear all" — both `danger`, and both clear `activeHistoryId` when they apply to it.
- `isHistoryResult` distinguishes a replayed result from a live one so the UI can label it — the tracker
  shows a "from history" pill (`PipelineTracker.vue:9-15`).

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
