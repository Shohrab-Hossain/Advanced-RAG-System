# Feature: Self-RAG pipeline

**Purpose:** answer a question from the indexed corpus with inline citations, deciding for itself whether
retrieval is even needed and verifying its own answer's grounding before returning it.

**Entry points:** `QueryInput.vue` submit → `ragStore.runQuery()` → `POST /api/query` (SSE) →
`rag_graph.invoke(initial_state)`.

**Implemented in:**

| Concern | File |
|---|---|
| Graph assembly + routing | `Backend/src/rag_pipeline/graph.py` |
| State shape | `Backend/src/rag_pipeline/state.py` |
| Planner | `Backend/src/rag_pipeline/generation/planner.py` |
| Retrieval fan-out | `Backend/src/rag_pipeline/retrieval/node.py` |
| Web search | `Backend/src/rag_pipeline/retrieval/web_node.py` |
| Aggregation | `Backend/src/rag_pipeline/ranking/aggregator.py` |
| Reranking | `Backend/src/rag_pipeline/ranking/reranker.py` |
| Compression | `Backend/src/rag_pipeline/generation/compressor.py` |
| Answer generation | `Backend/src/rag_pipeline/generation/reasoning.py` |
| Grounding verification | `Backend/src/rag_pipeline/generation/reflection.py` |
| HTTP + SSE | `Backend/src/app.py` (`/api/query`) |

**Inputs:** `{query: string, provider: "openai"|"ollama", model?: string}`.
**Outputs:** a stream of typed SSE events, terminated by
`done → {answer, sources[], metadata}` then `stream_end`.

**Behaviour:**

- Four LLM calls on the happy path — planner, compressor (only above 4000 chars), reasoning, reflection —
  all at `temperature=0`, all except the compressor in JSON mode.
- Three routing outcomes out of the planner: full retrieval, web-search-only, or direct answer with no
  retrieval at all.
- Up to 3 generation attempts (`MAX_REFLECTION_RETRIES=2`); an ungrounded answer with a useless knowledge
  base escalates the retry to include web search.
- An answer that stays ungrounded ships with the appended caveat
  `⚠️ *Some claims may not be fully supported by the retrieved documents.*`
- Only sources the model explicitly cited (`cited_sources` indices) are returned.

The node-by-node mechanism, the exact routing predicates, and the escalation heuristic are specified in
[`../../runtime/query-pipeline/README.md`](../../runtime/query-pipeline/README.md). The wire shapes are in
[`../../api/sse-events/README.md`](../../api/sse-events/README.md).

**Depends on:** [`hybrid-retrieval`](../hybrid-retrieval/README.md) for evidence,
[`llm-provider-selection`](../llm-provider-selection/README.md) for the model,
`core/events.py` for progress reporting, and an indexed corpus from
[`knowledge-base-management`](../knowledge-base-management/README.md).

**Gotchas:**

- **`final_answer` is the termination signal.** Setting it anywhere other than the reflection node's final
  branch would end the run early.
- **Retries do not improve retrieval.** `reflection_feedback` never reaches the retriever; only escalation
  to web search actually changes what the second pass sees.
- **`confidence` is self-reported by the LLM**, not measured. Do not treat it as a calibrated score.
- **Two config sources.** Nodes read `RETRIEVAL_TOP_K`, `RERANK_TOP_K`, `MAX_CONTEXT_CHARS`, and
  `MAX_REFLECTION_RETRIES` via `os.getenv` at import time, not via `Config`. Changing `Config` alone has no
  effect on them, and import-time reads mean an env change requires a restart.
- **Every node swallows its exceptions.** A silent degradation shows up as a `stage_error` event, so read
  the event log before concluding a stage "worked".
