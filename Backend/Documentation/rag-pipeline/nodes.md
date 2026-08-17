<div align="center">

# 🧩 Node Reference

### Every one of the eight pipeline nodes — what it reads, what it returns, what it emits, and how it fails.

</div>

<br>

---

<br>

## Content Tree

<pre>
Node Reference
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-node-contract">🧱 1. The node contract</a>
│   ├── <a href="#11-the-shape-every-node-shares">1.1 The shape every node shares</a>
│   └── <a href="#12-reading-these-entries">1.2 Reading these entries</a>
│
├── <a href="#-2-planner">🧭 2. planner</a>
├── <a href="#-3-retrieval">🔍 3. retrieval</a>
├── <a href="#-4-external_tools">🌐 4. external_tools</a>
├── <a href="#-5-aggregate">🧮 5. aggregate</a>
├── <a href="#-6-rerank">📊 6. rerank</a>
├── <a href="#-7-compress">📦 7. compress</a>
├── <a href="#-8-reason">💬 8. reason</a>
├── <a href="#-9-reflect">🪞 9. reflect</a>
│
└── <a href="#-10-emit-call-site-index">📋 10. Emit call-site index</a>
</pre>

<br>

---

<br>

## 📖 Overview

This page documents all eight nodes registered in `build_graph()`
([`workflow.py:62-69`](../../src/adrag/custom_packages/rag_pipeline/workflow.py)). The graph that wires
them, the two routers, and the retry loop are in [`README.md`](README.md); the state they share is in
[`state-model.md`](state-model.md).

> [!IMPORTANT]
> **A node's identity in the SSE stream is not its name in the graph.** Five of the eight `add_node`
> names differ from the `stage` id the node emits — `aggregate` emits `aggregator`, `rerank` emits
> `reranker`, `compress` emits `compressor`, `reason` emits `reasoning`, `reflect` emits `reflection`.
> Each entry below states both. The `emit()` call sites are the contract; renaming a node breaks
> nothing, changing a `stage` literal silently breaks the frontend tracker.

---

## 🧱 1. THE NODE CONTRACT

### 1.1 The shape every node shares

Verified identical across all eight:

```python
def <name>_node(state: RAGState) -> dict:
    session_id = state.get("session_id")
    # ... read what you need from state ...
    emit(session_id, "stage_start", {"stage": "<stage-id>", "message": "..."})
    # ... do the work ...
    emit(session_id, "stage_complete", {"stage": "<stage-id>", ...stats...})
    return {"only": ..., "the": ..., "modified": ...}
```

Four conventions hold throughout, and a new node should match all four:

- **The first statement reads `session_id`** — it is the first argument to every `emit()`.
- **The module docstring ends with an `Emits:` line** naming the event types the node produces. This is
  the only machine-adjacent record of the event contract; never add a node without one.
- **The return dict carries only modified keys.** LangGraph merges it into the state, overwriting.
- **The node catches its own exceptions and degrades**, emitting `stage_error` and returning a usable
  fallback — with exactly two exceptions, `retrieval` and `aggregate`, which have no error path at all.

### 1.2 Reading these entries

Each entry opens with a fact table, then covers the mechanism, the prompt where there is one, and the
failure behaviour. `file:line` citations are paired with the enclosing identifier; the line number is
the convenience, the name is the durable half. Paths are relative to
`Backend/src/adrag/custom_packages/rag_pipeline/`.

---

## 🧭 2. PLANNER

| | |
|---|---|
| **Graph name** | `planner` |
| **Emitted `stage` id** | `planner` |
| **Function** | `planner_node`, `generation/planner.py:49` |
| **Reads** | `query`, `provider`, `ollama_model`, `session_id` |
| **Returns** | `retrieve`, `use_external`, `query_type` |
| **LLM call** | 1 — `get_llm(provider, json_mode=True, model=ollama_model)` (`planner.py:61`) |
| **Emits** | `stage_start` → `stage_complete` \| `stage_error` |
| **Position** | entry point; its output drives `_route_planner` |

**What it does.** One LLM call classifies the query into a retrieval strategy before any retrieval
happens. This is the Self-RAG idea: the cheapest way to avoid retrieving irrelevant evidence is to
decide, up front, not to retrieve.

**The prompt** (`_PLANNER_PROMPT`, `planner.py:18-46`) is a `ChatPromptTemplate.from_messages` pair —
a system message carrying the rules and a human turn of just `"Query: {query}"`. The rules are explicit
about both booleans:

