<div align="center">

# 📡 Pipeline Tracker

### Eight rows driven by eight string ids that must match the server byte-for-byte — and five of those eight are not the graph node names.

<br>

[![Rows](https://img.shields.io/badge/stage%20rows-8-1c7ed6)](#51-the-eight-rows)
[![Statuses](https://img.shields.io/badge/statuses-5-7c5cff)](#52-the-five-statuses)
[![Detail chips](https://img.shields.io/badge/detail%20chips-8-f59e0b)](#53-the-detail-chips)

[![Stage ids ≠ node names](https://img.shields.io/badge/stage%20ids%20%E2%89%A0%20node%20names-5%20of%208-ef4444)](#-3-the-stage-id-contract)
[![Retry cap](https://img.shields.io/badge/passes-3%20max-3fb950)](#42-the-retry-re-animation)

</div>

<br>

---

<br>

## Content Tree

<pre>
Pipeline Tracker
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#-3-the-stage-id-contract">🔒 3. The stage-id contract</a>
│   ├── <a href="#31-the-mapping">3.1 The mapping</a>
│   └── <a href="#32-why-it-fails-silently">3.2 Why it fails silently</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-one-clean-pass">4.1 One clean pass</a>
│   └── <a href="#42-the-retry-re-animation">4.2 The retry re-animation</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-the-eight-rows">5.1 The eight rows</a>
│   ├── <a href="#52-the-five-statuses">5.2 The five statuses</a>
│   ├── <a href="#53-the-detail-chips">5.3 The detail chips</a>
│   └── <a href="#54-progress-arithmetic">5.4 Progress arithmetic</a>
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

The pipeline tracker is the reason this project streams instead of returning a single JSON response. It
renders eight rows — one per pipeline stage — and animates them live as the server works, so a query
that takes twenty seconds shows *what* it is doing for those twenty seconds rather than a spinner.

It is two components, 160 lines together, and it holds **no state of its own**. `PipelineTracker.vue`
iterates the exported `STAGES` array and hands each entry plus its current status to a `StageRow`;
`StageRow.vue` is a pure presentational leaf with two props and no store import at all. Everything the
tracker displays was written into `stageStatuses` by the store's event dispatcher.

The whole feature rests on one fact, and it is the fact this page exists to make unmissable: **the eight
row ids are the `stage` strings the server emits, and five of those eight differ from the LangGraph node
names.**

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

During a run the user sees, from top to bottom:

- A **"Pipeline"** section label, with a spinning ring while the run is in flight.
- A **"Retry N"** pill in teal, whenever the reflection agent has sent the pipeline round again.
- A **counter** reading e.g. `3/8` while running — the number, no word after it.
- A **progress bar** that fills as stages finish and turns from teal to emerald on completion.
- **Eight rows**, each with a status glyph, a label, a one-line message and — once complete — a row of
  small grey chips carrying whatever numbers that stage reported.
- An **error block** below them if the run failed.

After the run the tracker stays on screen beneath the answer. Reopening a past run from the history
sidebar redraws all eight rows from the saved snapshot and swaps the spinner for a **"from history"**
pill.

The rows are not decorative: a stage that is skipped says so, a stage that failed says why, and the
chips report the real counts — how many vectors matched, how many web results came back, how far the
context was compressed, whether the answer was judged grounded.

---

## 📍 2. WHERE IT LIVES

Paths are relative to `Frontend/src/`.

| Concern | Path | Anchor |
|---|---|---|
| The eight-row display contract | `store/ragStore.js:16-25` | `STAGES` |
| Per-stage status record | `store/ragStore.js:43` | `stageStatuses` |
| Event → status dispatch | `store/ragStore.js:84-125` | `_applyEvent` |
| The retry branch | `store/ragStore.js:87-96` | *(before the stage guard)* |
| Container, counter, bar | `pages/chat/components/PipelineTracker/PipelineTracker.vue` | 74 lines |
| One row | `pages/chat/components/PipelineTracker/StageRow.vue` | 86 lines |

```text
pages/chat/components/PipelineTracker/
│
├── 📄 PipelineTracker.vue   Card, spinner, retry pill, counter, progress bar, 8 rows, error block
└── 📄 StageRow.vue          SATELLITE — one row: glyph, label, message, detail chips
```

`StageRow.vue` sits **inside** `PipelineTracker/` rather than beside it, because exactly one component
uses it. That is the satellite rule, and it is what stops `components/` filling up with names that only
mean something next to their parent.

---

## 🔒 3. THE STAGE-ID CONTRACT

### 3.1 The mapping

**An SSE `stage` id is not the graph node name. Five of the eight differ.**

| Graph node (`workflow.py`) | Emitted `stage` id | Same? |
|---|---|---|
| `planner` | `planner` | ✅ |
| `retrieval` | `retrieval` | ✅ |
| `external_tools` | `external_tools` | ✅ |
| `aggregate` | **`aggregator`** | ❌ |
| `rerank` | **`reranker`** | ❌ |
| `compress` | **`compressor`** | ❌ |
| `reason` | **`reasoning`** | ❌ |
| `reflect` | **`reflection`** | ❌ |

The right-hand column is what `STAGES` (`ragStore.js:16-25`) contains, and today the two sets match
exactly.

> [!CAUTION]
> **The `emit()` call sites are the contract, not the workflow file.** Renaming a graph node breaks
> nothing on this page — the node name never crosses the wire. Changing an `emit(...)` `stage` value
> silently stops the matching row updating, forever, with no error anywhere.
>
> The reason it is silent is one line in the store:
>
> ```js
> // src/store/ragStore.js:99
> if (!stage || !(stage in stageStatuses)) return
> ```
>
> An event whose stage is not one of the eight keys is **dropped without a warning**. That guard is
> correct — it is what keeps a pipeline-level event from corrupting a row — but it also means a
> mismatched id produces a row that simply never moves. Anyone renaming a stage must change the emit
> site and `STAGES` in the same commit.

### 3.2 Why it fails silently

The asymmetry is worth stating plainly, because it inverts the usual intuition that the graph definition
is the source of truth:

| Change | Consequence |
|---|---|
| Rename a node in `workflow.py` | **Nothing.** The node name is internal to the graph. |
| Change an `emit(...)` `stage` value | That row freezes at `idle` for every future run. Silent. |
| Add a stage to `STAGES` with an id nobody emits | A permanently idle ninth row, and the counter's denominator grows. |
| Remove a stage from `STAGES` that is still emitted | Its events are dropped by the guard; the pipeline runs fine and the UI never mentions it. |

Only `planner`, `retrieval` and `external_tools` coincide across both naming schemes — which is exactly
why `external_tools` was for a long time the example used to state the rule, and why the rule read as
true when it was not.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 One clean pass

```text
runQuery()        → resetPipeline()   → all 8 rows { status: 'idle', message: '', details: null }
stage_start       → that row 'active' → spinning ring, emerald label, message from data.message
stage_complete    → that row 'complete' → ✓, chips built from the whole payload
retrieval_result  → the retrieval row 'complete'  (its ONLY completion — see below)
stage_skip        → that row 'skipped'  → –, opacity-35
stage_error       → that row 'error'    → ✗, red tint, message from data.error
finalize          → that row 'complete' → message defaults to 'Done'
done              → intercepted by the client; the tracker stops changing
```

> [!IMPORTANT]
> **`retrieval_result` is the retrieval row's only completion.** The retrieval node never emits
> `stage_complete`; it emits its own richer event carrying the three per-store counts. The store handles
> this with a deliberate `switch` fall-through that gives `stage_complete` and `retrieval_result` one
> shared body (`ragStore.js:106-111`). Remove that fall-through and the retrieval row spins `active` for
> the rest of the run while everything else completes around it.

### 4.2 The retry re-animation

This is the tracker's most interesting behaviour and the best worked example of the whole event system.
When the reflection agent judges an answer insufficiently grounded, it sends the pipeline round again —
and the tracker has to *rewind* rather than start over.

1. The reflection node decides to retry and emits a **`retry`** event carrying `attempt`,
   `max_attempts`, `reason`, `escalate_external` and `message` — **and deliberately no `stage` key**,
   because it is a pipeline-level event, not a stage-level one.
2. The HTTP client sees a type that is not `done`, `stream_end` or `error`, so it falls through to
   `onEvent('retry', data)`.
3. The store catches it **before the stage guard** and returns early:

   ```js
   // src/store/ragStore.js:87
   if (type === 'retry') {
     retryCount.value = (data.attempt || 1) - 1
     ;['retrieval', 'external_tools', 'aggregator', 'reranker', 'compressor', 'reasoning', 'reflection']
       .forEach((s) => { stageStatuses[s] = { status: 'idle', message: '', details: null } })
     return
   }
   ```

4. `PipelineTracker.vue:18-24` renders the **"Retry N"** pill; `completedCount` drops, so the progress
   bar **rewinds**; the seven reset rows revert to their idle emoji and re-animate as the second pass
   emits.
5. The loop is capped by the server at two additional attempts, so **three passes maximum**.

Three details that are exactly this way for a reason:

- **`retryCount` is assigned, not incremented.** The server's `attempt` numbers the pass about to begin,
  so `attempt - 1` is the number of retries *already spent* — which is what the pill should read.
- **The reset list is seven stages and excludes `planner`.** The planner does not run again, so its row
  correctly keeps its completed state while everything after it rewinds.
- **There is no `case 'retry':` in the switch.** It cannot be one: the switch runs after a guard that
  would have already dropped the event.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 The eight rows

`PipelineTracker.vue` reads `useRagStore` and the exported `STAGES` (`:59`) and renders:

| Element | Condition | Line |
|---|---|---|
| `.card` wrapper with a `section-label section-label-amber` "Pipeline" | always | `:2`, `:6` |
| Spinner — an `animate-spin` ring | `store.isRunning` | `:7-8` |
| "from history" pill | `isHistoryResult && !isRunning` | `:9-15` |
| "Retry N" pill, teal | `store.retryCount > 0` | `:18-24` |
| `{{ completedCount }}/{{ STAGES.length }}` counter | `store.isRunning` | `:25-28` |
| Progress bar | `isRunning \|\| hasResult` | `:33-38` |
| **8 × `<StageRow>`**, keyed by `stage.id` | always | `:42-43` |
| Error block | `store.error` | `:47-53` |

Each row receives two props (`StageRow.vue:39`): `stage` — one `STAGES` entry, giving the label, icon
and static description — and `status` — the `{ status, message, details }` record for that id. It emits
nothing and imports no store.

`const s = computed(() => props.status.status)` (`:40`) is the single switch every class map keys on.

### 5.2 The five statuses

The vocabulary is exactly five values, and each has a distinct glyph (`StageRow.vue:5-10`):

| Status | Glyph | Row treatment |
|---|---|---|
| `active` | a **spinning ring** — `border-t-transparent rounded-full animate-spin` | emerald tint, emerald message text |
| `complete` | `✓` | emerald tint, muted message, chips visible |
| `error` | `✗` | red tint |
| `skipped` | `–` | **`opacity-35`** — the whole row dims |
| `idle` *(fallback)* | **`stage.icon`** — the emoji from `STAGES` | neutral |

The idle fallback is what makes an untouched tracker readable rather than blank: before a run starts,
each row shows its own emoji and its static `desc` string.

Four computed class maps drive the styling, each an object of `class: boolean` pairs — `rowClass`
(`:42-47`), `iconBg` (`:49-57`), `labelClass` (`:59-65`) and `msgClass` (`:67-70`).

> [!NOTE]
> **`iconBg` declares one combined `active || complete` key** (`:53-54`). It previously declared the same
> class string under two separate keys, which is a duplicate-key error: the second silently won, and an
> *active* stage rendered with no icon background at all. The combined key is the fix, and the comment
> above it names the old defect so it does not come back.

The message line (`:22-24`) renders `status.message || stage.desc` — so a row that has not spoken yet
shows its static description instead of an empty gap. It is `truncate`d to a single line.

### 5.3 The detail chips

Chips render **only when the row is `complete`** (`:26-31`, `:72-85`), and they are built from
`props.status.details` — which is the *entire* event payload the store stashed there. The component
probes eight keys with `!= null` and renders the ones present:

| Payload key | Rendered as | Arrives on |
|---|---|---|
| `vector_count` | `142 vector` | `retrieval_result` |
| `bm25_count` | `142 BM25` | `retrieval_result` |
| `graph_count` | `27 graph` | `retrieval_result` |
| `web_count` | `5 web` | the `external_tools` `stage_complete` — **not** `retrieval_result` |
| `top_k` | `top 5` | the `reranker` `stage_complete` |
| `confidence` | `87% conf.` — `Math.round(x * 100)` | `reasoning` / `reflection` `stage_complete` |
| `grounded` | `grounded ✓` **or** `ungrounded` | the `reflection` `stage_complete` |
| `ratio` | `62% size` — `Math.round(x * 100)` | the `compressor` `stage_complete` |

Two precise points:

- **The compression key is `ratio`**, not `compression_ratio`. It matches what the compressor node
  emits.
- **All chips render in the same muted stone pill** (`:28-30`). `grounded` is *not* colour-coded green
  or red here — the colour distinction between grounded and ungrounded exists only on the answer badge
  in `ResultDisplay`.

**`details` holds far more than eight keys.** Payloads across the pipeline also carry `retrieve`,
`use_external`, `query_type`, `reasoning`, `before`, `after`, `sources`, `scores`, `original_chars`,
`compressed_chars`, `is_sufficient`, `key_facts`, `issues`, `will_retry` and `escalate_external`. The
eight probes are a deliberate editorial subset, not the limit of what is available — which is what makes
adding a chip a one-line change with no backend work at all.

### 5.4 Progress arithmetic

Two computeds, and both encode a judgement:

```js
// src/pages/chat/components/PipelineTracker/PipelineTracker.vue:64
const completedCount = computed(() =>
  STAGES.filter((s) => ['complete', 'skipped'].includes(store.stageStatuses[s.id]?.status)).length
)
```

**A skipped stage counts as progress.** That is right, not a shortcut: `retrieval` and `external_tools`
are legitimately skippable — the planner can decide a question needs no retrieval, and web search is
opt-in — so a run that skips two stages is not a run that is 25 % stuck.

```js
// src/pages/chat/components/PipelineTracker/PipelineTracker.vue:68
const progressPct = computed(() => {
  if (store.hasResult) return 100
  const active = STAGES.some((s) => store.stageStatuses[s.id]?.status === 'active')
  return Math.round(((completedCount.value + (active ? 0.5 : 0)) / STAGES.length) * 100)
})
```

**An active stage counts as half.** The bar therefore advances the moment a stage *starts*, not only
when it finishes — which matters because the slowest stages (reranking, reasoning) are exactly the ones
where a stationary bar reads as a hang. `hasResult` short-circuits to `100` so the bar cannot end at
94 % after a run that skipped something.

The bar's colour flips from teal to emerald on completion (`:36`), and the counter renders as `3/8` with
**no word after it**.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

The tracker consumes six of the ten wire types, all of them stage-level:

| Type | Carries | Effect |
|---|---|---|
| `stage_start` | `stage`, `message` | row → `active` |
| `stage_complete` | `stage`, `message`, plus stage-specific counters | row → `complete`, chips built |
| `retrieval_result` | `stage`, `message`, `vector_count`, `bm25_count`, `graph_count` | the retrieval row's only completion |
| `stage_skip` | `stage`, `message` | row → `skipped` |
| `stage_error` | `stage`, **`error`** | row → `error` |
| `finalize` | `stage`, `message` | row → `complete` |

Plus **`retry`**, out of band, carrying no `stage` at all.

Note the payload asymmetry: **`stage_error` puts its human text under `error`; every other type uses
`message`.** The store reads accordingly (`ragStore.js:118` versus `:104`, `:109`, `:114`, `:122`).

The remaining four types never reach this component: `done`, `error` and `stream_end` are intercepted by
the HTTP client, and the fourth route-framed type never enters the stage machinery. Full payload
specifications for all ten are in
[`../../../Backend/Documentation/api/query.md`](../../../Backend/Documentation/api/query.md); the
producing side is [`../../../Backend/Documentation/sse-event-bus/README.md`](../../../Backend/Documentation/sse-event-bus/README.md).

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **A mismatched stage id produces a permanently idle row, not an error.** This is the single most
  important thing on this page (§3.2).

- **A skipped stage advances the bar.** Intentional, but it means `6/8` does not imply six stages did
  work.

- **The counter only renders while running**, so a finished run shows the bar at 100 % with no `8/8`
  beside it.

- **Chips appear only on `complete`.** A stage that errors has a message but never chips, even if its
  payload carried counters.

- **`details` is a frontend-invented field.** No wire payload has a `details` key — the store assigns
  the whole event object into it. Looking for `details` in the backend will find nothing.

- **A retry rewinds the bar.** Watching the percentage go backwards is correct behaviour, not a
  glitch — the pipeline genuinely re-ran seven of its eight stages.

- **The planner row survives a retry.** Deliberate: it does not re-run.

- **On error, every row freezes where it stood.** The store's error handler does not touch
  `stageStatuses`, so the last completed stage is still visible. That frozen state *is* the diagnostic.

- **A history entry written before stage snapshots existed renders all eight rows as generic
  "Pipeline completed"** — the store's per-stage fallback, chosen so an old entry reads as old rather
  than broken.

---

## 💥 8. FAILURE MODES

| Failure | Tracker behaviour |
|---|---|
| A stage emits an id not in `STAGES` | The event is dropped at the store's guard; that row stays `idle` for the whole run |
| A stage errors | `✗`, red tint, `data.error` as the message; **all other rows keep their state** |
| The stream dies mid-run | Every row freezes; no terminal event ever arrives, so nothing resets |
| The user cancels | Same freeze; the error block reads *"Query cancelled"* |
| A malformed frame | Discarded in the client before it reaches the store — the tracker never sees it |
| More than eight stages emitted | Extra ids are dropped by the guard; the counter denominator stays at `STAGES.length` |
| `retrieval_result` never arrives | The retrieval row hangs `active` — it has no other completion path |

---

## 🧩 9. EXTENSION POINTS

**Add a chip.** One `!= null` probe in `StageRow.vue:72-85`, following the existing eight. The payload
key is already in `details`; no backend or store change is needed unless the server does not yet emit
the value.

**Add a stage row.** Append to `STAGES` (`ragStore.js:16-25`) with `id` set to **exactly the string the
new node emits** — not the graph node name. `_initialStages()`, the tracker's iteration and the counter
denominator all follow automatically. Decide explicitly whether the new stage belongs in the retry reset
list at `ragStore.js:93`.

**Colour-code a chip.** The chip markup is one shared muted pill (`:28-30`); a per-key class map beside
the existing four computeds would be the natural shape, matching how `rowClass` and `iconBg` are built.

**Show more of `details`.** Everything the pipeline emits is already there. An expandable per-row panel
dumping `props.status.details` would need no plumbing at all — the data is sitting unused.

**What not to touch.** Do not move the `retry` handling into the switch; it would be unreachable behind
the stage guard. Do not remove the `retrieval_result` fall-through. Do not give `StageRow` a store
import — it is rendered eight times and the props boundary is what keeps that cheap. Do not "simplify"
`iconBg` back into separate `active` and `complete` keys.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **Stage ids as an independent naming scheme.** The emitted ids read as *agents* — `aggregator`,
  `reranker`, `compressor`, `reasoning`, `reflection` — while the graph nodes read as *verbs*. The UI
  labels people, the graph labels operations, and the wire carries the UI's vocabulary. It is defensible
  and it is also the single most-broken assumption about this system, which is why the contract is
  stated three times across these docs rather than once.

- **A skipped stage counts as done.** The alternative — treating skips as incomplete — would make a
  perfectly healthy no-retrieval run look stalled at 75 %. The cost is that the counter measures
  *stages resolved*, not *work performed*.

- **Half-credit for an active stage.** A bar that only moves on completion sits still through the two
  slowest stages in the pipeline. Half-credit trades numerical honesty for the thing a progress bar is
  actually for: evidence of motion.

- **A stateless row component.** `StageRow` could read the store and take one prop instead of two. Eight
  store subscriptions instead of one, in exchange for a shorter parent template — the wrong trade, and
  the same reasoning that keeps `SourceCard` stateless.

**Continue reading:**

- [`README.md`](README.md) — the chat page this component sits on
- [`../state/README.md`](../state/README.md) — `STAGES`, `stageStatuses` and the event dispatcher
- [`../api-clients/README.md`](../api-clients/README.md) — how a frame becomes an `onEvent` call
- [`../../../Backend/Documentation/api/query.md`](../../../Backend/Documentation/api/query.md) — every event payload in full
- [`../../../Backend/Documentation/rag-pipeline/nodes.md`](../../../Backend/Documentation/rag-pipeline/nodes.md) — the eight nodes behind the eight rows
