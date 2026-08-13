# AGENTS.md — the project-context world

`project-context/` captures everything about **what adRAG is**, at a density that lets an agent rebuild
it from scratch. This file introduces that world and tells you how to move through it. It does **not**
list the rebuild steps — those live in one place only.

<br>

---

<br>

## What this bucket is

adRAG is a multi-stage RAG system: a Flask + LangGraph backend that plans, retrieves from a vector store,
a BM25 index and an entity graph, reranks with a cross-encoder, compresses, answers with citations, and
self-verifies grounding; plus a Vue 3 SPA that streams every stage live over Server-Sent Events.

Everything here is **regeneratable** — derived from `Backend/` and `Frontend/` by reading the code. That
is what makes it safe to refresh in place: if a doc and the code disagree, the code wins and the doc gets
fixed. The two things that are *not* regeneratable — the recorded rationale in `../decisions/` and the
solved-problem history in `../history/` — deliberately live outside this bucket.

<br>

---

<br>

## How to read it

Start at [`README.md`](README.md) for the map, then walk:

1. [`overview/`](overview/README.md) — what is being built and why; the non-goals matter as much as the goals.
2. [`architecture/`](architecture/README.md) — the component topology on both sides of the HTTP boundary.
3. [`runtime/`](runtime/README.md) — the flows you would otherwise have to re-derive from code: backend
   startup and the traps that let it come up looking healthy while being wrong, the eight-node query
   pipeline and its reflection retry loop, the SSE session bus, and ingestion.
4. [`features/`](features/README.md) — the per-feature specs, each naming the files that implement it.
5. [`api/`](api/README.md), [`data/`](data/README.md), [`design/`](design/README.md),
   [`conventions/`](conventions/README.md), [`operations/`](operations/README.md),
   [`security/`](security/README.md) — the reference areas, read as your task needs them.

Use [`codebase-map.md`](codebase-map.md) to jump straight to a directory. Consult
[`../decisions/ADRs/`](../decisions/ADRs/INDEX.md) for *why* a choice was made and
[`../history/`](../history/) for what has already been solved — reference them, never re-derive them.

<br>

---

<br>

## To actually rebuild adRAG

Follow **[`build-from-scratch.md`](build-from-scratch.md)** — the single structured reconstruction guide
with the real ordered steps, from prerequisites through install, configuration, first run, and
verification. This cookbook only points you there; keeping the steps in one file is what stops them
drifting across the four cookbook files.

<br>

---

<br>

## Writing into this bucket

Edit in place and keep it dense: real paths, real env-var names, real hex values, real payload shapes.
Skip what a glance at two source files makes obvious, but never drop a fact the rebuild needs. When you
add, move, or rename a doc, update the owning area's `README.md` — and [`README.md`](README.md)'s tree if
the structure changed — in the same edit. Anything you could not verify from the code gets an explicit
`TODO:` marker, not a plausible guess.

`Backend/documentation/` and `Frontend/Documentation/` are a separate, publishable layer. Read them as
input; never link to them from here.
