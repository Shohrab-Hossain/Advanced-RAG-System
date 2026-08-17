<div align="center">

# 🗃 State

### Three Pinia stores, flat by kind — one owns the app shell, one turns an SSE stream into eight animated rows, one owns the corpus.

<br>

[![Stores](https://img.shields.io/badge/stores-3-1c7ed6)](#-1-purpose--user-visible-behavior)
[![Style](https://img.shields.io/badge/Pinia-setup%20style-7c5cff)](#31-setup-style-stores-and-genuine-privacy)
[![Manifest](https://img.shields.io/badge/manifest-package.json-3fb950)](../../package.json)

[![Persisted keys](https://img.shields.io/badge/localStorage%20keys-2-f59e0b)](#53-chat-history-persistence)
[![Event types handled](https://img.shields.io/badge/SSE%20types%20handled-7-f59e0b)](#52-_applyevent--the-eventstate-dispatch-table)
[![Store→service edges](https://img.shields.io/badge/store%E2%86%92service%20edges-2-3fb950)](#33-the-layering-invariants)

</div>

<br>

---

<br>

## Content Tree

<pre>
State
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│   ├── <a href="#11-what-the-user-actually-observes">1.1 What the user actually observes</a>
│   ├── <a href="#12-the-three-stores-at-a-glance">1.2 The three stores at a glance</a>
│   └── <a href="#13-what-deliberately-stays-out-of-a-store">1.3 What deliberately stays out of a store</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-setup-style-stores-and-genuine-privacy">3.1 Setup-style stores, and genuine privacy</a>
│   ├── <a href="#32-the-one-reactive-in-the-codebase">3.2 The one reactive() in the codebase</a>
│   └── <a href="#33-the-layering-invariants">3.3 The layering invariants</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-the-ui-store-and-the-promise-modal">4.1 The 'ui' store and the promise-modal</a>
│   ├── <a href="#42-a-query-run-start-to-finish">4.2 A query run, start to finish</a>
│   ├── <a href="#43-the-provider-cascade">4.3 The provider cascade</a>
│   └── <a href="#44-an-upload-in-two-phases">4.4 An upload, in two phases</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-the-stages-constant">5.1 The STAGES constant</a>
│   ├── <a href="#52-_applyevent--the-eventstate-dispatch-table">5.2 _applyEvent — the event→state dispatch table</a>
│   ├── <a href="#53-chat-history-persistence">5.3 Chat-history persistence</a>
│   ├── <a href="#54-restoring-a-past-run">5.4 Restoring a past run</a>
│   └── <a href="#55-the-split-error-policy-on-kbstore">5.5 The split error policy on kbStore</a>
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

There are **three** Pinia stores, and all three sit flat in `Frontend/src/store/` — no per-capability
subfolders, no barrel of modules. The domain lives in the filename, not in a directory:

- **`store/index.js`** registers the id **`'ui'`** and owns the app shell — the dark/light theme and a
  single modal slot. It knows nothing about RAG, nothing about HTTP, and imports only Pinia and Vue.
- **`store/ragStore.js`** registers **`'rag'`** and is the largest and most interesting file in the
  frontend: it owns the query, the eight pipeline stage rows, the answer, the cited sources, and the
  chat history. It is where a stream of Server-Sent Events becomes reactive UI state.
- **`store/kbStore.js`** registers **`'knowledgeBase'`** and owns the corpus — index statistics, the
  knowledge-base list, and the two-phase upload progress.

Every store is written in **setup style** — `defineStore('id', () => { … })` returning a flat object of
refs, computeds and functions. None uses the options object. Each store that talks to the network
imports exactly one HTTP client and nothing else.

> [!IMPORTANT]
> **The store id and the filename deliberately differ for the shell store.** The file is `index.js`, the
> id is `'ui'`, and every consumer writes `import { useUiStore } from '../../../store'` — folder-index
> resolution, no filename. If you grep for `uiStore.js` you will not find it.

**Where this fits:** the two HTTP clients these stores sit on top of are documented in
[`../api-clients/README.md`](../api-clients/README.md); the components that read this state are covered
by the [chat](../chat/README.md), [knowledge-base](../knowledge-base/README.md) and
[configuration](../configuration-page/README.md) pages. The server side of the event stream is
[`../../../Backend/Documentation/sse-event-bus/README.md`](../../../Backend/Documentation/sse-event-bus/README.md).

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

### 1.1 What the user actually observes

Four behaviours in the running app are pure store consequences, and each one is worth naming because
each is easy to attribute to the wrong layer:

| Observed behaviour | The store fact behind it |
|---|---|
| The app opens **dark** on a fresh machine and remembers the choice | `theme` is `localStorage.getItem('rag-theme') \|\| 'dark'` (`store/index.js:9`), and `applyTheme` runs at store-creation time (`:12`) |
| Chat history survives a reload, newest first | `chatHistory` hydrates from `localStorage['rag-chat-history']` once, at store creation (`ragStore.js:59`) |
| Eight tracker rows animate live, then freeze if the run errors | `_applyEvent` mutates `stageStatuses` per stage; `onError` deliberately leaves those rows untouched (`ragStore.js:160-164`) |
| The "No documents indexed yet" banner disappears after one upload | `kbStore.hasDocuments` is `indexStats.vector_count > 0` (`kbStore.js:28`), refreshed after every ingest |

### 1.2 The three stores at a glance

| File | Store id | Lines | Backing client | Persists to |
|---|---|---|---|---|
| `store/index.js` | `'ui'` (`:8`) | 49 | **none** | `localStorage['rag-theme']` |
| `store/ragStore.js` | `'rag'` (`:30`) | 249 | `services/ragApi` (`:13`) | `localStorage['rag-chat-history']` |
| `store/kbStore.js` | `'knowledgeBase'` (`:14`) | 121 | `services/kbApi` (`:12`) | nothing |

`kbStore` holds no persisted state on purpose: everything it knows is server truth, refetched on mount
and after every write.

### 1.3 What deliberately stays out of a store

Plenty of state is local, and the split is consistent. A value that only one component renders stays a
`ref` inside that component — `sidebarOpen` in `ChatView.vue:129`, `localQuery` in `QueryInput.vue:78`,
`selectedSource` in `ResultDisplay.vue:103`, `dragCount` in `UploadPanel.vue:96`, `checking` in
`LLMSelector.vue`. Nothing in the tree lifts that state into Pinia "just in case".

The rule the code follows: **a store holds state that outlives its component or crosses a page
boundary.** Everything else is a local ref, and **five components import no store at all** —
`StageRow.vue`, `SourceCard.vue`, `IndexStats.vue`, `KnowledgeBaseList.vue` and `FileTypeIcon.vue` are
pure presentational leaves, props in and emits out.

---

## 📍 2. WHERE IT LIVES

Paths are relative to `Frontend/src/`.

| Concern | Path | Anchor |
|---|---|---|
| Theme + modal | `store/index.js:8` | `useUiStore` |
| Query, stages, history | `store/ragStore.js:30` | `useRagStore` |
| The display contract for the eight rows | `store/ragStore.js:16-25` | `STAGES` |
| SSE event dispatch | `store/ragStore.js:84` | `_applyEvent` |
| History persistence | `store/ragStore.js:55-61` | `_loadHistory`, `_persistHistory` |
| Corpus + upload | `store/kbStore.js:14` | `useKbStore` |
| The fake indexing bar | `store/kbStore.js:62` | `_animateIndexing` |

```text
src/store/
│
├── 📄 index.js       The 'ui' store — theme (dark by default) + one promise-backed modal slot
├── 📄 ragStore.js    The 'rag' store — STAGES, query lifecycle, SSE dispatch, chat history
└── 📄 kbStore.js     The 'knowledgeBase' store — index stats, KB list, two-phase upload
```

> [!NOTE]
> **A new capability adds two files, not two folders** — `store/<abbrev>Store.js` beside these three,
> and `services/<abbrev>Api.js` beside the two clients. The flat-by-kind rule for state and HTTP is
> deliberately *different* from the ownership rule that places components; both are load-bearing and
> neither should be "tidied" into the other.

---

## 🏗️ 3. ARCHITECTURE

### 3.1 Setup-style stores, and genuine privacy

Every store is `defineStore(id, () => { … })`, and the returned object is the store's entire public
surface. That is not a stylistic preference — it buys **real encapsulation**, which the options API
cannot express:

```js
// src/store/ragStore.js:234 — the return statement IS the access-control list
return {
  STAGES, llmProvider, ollamaModel, openaiModel, availableProviders,
  query, isRunning, stageStatuses, events, retryCount,
  answer, sources, metadata, error, isHistoryResult, chatHistory,
  hasResult,
  resetPipeline, runQuery, abortQuery,
  loadHistoryItem, deleteHistoryItem, clearChatHistory,
  fetchProviders, setOllamaModel, setOpenaiModel,
}
```

Four things defined in the closure are **not** in that list and are therefore unreachable from any
component: `_applyEvent` (`:84`), `_loadHistory` (`:55`), `_persistHistory` (`:61`) and `_abortFn`
(`:64`). `_abortFn` is a plain `let`, not a `ref`, precisely because nothing renders it — making it
reactive would buy a dependency-tracking cost for a value no template reads.

The leading underscore is a convention; the omission from the return statement is the enforcement.

### 3.2 The one `reactive()` in the codebase

Every piece of state in all three stores is a `ref()` — with exactly one exception:

```js
// src/store/ragStore.js:43
const stageStatuses = reactive(_initialStages())
```

`_initialStages()` (`:27-28`) builds `{ [id]: { status: 'idle', message: '', details: null } }` for all
eight stage ids via `Object.fromEntries`. The shape is **fixed** — the same eight keys for the life of
the app — and the object is **mutated per key**, never replaced. That is exactly the case `reactive`
exists for: a keyed record where writes are always `stageStatuses[stage] = {…}` and never
`stageStatuses = {…}`.

The practical consequence: a consumer writes `store.stageStatuses[stage.id]`, with no `.value`, while
every other store field needs the ref unwrapping that Pinia does for you at the component boundary.

### 3.3 The layering invariants

These were verified by extracting **every** `import` statement under `src/`. They are not aspirations:

| Invariant | Status | Evidence |
|---|---|---|
| Services import nothing local | ✅ | `ragApi.js:9` and `kbApi.js:8` each import **only `axios`** |
| The two clients never import each other | ✅ | neither file references the other |
| Each client builds its own axios instance | ✅ | `ragApi.js:14`, `kbApi.js:13` — two `axios.create` calls |
| Stores never import components | ✅ | store imports are Pinia/Vue plus at most one service |
| `store/index.js` knows nothing about RAG or HTTP | ✅ | its only imports are `pinia` and `vue` (`:1-2`) |
| `ragStore` and `kbStore` never import each other | ✅ | `ragStore.js:13` → `ragApi`; `kbStore.js:12` → `kbApi` |
| `shared/` never imports `pages/` | ✅ | shared components import Vue, Vue Router, `store/`, `services/` |
| Components call store actions, not services | ✅ **with one exception** | `NavBar.vue:111` imports `healthCheck` from `services/ragApi` |

**Exactly one component→service edge exists in the whole tree**, and it is the accepted one: the
navbar's health indicator. Nothing else in `shared/` or `pages/` imports a service module.

<p align="center">
  <img src="../../../.readme-lib/documentation/frontend-architecture/diagrams/svg/frontend-ownership-layering.svg" alt="The frontend dependency map in six bands, every arrow pointing downward. Band 1, ENTRY: main.js boots App.vue and router/index.js, whose four routes are lazy imports. Band 2, PAGES, placed by ownership — one folder per route, each owning its own components: pages/home/ holds HomeView.vue, which owns nothing and imports nothing; pages/chat/ holds ChatView.vue over ChatHistorySidebar, QueryInput, PipelineTracker and ResultDisplay, with StageRow nested inside PipelineTracker/ and SourceCard nested inside ResultDisplay/ as satellites; pages/knowledge-base/ holds KnowledgeBaseView.vue over UploadPanel, IndexStats and KnowledgeBaseList; pages/configuration/ holds ConfigView.vue over LLMSelector. The router reaches each of the four views by a dashed lazy-import edge. Band 3, SHARED, promoted only at a second page consumer: NavBar.vue, ModalDialog.vue and FileTypeIcon.vue — FileTypeIcon is drawn with a blue border and takes three blue incoming edges from ResultDisplay and SourceCard on the chat page and KnowledgeBaseList on the knowledge-base page, which is the two-page consumer set that earns it a place in shared/. Band 4, store/, flat by kind with no per-capability folders: ragStore.js id 'rag', kbStore.js id 'knowledgeBase', and index.js id 'ui' which imports pinia and vue only and has no outgoing edge at all. Band 5, services/, flat by kind, each building its own axios instance: ragApi.js and kbApi.js. Only ragStore reaches ragApi and only kbStore reaches kbApi; there is no service-to-service edge. Band 6 is the Flask API, 8 routes, reached through the dev proxy /api to port 5000. One amber dashed edge cuts across the bands from NavBar.vue straight to ragApi.js, labelled healthCheck() — the ONE component-to-service edge; every other component reaches HTTP only through a store. The five grey nodes — StageRow, SourceCard, IndexStats, KnowledgeBaseList and FileTypeIcon — are the presentational leaves that import no store at all." width="820">
</p>

<sub>Diagram source: <a href="../../../.readme-lib/documentation/frontend-architecture/diagrams/mermaid-source/frontend-ownership-layering.mmd"><code>frontend-ownership-layering.mmd</code></a> — edit it, then regenerate the SVG (don't hand-edit the SVG).</sub>

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 The `'ui'` store and the promise-modal

The shell store is 49 lines and carries one genuinely good idea. A modal confirmation is normally
awkward in Vue — the component that needs an answer is not the component that renders the dialog. This
store solves it by **parking the promise's `resolve` function inside store state**:

```js
// src/store/index.js:31 — confirm() returns a Promise<boolean>
function confirm (message, options = {}) {
  return new Promise((resolve) => {
    modal.value = {
      type: 'confirm',
      message,
      danger: options.danger ?? false,
      confirmText: options.confirmText ?? null,
      cancelText: options.cancelText ?? null,
      resolve,
    }
  })
}
```

The full cycle, four steps:

1. A component `await`s `ui.confirm('Delete this chat from history?', { danger: true })`. Its own
   function suspends mid-body.
2. `modal.value` is now non-null, so `ModalDialog` — mounted once in `App.vue` — renders from it.
3. The user clicks. `ModalDialog` calls `ui.close(true)` or `ui.close(false)`.
4. `close(result = true)` (`:44-46`) calls the stored `resolve(result)` and nulls `modal`. The awaiting
   component resumes on the next microtask with a plain boolean.

**Five call sites use it, and four of the five are destructive** — deleting one history entry
(`ChatHistorySidebar.vue:114`), clearing all history (`:123`), deleting one knowledge base
(`KnowledgeBaseView.vue:60`), clearing the whole index (`:66`), all with `danger: true`. The fifth is
the duplicate-upload prompt (`UploadPanel.vue:134`), **the only non-`danger` confirm in the app** —
covered in [`../knowledge-base/README.md`](../knowledge-base/README.md).

`ui.alert(message)` (`:27-29`) exists and follows the same pattern, but **nothing in `src/` calls it**.

The theme half is smaller and equally direct: `applyTheme(t)` (`:4-6`) does
`document.documentElement.classList.toggle('dark', t === 'dark')`, which is the hook
`darkMode: 'class'` keys on. It is invoked at store-creation time rather than from a lifecycle hook,
which is why `App.vue:20` calls `useUiStore()` **bare, for the side effect**, using no returned value.

### 4.2 A query run, start to finish

`runQuery(q)` (`ragStore.js:127-167`) is the store's spine. In order:

1. **Guard** — `if (!q.trim() || isRunning.value) return` (`:128`). A double submit is impossible from
   the store side, independent of whatever the button's `:disabled` says.
2. **Claim the run** — `query.value = q.trim()`, `isRunning.value = true`, then `resetPipeline()`
   (`:129-131`), which returns all eight stages to `idle` and clears `events`, `answer`, `sources`,
   `metadata`, `error`, `retryCount` and `isHistoryResult`.
3. **Resolve the model** (`:133-135`) — `ollama` → `ollamaModel.value`, `openai` → `openaiModel.value`,
   otherwise `null`. Both branches are live: the `model` field overrides the chat model for **either**
   provider.
4. **Open the stream** — `streamQuery(q, llmProvider.value, model || null, { onEvent, onDone, onError })`
   (`:136`). The call returns a controller synchronously, not a promise; the store stores its `abort`
   in `_abortFn`.
5. **`onEvent`** (`:137`) forwards straight into `_applyEvent` (§5.2).
6. **`onDone(result)`** (`:138-159`) writes `answer`, `sources` and `metadata` with `|| ''`, `|| []`,
   `|| {}` fallbacks, clears `isRunning`, sets `isHistoryResult = false`, drops `_abortFn` — and **only
   if `result.answer` is truthy** unshifts a history entry and persists it (§5.3).
7. **`onError(msg)`** (`:160-164`) sets `error`, clears `isRunning` and `_abortFn`. **It does not touch
   `stageStatuses`** — every row freezes exactly where it was, which is what makes an error diagnosable
   from the tracker instead of erasing the evidence.

`abortQuery()` (`:169-173`) calls `_abortFn?.()`, clears `isRunning`, and sets
`error = 'Query cancelled'` itself — because the client suppresses the browser's `AbortError` rather
than reporting it as a failure (see [`../api-clients/README.md`](../api-clients/README.md)).

### 4.3 The provider cascade

`fetchProviders()` (`:205-224`) does three distinct jobs, and it is the only place the frontend reshapes
a wire payload:

1. **Array → map.** The endpoint returns `providers` as an **array**; the store indexes it by id —
   `for (const p of data.providers) map[p.id] = p` (`:209`), then `availableProviders.value = map`
   (`:210`). Every consumer reads `availableProviders.openai` / `.ollama`, never a `.find()`.
2. **Auto-select, in strict order** (`:212-218`): the server's `default` **if that provider is
   available** → else `openai` if available → else `ollama` if available → else leave `llmProvider`
   untouched. A server default naming an unreachable provider therefore never strands the UI.
3. **Pre-fill** (`:220-222`): if `openaiModel` is still empty and the server reported one, adopt it.
   **`ollamaModel` gets no equivalent pre-fill here** — `LLMSelector` does that instead, because the
   server's configured Ollama model may name something that was never pulled.

The whole body sits inside `try { … } catch { /* ignore — server might not be up yet */ }` (`:206`,
`:223`). **A dead backend is silent by design**; the offline signal is the navbar's health pill, not an
exception here.

> The `availableProviders` ref is **replaced wholesale**, never merged. Its seed value
> (`:35-38`) exists only so the first render before any fetch has a shape to read.

### 4.4 An upload, in two phases

`uploadDocument(file, { queueCurrent = 1, queueTotal = 1 })` (`kbStore.js:32-60`) drives a bar with two
different meanings:

1. Reset every flag and counter, and null `uploadResult` (`:33-39`).
2. **Phase 1** — `await uploadFile(file, pct => uploadProgress.value = pct)` (`:42`). This is a **real**
   measurement of browser→server byte transfer.
3. **Phase 2** — `isIndexing = true` **then** `uploading = false` (`:44-45`), in that order and in the
   same tick, so Vue batches both DOM updates and there is no flash of an empty bar.
4. `await _animateIndexing()` (`:46`) — see the warning below.
5. `isIndexing = false`, `indexingProgress = 100` (`:47-48`), then `await refreshStats()` and
   `await fetchKnowledgeBases()` (`:49-50`), then publish `uploadResult = result` (`:51`).
6. `catch` (`:53-55`) records `{ error: err.response?.data?.error || err.message }` — the backend's JSON
   `error` key first, the axios message as fallback — and **re-throws**, so the caller can react.
7. `finally` (`:56-59`) forces both phase flags false whatever happened.

> [!WARNING]
> **`_animateIndexing()` measures nothing. It is a fixed client-side animation.**
> `kbStore.js:62-76` steps `indexingProgress` by `+5` every `80 ms` until it reaches `95`, then
> resolves — so it always takes **about 1.5 seconds regardless of the real indexing time**, and it
> resolves before the server's work is reflected anywhere. There is no ingestion progress channel to
> drive it from: `POST /api/upload` is **fully synchronous**, with no job id, no polling endpoint and
> no event stream, so by the time step 4 runs the server has already finished. The bar is honest that
> *something is happening* and dishonest about *how far along it is*. A 200-page PDF and a one-line
> text file produce the identical animation.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 The `STAGES` constant

**The problem:** the tracker must render eight rows in a fixed order, with a label, an icon and a
one-line description each, and its keys must match the ids the server puts on the wire — exactly.

`STAGES` (`ragStore.js:16-25`) is an exported array of `{ id, label, icon, desc }` in display order:

| `id` | `label` | `icon` | `desc` |
|---|---|---|---|
| `planner` | Self-RAG Planner | 🧠 | Decides if retrieval is needed |
| `retrieval` | Hybrid Retrieval | 🔍 | Vector + BM25 + GraphRAG |
| `external_tools` | External Tools | 🌐 | Web search for live data |
| `aggregator` | Evidence Aggregator | 📚 | Merge & deduplicate sources |
| `reranker` | Cross-Encoder Reranker | 🎯 | Score & rank by relevance |
| `compressor` | Context Compressor | ✂️ | Summarize to fit LLM window |
| `reasoning` | Reasoning Agent | 💡 | Generate cited answer |
| `reflection` | Self-Reflection Agent | 🔮 | Verify grounding & citations |

> [!CAUTION]
> **These ids are the emitted SSE `stage` values, not the LangGraph node names — five of the eight
> differ.** The graph registers `aggregate` · `rerank` · `compress` · `reason` · `reflect`; the frames
> those nodes emit carry `aggregator` · `reranker` · `compressor` · `reasoning` · `reflection`. Only
> `planner`, `retrieval` and `external_tools` coincide. **The `emit()` call sites are the contract.**
> Renaming a graph node breaks nothing here; changing an `emit(...)` `stage` value silently stops that
> row updating forever, because the guard at `ragStore.js:99` drops any event whose stage is not a key
> of `stageStatuses`. The full contract is in
> [`../chat/pipeline-tracker.md`](../chat/pipeline-tracker.md).

`STAGES` is exported and consumed by `PipelineTracker.vue:59` for iteration and the row count. It is
**the** display contract; the six teaser chips on the chat empty state are a separate, shorter list and
are not a second source of stage truth.

### 5.2 `_applyEvent` — the event→state dispatch table

**The problem:** a single stream carries pipeline-level events and stage-level events through one
callback, and the stage-level ones must be routed by an id the payload may not have.

Every event is first appended to the raw `events` log (`:85`) — **including the ones the switch never
sees** — so the log is complete even where the state machine is selective. Then:

```js
// src/store/ragStore.js:87 — the pipeline-level branch, BEFORE the stage guard
if (type === 'retry') {
  retryCount.value = (data.attempt || 1) - 1
  ;['retrieval', 'external_tools', 'aggregator', 'reranker', 'compressor', 'reasoning', 'reflection']
    .forEach((s) => { stageStatuses[s] = { status: 'idle', message: '', details: null } })
  return
}

const stage = data?.stage                          // :98
if (!stage || !(stage in stageStatuses)) return    // :99 — the guard
```

Two details in that block are easy to get backwards, and both are deliberate:

- **`retryCount` is assigned, not incremented** — `(data.attempt || 1) - 1` (`:91`). The server's
  `attempt` numbers the pass *about to begin*, so the first `retry` frame sets the counter to `1`.
- **The reset list is seven stages and excludes `planner`** (`:93`). The planner does not re-run on a
  retry, so its row correctly keeps its completed state while the rest rewind.

The `retry` event **carries no `stage` key at all**, by design on the server side — which is exactly why
it must be handled before the guard. There is **no `case 'retry':` anywhere in the switch**.

After the guard, the switch (`:101-124`) has exactly six labels:

| Event type | Line | Effect on `stageStatuses[stage]` |
|---|---|---|
| `stage_start` | `:102-105` | `status = 'active'`, `message = data.message \|\| ''` |
| `stage_complete` **and** `retrieval_result` | `:106-111` | *(fall-through, one shared body)* `status = 'complete'`, `message = data.message \|\| ''`, **`details = data`** |
| `stage_skip` | `:112-115` | `status = 'skipped'`, `message = data.message \|\| 'Skipped'` |
| `stage_error` | `:116-119` | `status = 'error'`, **`message = data.error \|\| 'Error'`** |
| `finalize` | `:120-123` | `status = 'complete'`, `message = data.message \|\| 'Done'` |

Three facts worth not blurring:

1. **`stage_error` is the only type read from `data.error`.** Every other reads `data.message`, matching
   the server, which puts the human text under `error` for that one type.
2. **`details` is a frontend-only field.** No wire payload has a `details` key — `:110` assigns the
   *whole* event payload into it, and `StageRow` mines that object for its chips.
3. **`retrieval_result` is the retrieval row's only completion.** The retrieval node never emits
   `stage_complete`. Delete the fall-through at `:107` and that row hangs `active` for the rest of the
   run.

**Status vocabulary — exactly five values:** `idle` · `active` · `complete` · `skipped` · `error`.

Unknown types, and known types carrying an unrecognised stage, are **silently dropped** by `:99`. The
three route-framed events (`done`, `error`, `stream_end`) never reach `_applyEvent` at all — the HTTP
client intercepts them first.

### 5.3 Chat-history persistence

The whole feature is two closure-private functions and a `localStorage` key.

| Aspect | Fact | Line |
|---|---|---|
| Medium | `localStorage` | `:57`, `:61` |
| Key | **`'rag-chat-history'`** | `:55` |
| Read | once, at store creation — `ref(_loadHistory())` | `:59` |
| Read failure | `try/catch` → `[]`; a corrupt blob is discarded silently | `:57` |
| Write | `JSON.stringify(chatHistory.value.slice(0, 50))` | `:61` |
| Order | newest first — `unshift` | `:147` |
| Written by | `runQuery.onDone` (`:157`), `deleteHistoryItem` (`:197`), `clearChatHistory` (`:202`) | |

An entry is exactly eight keys (`:147-156`):

```js
{
  id:            Date.now().toString(),                       // :148 — a string, not a number
  query:         query.value,                                 // :149 — the trimmed text
  answer:        result.answer,                               // :150
  sources:       result.sources || [],                        // :151
  metadata:      result.metadata || {},                       // :152
  stageStatuses: JSON.parse(JSON.stringify(stageStatuses)),   // :153 — a deep clone
  retryCount:    retryCount.value,                            // :154
  timestamp:     Date.now(),                                  // :155
}
```

The `stageStatuses` deep clone is what makes a history entry replayable: reopening a past run redraws
the full tracker, not just the answer.

> [!IMPORTANT]
> **The 50-entry cap is on the WRITE, not on the array.** `chatHistory.value` is never truncated, so
> within one session the sidebar can list more than fifty entries — and **a page reload then silently
> drops everything past the newest fifty**. This is observable, not theoretical: run 55 queries, see 55
> entries, reload, see 50.

### 5.4 Restoring a past run

`loadHistoryItem(item)` (`:175-193`) restores `query`, `answer`, `sources`, `metadata` and `retryCount`,
clears `error`, and sets `isHistoryResult = true` with `isRunning = false` — the flag that makes the
tracker show its "from history" pill instead of a spinner.

Per stage (`:184-192`) it uses the saved snapshot **if present**, and otherwise falls back to
`{ status: 'complete', message: 'Pipeline completed', details: null }`. That fallback exists for
entries written before `stageStatuses` was part of the record: without it, an old entry would render
eight blank rows, which reads as a broken run rather than an old one.

**It does not clear `events`.** The raw debug log still holds whatever the last *live* run produced.

### 5.5 The split error policy on `kbStore`

The corpus store handles failure two different ways, on purpose:

| Action | Line | Policy |
|---|---|---|
| `refreshStats()` | `:78-82` | **swallows** — `catch { /* ignore */ }` |
| `fetchKnowledgeBases()` | `:84-89` | **swallows** |
| `uploadDocument()` | `:32-60` | records to `uploadResult`, then **re-throws** |
| `removeKnowledgeBase(hash)` | `:91-97` | **propagates** — no try/catch at all |
| `clearIndex()` | `:99-104` | **propagates** |

The two **read** actions swallow so a backend that is down leaves a quiet zero-state rather than a wall
of errors on a page the user has only just opened. The three **write** actions propagate because a user
who clicked *Delete* is entitled to know it failed. `removeKnowledgeBase` also calls
`resetUploadResult()` first (`:92`), so a stale success banner from an earlier upload cannot survive a
subsequent delete.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

The stores consume four distinct payload families. None of them is validated at runtime — every read is
defensive (`?.`, `||`, `??`) rather than schema-checked.

| Payload | Enters at | Shape the store depends on |
|---|---|---|
| SSE stage events | `_applyEvent` via `onEvent` | a `stage` key matching a `STAGES` id, plus `message` (or `error` for `stage_error`) |
| The `done` payload | `runQuery.onDone` | `{ answer, sources, metadata }` — all three read with fallbacks |
| Provider list | `fetchProviders` | `{ providers: [ { id, label, model, base_url, available, models } ], default }` |
| Corpus stats | `refreshStats` | `{ vector_count, bm25_count, graph: { entities, documents, edges } }` |
| Upload result | `uploadDocument` | `{ success, file_name, file_hash, chunks_indexed, kb, stats }` |

**Eleven wire types exist across the whole stream** — seven produced by the pipeline itself (from 31
`emit()` call sites) plus three framed by the route. The frontend accounts for all ten across two
files: six switch labels plus `retry` here, and `done` / `error` / `stream_end` intercepted in the
client. The full event catalogue lives in
[`../../../Backend/Documentation/api/query.md`](../../../Backend/Documentation/api/query.md).

> [!NOTE]
> **A pipeline failure arrives as HTTP `200`.** Once the stream is open, every error is in-band — an
> `error` event on a successful response, not an error status. The only HTTP failures the stores can
> see are the two pre-stream `400`s, and those surface through `onError` like any other.

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **The in-memory history is uncapped; only the write is capped.** A reload is what truncates (§5.3).

- **A history `id` is a millisecond timestamp and can collide.** `id` and `timestamp` are two separate
  `Date.now()` calls (`:148`, `:155`), so they can even differ by a millisecond from each other. Two
  entries created inside the same millisecond would share an id — unreachable by hand, but the id is
  not a real unique key.

- **There is no storage-quota handling.** `localStorage.setItem` (`:61`) is unguarded, and entries embed
  the full `sources` array — each source carrying a complete `content` string. A `QuotaExceededError`
  would propagate straight out of `onDone`, after the answer has already been assigned. The quota is a
  realistic ceiling for a long-lived session, not a hypothetical one.

- **`runQuery` stores the trimmed query but sends the untrimmed one.** `query.value = q.trim()`
  (`:129`), then `streamQuery(q, …)` (`:136`) passes the original `q`. Harmless — the server strips it
  — but the two values are genuinely different objects.

- **`loadHistoryItem` leaves `events` populated from the previous live run.** Nothing renders `events`
  today, so this is invisible; it would matter the moment a debug panel read it.

- **`availableProviders` is replaced, not merged** (`:210`). A provider the server stops reporting
  vanishes from the map entirely rather than going `available: false`.

- **`ui.alert()` is dead code today** — defined at `store/index.js:27`, called nowhere in `src/`.

- **`store/index.js` carries no header docstring**, unlike its two siblings, which both open with the
  house title/underline/purpose block. A small convention deviation, noted so it gets fixed rather than
  copied.

- **`stageStatuses` is `reactive`, everything else is `ref`.** Reaching for `.value` on it in a store
  action is the mistake this asymmetry invites.

---

## 💥 8. FAILURE MODES

| Failure | Symptom | Store behaviour |
|---|---|---|
| Backend not running when the config page mounts | Provider pills read "No key" / "Offline" | `fetchProviders` swallows the error (`:206`, `:223`); state keeps its seed shape |
| Backend not running when the KB page mounts | Zeroed stats, empty KB list | `refreshStats` and `fetchKnowledgeBases` both swallow |
| Pipeline error mid-run | `error` set; tracker rows **freeze in place** | `onError` (`:160-164`) touches no stage; the frozen rows are the diagnostic |
| User cancels a run | `error = 'Query cancelled'`; rows freeze | `abortQuery` (`:169-173`) sets the message itself — the client suppresses `AbortError` |
| Corrupt `rag-chat-history` blob | History silently empty on next load | `_loadHistory`'s `try/catch` returns `[]` (`:57`) — no warning, no recovery |
| `localStorage` quota exceeded on save | Uncaught error after the answer renders | Unguarded `setItem` (`:61`) |
| An event arrives with an unknown `stage` | **Nothing** — dropped | The guard at `:99` returns silently |
| Upload of one file in a batch fails | That file's error lands in `uploadResult`; the queue continues | The store re-throws; the caller swallows deliberately |
| Delete or clear fails | The error propagates to the component | No try/catch on the three write actions |

The pattern: **reads fail quietly, writes fail loudly, and the pipeline's own failures are preserved
rather than cleaned up.**

---

## 🧩 9. EXTENSION POINTS

**Add a pipeline stage.** Append an entry to `STAGES` (`ragStore.js:16-25`) whose `id` is **byte-for-byte
the `stage` string the new node emits**, not the graph node name. `_initialStages()` picks it up
automatically, `PipelineTracker` iterates it, and `StageRow` renders it. If the stage should rewind on a
retry, add its id to the reset list at `:93` as well — the omission of `planner` there is a decision,
not an oversight.

**Add a chip to a stage row.** Nothing here needs changing: `details` already holds the entire event
payload (`:110`). Adding a chip is a one-line probe in `StageRow.vue` — see
[`../chat/pipeline-tracker.md`](../chat/pipeline-tracker.md).

**Add a new capability store.** Create `store/<abbrev>Store.js` and `services/<abbrev>Api.js` — two
files, flat, no folders. Use setup style, return only what components may touch, import exactly one
client, and decide the read-swallows / write-propagates policy explicitly (§5.5).

**Persist a new field.** Follow the `_loadHistory` / `_persistHistory` pair: a `try/catch` read at store
creation, an explicit write function, and a namespaced key (`rag-*`). Do not reach for a persistence
plugin for one field — there is none installed, and the two current keys do not justify one.

**What not to touch.** Do not move the `retry` branch below the stage guard — it carries no `stage` and
would be dropped. Do not remove the `retrieval_result` fall-through — it is the retrieval row's only
completion. Do not have a component import a service module: the single accepted exception is
`NavBar.vue:111`, and it is accepted because it predates and justifies the rule, not because the rule is
soft.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **Flat by kind for state and HTTP, by ownership for components.** Two placement rules that look
  inconsistent and are not. A store's identity is its domain, and a domain is one file — nesting it
  would create a folder that never gains a second member. A component's identity is *who uses it*, so
  moving it up to `shared/` is a meaningful event that a flat directory cannot express. The split is
  intentional, and merging the two rules is the most likely accidental regression in this tree.

- **Setup style everywhere.** The options API would make `_applyEvent` and `_persistHistory` public
  members with an underscore, enforced by nothing. Closure privacy is the reason this store can expose a
  25-entry public surface while carrying four genuinely internal helpers.

- **Reads swallow, writes propagate.** An error boundary per action rather than one global handler. It
  costs a repeated `try/catch` and buys a UI that degrades to a zero-state instead of an error page when
  the backend is simply not up yet — the normal case during development.

- **The answer is the persisted artifact, not the run.** History stores the finished result plus a stage
  snapshot, never the raw event log. That is why a restored run redraws instantly and why `events` is
  left alone on restore.

**Continue reading:**

- [`../api-clients/README.md`](../api-clients/README.md) — the two axios clients and the SSE stream reader
- [`../chat/pipeline-tracker.md`](../chat/pipeline-tracker.md) — the stage-id contract and the eight rows
- [`../chat/README.md`](../chat/README.md) — the page that consumes almost all of `ragStore`
- [`../knowledge-base/README.md`](../knowledge-base/README.md) — the page that consumes `kbStore`
- [`../../../Backend/Documentation/sse-event-bus/README.md`](../../../Backend/Documentation/sse-event-bus/README.md) — the server side of the stream
- [`../../../Backend/Documentation/api/query.md`](../../../Backend/Documentation/api/query.md) — every event type in full