- **`retrieve = true`** → the question is likely about user-uploaded domain documents (company reports,
  research papers, personal files).
- **`retrieve = false`** → general world knowledge (history, science, geography, famous people,
  events), math, greetings, **and coding questions**.
- **`use_external = true`** → recent events (last 1–2 years), live data, current news, breaking
  information.
- **`use_external = false`** → everything else.

Four worked examples follow (`planner.py:30-34`) — the moon landing as `retrieve=false`, *"what does
the attached report say about revenue"* as `retrieve=true`, *"what happened in the stock market
today"* as `use_external=true`. Those examples are what make a small local model answer this reliably;
they are not decoration.

**Coercion.** Both booleans go through `bool(result.get(..., default))` with defaults `True` / `False`,
and `query_type` defaults to `"factual"` (`planner.py:65-67`).

**The `stage_complete` payload** carries `retrieve`, `use_external`, `query_type`, `reasoning` and a
composed `message`. **`reasoning` is the model's one-sentence justification — it is surfaced to the UI
but stored in no state key**, so it exists only in the event stream.

**Failure.** `except Exception` → `stage_error`, then:

```python
# generation/planner.py:88
except Exception as e:
    emit(session_id, "stage_error", {"stage": "planner", "error": str(e)})
    return {"retrieve": True, "use_external": False, "query_type": "factual"}
```

**The planner fails toward retrieval.** An LLM outage degrades the run to a plain RAG query rather than
to an uncited direct answer — the safer of the two failure directions.

---

## 🔍 3. RETRIEVAL

| | |
|---|---|
| **Graph name** | `retrieval` |
| **Emitted `stage` id** | `retrieval` |
| **Function** | `retrieval_node`, `retrieval/hybrid_node.py:25` |
| **Reads** | `query`, `retrieve`, `session_id` |
| **Returns** | `vector_docs`, `bm25_docs`, `graph_docs` — **never `web_docs`** |
| **LLM call** | none |
| **Emits** | `stage_start` → `retrieval_result` \| `stage_skip` |
| **Position** | one of three planner targets; also the target of the single loop edge |

**What it does.** Fans one query out across the three local stores and returns three separate lists.
The merge happens later, in `aggregate`.

```python
# retrieval/hybrid_node.py:41
vector_docs = vector_store.search(query, top_k=TOP_K)
bm25_docs = bm25_store.search(query, top_k=TOP_K)
graph_docs = graph_store.search(query, top_k=max(TOP_K // 2, 3))
```

`TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "10"))` (`hybrid_node.py:22`). **The graph store gets half the
budget, floored at three** — five candidates at the default against ten each from vector and BM25.

**Skip gate.** `if not state.get("retrieve", True)` → `stage_skip` and three empty lists
(`hybrid_node.py:29-34`). Note that the skip return **does not include `web_docs`**, so a previous
pass's web results would survive through it untouched.

> [!WARNING]
> **Three gotchas live in this eleven-line node, and two of them contradict its own docstring.**
>
> - **It is not parallel.** `hybrid_node.py:4` says *"Runs three retrieval strategies in parallel"* —
>   the code is three sequential synchronous calls. No thread pool, no `asyncio`. Do not repeat
>   "parallel" as a performance claim.
> - **It emits `retrieval_result`, never `stage_complete`** (`hybrid_node.py:45`). A client handling
>   only the four `stage_*` types leaves the retrieval row stuck on *active*.
> - **It has no `try`/`except` anywhere.** A store exception propagates out of the node, out of
>   `rag_graph.invoke()`, into the route's handler, and reaches the browser as an in-band `error` event
>   on a `200`. This is the only node with no error path of its own, so a store failure produces **no
>   `stage_error`** on the retrieval row.

**The `retrieval_result` payload** carries `stage`, `vector_count`, `bm25_count`, `graph_count` and a
composed `message` of the form `Vector: 10 | BM25: 7 | Graph: 3`.

