# Runtime: the query pipeline

The compiled LangGraph workflow in `Backend/src/rag_pipeline/graph.py`. One `RAGState` dict is threaded
through eight nodes; each returns only the keys it modifies, and LangGraph merges them.

<br>

## Topology

```
                planner
                   │
      ┌────────────┼────────────────────┐
 retrieve=True  use_external only   neither
      │            │                    │
  retrieval ──► external_tools ──► aggregate ──► rerank ──► compress ──► reason ──► reflect
      ▲                                                                               │
      └──────────────── not grounded AND retry budget remains ────────────────────────┘
                                                                                       │
                                                                                  final_answer set
                                                                                       ▼
                                                                                      END
```

Entry point: `planner`. Fixed edges: `retrieval → external_tools`, `external_tools → aggregate`,
`aggregate → rerank → compress → reason → reflect`.

Two conditional edges carry all the branching:

- **`_route_planner`** — returns `"retrieval"` when `state["retrieve"]` (default `True`), else
  `"external_tools"` when `use_external`, else `"aggregate"`. That third path is the *direct answer* mode:
  no retrieval at all, so `aggregate` merges empty lists and the reasoning node falls through to its
  no-context branch.
- **`_route_reflection`** — returns `END` if `state["final_answer"]` is truthy, else `"retrieval"`.
  **The presence of `final_answer` *is* the termination signal**; there is no separate done flag. A node
  that accidentally set `final_answer` early would end the run.

Note that `retrieval` always flows into `external_tools`, which no-ops itself and emits a `stage_skip`
when `use_external` is false. This keeps the edge set static while making web search optional.

<br>

## Node by node

| # | Node | Reads | Writes | Emits |
|---|---|---|---|---|
| 1 | `planner_node` | `query`, `provider`, `ollama_model` | `retrieve`, `use_external`, `query_type` | `stage_start` → `stage_complete` \| `stage_error` |
| 2 | `retrieval_node` | `query`, `retrieve` | `vector_docs`, `bm25_docs`, `graph_docs` | `stage_start` → `retrieval_result`, or `stage_skip` |
| 3 | `external_tools_node` | `query`, `use_external` | `web_docs` | `stage_start` → `stage_complete` \| `stage_skip` \| `stage_error` |
| 4 | `aggregator_node` | the four doc lists | `all_docs` | `stage_start` → `stage_complete` |
| 5 | `reranker_node` | `query`, `all_docs` | `context` | `stage_start` → `stage_complete` \| `stage_error` |
| 6 | `compressor_node` | `query`, `context`, `provider` | `compressed_context` | `stage_start` → `stage_complete` \| `stage_error` |
| 7 | `reasoning_node` | `query`, `compressed_context`, `context`, `provider` | `answer`, `sources` | `stage_start` → `stage_complete` \| `stage_error` |
| 8 | `reflection_node` | `query`, `answer`, `context`, `retry_count`, `use_external` | `grounded`, `reflection_feedback`, `retry_count`, and on the final pass `final_answer`, `final_sources`, `pipeline_metadata` | `stage_start` → `stage_complete` → `retry` \| `finalize` \| `stage_error` |

The `stage` values in the emitted payloads are `planner`, `retrieval`, `external_tools`, `aggregator`,
`reranker`, `compressor`, `reasoning`, `reflection` — matching the frontend's `STAGES` ids exactly.

<br>

## The mechanisms worth knowing

**Planner (Self-RAG decision).** A JSON-mode LLM call returns
`{retrieve, use_external, query_type, reasoning}`. The system prompt defines `retrieve=true` as
"about user-uploaded domain documents" and `retrieve=false` as general world knowledge, math, greetings,
and coding questions; `use_external=true` is reserved for recent events and live data. Four worked
examples are inlined in the prompt. On any exception it falls back to
`{retrieve: True, use_external: False, query_type: "factual"}` — i.e. the safe, retrieve-everything path.

**Hybrid retrieval fan-out.** Sequential calls (despite the module docstring saying "in parallel"):
`vector_store.search(query, top_k=10)`, `bm25_store.search(query, top_k=10)`,
`graph_store.search(query, top_k=max(10 // 2, 3))` → 5. Results stay in three separate lists until
aggregation.

