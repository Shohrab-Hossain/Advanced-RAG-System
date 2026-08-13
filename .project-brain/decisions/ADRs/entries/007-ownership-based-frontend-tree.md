# ADR-007: `Frontend/src/` is sorted by ownership, not by kind
Date: 2026-08-13 · Status: accepted

> **Recorded at decision time** — the decisions below were settled with the owner *before* the refactor
> contract was authored, and the reasoning is preserved in the archived plan brief
> [`152630-frontend-src-reorganisation`](../../../history/PLANS/entries/2026-08-13/152630-frontend-src-reorganisation/brief.md).
> This is not a reconstruction. ADRs 001–005 were recovered from the code after the fact and mark their
> alternatives as *inferred*; ADR-006 and this record were written from the reasoning as it was actually
> weighed. **The *Alternatives considered* section below is a record of what was argued, not an inference**
> — the load-bearing rejection is the owner's own counter-proposal, argued down on the record. Every
> mechanism claim is additionally grounded in the tree as it stands after the refactor.

## Context

`Frontend/src/` was the **stock Vue CLI scaffold**: `components/`, `views/`, `stores/`, `services/` — one
bucket per *kind of thing*. The owner's `vue-file-tree` preference sorts on a different axis entirely:

> **A folder exists because something OWNS what is in it.** *Ownership, never similarity, decides
> placement.*

That single inversion is the whole of this decision; everything below follows from it.

**The bucket did not survive its own import graph.** `components/` held 12 files:

| Component | Imported by | Real owner |
|---|---|---|
| `NavBar` · `ModalDialog` | `App.vue` | site chrome → **shared** |
| `FileTypeIcon` | `ResultDisplay`, `SourceCard`, `KnowledgeBaseView` | 2 pages → **shared** |
| `QueryInput` · `PipelineTracker` · `StageRow` · `ResultDisplay` · `SourceCard` | `ChatView` (+ each other) | **chat page only** |
| `LLMSelector` | `ConfigView` | **configuration page only** |
| `FileUpload` · `KnowledgeBases` · `StatBadge` | **nothing** | dead |

**9 of 12 were owned by exactly one page; 3 were owned by nothing; only 3 were genuinely shared.** The
bucket was never a shared tier — it was a pile that happened to contain three shared things. The three
orphans were earlier extracted versions of sections that `KnowledgeBaseView.vue` had since inlined (its 371
lines carried their own drop zone, progress bar, stat cards and KB list).