Store internals — cosine vs BM25 vs graph traversal, and why their scores are not comparable — are in
[`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md).

---

## 🌐 4. EXTERNAL_TOOLS

| | |
|---|---|
| **Graph name** | `external_tools` |
| **Emitted `stage` id** | `external_tools` |
| **Function** | `external_tools_node`, `retrieval/web_node.py:20` |
| **Reads** | `query`, `use_external`, `session_id` |
| **Returns** | `web_docs` — **on every path, including both failures** |
| **LLM call** | none |
| **Emits** | `stage_start` → `stage_complete` \| `stage_skip` \| `stage_error` |
| **Position** | always downstream of `retrieval`; also a direct planner target |

**What it does.** Searches DuckDuckGo when the pipeline needs information the knowledge base cannot
have — recent events, live data — either because the planner said so or because reflection escalated.

**Skip gate.** `if not state.get("use_external", False)` → `stage_skip` and `{"web_docs": []}`
(`web_node.py:24-29`). Because the static `retrieval → external_tools` edge always routes through this
node, **the skip path is the common case**, and the tracker shows *"Web search not needed"* on most
runs.

> [!NOTE]
> The skip return **clears** `web_docs` rather than leaving it alone. On a retry that does not
> escalate, any web results from the previous pass are therefore wiped; on one that does escalate,
> they are replaced. This asymmetry with `retrieval`'s skip path (which omits the key entirely) is the
> clearest live example of overwrite-not-accumulate merge semantics —
> [`state-model.md`](state-model.md) §3.

**The provider.** DuckDuckGo, no API key. The import is deferred *and* dual-named to survive the
package rename:

```python
# retrieval/web_node.py:37
try:
    from ddgs import DDGS          # new package name (>=7.0)
except ImportError:
    from duckduckgo_search import DDGS  # legacy fallback
```

**`WEB_RESULTS = 5`** (`web_node.py:17`) is a **hardcoded module constant, not env-driven** — the only
retrieval width in the pipeline that cannot be tuned by configuration.

**Document shape** (`web_node.py:45-56`) differs from a KB document in three ways worth knowing:

- `content` is `f"{title}\n\n{body}"` — title and snippet concatenated.
- `metadata` carries `url`, `title`, `source_type: "web"`, and **`file_name` set to the href**, so a
  web source displays its URL where a document shows its filename.
- **`score` is the hardcoded constant `0.7`** for every web result — it encodes no relevance at all.

There is also a bare `print(...)` per result (`web_node.py:57`) — stdout noise, no logger.

**Failure.** Two paths, both returning `{"web_docs": []}`: an `ImportError` emits `stage_error` with
`"duckduckgo-search not installed"`, and any other exception emits `stage_error` with the message.
**Web search failure is always non-fatal.**

---

## 🧮 5. AGGREGATE

| | |
|---|---|
| **Graph name** | `aggregate` |
| **Emitted `stage` id** | **`aggregator`** |
| **Function** | `aggregator_node`, `ranking/aggregator.py:19` |
| **Reads** | `vector_docs`, `bm25_docs`, `graph_docs`, `web_docs` |
| **Returns** | `all_docs` |
| **LLM call** | none |
| **Emits** | `stage_start` → `stage_complete` (no error path) |
| **Position** | the convergence point of all three planner branches |

**What it does.** Concatenates the four result lists in fixed order, deduplicates by exact content
identity, and sorts. It is the only node with no branches at all — it always emits exactly
`stage_start` and `stage_complete`.

```python
# ranking/aggregator.py:34
# Keep the copy with the highest score for each unique content hash
best: dict[str, dict] = {}
for doc in raw:
    h = hashlib.md5(doc["content"].encode("utf-8", errors="replace")).hexdigest()
    if h not in best or doc["score"] > best[h]["score"]:
        best[h] = doc

unique_docs = sorted(best.values(), key=lambda d: d["score"], reverse=True)
```

**The dedup key is an MD5 of the content string** — exact identity. Near-duplicates do not collapse: a
chunk differing by one character, or the same passage chunked at a different offset, survives as two
entries. This is the correct behaviour for the actual overlap case (vector and BM25 returning the
*same* chunk id), and a limitation for everything else.

**The tie-break and the sort both use the raw `score`**, which is not comparable across stores. The
consequences are covered in [`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md) §4; the
short version is that the retained copy's `content` and `metadata` are identical either way, but its
**`source` attribution is systematically biased toward the unbounded scales** (BM25 and graph). Since
the reranker re-sorts everything downstream, the ordering here only survives on the reranker's fallback
path.

**The `stage_complete` payload** carries `before`, `after`, a `sources` distribution built with a
`defaultdict(int)`, and a message of the form `12 unique docs (from 18 total, 6 duplicates removed)`.

---

## 📊 6. RERANK

