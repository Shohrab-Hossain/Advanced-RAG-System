# Entity: `RAGState`

The single `TypedDict` that flows through every pipeline node, defined in
`Backend/src/rag_pipeline/state.py`. Each node reads what it needs and returns **only the keys it
modifies**; LangGraph merges the returned dict into the state.

<br>

## Fields

| Group | Field | Type | Written by | Meaning |
|---|---|---|---|---|
| Input | `query` | `str` | `/api/query` | the user's question, stripped |
| | `session_id` | `Optional[str]` | `/api/query` | UUID keying the SSE queue |
| | `provider` | `str` | `/api/query` | `"openai"` \| `"ollama"` |
| | `ollama_model` | `Optional[str]` | `/api/query` | model override; `None` → env default. Despite the name it is passed to `get_llm` for both providers |
| Planner | `retrieve` | `bool` | `planner_node` | query the knowledge base? |
| | `use_external` | `bool` | `planner_node`, `reflection_node` | run web search? Reflection can flip it to `True` on escalation |
| | `query_type` | `str` | `planner_node` | `"factual"` \| `"analytical"` \| `"conversational"` |
| Retrieval | `vector_docs` | `List[Document]` | `retrieval_node` | dense hits |
| | `bm25_docs` | `List[Document]` | `retrieval_node` | sparse hits |
| | `graph_docs` | `List[Document]` | `retrieval_node` | graph-traversal hits |
| | `web_docs` | `List[Document]` | `external_tools_node` | web hits |
| Aggregation | `all_docs` | `List[Document]` | `aggregator_node` | deduplicated union, score-sorted |
| Reranking | `context` | `List[Document]` | `reranker_node` | top `RERANK_TOP_K` by `rerank_score` |
| Compression | `compressed_context` | `str` | `compressor_node` | the text actually put in the answer prompt |
| Generation | `answer` | `str` | `reasoning_node` | raw generated answer |
| | `sources` | `List[dict]` | `reasoning_node` | citation records for the **cited** context docs only |
| Reflection | `grounded` | `bool` | `reflection_node` | is every claim traceable to context? |
| | `reflection_feedback` | `str` | `reflection_node` | the critic's feedback text |
| | `retry_count` | `int` | `reflection_node` | retries so far; the loop guard |
| Final | `final_answer` | `str` | `reflection_node` | answer + optional caveat. **Its presence terminates the graph** |
| | `final_sources` | `List[dict]` | `reflection_node` | copy of `sources` at finalisation |
| | `pipeline_metadata` | `dict` | `reflection_node` | run summary, shape below |

<br>

## `Document` (nested TypedDict)

```python
{ "content": str,          # the chunk text
  "metadata": dict,        # file_name, page, url, … (see ../document-chunk/)
  "score": float,          # retriever-native initial score
  "source": str,           # "vector" | "bm25" | "graph" | "web"
  "rerank_score": float }  # cross-encoder score; 0.0 until reranked; may be negative
```

<br>

## `sources[]` record (what reaches the client)

Built in `reasoning_node` from `context`:

| Field | Type | Notes |
|---|---|---|
| `index` | int | 1-based; matches the `[n]` citations in the answer |
| `file_name` | str | `metadata.file_name` or `metadata.title` or `"Unknown"` |
| `source_type` | str | the document's `source` tag |
| `url` | str | `metadata.url` or `""` |
| `page` | int \| str | `metadata.page` or `""` |
| `rerank_score` | float | rounded to 4 dp; falls back to `score` |
| `content_preview` | str | first 250 characters |
| `content` | str | the full chunk, for the UI's expand panel |

<br>

## `pipeline_metadata`

```python
{ "query_type": str, "sources_used": List[str],   # the `source` tag of each context doc
  "retry_count": int, "grounded": bool,
  "confidence": float,  # 2 dp, self-reported by the reflection model
  "issues": List[str] }
```

On a reflection exception the metadata is replaced entirely by `{"error": str(exc)}`.

<br>

## Initialisation

`/api/query` builds the **complete** initial state — every key present, lists empty, `retrieve=True`,
`use_external=False`, `query_type="factual"`, `grounded=True`, `retry_count=0`. Nodes therefore never face
a missing key, though most still use `state.get(...)` with a default.

<br>

## Constraints worth knowing

- **`TypedDict` is not enforced at runtime.** Nothing validates a node's return; a typo'd key is silently
  added to the state.
- **Returned keys overwrite, never merge.** `retrieval_node` returns fresh lists on every pass, so a retry
  discards the previous attempt's documents rather than accumulating them.
- **`final_answer` is load-bearing control flow**, not just data — see
  [`../../runtime/query-pipeline/README.md`](../../runtime/query-pipeline/README.md).
- **`answer` and `final_answer` differ** only by the ungrounded caveat; `/api/query` prefers
  `final_answer` and falls back to `answer`.
