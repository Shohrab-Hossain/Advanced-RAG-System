---
id: 152630-frontend-src-reorganisation
title: Reorganise Frontend/src/ onto the vue-file-tree preference
status: done
priority: blocking
type: refactor
created: 2026-08-13
updated: 2026-08-13
owner: Shohrab + Claude
branch: claudesh/frontend-src-tree
---

# 🗂 Reorganise Frontend/src/ onto the vue-file-tree preference

| Field | Value |
|:--|:--|
| **⚡ Priority** | 🔴 **Blocking** |
| **🎯 Goal** | Move Frontend/src/ from the stock Vue CLI similarity buckets onto the ownership-based tree the vue-file-tree preference specifies, behaviour-preserving. |
| **📖 Brief** | context & rationale → [`brief.md`](brief.md) |

<br>

---

## 📊 PROGRESS

> *Two bars: **Plan** counts phases; **Phase** counts the current phase's steps. The Phase bar, status counts,
> and Focus are for the active phase only and reset when a new phase begins.*

| Bar | Progress | Detail |
|:--|:-:|:--|
| **Plan** | `██████████`<br>**100%** | **Phase 2 of 2** · 2 phases complete |
| **Phase&nbsp;2** | `██████████`<br>**100%** | 3 / 3 steps · ✅ Done |

**🔢 Status counts** *(Phase 2)*

| ✅&nbsp;Done | 🔄&nbsp;Processing | ⏳&nbsp;Not&nbsp;started | ⏸&nbsp;Paused | 🚫&nbsp;Blocked | ❌&nbsp;Failed | ⏭&nbsp;Skipped |
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 3 | 0 | 0 | 0 | 0 | 0 | 0 |

**🎯 Focus** *(Phase 2)*

- **▶ Now** — Step 2.1 - splitting KnowledgeBaseView.vue (371 lines) into page-owned components + a knowledgeBaseView.js sibling
- **⏭ Next** — Step 2.2 - re-measure ChatView.vue and any other .vue still over 200 lines
- **🚧 Blockers** — none

<br>

---

## 🧱 PHASES

| # | Phase&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Progress&nbsp;&nbsp;&nbsp;&nbsp; | Status&nbsp;&nbsp;&nbsp;&nbsp; | Scope |
|:--:|:--|:--:|:--:|:--|
| **1** | **Reorganise the tree** | `██████████`<br>**100%** | ✅&nbsp;Done |  |
| **2** | **Split the oversized files** | `██████████`<br>**100%** | ✅&nbsp;Done |  |

<br>

---

## 🔎 VERIFICATION

> *Derived from the walk — never authored. Each step declared what it would produce; this is what `walk-plan.py` found on disk.*

| Phase | Steps | Outstanding |
|:--:|:--|:--|
| **1** | 1&nbsp;awaiting · 6&nbsp;settled | 1.5 |
| **2** | 3&nbsp;none | — |

<br>

---

## 🧭 STEPS

> *`Status` — did the work happen (written by `mark-step`). `Verified` — did anything confirm it, and does that still hold (**derived**, never written). `How` — by what means it was to be confirmed. A passing outcome reads **verified** whichever way it was reached; `How` is what says which.*

### ▊ Phase 1 · Reorganise the tree

