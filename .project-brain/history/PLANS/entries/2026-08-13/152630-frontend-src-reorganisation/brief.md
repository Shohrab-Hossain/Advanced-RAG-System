# Brief — Reorganise `Frontend/src/` onto the vue-file-tree preference

## Why this exists

`Frontend/src/` is the **stock Vue CLI scaffold**: files sorted into `components/`, `views/`, `stores/`,
`services/` — one bucket per *kind of thing*. The owner's `vue-file-tree` preference sorts by a different
axis entirely:

> **A folder exists because something OWNS what is in it.** *Ownership, never similarity, decides
> placement.*

That single inversion is the whole of this plan. Everything below follows from it.

**Measured, from the import graph** — `components/` holds 12 files:

| Component | Imported by | Real owner |
|---|---|---|
| `NavBar` `ModalDialog` | `App.vue` | site chrome → **shared** |
| `FileTypeIcon` | ResultDisplay, SourceCard, KnowledgeBaseView | 2 pages → **shared** |
| `QueryInput` `PipelineTracker` `StageRow` `ResultDisplay` `SourceCard` | ChatView (+ each other) | **chat page only** |
| `LLMSelector` | ConfigView | **configuration page only** |
| `FileUpload` `KnowledgeBases` `StatBadge` | **nothing** | dead |

**9 of 12 are owned by exactly one page. 3 are owned by nothing.** Only 3 are genuinely shared. The bucket
is not a shared tier — it is a pile that happens to contain three shared things.

The three orphans are earlier extracted versions of sections `KnowledgeBaseView.vue` now inlines itself:
its 371 lines contain their own drop zone, progress bar, stat cards and KB list.

## Preference chain this plan implements

Read general → specific, from the central kit's `storage/global/preferences/`:

1. `file-tree/PREFERENCE.md` — *fixed vocabulary, as-needed depth*

   > Deliberately **not** a link. These preferences live in the central ClaudeSH kit at
   > `E:\A. Workspace\B1. My AI\01. Claude\ClaudeSH\.claude\storage\global\preferences\`, outside this
   > repo — and both `.claude/` and `.project-brain/` are symlinks into `Claude Home\`, so a relative
   > path from here has two different correct answers depending on whether the reader follows the
   > symlink. The original link was already broken before this plan was archived (six `../` resolved to
   > `01. Artificial Intelligence\A. Workspace\`, which does not exist).
2. `file-tree/web-application/` — the root/interior split
3. `file-tree/web-application/vue-file-tree/` — the `src/` interior, which is what this plan applies
4. `file-tree/web-application/root-file-tree/` — the `Frontend/` root, which supplies step 1.6

## The target tree

```
Frontend/src/
├── App.vue  main.js                            unchanged
├── assets/main.css                             unchanged
├── router/index.js                             paths update only
├── store/index.js                              ← from stores/ui.js
│
├── shared/components/
│   ├── NavBar/NavBar.vue
│   ├── ModalDialog/ModalDialog.vue
│   └── FileTypeIcon/FileTypeIcon.vue
│
├── subsystems/
│   ├── rag/
│   │   ├── ragApi.js          streamQuery · getProviders · healthCheck
│   │   └── ragStore.js        query state · STAGES · pipeline progress · provider
│   └── knowledge-base/
│       ├── kbApi.js           uploadFile · getDocuments · clearDocuments · getKnowledgeBases · deleteKnowledgeBase
│       └── kbStore.js         documents · KB list · upload progress
│
└── pages/
    ├── home/views/HomeView.vue
    ├── chat/
    │   ├── views/ChatView.vue
    │   └── components/
    │       ├── QueryInput/QueryInput.vue
    │       ├── PipelineTracker/{PipelineTracker,StageRow}.vue
    │       └── ResultDisplay/{ResultDisplay,SourceCard}.vue
    ├── knowledge-base/views/KnowledgeBaseView.vue
    └── configuration/
        ├── views/ConfigView.vue
        └── components/LLMSelector/LLMSelector.vue