| | |
|---|---|
| **Graph name** | `rerank` |
| **Emitted `stage` id** | **`reranker`** |
| **Function** | `reranker_node`, `ranking/reranker.py:34` |
| **Reads** | `query`, `all_docs` |
| **Returns** | `context` |
| **LLM call** | none — a cross-encoder, not a chat model |
| **Emits** | `stage_start` → `stage_complete` \| `stage_error` |
| **Position** | the funnel: many candidates in, `RERANK_TOP_K` out |

**What it does.** Scores every `(query, document)` pair with a cross-encoder and keeps the highest. This
is the **first and only point in the pipeline where a single comparable relevance number exists** — the
four inbound `score` scales are mutually incomparable, and `rerank_score` is not.

```python
# ranking/reranker.py:51
try:
    reranker = _get_reranker()
    pairs = [(query, doc["content"]) for doc in all_docs]
    scores = reranker.predict(pairs)

    scored = [
        {**doc, "rerank_score": float(score)}
        for doc, score in zip(all_docs, scores)
    ]
    scored.sort(key=lambda d: d["rerank_score"], reverse=True)
    top = scored[:RERANK_TOP_K]
```

**The model** is `RERANKER_MODEL`, default `cross-encoder/ms-marco-MiniLM-L-6-v2`, loaded through a lazy
module-level singleton `_get_reranker()` (`reranker.py:23-31`) that defers
`from sentence_transformers import CrossEncoder` into the function body — so importing the pipeline does
not pay for the model.

**Cost.** One cross-encoder forward pass per candidate, in a single batched `predict()` call. At the
defaults that is up to 30 pairs (10 vector + 10 BM25 + 5 graph + 5 web, before dedup). **This is the
pipeline's dominant local-compute step**, and it scales linearly with `RETRIEVAL_TOP_K`.

**Width.** `RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))` — five documents become the `context`
that every downstream node sees.

**Empty input.** `all_docs == []` short-circuits to a `stage_complete` carrying *"No documents to
rerank"* and returns `{"context": []}` (`reranker.py:44-49`) — which is what sends the reasoning node
down its no-context direct-answer branch.

> [!CAUTION]
> **The fallback path is the most consequential error path in the pipeline, and it breaks two features
> at once.**
>
> ```python
> # ranking/reranker.py:72
> except Exception as e:
>     emit(session_id, "stage_error", {"stage": "reranker", "error": str(e)})
>     fallback = sorted(all_docs, key=lambda d: d.get("score", 0), reverse=True)[:RERANK_TOP_K]
>     return {"context": fallback}
> ```
>
> It sorts by the **incomparable raw `score`**, so BM25's unbounded scale dominates and a strong cosine
> match at `0.9` loses to a mediocre BM25 hit at `7.4`. And because those documents keep the
> `rerank_score: 0.0` their stores seeded, the reflection node's escalation test `max_rerank < 0`
> evaluates `0.0 < 0` → `False` — so **a broken reranker also silently disables web-search
> escalation**. One `stage_error` on the reranker row is the only signal.

**The `stage_complete` payload** carries `top_k`, `scores` (the selected `rerank_score`s rounded to four
places), `sources`, and a message. Those `scores` are what the UI shows per stage, and they are
**raw logits — negatives are normal and meaningful**.

---

## 📦 7. COMPRESS

| | |
|---|---|
| **Graph name** | `compress` |
| **Emitted `stage` id** | **`compressor`** |
| **Function** | `compressor_node`, `generation/compressor.py:37` |
| **Reads** | `query`, `context`, `provider`, `ollama_model` |
| **Returns** | `compressed_context` |
| **LLM call** | 1 — **conditional**, only above the threshold (`compressor.py:75`) |
| **Emits** | `stage_start` → `stage_complete` \| `stage_error` |
| **Position** | between ranking and generation |

**What it does.** Assembles the top-k documents into one numbered text block and, **only if that block
is too long**, asks an LLM to compress it down to the query-relevant parts.

**The assembly is the important half**, because it is where the `[1]`, `[2]` citation indices are
created:

```python
# generation/compressor.py:56
doc_blocks = []
for i, doc in enumerate(context):
    meta = doc.get("metadata", {})
    label = meta.get("file_name") or meta.get("title") or doc.get("source", f"Source {i+1}")
    doc_blocks.append(f"[{i+1}] {label}\n{doc['content']}")
full_text = "\n\n---\n\n".join(doc_blocks)
```