| # | Status&nbsp;&nbsp;&nbsp;&nbsp; | Verified&nbsp;&nbsp; | Executor | How | Ev | Step / Substep&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Notes *(detail → LOG)* |
|:--|:--|:--|:--|:--|:--|:--|:--|
| 1.1 | ✅&nbsp;Done | ✅&nbsp;verified | orch·maker | auto | — | Run the git-managing branch gate (.claude/skills/csh-git-managing/references/capabilities/branching.md) and create branch 'claudesh/frontend-src-tree' off 'feature'. This is a structural, cross-cutting change touching every file under Frontend/src/, so the branch exists BEFORE the first edit. git-guard blocks git writes without a single-use token; write the token, then switch. No content is edited in this step. |  |
| 1.2 | ✅&nbsp;Done | ✅&nbsp;verified | orch·maker | auto | — | Create the target skeleton and MOVE all 20 files with 'git mv' — no content edits at all, imports stay broken until 1.4. Targets: stores/ui.js -> store/index.js; components/{NavBar,ModalDialog,FileTypeIcon}.vue -> shared/components/<Name>/<Name>.vue; views/HomeView.vue -> pages/home/views/; views/ChatView.vue -> pages/chat/views/; components/{QueryInput}.vue -> pages/chat/components/QueryInput/; components/{PipelineTracker,StageRow}.vue -> pages/chat/components/PipelineTracker/; components/{ResultDisplay,SourceCard}.vue -> pages/chat/components/ResultDisplay/; views/KnowledgeBaseView.vue -> pages/knowledge-base/views/; views/ConfigView.vue -> pages/configuration/views/; components/LLMSelector.vue -> pages/configuration/components/LLMSelector/; services/api.js and stores/rag.js -> subsystems/rag/ (unsplit for now, split in 1.3). Then 'git rm' the three orphans FileUpload.vue, KnowledgeBases.vue, StatBadge.vue — nothing imports them and KnowledgeBaseView.vue inlines its own versions of all three; git history keeps them. Leave App.vue, main.js, assets/main.css and router/index.js where they are. Create NO empty folders — as-needed depth. | needs 1.1 |
| 1.3 | ✅&nbsp;Done | ✅&nbsp;verified | orch·maker | auto | — | Split the two moved files that 1.2 left whole, into the four flat subsystem files. subsystems/rag/api.js -> ragApi.js (streamQuery, getProviders, healthCheck) + kbApi.js (uploadFile, getDocuments, clearDocuments, getKnowledgeBases, deleteKnowledgeBase), the latter moving to subsystems/knowledge-base/. subsystems/rag/rag.js -> ragStore.js (query state, the STAGES constant, pipeline progress, provider selection) + kbStore.js (documents, KB list, upload progress), the latter to subsystems/knowledge-base/. getProviders and healthCheck go with ragApi.js: the provider is carried on the RAG query itself and healthCheck hits the same backend. Each subsystem holds FLAT files — do NOT create services/ or store/ subfolders inside them, each would hold one file. Keep both stores in Pinia setup style, keep the axios client shape, keep every exported name so 1.4 is a pure path rewrite. | needs 1.2 |
| 1.4 | ✅&nbsp;Done | ✅&nbsp;verified | orch·maker | auto | — | Rewrite every import path across Frontend/src/ to the tree 1.2 and 1.3 produced, and fix router/index.js's four lazy route imports to point at pages/<name>/views/<Name>View.vue. Every component that consumed useRagStore now imports from subsystems/rag/ragStore or subsystems/knowledge-base/kbStore depending on which half of the split it uses — KnowledgeBaseView and its upload path take kbStore, ChatView and the pipeline components take ragStore, ConfigView and LLMSelector take ragStore for providers. NavBar imports healthCheck from subsystems/rag/ragApi and useUiStore from store/index. App.vue imports NavBar and ModalDialog from shared/components/. This step is path rewrites only — no logic, no template, no styling change. The build passing is the proof every import resolves. | needs 1.3 |
| 1.5 | ✅&nbsp;Done | 🕓&nbsp;awaiting | orch·maker | human | — | Boot the app ('npm run serve' in Frontend, backend on its port) and confirm all four routes render as they did before the move: / (home), /chat (query input, pipeline tracker, result display), /knowledge-base (drop zone, index stats, KB list), /configuration (LLM selector). A build passing only proves imports resolve — it does not prove a store binding survived the split. Check specifically that the pipeline stages animate on a query and that the KB page's stats populate, since those are the two surfaces the rag.js split touches. | needs 1.4 |
| 1.6 | ✅&nbsp;Done | ✅&nbsp;verified | orch·maker | auto | — | Rename Frontend/documentation/ to Frontend/Documentation/ with 'git mv', matching the root-file-tree preference's vocabulary. Windows is case-insensitive on paths so this must go through git to land — verify with 'git ls-files'. Do NOT rewrite the docs' contents here; Frontend/Documentation/README.md is known stale (it describes Vite, npm run dev and port 5173 against a Vue CLI / npm run serve / port 8080 reality) and fixing it is separate work. | needs 1.1 |
| 1.7 | ✅&nbsp;Done | ✅&nbsp;verified | orch·maker | auto | — | Update .claude/CLAUDE.md so it describes the tree that now exists. TWO sections are wrong the moment 1.4 lands, and both must change. (a) LAYOUT — the Frontend/src/ subtree lists 'components/ (12 components)', 'views/ (4 pages)', 'stores/' and 'services/'; replace with store/ · shared/components/ · subsystems/{rag,knowledge-base}/ · pages/{home,chat,knowledge-base,configuration}/, and drop the three deleted orphans from the component count. (b) CONVENTIONS TO MATCH — the 'Where a new file goes' paragraph says 'a page -> src/views/<Name>View.vue plus a lazily-imported router entry; a component -> flat in src/components/, no sub-folders'. Every clause is now false. Replace with the ownership rule (a folder exists because something owns what is in it), one-folder-per-component, the page/subsystem line (a page may own views/, a subsystem never does), and where a new store goes (app-shell state in store/, capability state with its subsystem). Keep the file's existing voice and formatting conventions; this is a targeted edit of two sections, NOT a refresh of the whole brief. Do not touch the guardrails, stack or commands sections. | needs 1.5 |

