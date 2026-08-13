<div align="center">

# 🧬 project-context — what adRAG is

### The regeneratable knowledge that captures adRAG completely enough to rebuild it.

<br>

[![Bucket](https://img.shields.io/badge/bucket-regeneratable-10B981)](#)
[![Backend](https://img.shields.io/badge/backend-Flask%20%2B%20LangGraph-3776AB)](#)
[![Frontend](https://img.shields.io/badge/frontend-Vue%203-42b883)](#)

</div>

<br>

---

## Content Tree

<pre>
project-context — what adRAG is
│
├── <a href="#-1-the-project-in-one-paragraph">📖 1. The project in one paragraph</a>
│
├── <a href="#-2-where-to-look">🗺️ 2. Where to look</a>
│
├── <a href="#-3-the-tree">📁 3. The tree</a>
│
└── <a href="#-4-read-order">🚀 4. Read order</a>
</pre>

<br>

---

<br>

## 📖 1. The project in one paragraph

**adRAG** is a multi-stage Retrieval-Augmented Generation system. A user uploads PDF / DOCX / TXT / MD
documents; each is chunked and indexed simultaneously into three stores — a dense vector index, a BM25
keyword index, and an entity knowledge graph. A query then runs an eight-node LangGraph pipeline: a
Self-RAG **planner** decides whether to retrieve at all, **hybrid retrieval** queries all three stores,
an **aggregator** deduplicates, a **cross-encoder reranker** picks the top evidence, a **compressor**
fits it into the LLM window, a **reasoning agent** writes a cited answer, and a **self-reflection agent**
verifies the answer is grounded — looping back to retrieval (escalating to web search when the knowledge
base was useless) if it is not. Every stage emits a Server-Sent Event, so the Vue 3 frontend renders the
pipeline live as it runs.

This bucket is the **regeneratable** half of the brain: a code-reading agent can rebuild everything here
from `Backend/` and `Frontend/`. It captures the project so it *can* be rebuilt; the ordered rebuild
steps themselves live in [`build-from-scratch.md`](build-from-scratch.md).

<br>

---

<br>

## 🗺️ 2. Where to look

| Area | Holds |
|---|---|
| [`overview/`](overview/README.md) | The mission and non-goals, the domain glossary, the tech stack with the reason for each piece |
| [`architecture/`](architecture/README.md) | System topology, the backend module graph, the frontend component graph, and the boundary between them |
| [`runtime/`](runtime/README.md) | The dynamic behaviour — backend startup and its silent traps, the query pipeline's node-by-node flow and retry loop, the SSE event bus, and the ingestion/indexing flow |
| [`features/`](features/README.md) | One folder per feature: what it does, which files implement it, what it depends on, and its gotchas |
| [`api/`](api/README.md) | The wire contracts — every HTTP endpoint's request/response shape, and every SSE event type's payload |
| [`data/`](data/README.md) | The data model — the chunk/document record, the knowledge-base registry, and the `RAGState` object that flows through the pipeline |
| [`design/`](design/README.md) | The visual identity — palette, typography, spacing, radii, shadows, motion, dark/light handling, with real token values |
| [`conventions/`](conventions/README.md) | How code here is written and where files go |
| [`operations/`](operations/README.md) | Every environment variable, the storage layout on disk, and the build/run commands |
| [`security/`](security/README.md) | Trust boundaries, what is validated where, and the invariants that must not break |
| [`codebase-map.md`](codebase-map.md) | Directory-by-directory tour of the repository |
| [`build-from-scratch.md`](build-from-scratch.md) | **The reconstruction guide — the ordered rebuild steps** |

<br>

---

<br>

## 📁 3. The tree

```
project-context/
│
├── 📁 overview/                What adRAG is and why
│   ├── 📄 glossary.md           Domain vocabulary
│   ├── 📄 mission.md            Problem, users, goals, non-goals
│   ├── 📄 tech-stack.md         Every dependency + why it is there
│   └── 📄 README.md             Area index
│
├── 📁 architecture/            Static structure
│   ├── 📄 backend.md            Flask + LangGraph module topology
│   ├── 📄 frontend.md           Vue 3 component + store topology
│   ├── 📄 system-overview.md    End-to-end flows across the boundary
│   └── 📄 README.md             Area index
│
├── 📁 runtime/                 Dynamic behaviour
│   ├── 📁 backend-startup/      Import-time sequence + the four startup traps
│   ├── 📁 ingestion-indexing/   Upload → chunk → three-store index
│   ├── 📁 query-pipeline/       Node-by-node flow + reflection loop
│   ├── 📁 sse-event-bus/        Session queues and streaming
│   └── 📄 README.md             Area index
│
├── 📁 features/                One folder per feature
│   ├── 📁 chat-history/         localStorage-backed query history
│   ├── 📁 hybrid-retrieval/     Vector + BM25 + graph retrieval
│   ├── 📁 knowledge-base-management/  Upload, list, delete KBs
│   ├── 📁 llm-provider-selection/     OpenAI / Ollama switching
│   ├── 📁 pipeline-tracker/     Live stage visualisation
│   ├── 📁 self-rag-pipeline/    The planner → reflection pipeline
│   └── 📄 README.md             Feature catalog + dependency map
│
├── 📁 api/                     Wire contracts
│   ├── 📁 http/                 REST endpoints
│   ├── 📁 sse-events/           Streamed event types
│   └── 📄 README.md             Area index
│
├── 📁 data/                    Data model
│   ├── 📁 document-chunk/       The indexed chunk + its metadata
│   ├── 📁 kb-registry/          The knowledge-base JSON registry
│   ├── 📁 rag-state/            The LangGraph state object
│   └── 📄 README.md             Area index
│
├── 📁 design/                  Visual identity
│   ├── 📁 theme/                Palette, type, spacing, motion tokens
│   └── 📄 README.md             Area index
│
├── 📁 conventions/             How code is written
│   ├── 📁 code-style/           Python + Vue style rules
│   ├── 📁 project-layout/       Where a new file goes
│   └── 📄 README.md             Area index
│
├── 📁 operations/              How it runs
│   ├── 📁 configuration/        Every env var + storage paths
│   ├── 📁 run-and-build/        Dev, build, and production commands
│   └── 📄 README.md             Area index
│
├── 📁 security/                Trust and invariants
│   ├── 📁 trust-boundaries/     Where untrusted input crosses in
│   └── 📄 README.md             Area index
│
├── 📄 build-from-scratch.md    The ordered reconstruction guide
├── 📄 codebase-map.md          Directory-by-directory tour
├── 📄 AGENTS.md                Agent cookbook for this bucket
└── 📄 README.md                You are here
```

<br>

---

<br>

## 🚀 4. Read order

[`overview/`](overview/README.md) → [`architecture/`](architecture/README.md) →
[`runtime/`](runtime/README.md) → [`features/`](features/README.md) → then whichever of
[`api/`](api/README.md), [`data/`](data/README.md), [`design/`](design/README.md),
[`conventions/`](conventions/README.md), [`operations/`](operations/README.md), and
[`security/`](security/README.md) your task needs. [`codebase-map.md`](codebase-map.md) is the fastest
way to find *where* something lives once you know *what* you are looking for.