The label resolution — `file_name` → `title` → `source` → `Source {i+1}` — exists because document
metadata and web metadata are disjoint key sets. Every consumer reads metadata this defensively.

**Three outcomes, and the middle one is the common case:**

| Condition | LLM call? | Returns | Emitted message |
|---|---|---|---|
| `context` is empty | no | `{"compressed_context": ""}` | *"No context to compress"* |
| `len(full_text) <= MAX_CONTEXT_CHARS` | **no** | the full text verbatim | *"Context already within limit (N chars)"* |
| over the threshold | yes | the compressed passage | `Compressed 6,200 → 3,100 chars` |

> [!IMPORTANT]
> **Compression is the exception, not the rule.** `MAX_CONTEXT_CHARS` defaults to `4000`; at
> `RERANK_TOP_K=5` and `CHUNK_SIZE=500`, five chunks total roughly 2 500 characters. The LLM path
> rarely fires on document-only context — it takes web results or an unusually large chunk size to
> cross the threshold. A reader who assumes every run pays for a compression call will mis-budget the
> pipeline's cost by 25%.

**The prompt** (`_COMPRESS_PROMPT`, `compressor.py:22-34`) instructs the model to preserve facts,
numbers, names, dates and relationships; drop off-topic and background-only content; output **one
coherent passage, not bullet points**; stay under `{max_chars}`; and *"Keep source references like [1],
[2] if present"* — which is what stops compression from destroying the citation indices.

**Two caps worth knowing:**

- **The LLM only sees `full_text[:10_000]`** (`compressor.py:79`). Context beyond 10 000 characters is
  discarded before the model reads it — a hard ceiling on what compression can even consider.
- **`max_chars` is an instruction, not an enforcement.** The returned length is measured and reported
  as a `ratio` but never clipped.

**Failure.** `stage_error` → returns `full_text[:MAX_CONTEXT_CHARS]` — a hard truncation, not a
compression, so the tail of the evidence is silently lost.

---

## 💬 8. REASON

| | |
|---|---|
| **Graph name** | `reason` |
| **Emitted `stage` id** | **`reasoning`** |
| **Function** | `reasoning_node`, `generation/reasoning.py:43` |
| **Reads** | `query`, `compressed_context`, `context`, `provider`, `ollama_model` |
| **Returns** | `answer`, `sources` |
| **LLM call** | 1, 2 or 3 depending on path (`reasoning.py:74` / `:86` / `:110`) |
| **Emits** | `stage_start` → `stage_complete` \| `stage_error` |
| **Position** | the generation step; feeds `reflect` |

**What it does.** Generates the answer with inline citations and decides which sources survive into the
UI.

**The source list is built first, before any LLM call** (`reasoning.py:56-69`) — one entry per `context`
document, in order:

| Field | Value |
|---|---|
| `index` | `i + 1` — 1-based, matching the compressor's `[n]` labels |
| `file_name` | `metadata.file_name` → `metadata.title` → `"Unknown"` |
| `source_type` | the document's `source` — `vector` \| `bm25` \| `graph` \| `web` |
| `url`, `page` | from metadata, empty string when absent |
| `rerank_score` | rounded to 4 places, falling back to `score` then `0.0` |
| `content_preview` | the first **250** characters |
| `content` | the full chunk — *"included for frontend expansion"* (`reasoning.py:66`) |

**Context selection** is `compressed_context or "\n\n".join(d["content"] for d in context_docs)`
(`reasoning.py:71`) — a fallback to raw concatenation when compression produced an empty string.

**The no-context branch** (`reasoning.py:73-83`). When the context text is blank or whitespace, the node
makes a **plain, non-JSON** LLM call:

```python
# generation/reasoning.py:74
llm = get_llm(provider, model=ollama_model)
result = llm.invoke(
    f"Answer this question directly (no documents available): {query}"
)
```

It emits `confidence: 0.5` and returns **`sources: []`**. This is the path the planner's
`retrieve=false, use_external=false` route lands in — the pipeline's direct-answer mode.

**The prompt** (`_REASONING_PROMPT`, `reasoning.py:19-40`) requires answering *"using ONLY the provided
context"*, inline `[1]`/`[2]` citations after each claim, specificity (exact facts, numbers, names), and
an explicit statement when the context is insufficient. The JSON shape is `answer`, `confidence`,
`cited_sources` (1-based indices), `key_facts`, `is_sufficient`.