The preference chain applied, general → specific: `file-tree` (*fixed vocabulary, as-needed depth*) →
`file-tree/web-application` (the root/interior split) → `.../vue-file-tree` (the `src/` interior, which is
what this decision applies) → `.../root-file-tree` (the `Frontend/` root). Those live in the central
ClaudeSH kit outside this repo, and both `.claude/` and `.project-brain/` are symlinks into `Claude Home\`,
so a relative link from here has two different correct answers — **deliberately not linked**.

## Decision

**Sort `Frontend/src/` by ownership.** Eight points, each deliberated rather than defaulted.

**1. The top-level vocabulary is fixed.** `App.vue` · `main.js` · `assets/` · `router/` · `store/` ·
`shared/` · `subsystems/` · `pages/`. Nothing else appears at the root of `src/`.

**2. `store/` at the root means *state owned by no single capability*** — not "where stores go". The theme
and the promise-based modal belong to the app shell itself, so `stores/ui.js` became `store/index.js`
(store id still `'ui'`, `store/index.js:8`). RAG query state does not qualify: **holding that state is what
makes `rag` a subsystem** rather than a page folder, so separating them would dissolve the definition.

**3. A subsystem owns its own API client and its own store, as flat files.**
`subsystems/rag/{ragApi.js,ragStore.js}` and `subsystems/knowledge-base/{kbApi.js,kbStore.js}`. Each
subsystem constructs its own axios client and reads `VUE_APP_API_URL` independently (`ragApi.js:12-14`,
`kbApi.js:11-13`); **subsystems never import each other.** `services/` and `store/` reappear *inside* a
subsystem when it grows enough to sort — not before.

**4. Every page gets a `views/` folder, uniformly** — all four, including `home` and `configuration`-style
pages that own nothing else. The preference states this is a project-level convention and that its two
reference projects differ, neither wrongly. Uniformity costs one folder on the pages that own nothing else
and removes the question *"which kind of page is this?"* from the reader's path to the view file.

> The preference explicitly warns against rationalising `views/` as *"for screens with sections"* — **10 of
> the 11 `views/` folders across both reference projects hold exactly one `.vue`.** It is a naming
> convention for where the routed view sits, not a container that earns its place by filling up.

**5. One component = one folder; satellites live inside their parent's folder.**
`<Name>/<Name>.vue`, with a component used only by one other component sitting beside it —
`PipelineTracker/StageRow.vue`, `ResultDisplay/SourceCard.vue`. A component owned by exactly one page lives
under `pages/<page>/components/`; only a component consumed by two or more pages is promoted to
`shared/components/`.

**6. The three orphans are deleted, not quarantined and not re-wired.** See *Alternatives*.

**7. `stores/rag.js` is split during the moves, not after.** Splitting while the files were already moving
rewrote every page's imports **once** instead of twice. The cost — the move phase stops being pure file
moves, so a build break is harder to attribute — was mitigated by keeping the pure move and the split as
separate steps, so the `git diff` between them is unambiguous.

**8. `healthCheck` and `getProviders` live in `ragApi.js`.** Neither is querying nor KB management.
`getProviders` because **the provider rides the RAG query itself**; `healthCheck` because it is the same
backend. `NavBar` (shared) therefore imports from `subsystems/rag/` — that direction is fine: shared and
pages both consume subsystems.

**The resulting tree** — 30 files, 2,437 lines:

```
Frontend/src/
├── App.vue · main.js · assets/main.css · router/index.js
├── store/index.js                              theme + promise modal · id 'ui'
│
├── shared/components/
│   ├── NavBar/NavBar.vue
│   ├── ModalDialog/ModalDialog.vue
│   └── FileTypeIcon/FileTypeIcon.vue
│
├── subsystems/
│   ├── rag/
│   │   ├── ragApi.js        healthCheck:18 · getProviders:23 · streamQuery:40
│   │   └── ragStore.js      id 'rag' · STAGES:16-25 · query lifecycle · provider
│   └── knowledge-base/
│       ├── kbApi.js         uploadFile:17 · getDocuments:33 · clearDocuments:38
│       │                    · getKnowledgeBases:45 · deleteKnowledgeBase:50
│       └── kbStore.js       id 'knowledgeBase' · indexStats · KB list · upload progress
│
└── pages/
    ├── home/views/HomeView.vue
    ├── chat/
    │   ├── views/{ChatView.vue, chatView.js}
    │   └── components/{ChatHistorySidebar/, PipelineTracker/, QueryInput/, ResultDisplay/}
    ├── knowledge-base/
    │   ├── views/{KnowledgeBaseView.vue, knowledgeBaseView.js}
    │   └── components/{UploadPanel/, IndexStats/, KnowledgeBaseList/}
    └── configuration/
        ├── views/ConfigView.vue
        └── components/LLMSelector/LLMSelector.vue