### ▊ Phase 2 · Split the oversized files

| # | Status&nbsp;&nbsp;&nbsp;&nbsp; | Verified&nbsp;&nbsp; | Executor | How | Ev | Step / Substep&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Notes *(detail → LOG)* |
|:--|:--|:--|:--|:--|:--|:--|:--|
| 2.1 | ✅&nbsp;Done | — | orch·maker | auto | — | Split pages/knowledge-base/views/KnowledgeBaseView.vue (371 lines before the move). Its template holds four separable sections — the upload drop zone, the unified upload/processing/indexing progress bar, the three index-stat cards, and the KB list — and its script holds four commented blocks (drag handlers, progress label/pct, upload helpers, KB management). Extract the template sections to page-owned components under pages/knowledge-base/components/<Name>/<Name>.vue, and move the pure logic to a camelCase sibling module knowledgeBaseView.js beside the view. Per the preference: the script is NEVER split into a .script.js — reactivity, template and lifecycle stay in the .vue, only pure functions leave. If styles are split, use a camelCase .css sibling imported as <style scoped src="./x.css"> and KEEP the scoped attribute; the <name>.style.css form is never used. Target under 200 lines for the view. | 371 -> 70 lines. Extracted UploadPanel, IndexStats, KnowledgeBaseList; pure helpers to views/knowledgeBaseView.js. View owns the data and passes finished view-models down, so no component imports upward into views/. · needs 1.5 |
| 2.2 | ✅&nbsp;Done | — | orch·maker | auto | — | Re-measure pages/chat/views/ChatView.vue after phase 1 (268 lines before the move) and split it the same way if it is still over 200 — its chat-history and message-list handling are the candidates for a camelCase chatView.js sibling. If phase 1's ragStore/kbStore split already brought it under, record that in the note and mark this step skipped with the measured line count as the reason. Apply the same rule to any other .vue phase 1 left over 200 lines. | ChatView 270 -> 130 (ChatHistorySidebar component + chatView.js PIPELINE_STEPS); its forbidden <style scoped> block moved to chatHistorySidebar.css imported via <style scoped src>. LLMSelector measured 204 and LEFT AS IS: its 38-line script is entirely computed/store-mutation/interval-lifecycle, so it carries no pure logic the preference permits moving to a sibling module - which is what G3 condemns. Splitting its two provider cards would need ~8 props to parameterise real differences. · needs 2.1 |
| 2.3 | ✅&nbsp;Done | — | orch·maker | human | — | Re-verify after the splits: the build passes and all four routes still render, with the same two focus surfaces as 1.5 (pipeline stages animate on a query, KB page stats populate). This catches a split that compiled but dropped a prop or a reactive binding. | Owner confirmed all four routes behave after the component extractions: sidebar slide-in, file-card dates, emit-backed delete/clear-all, pipeline animation, KB stats. · needs 2.2 |

<br>

---

## ✅ DEFINITION OF DONE

*The plan is done when every predicate below holds — re-derived from the files, not from the status table.*

- [x] **G1** — Every file under Frontend/src/ sits where the vue-file-tree preference's ownership rule puts it — no top-level similarity bucket (components/ · views/ · stores/ · services/) remains, single-page-owned components live under their page, the three genuinely cross-page components live in shared/, and the RAG and knowledge-base capabilities live as subsystems with their own state — AND .claude/CLAUDE.md's Layout and Conventions sections describe that tree rather than the retired one, so a fresh agent is not instructed to rebuild the buckets this plan removed.
- [x] **G2** — The reorganisation is behaviour-preserving: the app builds with exit 0 and all four routes render and function as they did before the move, including the SSE pipeline stage animation and the knowledge-base index stats.
- [x] **G3** — No .vue file under Frontend/src/ exceeds 200 lines carrying logic the preference says belongs in a camelCase sibling module, and no split uses the forbidden <name>.script.js or <name>.style.css forms.

<br>

---

## 🌿 GIT

**Branch lineage**

| Field | Value |
|:--|:--|
| **Parent branch** | `feature` |
| **Active branch** | `claudesh/frontend-src-tree` |
| **Merges into** | `feature` |
