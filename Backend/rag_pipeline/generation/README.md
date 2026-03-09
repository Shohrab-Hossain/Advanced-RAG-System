# generation/ — LLM-Based Generation Nodes

Four nodes that use the LLM (OpenAI or Ollama) to reason about, generate, and
verify the final answer. All nodes read `state["provider"]` and call
`encoding/llm.py` to get the right model.

## Files

### `planner.py` — Self-RAG Planner
**Purpose:** Decide the retrieval strategy *before* hitting any vector store.
**LLM call:** JSON mode — outputs a decision object.

```json
{
  "retrieve": true,
  "use_external": false,
  "query_type": "factual",
  "reasoning": "Query is about document content"
}
```

Routing decisions:
- `retrieve=true` → run hybrid KB retrieval
- `use_external=true` → also (or only) run web search
- `retrieve=false, use_external=false` → skip retrieval, answer directly

Fallback on LLM error: `retrieve=true, use_external=false`.

---

### `compressor.py` — Context Compressor
**Purpose:** Shrink the concatenated top-k docs to fit the LLM context window.
**When it runs:** Only when `len(full_context) > MAX_CONTEXT_CHARS` (default 4000).
**LLM call:** Extracts only query-relevant passages from each source.

If already within the limit, it passes through unchanged (no LLM call).
On error, falls back to a hard truncate of the first `MAX_CONTEXT_CHARS` chars.

---

### `reasoning.py` — Reasoning / Answer Generation Agent
**Purpose:** Generate a cited answer from the compressed context.
**LLM call:** JSON mode — outputs structured answer with citations.

```json
{
  "answer": "The capital is Paris [1].",
  "confidence": 0.95,
  "cited_sources": [1],
  "key_facts": ["Paris is the capital of France"],
  "is_sufficient": true
}
```

Source registry: builds `sources[]` list with `file_name`, `page`, `url`,
`rerank_score`, and `content_preview` — passed to the frontend for display.

Fallback on JSON parse error: plain `llm.invoke()` for raw text answer.
Fallback on empty context: direct LLM answer (no documents available).

---

### `reflection.py` — Self-Reflection Agent
**Purpose:** Verify the answer is grounded in the retrieved context.
**LLM call:** JSON mode — strict grounding audit.

```json
{
  "grounded": true,
  "confidence": 0.88,
  "issues": [],
  "feedback": "All claims are supported",
  "should_retry": false
}
```

**Retry logic:**
1. If `grounded=false` and `should_retry=true` and retry budget remains → loop back to retrieval
2. If retry and KB context was weak (`max_rerank_score < 0` or no docs) → set `use_external=True` before looping (escalates to web search)
3. If grounded or budget exhausted → write `final_answer` and end pipeline

Adds a caveat `⚠️ Some claims may not be fully supported...` when finalising with `grounded=false`.

## Data Flow

```
query + context
  │
  ▼
planner  ─────────────────────────────────── routing decision
                                                    │
compressed context                                  │
  │                                                 │
  ▼                                                 │
compressor ──► reasoning ──► reflection ──► final_answer
                                  │
                            [retry loop]
                          back to retrieval/
```