```

## Alternatives considered

- **Keep `store/` and `services/` as root folders, with `rag/` and `knowledge-base/` subfolders inside
  each** — *rejected, and this is the load-bearing one: the owner proposed it and it was argued down on the
  record.* It sorts by **kind first, domain second** — the same shape as the `components/` bucket this whole
  change was undoing, with a domain layer bolted on. The measured cost: *"rag"* then lives at **two
  top-level addresses**, `store/rag/` and `services/rag/`, so changing one capability means opening two
  folders that must stay in sync and **neither tells you the other exists** — for the 2-way split, 4 folders
  holding 4 files. It also contradicts the preference on both folders: `store/` is defined as *"the global
  store root — typically one `index.js`; per-subsystem stores live with their subsystem"*, and `services/`
  is not in the `src/` top-level vocabulary at all — it appears only *inside* a page or a subsystem.

  **But the depth objection behind the proposal was correct, and it was honoured.** `subsystems/rag/services/api.js`
  is four levels for a single file, and the preference already answers that: *"a subsystem is not required
  to have any folders at all"* — two subsystems in the reference project are bare files. So subsystems hold
  **flat files**, which makes `subsystems/rag/ragApi.js` the *same depth* as the rejected
  `services/rag/ragApi.js`, with each capability at **one** address instead of two. **This concession is
  what makes the flat-file rule (Decision 3) non-arbitrary** — it is a resolved objection, not a style
  preference, and re-nesting a subsystem before it has enough files to sort would re-open it.

- **Quarantine the three orphans in `src/library/`** — *rejected.* The preference offers exactly that
  pattern (a holding pen for unwired code, kept rather than deleted), but it is opt-in, and *as-needed
  depth* says **a file with no owner has no place in the tree**. **git history is the holding pen.**

- **Re-wire the three orphans into the KB page** instead of deleting them — *rejected.* Extracting
  `KnowledgeBaseView`'s inlined sections back out into those three specific files is a **rewrite, not a
  move**, and the markup had drifted. The extraction was done properly afterwards, sized from what the move
  left behind — and it produced three *differently named, differently shaped* components
  (`UploadPanel/`, `IndexStats/`, `KnowledgeBaseList/`), which is the retroactive proof that restoring the
  old three would have been the wrong target.

- **Give `views/` to a page only when it owns other folders** (the shallower, conditional form) —
  *rejected.* With four pages, two would have had it and two would not, so a reader must know which kind of
  page they are looking at *before* they can guess where the view file sits. See Decision 4.

- **Group by domain at the root** (`src/website/`, `src/workspace/`) — *rejected.* The preference's domain
  test is *"could a user plausibly never visit the other group?"*; with 4 pages, one nav and one audience it
  fails. Pages stay flat.

- **Move `stores/rag.js` whole and split it later** — *rejected.* It rewrites every page's imports twice.
  See Decision 7.

- **Move `public/index.html` to the `Frontend/` root**, as the root-file-tree preference wants — *rejected.*
  **Vue CLI requires `public/index.html`.** Accepted deviation, the same class as the preference's own
  *"config sits at the root because that is where the toolchain looks"* — the external constraint wins.

## Consequences

**Makes easy**

- **One capability, one address.** Changing RAG means opening `subsystems/rag/`; changing a chat screen
  means opening `pages/chat/`. Nothing that belongs to one page is reachable from another page's folder.
- **A component's blast radius is readable from its path.** `pages/chat/components/QueryInput/` cannot be
  in use anywhere but the chat page; `shared/components/` is now a real contract rather than a residue.
- **Deleting a page deletes its components with it** — they are inside it, not in a pile it shares.
- **The store split matches the API split.** `kbStore` + `kbApi` move together; a KB change touches one
  folder.

**Makes hard / watch out for**

> The first three cannot be re-derived from the code. A later reader who does not find them here will
> reasonably conclude each is a defect and "fix" it.

- **`pages/knowledge-base/` and `subsystems/knowledge-base/` share a name *deliberately*.** The **page**
  routes to the screen; the **subsystem** holds the capability that screen consumes. It reads oddly in an
  import list, and it is semantically correct. **Do not rename either half to break the collision** — the
  names are equal because the concepts are.
- **`LLMSelector.vue` is left at 204 lines on purpose.** Its `<script setup>` is lines **167–204** only —
  five computeds, two derived computeds, `select()`, `refresh()`, a 15-second poll timer, and
  `onMounted`/`onUnmounted`. There is **no pure logic to extract**: the length is template, and the script
  is entirely reactive glue, which the camelCase pure-logic sibling convention explicitly does not take.
  This is neither an oversight nor a pending cleanup, so a size threshold alone should not reopen it.
- **`FileUpload.vue`, `KnowledgeBases.vue` and `StatBadge.vue` were deleted, not quarantined.** git history
  is the holding pen (they are recoverable from the commit before this refactor). If a future change wants
  one of them back, recover it from history — **do not create a `src/library/` to hold unwired code**, which
  is the pattern this decision declined.
- **Two consumers now cross the subsystem boundary, by necessity.** `pages/chat/views/ChatView.vue:118-119`
  takes `ragStore` *and* `kbStore` (for `hasDocuments`, which drives the no-documents warning), and
  `shared/components/NavBar/NavBar.vue:108-111` takes `ragStore` (provider badge), `kbStore`
  (`refreshStats` + `fetchKnowledgeBases` on mount), the `ui` store, and `healthCheck` straight from
  `ragApi` — the one sanctioned component→service import, which survives this refactor unchanged. These are
  the main cross-subsystem edges the split created; they go through the *stores*, never subsystem-to-subsystem.
- **`VUE_APP_API_URL` now has two construction sites, not one.** `ragApi.js:12` and `kbApi.js:11` each read
  it into their own `BASE`. The *behaviour* of the seam is unchanged (ADR-006 still holds); the number of
  places that implement it doubled, so a change to the base-URL rule must be made twice.
- **`kbStore.js`'s file name and store id differ** — the file is `kbStore.js`, the Pinia id is
  `'knowledgeBase'` (`kbStore.js:14`). Search by id will not find the file and vice versa.
- **There is no path alias.** No `@/` is declared in `vue.config.js` or anywhere else, so every import is
  relative and the deepest is `../../../../` from `pages/<page>/components/<Name>/`. **Do not invent an
  alias while following this tree** — none exists to follow.
- **Depth costs a level.** A page-owned component sits four folders deep. That is the accepted price of
  every capability having exactly one address.

## Old → new path map

**This table is the compensating control for a deliberate omission.** `decisions/` is append-only, so
**ADRs 003, 005 and 006 were left byte-unedited** even though the frontend paths they cite no longer exist.
They are correct records of decisions made against the tree as it was; rewriting them would destroy the
record. **This map is how their paths resolve** — and how a reader arriving from `history/` or an older
brief resolves theirs.

**Where the three unedited ADRs' dangling references point now:**

| Unedited ADR | Path it cites | Resolves to |
|---|---|---|
| `003-sse-for-pipeline-progress.md:6` | `Frontend/src/services/api.js` (`streamQuery`) | `Frontend/src/subsystems/rag/ragApi.js:40` |
| `005-dual-llm-provider.md:6` | `Frontend/src/views/ConfigView.vue` | `Frontend/src/pages/configuration/views/ConfigView.vue` |
| `006-dev-launcher-env-injected-ports.md:7` | `Frontend/src/services/api.js` | **both** `subsystems/rag/ragApi.js` **and** `subsystems/knowledge-base/kbApi.js` |
| `006-…:19` (inside its seam table) · `006-…:68` | `Frontend/src/services/api.js:12` — `BASE = process.env.VUE_APP_API_URL \|\| ''` | **both** `subsystems/rag/ragApi.js:12` **and** `subsystems/knowledge-base/kbApi.js:11` — each is now its own `const BASE` |

ADR-006's seam claim still holds in full; it simply has **two implementation sites** instead of one. Note
that this single old path resolves to **two** new ones — reading only one of them under-reports the seam.

**The full move, by class** (similarity indices are git's own, from
`git diff --name-status -M 914c6b8..1f177af`):

| Class | Old path | New path |
|---|---|---|
| **Root store** | `src/stores/ui.js` | `src/store/index.js` *(R100 — content identical; id still `'ui'`)* |
| **Subsystem stores** | `src/stores/rag.js` | **split** → `src/subsystems/rag/ragStore.js` *(R071)* **+** `src/subsystems/knowledge-base/kbStore.js` *(new)* |
| **Subsystem APIs** | `src/services/api.js` | **split** → `src/subsystems/rag/ragApi.js` *(R075, 3 exports)* **+** `src/subsystems/knowledge-base/kbApi.js` *(5 exports)* |
| **Shared components** | `src/components/NavBar.vue` | `src/shared/components/NavBar/NavBar.vue` *(R094)* |
| | `src/components/ModalDialog.vue` | `src/shared/components/ModalDialog/ModalDialog.vue` *(R097)* |
| | `src/components/FileTypeIcon.vue` | `src/shared/components/FileTypeIcon/FileTypeIcon.vue` *(R100)* |
| **Page components** | `src/components/QueryInput.vue` | `src/pages/chat/components/QueryInput/QueryInput.vue` *(R098)* |
| | `src/components/PipelineTracker.vue` | `src/pages/chat/components/PipelineTracker/PipelineTracker.vue` *(R097)* |
| | `src/components/StageRow.vue` | `src/pages/chat/components/PipelineTracker/StageRow.vue` *(R100 — satellite)* |
| | `src/components/ResultDisplay.vue` | `src/pages/chat/components/ResultDisplay/ResultDisplay.vue` *(R097)* |
| | `src/components/SourceCard.vue` | `src/pages/chat/components/ResultDisplay/SourceCard.vue` *(R097 — satellite)* |
| | `src/components/LLMSelector.vue` | `src/pages/configuration/components/LLMSelector/LLMSelector.vue` *(R099)* |
| **Deleted** | `src/components/FileUpload.vue` · `src/components/KnowledgeBases.vue` · `src/components/StatBadge.vue` | **none** — recover from git history if ever needed |
| **Views** | `src/views/HomeView.vue` | `src/pages/home/views/HomeView.vue` *(R100)* |
| | `src/views/ConfigView.vue` | `src/pages/configuration/views/ConfigView.vue` *(R098)* |
| | `src/views/ChatView.vue` | `src/pages/chat/views/ChatView.vue` *(rewritten, 268 → 130 lines)* |
| | `src/views/KnowledgeBaseView.vue` | `src/pages/knowledge-base/views/KnowledgeBaseView.vue` *(rewritten, 371 → 70 lines)* |

**The general rules**, for a path this table does not name literally:

- `src/stores/<x>.js` → `src/store/index.js` if the state is owned by no capability, else
  `src/subsystems/<capability>/<x>Store.js`
- `src/services/api.js` → `src/subsystems/<capability>/<x>Api.js`
- `src/components/<Name>.vue` → `src/shared/components/<Name>/<Name>.vue` (2+ pages consume it) **or**
  `src/pages/<page>/components/<Name>/<Name>.vue` (one page owns it) **or** inside the parent component's
  folder (one component owns it)
- `src/views/<Name>View.vue` → `src/pages/<page>/views/<Name>View.vue`

**No path in this map has a new-side line number that predates the refactor** — the two rewritten views
(`ChatView.vue`, `KnowledgeBaseView.vue`) changed enough that git recorded them as a delete plus an add, so
any `file:line` citation against their old form is stale in both halves and must be re-read, not remapped.

The conventions this tree encodes are recorded in
[`../../../project-context/conventions/project-layout/README.md`](../../../project-context/conventions/project-layout/README.md)
and [`../../../project-context/conventions/code-style/README.md`](../../../project-context/conventions/code-style/README.md);
the resulting architecture in
[`../../../project-context/architecture/frontend.md`](../../../project-context/architecture/frontend.md);
the ordered rebuild steps in
[`../../../project-context/build-from-scratch.md`](../../../project-context/build-from-scratch.md).