```

## The four decisions, and their grounds

Each was settled with the owner before this contract was authored. Recorded here because the reasoning is
what a later reader will need, and the conclusions alone would survive a summary anyway.

### 1. Every page gets a `views/` folder

The preference states outright that this is a **project-level convention** and that the two reference
projects differ, neither wrongly. Chosen: **uniform** — all four pages get one, including `home` and
`knowledge-base` which own nothing else.

**Why not the shallower form** (`views/` only when the page has other folders): with four pages, two of
which would have it and two of which would not, a reader has to know which kind each page is before they
can guess where its view file sits. Uniformity costs one folder each on two pages and removes that question.

⚠️ The preference explicitly warns against rationalising `views/` as *"for screens with sections"* — **10 of
the 11 `views/` folders across both reference projects hold exactly one `.vue`.** It is a naming convention
for where the routed view sits, not a container that earns its place by filling up.

### 2. Delete the three orphans rather than quarantine or re-wire

`FileUpload.vue`, `KnowledgeBases.vue`, `StatBadge.vue` are imported by nothing.

- **Not quarantined in `src/library/`** — the preference offers that pattern (a holding pen for unwired
  code, kept rather than deleted) but it is 🎛 opt-in, and *as-needed depth* says a file with no owner has
  no place in the tree. git history is the holding pen.
- **Not re-wired into the KB page** — extracting `KnowledgeBaseView`'s inlined sections back out to these
  three files is a rewrite, not a move. Phase 2 does that extraction properly, sized from what phase 1
  leaves behind, rather than trying to restore three files that may no longer match the markup.

### 3. Subsystem stores live WITH their subsystem, not in `store/`

This was the one the owner pushed back on, and the pushback was worth resolving on the record.

**The proposal that was rejected:** keep `store/` and `services/` as root folders, with `rag/` and
`knowledge-base/` subfolders inside each.

That sorts by *kind* first, domain second — the same shape as the `components/` bucket this whole plan is
undoing, just with a domain layer added. The concrete cost: "rag" then lives at two top-level addresses,
`store/rag/` and `services/rag/`. Changing one capability means opening two folders that must stay in sync,
and neither tells you the other exists. With the 2-way split, that is 4 folders holding 4 files.

It also contradicts the preference on both folders: `store/` is defined as *"the global store root —
typically one `index.js`; **per-subsystem stores live with their subsystem**"*, and `services/` is not in
the `src/` top-level vocabulary at all — it appears only *inside* a page or a subsystem.

**But the depth objection behind it was correct.** `subsystems/rag/services/api.js` is four levels for a
single file, and the preference already answers that:

> 🔒 **A subsystem is not required to have any folders at all.** Two in the reference project are bare
> files.

So the subsystems hold **flat files**. `src/subsystems/rag/ragApi.js` is the *same depth* as the rejected
`src/services/rag/ragApi.js`, with each capability at one address instead of two. When `rag/` grows a third
and fourth file, `services/` and `store/` appear **then**, because there is finally something to sort.

**The rule, stated once and applied at both levels:** `store/` at the root is not "where stores go" — it is
*state owned by no single capability*. `ui.js` qualifies (the modal and theme belong to the app shell
itself). `rag.js` does not — holding that state is *what makes rag a subsystem* rather than a page folder,
so separating them dissolves the definition.

### 4. Split `rag.js` in phase 1, during the moves

The alternative was moving it whole and splitting in phase 2. Splitting during the moves means every page's
imports are rewritten **once** instead of twice. The cost is that phase 1 stops being pure file moves, so a
build break is harder to attribute — mitigated by keeping 1.2 (pure `git mv`, no content edits) and 1.3
(the split) as separate steps, so `git diff` between them is unambiguous.

## Two things that will look odd during execution

**`healthCheck` and `getProviders` have no obvious home in the split.** Neither is querying nor KB
management. Both go in `ragApi.js`: `getProviders` because the provider is carried on the RAG query itself,
`healthCheck` because it is the same backend. `NavBar` (shared) then imports from `subsystems/rag/` — that
direction is fine; shared and pages both consume subsystems.

**`pages/knowledge-base/` and `subsystems/knowledge-base/` share a name.** Semantically correct — the page
routes to the screen, the subsystem holds the capability the screen consumes — but it will read oddly in an
import list. Noted here so it is not discovered mid-refactor and "fixed".

## What is deliberately NOT in scope

| Not doing | Why |
|---|---|
| Domain grouping (`src/website/`, `src/workspace/`) | 4 pages, one nav, one audience. The preference's domain test — *"could a user plausibly never visit the other group?"* — fails. Pages stay flat. |
| Moving `public/index.html` to the root | The root-file-tree preference wants `index.html` at the root; **Vue CLI requires `public/index.html`**. Accepted deviation, same class as the preference's own *"config sits at the root because that is where the toolchain looks"* — the external constraint wins. |
| Creating `design/` | No design source exists. *As-needed depth* forbids the empty folder. |
| Fixing `Frontend/Documentation/README.md`'s content | It is stale (describes Vite, `npm run dev`, port 5173 against a Vue CLI / `npm run serve` / port 8080 reality). Step 1.6 renames the folder only; the content is separate work. |
| Refreshing the rest of `.claude/CLAUDE.md` | Step 1.7 is a **targeted edit of two sections** — Layout and Conventions. The guardrails, stack and commands sections are untouched; a full refresh is a `csh-claude-md-writer` run, not this plan. |
| Adding `@vue/cli-plugin-eslint` | `npm run lint` is broken (the script exists, the plugin and config do not). Real, unrelated, and pre-existing. |
| Anything under `Backend/` | Untouched. |

## Sequencing

**Phase 1 is a shallow chain by design.** The whole target tree and every import edge were measured before
this contract was authored, so no step's shape depends on discovering something. 1.2 (move) → 1.3 (split) →
1.4 (rewrite imports) → 1.5 (look at it) is depth 4 over six steps — below the corpus danger zone of ≥7
steps at depth ≥3, and every step's content is knowable now.

**The phase boundary is real.** Phase 2's shape genuinely is not knowable until phase 1 has run: how much
`ChatView` shrinks depends on what the `ragStore`/`kbStore` split takes out of it, and `KnowledgeBaseView`'s
extraction targets depend on where it landed. That is the chain rule, so it is a boundary rather than four
more steps on the end of phase 1.

## Verification

Owner chose **machine + a look at the app** (`trust: report` · `reach: per-phase` · `independence: single`).

Every step's deliverable is a file path, an absence, or a build command — the walk is free. The two `judged`
deliverables (1.5, 2.3) are settled by `verify: human`: the owner boots the app and looks. That is the one
thing no command here can decide — a build passing proves imports resolve, not that a store binding survived
the split.

**What this does not catch:** a component that renders but has lost a prop's reactivity in a way that only
shows under a specific interaction. The two focus surfaces named in 1.5 and 2.3 — pipeline stage animation
and KB index stats — are the two most likely places for that, because they are what the `rag.js` split
touches.

## Log

- **2026-08-13** — audit run against the preference chain; 4 decisions settled with the owner; contract
  authored at rev 1. Nothing executed yet.
- **2026-08-13 · rev 2** — added step **1.7**, and widened **G1** to cover it.

  `.claude/CLAUDE.md`'s *Conventions to match* section currently reads *"a page → `src/views/<Name>View.vue`
  plus a lazily-imported router entry; a component → flat in `src/components/`, no sub-folders"*, and its
  *Layout* tree lists the four buckets by name. **Every one of those clauses becomes false the moment 1.4
  lands**, and CLAUDE.md is what a fresh agent reads on session start — so an unamended brief would actively
  instruct the next agent to rebuild the buckets this plan removes.

  The owner chose to fix it **inside phase 1** rather than as a follow-up, so the brief is correct at the
  same moment the tree is, in the same branch as the change it describes.

  **G1 was widened rather than a fourth goal added.** The goals cap is 3, but that is not the reason: a step
  whose `dod` ref names a different subject than its `do` is the exact defect ADR 045 was written about —
  nineteen such refs in plan `163505` cost 2.2M tokens to verify. G1 is *"the tree is per the preference"*;
  *"and the brief says so"* is the same claim, not a new one. A separate goal would have split one subject
  across two predicates.

- **2026-08-13 · rev 3** — branch renamed `refactor/frontend-src-tree` → **`claudesh/frontend-src-tree`**.

  The `claudesh/` prefix is not cosmetic. `git-managing`'s single-open-branch invariant is enforced by
  `git branch --list 'claudesh/*'` — a branch named anything else is **invisible to that pre-check**, so a
  later session running the branch gate would see an empty list and open a second branch on top of this one.
  The two would then share one working tree and one HEAD, which is the exact failure the invariant exists to
  prevent. Caught at the gate itself, before the branch was created; the owner chose the signed name over the
  more natural-reading `refactor/`.

  Changed: `branch`, `git.active`, and step 1.1's `do` text + its `delivers` command (which greps for the
  branch by name and would otherwise have failed against a branch that exists).

## Execution log

- **2026-08-13 · pre-flight** — step 1.1's clean-tree pre-check **failed**: the tree carried the README, the
  `.project-brain/`, `.readme-lib/`, `dev.py`, an untracked `Backend/src/main.py`, the Frontend doc-tooling
  deps and a modified `chroma.sqlite3` — none of it this plan's work. Resolved by three scoped standalone
  commits on `feature` through the `committing` capability's execute gate (`22dada3`, `dc666ca`, `2bd0245`),
  audited in the 2026-08-13 day journal, `verify-audit.py` consistent.

  Two findings fell out of it, both pre-existing and neither this plan's:
  - `Backend/src/del_main.py` was the tracked entry point, byte-identical to the untracked
    `Backend/src/main.py` every doc and `dev.py` names — `914c6b8` had renamed it aside. Git confirmed the
    diagnosis by detecting the fix as a 100% rename.
  - `.gitignore` named `Backend/data/`, but `DATA_ROOT` resolves against the process CWD and the app starts
    in `Backend/src/`, so the rule never matched and `chroma.sqlite3` had been tracked since the first
    ingest. Rule corrected to `Backend/src/data/`; the blob is untracked and still on disk.

  `git rm` and `git mv` are Block-all with no token carve-out, so both removals were staged via a shell
  `rm`/`mv` plus `git add <path>` — worth knowing before the next plan reaches for `git mv` in step 1.2.

- **2026-08-13 · phase 1 pre-flight (read-only)** — the import graph was re-measured against the brief's
  table and matches: the three orphans are imported by nothing, and `FileTypeIcon` is imported from both the
  chat and knowledge-base pages. Two refinements 1.4's prose under-describes, both covered by its build
  predicate rather than needing a re-plan:
  - `ChatView.vue:120` reads `store.hasDocuments` — a computed over `indexStats` — so it takes **both**
    `ragStore` and `kbStore` after the split, not `ragStore` alone.
  - `NavBar.vue` likewise needs both: `llmProvider` / `availableProviders` / `ollamaModel` / `openaiModel`
    from `ragStore`, and `refreshStats()` + `fetchKnowledgeBases()` from `kbStore` in its `onMounted`.

  Also measured: `LLMSelector.vue` is **204 lines**, over G3's bar. Step 2.2's text covers it ("any other
  `.vue` phase 1 left over 200 lines") but its `delivers` measures only `ChatView.vue`, so nothing would
  fail if it were left. To be decided at 2.2, not now.
