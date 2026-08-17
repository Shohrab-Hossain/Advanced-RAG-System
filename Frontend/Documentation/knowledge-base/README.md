<div align="center">

# 📚 Knowledge Base Page

### A view-model container, three presentational children, a sequential upload queue — and a duplicate check that asks a different question than the server does.

<br>

[![Components](https://img.shields.io/badge/components-3-1c7ed6)](#-2-where-it-lives)
[![Zero-store children](https://img.shields.io/badge/children%20with%20no%20store-2%2F3-7c5cff)](#31-the-view-model-pattern)
[![Manifest](https://img.shields.io/badge/manifest-package.json-3fb950)](../../package.json)

[![Accepted types](https://img.shields.io/badge/accepted%20extensions-35-f59e0b)](#52-accept_attr-and-what-it-does-not-do)
[![Client dedup](https://img.shields.io/badge/client%20dedup-filename-ef4444)](#53-the-dedup-mismatch)
[![Server dedup](https://img.shields.io/badge/server%20dedup-content%20MD5-ef4444)](#53-the-dedup-mismatch)

</div>

<br>

---

<br>

## Content Tree

<pre>
Knowledge Base Page
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│   ├── <a href="#11-what-the-user-can-do">1.1 What the user can do</a>
│   └── <a href="#12-what-the-page-shows">1.2 What the page shows</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-the-view-model-pattern">3.1 The view-model pattern</a>
│   └── <a href="#32-tailwind-classes-in-a-js-file">3.2 Tailwind classes in a .js file</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-mount">4.1 Mount</a>
│   ├── <a href="#42-the-upload-queue">4.2 The upload queue</a>
│   └── <a href="#43-delete-and-clear">4.3 Delete and clear</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-the-three-state-progress-bar">5.1 The three-state progress bar</a>
│   ├── <a href="#52-accept_attr-and-what-it-does-not-do">5.2 ACCEPT_ATTR, and what it does not do</a>
│   ├── <a href="#53-the-dedup-mismatch">5.3 The dedup mismatch</a>
│   └── <a href="#54-the-stat-cards">5.4 The stat cards</a>
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

The knowledge-base page is where documents enter the system. It is one view —
`pages/knowledge-base/views/KnowledgeBaseView.vue`, 70 lines — an 87-line pure sidecar, and three
components: an upload panel, a statistics strip and the list of indexed files.

Structurally it is the cleanest container/presentational split in the codebase, and the view says so
itself: *"The children are presentational — the view owns the data and hands each one a finished
view-model, so no component reaches back up into this folder."* Two of the three children import no
store at all.

Behaviourally it has one thing every reader should leave knowing: **the client and the server decide
"is this a duplicate?" by different keys.** The browser compares filenames; the server compares content
hashes. Most of the time that difference is invisible; twice it is not, and both cases are surprising
(§5.3).

**Where this fits:** the store behind this page is [`../state/README.md`](../state/README.md); the five
HTTP routes it drives are
[`../../../Backend/Documentation/api/knowledge-base.md`](../../../Backend/Documentation/api/knowledge-base.md);
what the server does with an uploaded file is
[`../../../Backend/Documentation/ingestion/README.md`](../../../Backend/Documentation/ingestion/README.md).

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

### 1.1 What the user can do

- **Upload** — drag files onto the drop zone, or click it to open the file picker. Multiple files at
  once are supported and are processed **one at a time**.
- **Re-index a duplicate** — dropping a file whose name matches one already indexed raises a
  confirmation offering to re-index it. Declining skips that file and continues with the rest of the
  batch.
- **See the corpus** — three statistic cards (vectors, keyword documents, graph structure) above a grid
  of file cards.
- **Delete one file** — a ✕ on each card, behind a confirmation.
- **Clear everything** — one button, behind a confirmation.

### 1.2 What the page shows

| Region | Source |
|---|---|
| Upload panel with a three-state progress bar and a status banner | `kbStore`'s upload flags, driven directly |
| Three statistic cards | `buildIndexStats(store.indexStats)` — a finished view-model |
| The file grid, newest first | `buildKbCards(store.knowledgeBases)` — a finished view-model |
| Per-file tiles: Vectors · Entities · Chunks | `kbStats(kb)` inside the card builder |

The list is newest-first because `GET /api/knowledge-bases` sorts by upload time descending. **The
frontend does no sorting of its own** — the order is a server contract, not a client preference.

---

## 📍 2. WHERE IT LIVES

Paths are relative to `Frontend/src/pages/knowledge-base/`.

```text
pages/knowledge-base/
│
├── 📁 views/
│   ├── 📄 KnowledgeBaseView.vue   The container — owns the data, hands down view-models. 70 lines
│   └── 📄 knowledgeBaseView.js    Sidecar: ACCEPT_ATTR, formatDate, kbStats, buildKbCards,
│                                  buildIndexStats. Pure — and 24 dark: class pairs. 87 lines
│
└── 📁 components/
    ├── 📁 UploadPanel/
    │   └── 📄 UploadPanel.vue         Drop zone, queue, dedup confirm, progress bar, banner. 163 lines
    ├── 📁 IndexStats/
    │   └── 📄 IndexStats.vue          Three cards. Props only — no store, no logic. 42 lines
    └── 📁 KnowledgeBaseList/
        └── 📄 KnowledgeBaseList.vue   The file grid and its empty state. Props in, events out. 86 lines
```

| Concern | Path | Anchor |
|---|---|---|
| Container wiring | `views/KnowledgeBaseView.vue:50-51` | `indexStats`, `kbCards` |
| Initial load | `views/KnowledgeBaseView.vue:53-55` | `onMounted` |
| Confirm gates | `views/KnowledgeBaseView.vue:59`, `:65` | `remove`, `clearAll` |
| Accepted extensions | `views/knowledgeBaseView.js:13-20` | `ACCEPT_ATTR` |
| Card view-models | `views/knowledgeBaseView.js:38`, `:50` | `buildKbCards`, `buildIndexStats` |
| Upload queue + dedup | `components/UploadPanel/UploadPanel.vue:125-150` | `handleFiles` |
| Progress labelling | `components/UploadPanel/UploadPanel.vue:111-121` | `progressLabel`, `progressPct` |

---

## 🏗️ 3. ARCHITECTURE

### 3.1 The view-model pattern

The view builds two computeds and passes them down as finished data:

```js
// src/pages/knowledge-base/views/KnowledgeBaseView.vue:50
const indexStats = computed(() => buildIndexStats(store.indexStats))
const kbCards    = computed(() => buildKbCards(store.knowledgeBases))
```

```html
<UploadPanel :accept="ACCEPT_ATTR" />
<IndexStats :stats="indexStats" />
<KnowledgeBaseList :items="kbCards" @remove="remove" @clear="clearAll" />
```

| Component | Props | Emits | Store |
|---|---|---|---|
| `UploadPanel` | `accept` (String, required) | none | `kbStore`, `ui` |
| `IndexStats` | `stats` (Array, required) | none | **none** |
| `KnowledgeBaseList` | `items` (Array, required) | `remove`, `clear` | **none** |

`IndexStats` and `KnowledgeBaseList` are pure functions of their props — they render whatever the
builders handed them and know nothing about the store, the API or each other. `KnowledgeBaseList`'s only
import is `FileTypeIcon`.

`UploadPanel` is the deliberate exception: it drives `kbStore` directly and emits nothing. Threading the
whole upload lifecycle — two progress phases, a queue counter, a confirm gate and a result banner —
through props and events would produce a far larger interface than the component itself.

The shape is worth naming because it is the most reusable idea on the page: **the container owns
reactivity and the transformation; the children own rendering.** A change to how a stat card looks is a
change in one place, and it is not necessarily the `.vue` file — which is the subject of the next
section.

### 3.2 Tailwind classes in a `.js` file

`buildIndexStats` (`knowledgeBaseView.js:50-87`) returns three cards, and each card carries **seven
Tailwind class strings** — `iconBg`, `cardBg`, `pillBg`, `labelColor`, `valueColor`, `dividerColor` — in
emerald, sky and teal.

> [!IMPORTANT]
> **`knowledgeBaseView.js` holds 24 `dark:` class pairs. It is the only `.js` file in the repo carrying
> Tailwind classes**, and it is why `IndexStats.vue` has only three. A colour change for the statistic
> cards is edited **here**, in a view-model, not in the template that renders it.
>
> That is surprising enough to trip anyone who opens `IndexStats.vue` looking for the emerald. It is
> also load-bearing for the build: Tailwind's purge scope is
> `['./public/index.html', './src/**/*.{vue,js,ts}']`, and `.js` is in that glob — which is the only
> reason these classes survive a production build. **Every class in that file is a complete literal**;
> a class assembled by string concatenation would be purged away and the card would render unstyled.

The defensible reading is that these strings are part of the view-model — a card *is* its numbers plus
its palette. The cost is that "where is this colour defined?" has a non-obvious answer for exactly three
cards on one page.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 Mount

```js
// src/pages/knowledge-base/views/KnowledgeBaseView.vue:53
onMounted(async () => {
  await Promise.all([store.refreshStats(), store.fetchKnowledgeBases()])
})
```

Both requests fire in parallel and both **swallow their errors** inside the store, so a backend that is
not running leaves a quiet zero-state — empty stats, empty list, no error surface. That is the intended
degradation for a page a developer opens before starting the API.

### 4.2 The upload queue

`handleFiles(files)` (`UploadPanel.vue:125-150`) is the page's control flow:

```text
for each file, sequentially (await inside the loop — never parallel):
   │
   ├─ is there a KB whose name matches, case-insensitively?
   │     ├─ no  → upload it
   │     └─ yes → ui.confirm("… is already in the knowledge base. Re-upload to re-index it?")
   │                ├─ declined → continue     (skip this file, keep the batch going)
   │                └─ accepted → await store.removeKnowledgeBase(duplicate.id)  → then upload
   │
   ├─ store.resetUploadResult()
   ├─ await store.uploadDocument(file, { queueCurrent: i + 1, queueTotal: total })
   └─ catch {}   ← deliberate: the store already recorded the error; one bad file must not
                   abort the rest of the queue

after the loop: setTimeout(() => store.resetUploadResult(), 6000)   ← the banner self-clears
```

Four decisions in that flow, each explicit in the code:

- **Sequential, never parallel** (`:128`). Ingestion writes three stores and a JSON registry with no
  transaction and no cross-store lock; concurrent ingest is the unsafe operation on the server side.
  One `await` per file is the client's half of keeping that safe.
- **The dedup confirm is the only non-`danger` confirmation in the app** (`:134-137`), with buttons
  *"Yes, re-index it"* / *"No, keep existing"*. Every other `ui.confirm` in the codebase is destructive
  and red.
- **Accepting the re-index deletes first, then uploads** (`:139`). The store's delete is awaited, so the
  new copy is never written against a stale entry.
- **The empty catch is intentional and carries its rationale in a comment** (`:144-147`): the store
  already recorded the failure on `uploadResult`, and the queue must continue so one bad file cannot
  abort the rest.

The drop zone itself (`:11-39`) handles `dragenter`, `dragover`, `dragleave` and `drop`, all with
`.prevent`, plus a click that forwards to a hidden `<input type="file" multiple :accept>`. `dragCount`
(`:96`, `:102`) reads `e.dataTransfer?.items?.length ?? 1`, so a multi-file drag shows **📚 "Drop N
files"** and a single file shows 📄. The whole zone goes `pointer-events-none opacity-50` while
`uploading || isIndexing` (`:18`).

### 4.3 Delete and clear

Both are `ui.confirm` gates with `danger: true`, in the view (`:59-63`, `:65-69`), and both delegate to
the store — `removeKnowledgeBase(id)` and `clearIndex()`. Neither swallows: an error propagates.

> [!WARNING]
> **The confirmation is client-side only. The API has no gate of its own.** `DELETE /api/clear` is
> **unauthenticated** and wipes the entire index — all three stores plus the registry plus the uploaded
> files — for anyone who can reach the port. The dialog protects against a misclick, not against a
> request. There is no auth on any route in this backend, which is the reason it must not be exposed
> beyond localhost.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 The three-state progress bar

**The problem:** an upload has two phases with completely different observability. The byte transfer is
measurable; the server-side indexing is not, because the endpoint is synchronous and reports nothing
until it is finished.

`UploadPanel` renders three visually distinct states (`:42-64`, `:111-121`):

| State | Label | Percentage | Bar |
|---|---|---|---|
| Transferring | *Uploading file…* | `store.uploadProgress` — **real** | determinate emerald |
| Server working | *Processing on server…* | **`null`** | **indeterminate `animate-shimmer` gradient** |
| Indexing | *Indexing chunks…* | `store.indexingProgress` — **animated** | determinate emerald |

`progressPct` returns `null` precisely when `uploading && uploadProgress >= 100` (`:117-121`) — the
window between "every byte is sent" and "the store flipped to the indexing phase".

**That middle state is the only honest segment of the bar.** It makes no numeric claim at all; the
shimmer says *working* and nothing else.

> [!WARNING]
> **The indexing bar is a fake, and it is worth knowing exactly how fake.** The store's
> `_animateIndexing()` steps the value by `+5` every `80 ms` until it reaches `95`, then resolves — a
> fixed animation of about **1.5 seconds regardless of the actual work**. There is no signal behind it:
> `POST /api/upload` is fully synchronous, with **no job id, no polling endpoint and no event stream**,
> so the server has already finished by the time the animation starts. A one-line text file and a
> 300-page PDF produce the identical bar. Anyone reading `indexingProgress` as a measurement is reading
> a timer.

The queue badge `N/M` appears whenever `uploadQueueTotal > 1` (`:47-51`), and the status banner
(`:67-80`) shows either a red `✗ {error}` or an emerald `✓ Indexed **{file_name}** — {chunks_indexed}
chunks added`, both keys coming straight from the upload response. A ✕ dismisses it early; otherwise it
self-clears after six seconds.

The panel header advertises **"up to 50 MB"** (`:6`), matching the server's request-size cap.

### 5.2 `ACCEPT_ATTR`, and what it does not do

`ACCEPT_ATTR` (`knowledgeBaseView.js:13-20`) is **35 extensions** joined with commas for the file
input's `accept` attribute:

```text
.pdf .docx .txt .md .json .csv .html .htm
.js .jsx .ts .tsx .css .scss .py .java .c .cpp .cs .go .rb .php .rs .sh .bat .pl
.swift .kt .scala .r .m .vb .lua .dart .sql
```

Its own comment says it mirrors the server's allow-list and asks that the two be kept in step. They
agree today: the server's configured extension set and its loader's supported-extension map both hold
35 entries, with an empty set difference in both directions.

> [!IMPORTANT]
> **`accept` is a file-picker hint, not enforcement.** It filters what the OS dialog offers and nothing
> else. A drag-and-drop, a renamed file, or a picker set to "All files" sends the request anyway — and
> the server re-checks, returning a `400` listing every accepted extension. The client list exists to
> make the picker pleasant; the server list is the rule.
>
> *(The comment beside `ACCEPT_ATTR` cites the server config as `Backend/src/config.py`; the real path
> is `Backend/src/adrag/config.py`. A stale code comment, corrected here rather than repeated.)*

### 5.3 The dedup mismatch

**This is the most important paragraph on the page.**

The client and the server both prevent duplicate work, and they ask different questions:

```js
// src/pages/knowledge-base/components/UploadPanel/UploadPanel.vue:130
const duplicate = store.knowledgeBases.find(
  (kb) => kb.name.toLowerCase() === file.name.toLowerCase()
)
```

**The client dedups by filename, case-insensitively.** The server dedups by **content MD5** — the hash
of the bytes is the knowledge-base id, and an ingest deletes every trace of that hash before writing the
new copy.

Most of the time the two agree, because most of the time the same file has the same name. The two cases
where they disagree are both silent and both surprising:

| Case | What the client does | What the server does | Net result |
|---|---|---|---|
| **Same bytes, new name** | Sees no match — **no prompt at all** | Recognises the content hash, deletes the old copy, re-indexes | **One** knowledge base, now carrying the new name. The old upload's file is still on disk, referenced by nothing. The user is never told a replacement happened. |
| **Different bytes, same name** | Prompts — *"already in the knowledge base"* | Sees a different hash, so it indexes a **second** knowledge base | If the user **declines**, they still end up with two entries once the file is uploaded another way; and the saved file on disk was overwritten by whichever upload landed last, so one entry's name now points at bytes that are gone. Deleting **either** entry removes the shared file. |

Two consequences worth stating plainly:

1. **A silent replace is possible.** Rename `report.pdf` to `report-final.pdf` without editing it,
   upload it, and the original knowledge base disappears — no prompt, no warning, no visible event
   beyond the name in the list changing.
2. **A shared file on disk is possible.** Two registry entries with different hashes can point at one
   overwritten file, and the per-file delete removes it by name, so deleting one breaks the other.
   Nothing in the upload path uniquifies a filename.

The root of it is that **identity means different things at the two layers**: the user thinks in
filenames, the system thinks in content. Neither choice is wrong on its own; the mismatch is the cost of
having both. The server-side half of this story, including what the orphaned files do to
`DELETE /api/clear`, is in
[`../../../Backend/Documentation/ingestion/README.md`](../../../Backend/Documentation/ingestion/README.md).

### 5.4 The stat cards

`buildIndexStats(stats)` (`knowledgeBaseView.js:50-87`) produces three cards, and the third has a
different shape from the first two:

| Card | Source | Shape |
|---|---|---|
| Vectors | `vector_count` | single number + the unit *vectors* |
| Keyword | `bm25_count` | single number + the unit *docs* |
| Graph | `graph.entities` / `graph.documents` / `graph.edges` | **`triple`** — three numbers labelled *entities* / *doc nodes* / *edges* |

`IndexStats.vue` branches exactly once, on `stat.triple` (`:17`, `:21`): either one big number with its
unit, or three numbers in a `grid-cols-3` aligned left / centre / right by position (`:23`). The grid is
`sm:grid-cols-[1fr_1fr_1.4fr]` (`:3`), with the graph card deliberately wider to fit its three columns.
The footer shows `stat.label` and, for non-triple cards only, `stat.desc` (`:30-33`).

> [!NOTE]
> **`graph.documents` counts chunk nodes, not files.** A 42-chunk PDF reports `documents: 42`. The card
> labels it *"doc nodes"*, which is honest — and the real **file** count is the number of cards in the
> list below it, not any number in this strip.

`buildKbCards` (`:38-45`) maps each registry entry to `{ id, name, uploadedLabel, stats }`, where
`uploadedLabel` is `formatDate` (`:24-27`) — a locale-driven
`{ month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }` — and `stats` is `kbStats(kb)`
(`:29-35`), the three per-file tiles Vectors · Entities · Chunks.

`KnowledgeBaseList` renders those cards in a `sm:grid-cols-2 lg:grid-cols-3` grid: a `FileTypeIcon` at
28 px, the name with a `:title` tooltip and `truncate`, the upload label, a ✕ that is
`opacity-20 group-hover:opacity-100`, and the three tiles. Its heading carries the count with correct
singular/plural (`:9`) and the line *"Each file is independently retrievable and can be removed without
affecting others"* (`:12-14`). The empty state (`:65-75`) is a 🗂️ tile, *"No documents yet"*, and a line
naming the accepted types.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

This page drives **five** of the eight backend routes, all through `kbStore` — no component here imports
an HTTP client.

| Route | Trigger | Response shape this page depends on |
|---|---|---|
| `GET /api/documents` | mount, and after every write | `{ vector_count, bm25_count, graph: { entities, documents, edges } }` |
| `GET /api/knowledge-bases` | mount, and after every write | `{ knowledge_bases: [ { id, name, uploaded_at, chunks, vectors, entities, edges } ] }` — newest first |
| `POST /api/upload` | each queued file | `{ success, file_name, file_hash, chunks_indexed, kb, stats }` |
| `DELETE /api/knowledge-bases/<hash>` | per-card ✕, and before a confirmed re-index | `200` always — it is idempotent and has no `404` |
| `DELETE /api/clear` | the Clear all button | `200` |

The upload is `multipart/form-data` with the single field name **`file`**.

Every field the cards render comes from the registry entry, and two of them are worth reading
carefully: `entities` is genuinely per-file, while `edges` is a corpus-wide total captured at index
time — so every row shows a different frozen snapshot of one global number. Details in
[`../../../Backend/Documentation/ingestion/README.md`](../../../Backend/Documentation/ingestion/README.md).

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **A silent replace when the bytes match under a new name** (§5.3). The single most surprising
  behaviour on this page.

- **A 50 MB rejection does not render as a friendly message.** The size cap is enforced by the WSGI
  layer before any route runs, so the response is an **HTML** error page rather than the JSON `error`
  key every other failure uses. The store's fallback shows the axios message instead.

- **The indexing percentage is a timer, not a measurement** (§5.1).

- **Declining a duplicate skips the file entirely.** It is a `continue`, not a queue abort — the rest of
  the batch proceeds.

- **A failed file does not stop the batch.** The empty catch is deliberate and commented.

- **Colours for the stat cards live in a `.js` file** (§3.2).

- **`graph.documents` is chunk nodes, not files** (§5.4).

- **The status banner disappears after six seconds** whether or not it was read. There is no history of
  past uploads beyond the KB list itself.

- **No client-side size check exists.** The panel advertises 50 MB but nothing validates it before
  sending, so an oversized file is a full upload attempt that ends in the HTML error above.

- **Nothing polls.** The stats and list refresh only on mount and after a write this page performed —
  a second browser tab uploading a file will not appear here until something triggers a refresh.

---

## 💥 8. FAILURE MODES

| Failure | What the user sees | Behaviour |
|---|---|---|
| Backend down at mount | Zeroed stats, empty list, no error | Both reads swallow inside the store |
| Unsupported extension | Red banner with the server's message listing accepted types | JSON `400` |
| File over 50 MB | Red banner with an axios-level message | HTML `413`-class response, not JSON |
| No text could be extracted | Red banner with the server's explanation | JSON error; **the file stays on the server's disk as an orphan** |
| One file in a batch fails | That file's banner appears; the queue continues | The empty catch at `:144-147` |
| Delete fails | The error propagates out of the store to the component | No try/catch on the write actions |
| Two entries sharing one file, one deleted | The other entry survives in the list but its file is gone | The dedup mismatch (§5.3) |
| Upload succeeds but the refresh fails | Success banner shows; stats and list stay stale | The two refresh calls swallow their errors |

---

## 🧩 9. EXTENSION POINTS

**Add an accepted file type.** Three places, and missing any one fails differently: the server's
configured extension set (or the route rejects it with a `400`), the server's loader map (or ingestion
raises), and `ACCEPT_ATTR` here (or the file picker hides it, though a drag-and-drop still works). The
server-side half is documented in
[`../../../Backend/Documentation/ingestion/README.md`](../../../Backend/Documentation/ingestion/README.md).

**Add a statistic card.** Append to `buildIndexStats` (`knowledgeBaseView.js:50-87`) with the same seven
class keys. `IndexStats.vue` needs no change unless the new card needs a shape other than single-number
or triple.

**Add a field to a file card.** Extend `buildKbCards` (`:38-45`) and render it in
`KnowledgeBaseList.vue`. The registry entry already carries more fields than the card shows.

**Make the dedup check match the server.** The honest fix is to hash the file in the browser before
uploading and compare against `kb.id` instead of `kb.name` — the `File` object plus `crypto.subtle`
makes that possible, though the server uses MD5 which `crypto.subtle` does not offer. Second best: keep
the name check as a courtesy prompt, and state in the UI that identity is by content, so a silent
replace stops being silent.

**Give the indexing bar a real signal.** That is a backend change first — a job id and a poll endpoint,
or an event stream for ingestion the way queries have one. Until that exists, no frontend change can
make `_animateIndexing` honest.

**What not to touch.** Do not parallelise the upload loop — the server has no cross-store lock. Do not
remove the empty catch without replacing the queue-continues behaviour it protects. Do not build a
Tailwind class by concatenation in `knowledgeBaseView.js`; the purge scope only keeps complete literals.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **Container owns data, children own rendering.** Two of three children are pure props-in components,
  which makes them trivially reusable and trivially testable. The exception, `UploadPanel`, is the case
  where the interface would have been larger than the implementation — a useful boundary test for the
  pattern rather than a violation of it.

- **The view-model carries its own palette.** Defensible — a card is its numbers plus its presentation —
  and genuinely surprising. It survives the build only because Tailwind's purge scope includes `.js`,
  which makes it a decision with a build-configuration dependency, not just a stylistic one.

- **A fake progress bar rather than none.** The alternative to `_animateIndexing` is a spinner. The
  animation was chosen because the shape of an upload is *transfer, then work*, and a bar that jumps
  from 100 % to a spinner reads as a failure. It is the right shape driven by the wrong data, and the
  fix is on the server side.

- **Sequential uploads on purpose.** Slower, and the only safe option: ingestion writes three stores and
  a registry with no transaction and no lock, so overlapping ingests can interleave into an inconsistent
  corpus with nothing surfaced.

- **Filename identity in the UI, content identity in the engine.** Content addressing buys idempotent
  re-indexing for free and makes the same document under any name converge on one entry. The cost is
  that identity is invisible to the user, which is the direct cause of both surprises in §5.3.

**Continue reading:**

- [`../state/README.md`](../state/README.md) — `kbStore`, the two-phase upload and the fake animation
- [`../api-clients/README.md`](../api-clients/README.md) — the five functions behind these five routes
- [`../design-system/README.md`](../design-system/README.md) — `.card`, `.animate-shimmer`, and where the palette lives
- [`../../../Backend/Documentation/ingestion/README.md`](../../../Backend/Documentation/ingestion/README.md) — load, chunk, hash, three stores and a registry
- [`../../../Backend/Documentation/api/knowledge-base.md`](../../../Backend/Documentation/api/knowledge-base.md) — the five routes in full
- [`../../../Backend/Documentation/hybrid-retrieval/stores.md`](../../../Backend/Documentation/hybrid-retrieval/stores.md) — what the three statistic cards are counting
