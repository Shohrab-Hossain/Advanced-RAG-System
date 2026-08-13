# ADR-001: LangGraph state machine for the RAG pipeline
Date: 2026-08-13 · Status: accepted

> Reconstructed from the code on 2026-08-13, not recorded at decision time. Context and consequences are
> grounded in `Backend/src/rag_pipeline/graph.py` and `state.py`; the rejected alternatives are inferred,
> not documented — see the TODO below.

## Context

The answer flow is not linear. Three things force branching and looping:

1. The **planner** must be able to skip retrieval entirely for general-knowledge questions, or route
   straight to web search — three distinct entry points into the rest of the pipeline.
2. The **reflection** step must be able to send an ungrounded answer *back* to retrieval, up to a retry
   budget — a backward edge.
3. Every step needs to read and write a shared, growing bundle of intermediate results (four document
   lists, the merged set, the reranked context, the compressed string, the answer, the grounding verdict)
   without each function needing a bespoke signature.

Expressing that as nested `if`/`while` around sequential function calls means the control flow is scattered
across the functions themselves, and adding a step means editing its neighbours.

## Decision

Model the pipeline as a compiled LangGraph `StateGraph` over a single `RAGState` TypedDict
(`Backend/src/rag_pipeline/graph.py`). Nodes are plain functions `(state) -> dict` that return only the
keys they modify; all routing lives in two functions, `_route_planner` and `_route_reflection`, attached as
conditional edges. The compiled graph is a module singleton, `rag_graph`, invoked once per query.

## Alternatives considered

TODO: no record exists in the repository of what else was weighed. The plausible options — a hand-written
sequential orchestrator, or LangChain's chain/agent abstractions — are **inferred, not documented**.
Confirm with the owner.

## Consequences

**Makes easy**

- The whole flow is legible in one file; the module docstring is an accurate ASCII diagram of it.
- Adding a node is `add_node` + one edge, with no change to its neighbours.
- Nodes are independently testable pure-ish functions over a dict.
- The retry loop is one conditional edge rather than a loop wrapped around six calls.

**Makes hard / watch out for**

- **Termination is implicit.** `_route_reflection` returns `END` iff `state["final_answer"]` is set. Any
  node that writes `final_answer` ends the run — a subtle coupling that is easy to break.
- **The only loop guard is `retry_count`.** Nothing else bounds the cycle inside the graph; the outer
  180-second SSE queue timeout in `app.py` is the last defence.
- **`TypedDict` is unenforced at runtime** — a typo'd return key is silently merged into the state.
- **Returned keys overwrite rather than accumulate**, so a retry discards the previous attempt's documents
  instead of adding to them.
- The pipeline is bound to LangGraph's version behaviour; `requirements.txt` pins only `langgraph>=0.1.0`.
