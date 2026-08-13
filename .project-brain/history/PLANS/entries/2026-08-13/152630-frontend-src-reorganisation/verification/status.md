---
plan: 152630-frontend-src-reorganisation
verdict: none
stale: false
predicates: 3
gates: 3
failing: 0
steps: 10
notDelivered: 0
awaitingJudgement: 0
---

# 🔍 Verification — Reorganise Frontend/src/ onto the vue-file-tree preference

| Field | Value |
|:--|:--|
| **🚦 Where it stands** | ⏳ **3 gate(s) not yet judged** |
| **⚖️ Verdict on record** | *none recorded* |
| **🎚 Effort bought** | `report` · `per-phase` · `single` — see [Turning it down](#-turning-it-down) |
| **📋 The plan** | what is being built → [`plan.md`](plan.md) |

<br>

---

## 📊 SUMMARY

> *A **gate** must hold before the plan can close. A **report** is recorded either way. A predicate with no live check is settled by its steps being marked done — which proves nothing on its own.*

| Bar | Progress | Detail |
|:--|:-:|:--|
| **Steps&nbsp;delivered** | `░░░░░░░░░░`<br>**0%** | 0 / 5 finished steps delivered what they promised *(of 10 total)* |
| **Gates&nbsp;holding** | `░░░░░░░░░░`<br>**0%** | 0 / 3 gates |
| **Live&nbsp;checks** | `░░░░░░░░░░`<br>**0%** | 0 / 3 predicates settled by a command that can fail |

**🔢 Predicate counts**

| ✅&nbsp;Holds | 🔴&nbsp;Failing | 👁&nbsp;Noted&nbsp;false | ⏭&nbsp;Skipped | ⏳&nbsp;Not&nbsp;yet | ⏳&nbsp;Not&nbsp;judged |
|:--:|:--:|:--:|:--:|:--:|:--:|
| 0 | 0 | 0 | 0 | 0 | 3 |

<br>

---

## 🚶 THE WALK — did every step do what it promised?

> *One row per step. **What it promised** is the step's own `delivers` declaration; **Did it?** is that declaration checked against the repo -- shown only once the step has FINISHED, since a deliverable that holds before its step runs was satisfied on arrival, not earned. Three of the four shapes cost nothing — only 👁&nbsp;*An agent's eyes* buys an agent.*

### ▊ Phase 1 — Reorganise the tree

| Step | What it promised to deliver | How | Step status | Did it? |
|:--|:--|:--|:--:|:--:|
| **1.1** | git rev-parse --verify claudesh/frontend-src-tree | ⚙️&nbsp;A command | ✅&nbsp;Done | ⏳&nbsp;Awaiting&nbsp;judgement |
| **1.2** | Frontend/src/store/index.js *(+16 more)* | 📄&nbsp;A file | ✅&nbsp;Done | ⏳&nbsp;Awaiting&nbsp;judgement |
| **1.3** | Frontend/src/subsystems/rag/ragApi.js — contains `streamQuery` *(+5 more)* | 📄&nbsp;A file | ✅&nbsp;Done | ⏳&nbsp;Awaiting&nbsp;judgement |
| **1.4** | cd Frontend && npm run build | ⚙️&nbsp;A command | ✅&nbsp;Done | ⏳&nbsp;Awaiting&nbsp;judgement |
| **1.5** | *no command can confirm a route RENDERS correctly — the build proves imports res…* | 👁&nbsp;An agent's eyes | 🔄&nbsp;In progress | · |
| **1.6** | git ls-files Frontend/Documentation | grep -q README.md | ⚙️&nbsp;A command | ✅&nbsp;Done | ⏳&nbsp;Awaiting&nbsp;judgement |
| **1.7** | .claude/CLAUDE.md — contains `subsystems/` *(+2 more)* | 📄&nbsp;A file | ⬜&nbsp;Not started | · |

### ▊ Phase 2 — Split the oversized files

| Step | What it promised to deliver | How | Step status | Did it? |
|:--|:--|:--|:--:|:--:|
| **2.1** | awk 'END{exit !(NR<200)}' Frontend/src/pages/knowledge-base/views… *(+1 more)* | ⚙️&nbsp;A command | ⬜&nbsp;Not started | · |
| **2.2** | awk 'END{exit !(NR<200)}' Frontend/src/pages/chat/views/ChatView.… | ⚙️&nbsp;A command | ⬜&nbsp;Not started | · |
| **2.3** | cd Frontend && npm run build *(+1 more)* | ⚙️&nbsp;A command | ⬜&nbsp;Not started | · |

**Legend**

| Icon | Means |
|:--:|:--|
| 📄 **A file** | the named file exists (and says the named thing) |
| ⚙️ **A command** | a command decides it — free, and it can fail |
| 🗑 **A removal** | the named path is gone |
| 👁 **An agent's eyes** | **the only shape that costs tokens** — no command can decide it |
| — **Self-declaring** | a command step: the command IS the work and its own proof |

<br>

---

## 🔒 THE PLAN-LEVEL GOALS

> *These are about the plan as a WHOLE — whether it achieved what it set out to. Per-step proof lives on the steps above, which is what lets this list stay short. Click an id to jump to its full text below.*

| # | Role | What it asserts | How it is settled | Effort | Status |
|:--|:--:|:--|:--|:--|:--:|
| [**G1**](#g1) | 🔒&nbsp;Gate | Every file under Frontend/src/ sits where the vue-file-tree preference's ownership rule p… | ⚠️&nbsp;No check | `report`<br>`per-phase`<br>`single` | ⏳&nbsp;Not&nbsp;judged |
| [**G2**](#g2) | 🔒&nbsp;Gate | The reorganisation is behaviour-preserving: the app builds with exit 0 and all four route… | ⚠️&nbsp;No check | `report`<br>`per-phase`<br>`single` | ⏳&nbsp;Not&nbsp;judged |
| [**G3**](#g3) | 🔒&nbsp;Gate | No .vue file under Frontend/src/ exceeds 200 lines carrying logic the preference says bel… | ⚠️&nbsp;No check | `report`<br>`per-phase`<br>`single` | ⏳&nbsp;Not&nbsp;judged |

**Legend**

| Icon | Means |
|:--:|:--|
| 🔒 **Gate** | **blocks the close** while it is red |
| 👁 **Report** | **never blocks** — reported for the record |
| ✅ **Live check** | a command runs and can fail |
| ⚠️ **No check** | falls back to step terminality — which a plan satisfies by construction the moment its steps are marked done |
| ⚠️ **Untrusted check** | a check exists but has never been observed both red and green, so it cannot tell a real finding from a broken command |
| ⚠️ **Reads nothing** | `covers` is empty, so nothing makes it re-run |
| ⏭ **Skipped** | taken out of the run by a recorded decision |

<br>

---

## 📖 THE PREDICATES IN FULL

> *The complete text of every predicate, in contract order. Linked from the table above.*

<a id="g1"></a>

### 🔒 G1 — ⏳&nbsp;Not&nbsp;judged

> Every file under Frontend/src/ sits where the vue-file-tree preference's ownership rule puts it — no top-level similarity bucket (components/ · views/ · stores/ · services/) remains, single-page-owned components live under their page, the three genuinely cross-page components live in shared/, and the RAG and knowledge-base capabilities live as subsystems with their own state — AND .claude/CLAUDE.md's Layout and Conventions sections describe that tree rather than the retired one, so a fresh agent is not instructed to rebuild the buckets this plan removed.

| | |
|:--|:--|
| **Role** | 🔒 **Gate** — **blocks the close** while it is red |
| **How it is settled** | ⚠️ **No check** — falls back to step terminality — which a plan satisfies by construction the moment its steps are marked done |
| **Effort** | `trust: report` · `reach: per-phase` · `independence: single` |

<a id="g2"></a>

### 🔒 G2 — ⏳&nbsp;Not&nbsp;judged

> The reorganisation is behaviour-preserving: the app builds with exit 0 and all four routes render and function as they did before the move, including the SSE pipeline stage animation and the knowledge-base index stats.

| | |
|:--|:--|
| **Role** | 🔒 **Gate** — **blocks the close** while it is red |
| **How it is settled** | ⚠️ **No check** — falls back to step terminality — which a plan satisfies by construction the moment its steps are marked done |
| **Effort** | `trust: report` · `reach: per-phase` · `independence: single` |

<a id="g3"></a>

### 🔒 G3 — ⏳&nbsp;Not&nbsp;judged

> No .vue file under Frontend/src/ exceeds 200 lines carrying logic the preference says belongs in a camelCase sibling module, and no split uses the forbidden <name>.script.js or <name>.style.css forms.

| | |
|:--|:--|
| **Role** | 🔒 **Gate** — **blocks the close** while it is red |
| **How it is settled** | ⚠️ **No check** — falls back to step terminality — which a plan satisfies by construction the moment its steps are marked done |
| **Effort** | `trust: report` · `reach: per-phase` · `independence: single` |

<br>

---

## 🎚 TURNING IT DOWN

> *Verification depth is a **purchase**, not a fixed cost. Set it **before** a run — not after paying for one.*

Edit `contract.json`: plan-wide under `verification`, or per predicate.

| Axis | Values | What it buys |
|:--|:--|:--|
| **`trust`** | `report` · `rederive` | **report** = believe the executor's own report · **rederive** = re-derive it from the artifacts |
| **`reach`** | `per-step` · `per-phase` · `spot` | **per-step** = check every step · **per-phase** = check at phase boundaries · **spot** = check a sample |
| **`independence`** | `single` · `double` | **single** = one pass · **double** = a second, independent pass |

**⏭ To take a predicate out of the run entirely**, give it a `skip`:

```jsonc
{ "id": "D7", "kind": "completeness", "text": "…",
  "skip": { "by": "owner", "reason": "throwaway plan — not worth an audit" } }
```

A skipped predicate is **reported as skipped, never gates, and never reads as satisfied**. The reason travels with the plan, so a later reader can tell a **decision** from an **oversight** — which is the whole point of the field.

<br>

---

## 🧾 AUDIT TRAIL

*No verdict recorded yet.*

<br>

---

<sub>Rendered from `contract.json` ⋈ `state.json` ⋈ `verdicts/` by `render-status.py`. **Never authored** — editing this file changes nothing.</sub>