**Citation filtering — the subtlest behaviour in the node:**

```python
# generation/reasoning.py:93
# Filter to only sources actually cited in the answer.
# If the LLM cited nothing (answered from training knowledge), return no sources.
cited_indices = set(result.get("cited_sources", []))
cited_sources = [s for s in sources if s["index"] in cited_indices]
```

**Only sources the model explicitly listed survive into state.** A retrieved-but-uncited document is
invisible in the UI — deliberate. But a model that **omits `cited_sources` from its JSON produces an
answer with zero sources even though retrieval succeeded**, because the set is empty and the filter
keeps nothing. That is the mechanism behind "the answer has no sources" reports.

**Two-level failure** (`reasoning.py:107-115`). On a parse or call failure the node emits `stage_error`,
then makes a **second, plainer attempt** with `f"Context:\n{context_text[:3000]}\n\nQuestion: {query}\n\nAnswer:"`.
If that also raises, it returns `"Unable to generate an answer."`. **Both fallbacks return the full
unfiltered `sources`** — so a degraded answer shows *more* sources than a successful one.

---

## 🪞 9. REFLECT

| | |
|---|---|
| **Graph name** | `reflect` |
| **Emitted `stage` id** | **`reflection`** |
| **Function** | `reflection_node`, `generation/reflection.py:53` |
| **Reads** | `query`, `answer`, `context`, `retry_count`, `use_external`, `sources`, `query_type`, `provider`, `ollama_model` |
| **Returns** | `grounded`, `reflection_feedback`, `retry_count` — plus `final_answer`, `final_sources`, `pipeline_metadata` on a terminating pass, plus `use_external` on an escalating retry |
| **LLM call** | 1 — `get_llm(provider, json_mode=True, …)` (`reflection.py:82`) |
| **Emits** | `stage_start` → `stage_complete` \| `retry` \| `finalize` \| `stage_error` |
| **Position** | terminal node; drives `_route_reflection` |

The pipeline's most complex node — simultaneously the critic, the loop controller, and the terminator.
It is the **only node that emits four event types**, and the only one that can write `final_answer`.

**`stage_start` carries the attempt counter** — `"attempt": retry_count + 1`,
`"max_attempts": MAX_RETRIES + 1` (`reflection.py:65-66`), so the UI can show *"attempt 2 of 3"* before
the verdict exists.

**The early return on an empty answer:**

```python
# generation/reflection.py:69
if not answer:
    return {
        "grounded": False,
        "reflection_feedback": "No answer to verify",
        "retry_count": retry_count,
    }
```

This sets **no `final_answer`** and **does not increment `retry_count`** — and it sits *above* the
budget check, so the router loops the run back to `retrieval` without spending budget. See
[`README.md`](README.md) §8 for the full chain and its bound.

**The critic prompt** (`_REFLECTION_PROMPT`, `reflection.py:23-50`) states three criteria — every
factual claim traceable to the context, no hallucinated numbers/names/events, citations that actually
support their claim — and closes with *"Be strict: if ANY claim cannot be verified from the context, set
grounded=false."* It returns `grounded`, `confidence`, `issues`, `feedback`, `should_retry`.

**The context handed to the critic is truncated to 4 000 characters** — `context_text[:4000]`
(`reflection.py:85`), a **hardcoded literal unrelated to `MAX_CONTEXT_CHARS`** despite the coincident
default. Changing `MAX_CONTEXT_CHARS` does not move it.

**Optimistic defaults.** `grounded` defaults to `True` and `confidence` to `0.8` when absent from the
model's JSON (`reflection.py:90-91`) — a malformed-but-parseable response reads as *grounded*.

**The retry decision** is one line, `reflection.py:97`, and requires all three of: not grounded, the
model's own `should_retry`, and remaining budget. **The model gets a veto** — it can call an answer
ungrounded and still decline the retry.

**The escalation heuristic** (`reflection.py:99-104`) and its dependence on the *sign* of `rerank_score`
are covered in [`README.md`](README.md) §5.4. The retry return merges `use_external: True` in
conditionally — **the only place outside the planner that writes that key**.

**The `retry` event** (`reflection.py:129-135`) carries `attempt`, `max_attempts`, `reason`,
`escalate_external` and `message`. **It has no `stage` key**, and that is the documented contract: a
retry is a statement about the whole run, not about one stage. Clients must handle it before any
stage-based dispatch.

