<div align="center">

# 🧬 adRAG — Project Brain

### The durable record of what adRAG is, why it is built this way, and how to rebuild it.

<br>

[![Layer](https://img.shields.io/badge/layer-project--brain-10B981)](#)
[![Buckets](https://img.shields.io/badge/buckets-3-0EA5E9)](#-2-the-three-buckets)
[![Format](https://img.shields.io/badge/format-markdown-8B5CF6)](#)

</div>

<br>

---

## Content Tree

<pre>
adRAG — Project Brain
│
├── <a href="#-1-what-this-folder-is">📖 1. What this folder is</a>
│
├── <a href="#-2-the-three-buckets">🗂️ 2. The three buckets</a>
│   ├── <a href="#21-mutability-is-the-split">2.1 Mutability is the split</a>
│   └── <a href="#22-why-uppercase-child-folders">2.2 Why UPPERCASE child folders</a>
│
├── <a href="#-3-folder-structure">📁 3. Folder structure</a>
│
├── <a href="#-4-where-to-start">🚀 4. Where to start</a>
│
└── <a href="#%EF%B8%8F-5-how-it-is-maintained">🛠️ 5. How it is maintained</a>
</pre>

<br>

---

<br>

## 📖 1. What this folder is

Git history records *what changed*. This folder records *what adRAG is, why it is built that way, and
how to rebuild it* — the intent a diff cannot capture. It is written for the next agent or human who
arrives with zero context about the project.

The bar it is held to: **a fresh agent, given only this folder and an empty editor, could rebuild
adRAG from scratch — same architecture, conventions, look, data model, and decisions — without
asking a single question.** Anything that fails that bar is a gap to close, not a detail to skip.

adRAG itself is a multi-stage Retrieval-Augmented Generation system: a Flask + LangGraph backend
(`Backend/`) that plans, retrieves from three stores, reranks, compresses, answers, and self-verifies;
and a Vue 3 single-page app (`Frontend/`) that streams every pipeline stage live over Server-Sent
Events. The pitch, the stack, and the reasons live one level down in
[`project-context/`](project-context/README.md).

<br>

---

<br>

## 🗂️ 2. The three buckets

### 2.1 Mutability is the split

The brain is an umbrella over three buckets, separated by **how safely they can be regenerated**:

| Bucket | Mutability | Holds | Maintained by |
|---|---|---|---|
| [`project-context/`](project-context/README.md) | ◇ regeneratable | what the project **is** — overview, architecture, runtime, features, api, data, design, conventions, operations, security | the keeper agent, re-derived from the code |
| [`decisions/`](decisions/README.md) | ◆ durable | ADRs — the **why** behind load-bearing choices | appended one record per decision, never regenerated |
| `history/` | ◆ durable | solved problems ([`ISSUES/INDEX.md`](history/ISSUES/INDEX.md)) + completed plans ([`PLANS/INDEX.md`](history/PLANS/INDEX.md)) | the `issues-logging` and `task-planning` skills |

`decisions/` and `history/` sit **outside** `project-context/` on purpose: they capture reasoning a
code-reading agent cannot reconstruct, so a "rewrite the brain from scratch" — which touches only
`project-context/` — is physically unable to discard them.

### 2.2 Why UPPERCASE child folders

Casing carries meaning inside the durable buckets. An **uppercase** child folder (`ADRs/`, `ISSUES/`,
`PLANS/`) marks append-only content that is never regenerated; lowercase marks regeneratable content.
One glance at the tree tells you what is safe to rewrite.

<br>

---

<br>

## 📁 3. Folder structure

```
.project-brain/
│
├── 📁 project-context/         Regeneratable knowledge — what adRAG is
│   ├── 📁 overview/             Mission, glossary, tech stack + why
│   ├── 📁 architecture/         Systems, components, boundaries
│   ├── 📁 runtime/              Backend startup, query pipeline, SSE bus, ingestion
│   ├── 📁 features/             One folder per feature
│   ├── 📁 api/                  HTTP endpoints + SSE event contract
│   ├── 📁 data/                 Chunks, KB registry, pipeline state
│   ├── 📁 design/               Theme, palette, typography, motion
│   ├── 📁 conventions/          Code style + project layout rules
│   ├── 📁 operations/           Config, env vars, build & run
│   ├── 📁 security/             Trust boundaries and invariants
│   ├── 📄 codebase-map.md       Directory-by-directory tour
│   ├── 📄 build-from-scratch.md The ordered reconstruction guide
│   ├── 📄 AGENTS.md             Agent cookbook for this bucket
│   └── 📄 README.md             Human cookbook for this bucket
│
├── 📁 decisions/               Durable ADRs — append only
│   └── 📁 ADRs/                 INDEX.md + entries/NNN-slug.md
│
├── 📁 history/                 Durable history — append only
│   ├── 📁 ISSUES/               Solved problems
│   └── 📁 PLANS/                Completed plans
│
├── 📄 AGENTS.md                How an agent operates this brain
└── 📄 README.md                You are here
```

<br>

---

<br>

## 🚀 4. Where to start

1. [`project-context/README.md`](project-context/README.md) — what adRAG is and how the knowledge is laid out.
2. [`project-context/overview/mission.md`](project-context/overview/mission.md) — the problem, the users, the non-goals.
3. [`project-context/architecture/system-overview.md`](project-context/architecture/system-overview.md) — how the pieces connect.
4. [`decisions/ADRs/INDEX.md`](decisions/ADRs/INDEX.md) — why the load-bearing choices were made.
5. [`project-context/build-from-scratch.md`](project-context/build-from-scratch.md) — when you actually need to rebuild it.

<br>

---

<br>

## 🛠️ 5. How it is maintained

`project-context/` is kept in step with the code as the project is built — a new feature updates its
feature spec, a new endpoint updates the API contract, a theme change updates the design tokens. The
durable buckets are **append-only**: add an ADR or a history entry, never regenerate one. An existing
ADR is edited only to mark it superseded by a later record.

Operating rules for working in this repository — how to run, build, and test it, and what never to do —
belong in the project's `.claude/CLAUDE.md`, not here. Agents should read
[`AGENTS.md`](AGENTS.md) next.
