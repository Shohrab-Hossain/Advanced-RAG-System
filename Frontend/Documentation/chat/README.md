<div align="center">

# 💬 Chat Page

### One view, six components, and a sidecar convention that keeps every pure function out of the SFC.

<br>

[![Components](https://img.shields.io/badge/components-6-1c7ed6)](#-2-where-it-lives)
[![Sidecars](https://img.shields.io/badge/sidecar%20files-3-7c5cff)](#31-the-sidecar-file-pattern)
[![Manifest](https://img.shields.io/badge/manifest-package.json-3fb950)](../../package.json)

[![Store edges](https://img.shields.io/badge/components%20with%20no%20store-2-3fb950)](#33-container-and-presentational)
[![Answer render](https://img.shields.io/badge/answer-marked%20%2B%20v--html-f59e0b)](#52-rendering-the-answer)
[![XSS](https://img.shields.io/badge/sanitiser-none-ef4444)](#-9-security-note)

</div>

<br>

---

<br>

## Content Tree

<pre>
Chat Page
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│   ├── <a href="#11-the-four-states-of-the-page">1.1 The four states of the page</a>
│   └── <a href="#12-what-the-user-can-do">1.2 What the user can do</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-the-sidecar-file-pattern">3.1 The sidecar-file pattern</a>
│   ├── <a href="#32-render-order-and-its-conditions">3.2 Render order, and its conditions</a>
│   └── <a href="#33-container-and-presentational">3.3 Container and presentational</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-submitting-a-query">4.1 Submitting a query</a>
│   └── <a href="#42-reopening-a-past-run">4.2 Reopening a past run</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-queryinput--autogrow-and-the-keyboard-contract">5.1 QueryInput — autoGrow and the keyboard contract</a>
│   ├── <a href="#52-rendering-the-answer">5.2 Rendering the answer</a>
│   ├── <a href="#53-the-source-cards-and-the-detail-panel">5.3 The source cards and the detail panel</a>
│   └── <a href="#54-the-history-sidebar">5.4 The history sidebar</a>
│
├── <a href="#-6-wire-shape-cross-boundary-contracts">🔌 6. Wire shape (cross-boundary contracts)</a>
│
├── <a href="#%EF%B8%8F-7-edge-cases--gotchas">⚠️ 7. Edge cases &amp; gotchas</a>
│
├── <a href="#-8-failure-modes">💥 8. Failure modes</a>
│
├── <a href="#-9-security-note">🔒 9. Security note</a>
│
├── <a href="#-10-extension-points">🧩 10. Extension points</a>
│
└── <a href="#-11-related-decisions--deeper-reading">🔗 11. Related decisions &amp; deeper reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

The chat page is where a question becomes a cited answer. It is one view —
`pages/chat/views/ChatView.vue`, 130 lines — plus **six** components in `pages/chat/components/`, and it
owns almost no state of its own: everything meaningful lives on the `'rag'` store, which the SSE stream
writes into as the pipeline runs.

The page has one structural idea worth learning before anything else. **Pure, non-reactive material is
moved out of the single-file component into a same-folder `.js` sidecar** — a convention used three
times in this codebase and stated in each sidecar's own header. Anything touching a store, a `ref` or a
lifecycle hook stays in the `.vue`; anything that is a pure function of its arguments does not.

The one component large enough to deserve its own page — the pipeline tracker and its `StageRow`
satellite — is documented separately in
[`pipeline-tracker.md`](pipeline-tracker.md).

**Where this fits:** the state every component here reads is
[`../state/README.md`](../state/README.md); the stream that fills it is
[`../api-clients/README.md`](../api-clients/README.md).

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

### 1.1 The four states of the page

The page renders one of four shapes, and every condition is explicit in the template:

| State | Condition | What is on screen |
|---|---|---|
| **Empty** | `!isRunning && !hasResult && !error` | The 🔬 tile and six teaser chips naming the pipeline steps |
| **Running** | `store.isRunning` | The tracker with a spinner, a live progress bar, and a Cancel button on the input |
| **Answered** | `store.hasResult` | The answer card, the source grid, the tracker, and a collapsed metadata block |
| **Failed** | `store.error` | The tracker's error block, with every stage row frozen where it stopped |

A **corpus warning** sits above all four: when `!kb.hasDocuments && !store.isRunning`, a banner with a
`RouterLink` to `/knowledge-base` explains that nothing is indexed yet (`ChatView.vue:41-55`). It is the
only place the chat page touches the knowledge-base store.

### 1.2 What the user can do

- **Ask** — type into the textarea and press **`Ctrl+Enter`** (or `Cmd+Enter`), or click the button.
- **Cancel** — a Cancel button appears only while a run is in flight (`QueryInput.vue:45-48`).
- **Start from an example** — four suggestion chips appear when the page is idle and unanswered:
  *Summarize the key findings* · *What are the main risks?* · *Who are the key stakeholders?* ·
  *What recommendations are given?* (`QueryInput.vue:81-86`).
- **Inspect a source** — click any source card to open a detail panel with the full chunk text.
- **Copy the answer** — one button, which flips to *"✓ Copied"* for two seconds.
- **Reopen a past run** — the History button toggles a sidebar listing every saved run, newest first,
  with a count pill when there is at least one.
- **Read the raw metadata** — a collapsed `<details>` block dumps `store.metadata` as formatted JSON.

---

## 📍 2. WHERE IT LIVES

Paths are relative to `Frontend/src/pages/chat/`.

```text
pages/chat/
│
├── 📁 views/
│   ├── 📄 ChatView.vue          The page — layout, conditions, the History toggle. 130 lines
│   └── 📄 chatView.js           Sidecar: PIPELINE_STEPS, the six teaser chips. Pure
│
└── 📁 components/
    ├── 📁 ChatHistorySidebar/
    │   ├── 📄 ChatHistorySidebar.vue   The overlay list, with two confirm gates. 132 lines
    │   ├── 📄 chatHistorySidebar.js    Sidecar: formatTime. Pure
    │   └── 📄 chatHistorySidebar.css   Sidecar: the sidebar + backdrop transitions
    ├── 📁 QueryInput/
    │   └── 📄 QueryInput.vue           Textarea, auto-grow, keyboard submit, example chips. 113 lines
    ├── 📁 PipelineTracker/
    │   ├── 📄 PipelineTracker.vue      The eight rows, counter and progress bar. 74 lines
    │   └── 📄 StageRow.vue             SATELLITE — one row. 86 lines
    └── 📁 ResultDisplay/
        ├── 📄 ResultDisplay.vue        Answer card, badges, copy, source grid, detail panel. 131 lines
        └── 📄 SourceCard.vue           SATELLITE — one cited source. 66 lines
```

**`StageRow.vue` and `SourceCard.vue` are satellites**: each is used by exactly one component, so it
lives inside that component's folder rather than beside it. A component used by exactly one *page* lives
under that page; one used by a second page moves to `shared/components/`. Three components qualify for
`shared/` today, and this page consumes two of them — `FileTypeIcon` (in both `ResultDisplay` and
`SourceCard`) and `ModalDialog` (indirectly, through `ui.confirm`).

| Concern | Path | Anchor |
|---|---|---|
| Page layout and conditions | `views/ChatView.vue:2` | template root |
| Teaser chips | `views/chatView.js:16-23` | `PIPELINE_STEPS` |
| Submit + auto-grow | `components/QueryInput/QueryInput.vue:88`, `:101` | `autoGrow`, `submit` |
| Markdown rendering | `components/ResultDisplay/ResultDisplay.vue:116` | `renderedAnswer` |
| Source selection | `components/ResultDisplay/ResultDisplay.vue:110` | `toggleSource` |
| History list + confirms | `components/ChatHistorySidebar/ChatHistorySidebar.vue:107-129` | `loadHistory`, the two delete handlers |
| Relative timestamps | `components/ChatHistorySidebar/chatHistorySidebar.js:8-18` | `formatTime` |

---

## 🏗️ 3. ARCHITECTURE

### 3.1 The sidecar-file pattern

Three components in this codebase split pure material into a same-folder `.js` file whose camelCase name
matches its `.vue`. Two of the three are on this page:

| Component | Sidecar | Exports | The rule, quoted from its own header |
|---|---|---|---|
| `ChatView.vue` | `chatView.js` | `PIPELINE_STEPS` | *"Pure — no store, no refs, no lifecycle."* (`:4`) |
| `ChatHistorySidebar.vue` | `chatHistorySidebar.js` | `formatTime` | *"Pure formatting … no store, no refs, no lifecycle."* (`:4`) |
| `KnowledgeBaseView.vue` | `knowledgeBaseView.js` | five helpers | *"Everything here is a pure function of its arguments … Reactivity stays in the .vue."* (`:5-6`) |

**The rule in one line:** *pure, testable, non-reactive material moves out of the SFC; anything touching
a store, a ref or a lifecycle hook stays in it.*

The pattern extends to CSS once: `chatHistorySidebar.css` is consumed as
`<style scoped src="./chatHistorySidebar.css">` (`ChatHistorySidebar.vue:132`), keeping the transition
rules out of a file that is otherwise template and logic.

What this buys is not line count — `chatView.js` is 23 lines — but a clean answer to *"can I read this
without knowing Vue?"* for the part of the code that is really just data.

> [!NOTE]
> **`PIPELINE_STEPS` is not a second source of stage truth.** It is **six** teaser chips — Plan ·
> Retrieve · Rerank · Compress · Generate · Reflect — deliberately shorter than the eight real stages,
> and it drives nothing but the empty state. The eight-row contract is `STAGES` on the rag store; see
> [`pipeline-tracker.md`](pipeline-tracker.md). *(The comment beside `PIPELINE_STEPS` names the pipeline
> file as `graph.py`; the real file is `workflow.py` — a stale code comment, corrected here rather than
> repeated.)*

### 3.2 Render order, and its conditions

`ChatView.vue` owns exactly one local ref — `sidebarOpen` (`:129`) — and reads two stores, `useRagStore`
(`:118`) and `useKbStore` (`:119`). The page body is `max-w-7xl mx-auto px-6 sm:px-8 py-6` (`:2`).

| # | Element | Condition | Line |
|---|---|---|---|
| — | `<ChatHistorySidebar :open @close>` | **always mounted**; visibility is internal to it | `:4` |
| 1 | Header — 💬 icon, "Chat", subtitle, History toggle | always | `:10-38` |
| 2 | "No documents indexed yet" banner + link to `/knowledge-base` | `!kb.hasDocuments && !store.isRunning` | `:41-55` |
| 3 | `<QueryInput />` | always | `:58` |
| 4 | Empty state — 🔬 tile + the `PIPELINE_STEPS` chips | `!isRunning && !hasResult && !error` | `:61-86` |
| 5 | `<ResultDisplay />` | `store.hasResult` | `:89` |
| 6 | `<PipelineTracker />` | `isRunning \|\| hasResult \|\| error` | `:92` |
| 7 | `<details>` "Pipeline Metadata" — `JSON.stringify(store.metadata, null, 2)` | `store.hasResult` | `:95-110` |

**The answer renders above the tracker.** Once a run finishes the reader sees the result first and the
trace second — an ordering choice, since during the run the tracker is the only thing on screen anyway.

The History button (`:24-37`) toggles `sidebarOpen` and shows `store.chatHistory.length` as a pill
whenever it is non-zero.

### 3.3 Container and presentational

Five of the six components on this page read the store directly; the two satellites do not:

| Component | Props | Emits | Store |
|---|---|---|---|
| `ChatHistorySidebar` | `open` (Boolean, default `false`) | `close` | `rag`, `ui` |
| `QueryInput` | none | none | `rag` |
| `PipelineTracker` | none | none | `rag` |
| `ResultDisplay` | none | none | `rag` |
| **`StageRow`** | `stage` (Object), `status` (Object) | none | **none** |
| **`SourceCard`** | `source` (Object), `selected` (Boolean) | `select` | **none** |

The split is by **repetition**, not by size: `StageRow` and `SourceCard` are each rendered N times in a
loop, so making them read the store would mean N subscriptions to the same object. Props-in, emit-out
keeps them cheap and trivially testable. Everything rendered once reads the store directly rather than
threading props through a layer that adds nothing.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 Submitting a query

```text
user types           → QueryInput.localQuery (local ref, seeded from store.query)
Ctrl/Cmd+Enter       → submit()  → guard on empty / running
                                 → store.runQuery(localQuery.value)
store.runQuery       → resetPipeline() → all 8 rows idle, answer/sources/metadata cleared
                     → streamQuery(...)  → SSE frames
each frame           → store._applyEvent → stageStatuses[stage] mutates → StageRow re-renders
done frame           → store answer/sources/metadata → ResultDisplay appears above the tracker
                     → history entry unshifted and persisted (only if the answer is non-empty)
```

Two details of the hand-off are easy to assume wrongly:

- **`submit()` does not set `store.query`.** It calls `store.runQuery(localQuery.value)` and nothing
  else (`QueryInput.vue:101-104`); the store assigns `query` itself as its second statement.
- **`localQuery` is seeded from `store.query`** (`:78`) and re-synced by a `watch` (`:107-112`), so
  navigating away and back keeps the text, and loading a history entry retypes the textarea to match.

### 4.2 Reopening a past run

Clicking an entry in the sidebar calls `loadHistory(item)` (`ChatHistorySidebar.vue:107-111`): set the
local highlight, call `store.loadHistoryItem(item)`, then `emit('close')`.

The store restores the answer, sources, metadata, retry count **and the saved stage snapshot**, and sets
`isHistoryResult = true`. The visible consequence: the whole page redraws exactly as it looked when the
run finished, including all eight tracker rows, and the tracker swaps its spinner for a **"from
history"** pill. Nothing is re-fetched and no request is made.

`activeHistoryId` (`:98`) tracks the highlighted row. A `watch` on `store.chatHistory[0]?.id`
(`:101-105`) auto-highlights a newly-saved entry — but **only when `!store.isHistoryResult`**, so
reopening an old run does not steal the highlight for the newest one.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 `QueryInput` — autoGrow and the keyboard contract

**The problem:** a textarea should grow with its content, but the user is also allowed to drag-resize
it, and a naive auto-grow fights that by resetting the height on every keystroke.

```js
// src/pages/chat/components/QueryInput/QueryInput.vue:88
function autoGrow () {
  const el = textareaRef.value
  if (!el) return
  const next = Math.min(el.scrollHeight, 400)
  if (next > el.offsetHeight) el.style.height = `${next}px`
}
```

The `next > el.offsetHeight` comparison (`:91`) is the whole trick: the box only ever grows, **never
shrinks**, so a manual resize survives. The element is `rows="3"` with
`style="min-height:80px; max-height:400px"` and `resize-y` (`:23`), so the ceiling is enforced twice —
once in CSS, once in the `Math.min`.

**Submit is `Ctrl+Enter` or `Cmd+Enter`** (`:25-26`), plus the button (`:38`). A bare Enter inserts a
newline, which is the right default for a box people paste paragraphs into. The `⌃↵` hint pill sits in
the textarea's corner (`:28-31`) so the shortcut is discoverable without a tooltip.

`submit()` (`:101-104`) guards on empty text and on `store.isRunning` — the same guard the store applies
independently, so a double-submit is impossible from either side.

### 5.2 Rendering the answer

The answer is Markdown, and `ResultDisplay` renders it in one computed:

```js
// src/pages/chat/components/ResultDisplay/ResultDisplay.vue:116
const renderedAnswer = computed(() => {
  try { return marked.parse(store.answer) } catch { return store.answer }
})
```

The result is injected with **`v-html`** into a `.prose-rag` container (`:31`), which is the twelve-rule
Markdown stylesheet defined in `main.css` (see [`../design-system/README.md`](../design-system/README.md)).
The `try/catch` fallback means a parse failure degrades to raw text rather than a blank card.

**The security implications of that `v-html` are covered in [§9](#-9-security-note) and are not
incidental — read them.**

Around the answer sit three metadata badges (`:9-27`), each rendered only when its key is present on
`store.metadata`:

| Badge | Rendering |
|---|---|
| `grounded` | emerald ✓ when true, teal ⚠ when false |
| `confidence` | `Math.round(x * 100)` as a percentage |
| `retry_count` | the number with correct pluralisation — *retry* / *retries* |

The copy button (`:34-36`, `:121-125`) uses `navigator.clipboard.writeText` and flips its own label to
*"✓ Copied"* for 2 000 ms.

### 5.3 The source cards and the detail panel

The sources card renders only when `store.sources.length` (`:41`), is collapsible via `sourcesOpen`
(default **open**, `:102`), and lays out `sm:grid-cols-2` (`:54`) keyed by `src.index` (`:56`).

**`SourceCard`** consumes exactly the fields the backend puts on a cited source:

| Field | Rendered as | Line |
|---|---|---|
| `index` | the `[1]` badge | `:12` |
| `file_name` | the card title | |
| `source_type` | a tag — `vector` → *Vector*, `bm25` → *BM25*, `graph` → *Graph*, `web` → *Web*, anything else verbatim | `:50`, `:52` |
| `content_preview` | the body, `line-clamp-3` | `:26` |
| `page` | `· p. N`, when present | `:31` |
| `url` | an external link, `target="_blank" rel="noopener"`, with `@click.stop` so it does not toggle the card | `:32-34` |
| `rerank_score` | `toFixed(3)`, or **`—` when null** | `:55-58` |

> The field is **`source_type`**, not `source` — it matches the backend's key on the cited-source object.

`scoreClass` (`:60-65`) tints the score emerald above a threshold and muted stone below it. **The
`rerank_score` can legitimately be negative** — it is a raw cross-encoder logit, not a probability — and
a negative score lands in the muted band, which is correct. *(As a code note: the `> 5` and `> 2`
branches return the identical class string, so the `> 5` branch is dead. The effective rule is emerald
above 2.)*

**Selection is by identity, not index.** `selectedSource` (`:103`) holds the source *object*, and
`toggleSource` (`:110-112`) compares by identity so clicking the open card closes it. A `watch` on
`store.sources` (`:108`) clears the selection whenever a new run lands, so a stale panel cannot survive
into the next answer.

The detail panel (`:64-87`) shows a `FileTypeIcon`, the label
(`file_name || url || 'Source'`, `:105-106`), an optional page number and a close ✕. Its body is a
`<pre>` of **`selectedSource.content || selectedSource.content_preview`** (`:85`) — the full chunk
preferred, the preview as fallback — in a `max-h-80 overflow-y-auto whitespace-pre-wrap` box.

### 5.4 The history sidebar

The sidebar is a two-part overlay: a fixed backdrop that closes on click (`:3-7`), and an `<aside>`
positioned **inside a `max-w-7xl mx-auto` wrapper** (`:11-12`) so its left edge aligns with the page
content rather than the viewport edge. It is `w-72` wide and starts at `top-14`, clearing the navbar.

The wrapper is `pointer-events-none` with the aside `pointer-events-auto` (`:11`, `:15`), so the
invisible full-width layer never swallows clicks meant for the page underneath. That pairing is the only
reason a full-width positioning wrapper is safe here.

Two destructive actions, both gated by `ui.confirm` with `danger: true`:

| Action | Line | Prompt | Buttons |
|---|---|---|---|
| Delete one entry | `:113-120` | *"Delete this chat from history?"* | *Yes, delete it* / *No, keep it* |
| Clear all | `:122-129` | *"Delete all chat history? This cannot be undone."* | *Yes, delete it* / *No, keep it* |

Affirmative button text rather than *OK/Cancel* is a small thing that makes a destructive dialog
readable at a glance. The per-item ✕ is `opacity-0 group-hover:opacity-100` with `@click.stop`
(`:69-75`), so it never fires the row's load handler.

**`formatTime`** (`chatHistorySidebar.js:8-18`) is four bands:

| Age | Output |
|---|---|
| under 1 minute | `Just now` |
| under 60 minutes | `12m ago` |
| under 24 hours | `3h ago` |
| older | `Mar 4` — `toLocaleDateString(undefined, { month: 'short', day: 'numeric' })` |

Passing `undefined` as the locale means the browser's own locale is used, so the date format follows the
user's system rather than being pinned to one region.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

This page issues exactly one request — `POST /api/query` — and everything else it renders is the
consequence of that stream.

**Outbound**, assembled by the store from the config page's selections:

```json
{ "query": "What are the main risks?", "provider": "openai", "model": "gpt-4o-mini" }
```

`model` is omitted entirely when no model is chosen, and it is honoured for **both** providers.

**Inbound**, the `done` payload — the only frame this page's answer half reads:

| Key | Shape | Consumed by |
|---|---|---|
| `answer` | Markdown string | `renderedAnswer` → `v-html` |
| `sources` | array of `{ index, file_name, source_type, url, page, rerank_score, content_preview, content }` | `SourceCard` and the detail panel |
| `metadata` | object — includes `grounded`, `confidence`, `retry_count` | the three badges and the `<details>` dump |

The stage-level frames belong to the tracker and are documented in
[`pipeline-tracker.md`](pipeline-tracker.md). The full server-side event catalogue is
[`../../../Backend/Documentation/api/query.md`](../../../Backend/Documentation/api/query.md).

**Local persistence.** Every finished run with a non-empty answer is appended to
`localStorage['rag-chat-history']`, newest first, and the write is capped at fifty entries — the exact
contract, including what the cap does and does not do, is in
[`../state/README.md`](../state/README.md).

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **A run that produces no answer is not saved.** The history unshift is conditional on
  `result.answer` being truthy, so an errored or empty run leaves no trace in the sidebar.

- **The sidebar can list more entries than a reload will keep.** The fifty-entry cap applies to the
  write, not the in-memory array — so a long session shows more than fifty, and a reload silently drops
  the excess.

- **The textarea never shrinks on its own.** By design (§5.1), but it means a user who pastes and then
  deletes a long block is left with a tall box until they drag it back.

- **`QueryInput` reads `store.query`, which the store sets from the trimmed text** — while the *request*
  carries the untrimmed original. Harmless, since the server strips it, but the two are not the same
  string.

- **The source detail panel prefers `content` over `content_preview`.** For a web result those can
  differ substantially, and the full `content` for a document chunk is the entire indexed passage.

- **`FileTypeIcon` renders an extension pill, not a generic icon, for an unknown type with a filename.**
  It uppercases the first four characters of the extension. The generic file glyph appears only when
  there is neither a recognised type nor a filename to fall back on.

- **The tracker stays mounted after a run finishes.** Its condition is
  `isRunning || hasResult || error`, so the trace remains readable next to the answer rather than
  vanishing at the moment it becomes interesting.

- **The metadata `<details>` block is a raw JSON dump.** It is deliberately unstyled and unparsed — a
  debugging affordance, not a designed surface.

---

## 💥 8. FAILURE MODES

| Failure | What the user sees | Where it is handled |
|---|---|---|
| No documents indexed | A banner above the input with a link to the knowledge-base page | `ChatView.vue:41-55` |
| Empty submission | Nothing — the button is disabled and `submit()` returns early | `QueryInput.vue:101` |
| Pipeline error mid-run | The tracker's error block; **every stage row frozen where it stopped** | the store leaves `stageStatuses` untouched on error |
| User cancels | *"Query cancelled"* in the error block; rows frozen | `abortQuery` → the client's abort |
| Markdown that fails to parse | The raw answer text, unstyled | the `try/catch` in `renderedAnswer` |
| Clipboard write denied | The label simply does not change | no catch — the promise rejects unobserved |
| A source with no `rerank_score` | `—` in the score slot | `scoreLabel`'s null branch |
| A corrupt history blob in `localStorage` | An empty sidebar, silently | the store's load `try/catch` |

The consistent theme: **failures degrade the surface rather than replacing it.** There is no error page
on this route and no toast system — the tracker's frozen rows *are* the error report.

---

## 🔒 9. SECURITY NOTE

> [!CAUTION]
> **The answer is rendered with `v-html`, and nothing sanitises it.** `marked` v12 ships **no sanitiser
> by default**, and `renderedAnswer` (`ResultDisplay.vue:116-119`) feeds its output straight into
> `v-html` at `:31`.
>
> The answer text is model output derived from documents the user uploaded. A crafted document can carry
> prompt-injection content through retrieval into the reasoning prompt, and from there into the answer —
> and any HTML in that answer lands in the DOM. The same unescaped-input decision runs through the whole
> backend: query text, retrieved chunks and web-search results are interpolated straight into every
> prompt, including the reflection prompt that judges grounding.
>
> This is an **accepted, documented, localhost-only risk**. It is safe only for the deployment this
> project actually targets: a single user, on their own machine, indexing their own documents. Combined
> with the backend's other accepted risks — a literal `"*"` in the CORS allowlist, the Werkzeug debugger
> on by default, and **no authentication on any route** — exposing this beyond localhost is a remote
> compromise, not a hardening exercise. Do not widen it, and do not treat the `try/catch` around
> `marked.parse` as a security control; it is a rendering fallback.

---

## 🧩 10. EXTENSION POINTS

**Add a metadata badge.** One `v-if` on `store.metadata.<key>` in `ResultDisplay.vue:9-27`, following
the existing three. The metadata object arrives whole from the `done` frame, so no plumbing is needed.

**Add a field to a source card.** `SourceCard.vue` receives the entire source object as one prop; add
the markup and a `v-if`. Adding a field on the *server* side needs no frontend change until you want to
render it.

**Add a component to this page.** New folder under `pages/chat/components/<Name>/<Name>.vue`. If it is
used by exactly one existing component, nest it inside that component's folder as a satellite instead —
the way `StageRow` and `SourceCard` are. If a **second page** starts importing it, move it to
`shared/components/<Name>/`, which is the event that promotion is meant to mark.

**Add a pure helper.** Put it in the sidecar, not the SFC, if it is a pure function of its arguments.
Create a sidecar if the component does not have one yet, and open it with the same header the existing
three use.

**Sanitise the answer.** The single highest-value change on this page: install a sanitiser and pipe
`marked.parse` output through it inside `renderedAnswer`. That is a one-function change at
`ResultDisplay.vue:116` and it closes the DOM half of the injection path — the prompt half stays open
by design.

**What not to touch.** Do not make `submit()` write `store.query` — the store owns that assignment. Do
not give `StageRow` or `SourceCard` a store import; the props boundary is what keeps N-times-rendered
components cheap. Do not move the auto-grow logic to shrink as well as grow without deciding what
happens to a manual resize.

---

## 🔗 11. RELATED DECISIONS & DEEPER READING

- **The sidecar convention.** Splitting pure material out of an SFC costs a file and buys a clean
  boundary: the sidecar is plain JavaScript that can be read, reasoned about and tested without a
  component harness. It is applied where the material is genuinely pure and nowhere else, which is why
  there are three sidecars rather than one per component.

- **Answer above trace.** The tracker is the whole story while a run is in flight and a footnote
  afterwards. Ordering the finished view answer-first accepts a layout jump at the moment of completion
  in exchange for putting the thing the user asked for at the top.

- **History as a snapshot, not a replay.** An entry stores the finished answer plus a deep clone of the
  stage statuses. Reopening it redraws instantly with no network call — and, deliberately, cannot
  re-run: a restored view is a record, not a resumable session.

- **Errors freeze rather than clear.** Leaving `stageStatuses` untouched on failure means the last
  successful stage is still visible, which turns "it broke" into "it broke at the reranker". That is the
  single most useful debugging affordance on the page and it costs one *absent* line of code.

**Continue reading:**

- [`pipeline-tracker.md`](pipeline-tracker.md) — the eight rows, the chips, and the stage-id contract
- [`../state/README.md`](../state/README.md) — the `'rag'` store this page is a view onto
- [`../api-clients/README.md`](../api-clients/README.md) — how the frames reach the store
- [`../design-system/README.md`](../design-system/README.md) — `.card`, `.prose-rag` and the animations used here
- [`../../../Backend/Documentation/api/query.md`](../../../Backend/Documentation/api/query.md) — the request and every event it can produce
- [`../../../Backend/Documentation/rag-pipeline/README.md`](../../../Backend/Documentation/rag-pipeline/README.md) — what actually happens between submit and answer