**Finalization** (`reflection.py:143-170`) appends the caveat when ungrounded, emits `finalize`, and
returns `final_answer`, `final_sources` (copied from `sources`), and `pipeline_metadata`:

```python
# generation/reflection.py:162
"pipeline_metadata": {
    "query_type": state.get("query_type", "factual"),
    "sources_used": [d.get("source") for d in context_docs],
    "retry_count": retry_count,
    "grounded": grounded,
    "confidence": round(confidence, 2),
    "issues": issues,
},
```

This is the **only** consumer of `query_type` anywhere in the codebase — it is echoed into metadata for
display and steers nothing.

> [!IMPORTANT]
> **The exception path fails open, and that is load-bearing.** It sets `grounded: True` **and**
> `final_answer: answer` (`reflection.py:172-181`) — passing an unverified answer through as grounded,
> with `pipeline_metadata: {"error": str(e)}`. Because it writes `final_answer`, it also **terminates**
> the graph. A critic outage therefore degrades answer quality rather than wedging the run in an
> unbounded retry loop. Change this polarity and a reflection outage becomes a hang.

---

## 📋 10. EMIT CALL-SITE INDEX

Every `emit()` in the pipeline — 31 call sites across the eight nodes. The `stage` value is the literal
inside each payload dict.

| Node file | Line | Event type | `stage` literal | Fires when |
|---|---|---|---|---|
| `planner.py` | 55 | `stage_start` | `planner` | always, first |
| `planner.py` | 69 | `stage_complete` | `planner` | the LLM decision parsed |
| `planner.py` | 89 | `stage_error` | `planner` | any exception |
| `hybrid_node.py` | 30 | `stage_skip` | `retrieval` | `retrieve=False` |
| `hybrid_node.py` | 36 | `stage_start` | `retrieval` | `retrieve=True` |
| `hybrid_node.py` | 45 | **`retrieval_result`** | `retrieval` | all three stores returned |
| `web_node.py` | 25 | `stage_skip` | `external_tools` | `use_external=False` |
| `web_node.py` | 31 | `stage_start` | `external_tools` | `use_external=True` |
| `web_node.py` | 59 | `stage_complete` | `external_tools` | the search returned |
| `web_node.py` | 67 | `stage_error` | `external_tools` | `ImportError` — ddgs missing |
| `web_node.py` | 74 | `stage_error` | `external_tools` | any other exception |
| `aggregator.py` | 22 | `stage_start` | **`aggregator`** | always |
| `aggregator.py` | 48 | `stage_complete` | **`aggregator`** | always — no error path |
| `reranker.py` | 39 | `stage_start` | **`reranker`** | always |
| `reranker.py` | 45 | `stage_complete` | **`reranker`** | `all_docs` empty |
| `reranker.py` | 63 | `stage_complete` | **`reranker`** | the cross-encoder scored |
| `reranker.py` | 73 | `stage_error` | **`reranker`** | model load or predict failed |
| `compressor.py` | 44 | `stage_start` | **`compressor`** | always |
| `compressor.py` | 50 | `stage_complete` | **`compressor`** | no context |
| `compressor.py` | 66 | `stage_complete` | **`compressor`** | already under the char limit |
| `compressor.py` | 84 | `stage_complete` | **`compressor`** | LLM compression succeeded |
| `compressor.py` | 94 | `stage_error` | **`compressor`** | compression failed |
| `reasoning.py` | 51 | `stage_start` | **`reasoning`** | always |
| `reasoning.py` | 78 | `stage_complete` | **`reasoning`** | no-context direct answer |
| `reasoning.py` | 98 | `stage_complete` | **`reasoning`** | the JSON answer parsed |
| `reasoning.py` | 108 | `stage_error` | **`reasoning`** | the JSON path failed |
| `reflection.py` | 62 | `stage_start` | **`reflection`** | always |
| `reflection.py` | 106 | `stage_complete` | **`reflection`** | verdict reached |
| `reflection.py` | 129 | **`retry`** | *(none — by design)* | `will_retry` is true |
| `reflection.py` | 150 | **`finalize`** | **`reflection`** | terminating pass |
| `reflection.py` | 173 | `stage_error` | **`reflection`** | any exception |

**Continue reading:**

- [`README.md`](README.md) — the graph, the routers, the retry loop, and the ten-section deep dive
- [`state-model.md`](state-model.md) — `RAGState`, merge semantics, and the invariants
- [`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md) — the three-store retrieval subsystem