**Deduplication.** `aggregator_node` hashes each document's `content` with MD5
(`encode("utf-8", errors="replace")`) and keeps the copy with the highest `score` per hash, then sorts
descending by `score`. Because `score` scales differ per store (cosine ≈ 0–1, BM25 unbounded, graph weight
counts), this ordering is only a rough pre-filter — the reranker is what actually establishes relevance.

**Cross-encoder reranking.** All `(query, content)` pairs go through
`CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2").predict()`; documents get a `rerank_score`, are
sorted descending, and the top `RERANK_TOP_K` (5) become `context`. The model is lazily loaded into the
module-global `_reranker`. **`rerank_score` can be negative** — ms-marco emits negative logits for
irrelevant pairs — and the reflection node depends on that sign. On failure it falls back to the
`score`-sorted top-k.

**Conditional compression.** Documents are formatted as `[i] <label>\n<content>` blocks joined by
`\n\n---\n\n`. If the total is `<= MAX_CONTEXT_CHARS` (4000) it is passed through unchanged and the
`stage_complete` event says "Context already within limit". Only above that does an LLM call compress it —
and the input to that call is itself truncated to the first 10,000 characters. On failure the fallback is a
hard slice to `MAX_CONTEXT_CHARS`.

**Answer generation.** A JSON-mode call returns
`{answer, confidence, cited_sources, key_facts, is_sufficient}`. A `sources` list is built from `context`
with 1-based `index`, `file_name`, `source_type`, `url`, `page`, `rerank_score`, `content_preview` (first
250 chars) and full `content`. Crucially, **only sources whose index appears in `cited_sources` are
returned** — if the model cited nothing, the answer ships with zero sources. Two fallbacks exist: no
context at all → a plain direct-answer call with empty sources; JSON parse failure → an unstructured
prompt whose result returns *all* sources.

**Reflection, retry, and escalation.** A strict JSON-mode grounding check returns
`{grounded, confidence, issues, feedback, should_retry}`. Then:

```
will_retry        = (not grounded) and should_retry and (retry_count < MAX_REFLECTION_RETRIES)
max_rerank        = max(rerank_score over context, default None)
kb_insufficient   = len(context) == 0 or (max_rerank is not None and max_rerank < 0)
escalate_external = will_retry and kb_insufficient and not state["use_external"]
```

If `will_retry`: emit a `retry` event, return `retry_count + 1` and — when escalating — also
`use_external: True`, so the next pass adds web search. `final_answer` is left unset, so
`_route_reflection` sends the graph back to `retrieval`.

If not retrying: `final_answer = answer` plus, when ungrounded, the literal caveat
`"\n\n⚠️ *Some claims may not be fully supported by the retrieved documents.*"`. It also writes
`final_sources` (copied from `state["sources"]`) and `pipeline_metadata` =
`{query_type, sources_used, retry_count, grounded, confidence, issues}`. A `finalize` event is emitted.

With the default `MAX_REFLECTION_RETRIES=2` the ceiling is **3 generation attempts**, and the reflection
`stage_start` event advertises `attempt` / `max_attempts` accordingly.

<br>

## Gotchas

- **`retry_count` is the only loop guard.** If a node ever forgot to increment it the graph would loop
  forever; there is no wall-clock cap inside the pipeline, only the 180-second SSE queue timeout in
  `app.py`.
- **Escalation is one-way.** Once `use_external` flips to `True` it stays `True` for the rest of the run.
- **The retry re-runs the whole tail**, not just retrieval — aggregate, rerank, compress, reason, and
  reflect all execute again, which is why the frontend resets those seven stages to `idle` on a `retry`
  event.
- **The reflection feedback is never fed to the retriever.** `reflection_feedback` is stored in state and
  shown in the retry event's `reason`, but `retrieval_node` reads only `query` — so a retry issues the
  *identical* retrieval unless escalation added web search.
- **`MAX_REFLECTION_RETRIES` is read in two places** — `graph.py` and `generation/reflection.py` — both via
  `os.getenv` with default `"2"`. `Config.MAX_REFLECTION_RETRIES` exists too but is not what the nodes use.
- **A direct-answer run still emits all eight stages**, several as `stage_skip`; the tracker greys those
  rows rather than hiding them.
