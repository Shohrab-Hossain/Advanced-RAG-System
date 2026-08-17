<div align="center">

# 🧾 State Model

### `RAGState` key by key — who writes each field, how LangGraph merges a node's return, and the invariants that follow.

</div>

<br>

---

<br>

## Content Tree

<pre>
State Model
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-two-typeddicts">📐 1. The two TypedDicts</a>
│   ├── <a href="#11-document--the-evidence-shape">1.1 Document — the evidence shape</a>
│   └── <a href="#12-ragstate--the-run">1.2 RAGState — the run</a>
│
├── <a href="#-2-the-22-state-keys">🔑 2. The 22 state keys</a>
│   ├── <a href="#21-the-writer--reader-matrix">2.1 The writer / reader matrix</a>
│   └── <a href="#22-every-key-is-seeded-before-the-graph-runs">2.2 Every key is seeded before the graph runs</a>
│
├── <a href="#-3-merge-semantics">🔀 3. Merge semantics</a>
│   ├── <a href="#31-returned-keys-overwrite-they-never-accumulate">3.1 Returned keys overwrite, they never accumulate</a>
│   ├── <a href="#32-what-that-means-on-the-loop-edge">3.2 What that means on the loop edge</a>
│   └── <a href="#33-an-omitted-key-survives-untouched">3.3 An omitted key survives untouched</a>
│
├── <a href="#-4-what-is-not-enforced-at-runtime">🚨 4. What is not enforced at runtime</a>
│
├── <a href="#-5-the-write-only-keys">👻 5. The write-only keys</a>
│
├── <a href="#-6-the-determinism-consequence">🎲 6. The determinism consequence</a>
│
├── <a href="#-7-invariants">🔒 7. Invariants</a>
│
└── <a href="#-8-how-nodes-read-configuration">🧰 8. How nodes read configuration</a>
</pre>

<br>

---

<br>

## 📖 Overview

One `TypedDict` flows through all eight nodes. Each node reads what it needs and returns only what it
modified; LangGraph merges that return into the state and hands the result to the next node. The whole
definition is 59 lines
([`state.py`](../../src/adrag/custom_packages/rag_pipeline/state.py)), and it is the pipeline's entire
inter-node contract — there are no per-node schemas, no message objects, no channels.

> [!IMPORTANT]
> **Every returned key replaces the previous value wholesale.** `RAGState` declares no reducer or
> annotated accumulator on any field — they are plain `TypedDict` entries, not
> `Annotated[..., operator.add]`. So a node cannot append to a list in state; it can only hand back a
> new one. This single fact explains most of the pipeline's surprising retry behaviour (§3.2), and it
> is the first thing to check when a change to state does not behave the way it reads.

---

## 📐 1. THE TWO TYPEDDICTS

### 1.1 `Document` — the evidence shape

Every retrieved chunk, from every source, has the same five keys
(`Document`, `state.py:11-17`):

```python
class Document(TypedDict):
    """Represents a retrieved piece of evidence."""
    content: str
    metadata: dict        # file_name, page, url, etc.
    score: float          # initial retrieval score
    source: str           # "vector" | "bm25" | "graph" | "web"
    rerank_score: float   # cross-encoder score (set by reranker node)
```

| Key | Meaning | Produced by |
|---|---|---|
| `content` | the chunk text (or, for a web result, `title\n\nbody`) | every store and the web node |
| `metadata` | store-dependent — document sources and web results carry **disjoint** key sets | the loader, or the web node |
| `score` | the initial retrieval score — **not comparable across stores** | each store, on its own scale |
| `source` | `"vector"` \| `"bm25"` \| `"graph"` \| `"web"` | each store, as a literal |
| `rerank_score` | the cross-encoder score — **every store seeds it `0.0`** | the reranker overwrites it |

Two of those rows carry the whole of the ranking story, and both are covered in depth in
[`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md): `score` mixes three incomparable
mathematical objects in one `float` field, and `rerank_score` is a raw logit whose **sign** is
load-bearing. Because every store seeds `rerank_score` to `0.0`, that value unambiguously means *"the
reranker has not run on this document."*

### 1.2 `RAGState` — the run

`RAGState` (`state.py:20-59`) is a flat `TypedDict` of 22 keys in nine commented groups: input,
planner outputs, retrieval outputs, aggregation, reranking, compression, generation, reflection, and
final output. It is declared as a plain `TypedDict` — not a Pydantic model, not a dataclass — which is
what makes §4 true.

---

## 🔑 2. THE 22 STATE KEYS

### 2.1 The writer / reader matrix

"Written by" means the key appears in a `dict` the node **returns**. Paths are relative to
`Backend/src/adrag/custom_packages/rag_pipeline/`.

| Group | Key | Type | Written by | Read by |
|---|---|---|---|---|
| Input | `query` | `str` | the route only (`query_routes.py:55`) | every LLM node, both retrieval nodes |
| Input | `session_id` | `str \| None` | the route only (`query_routes.py:56`) | every node — the first `emit()` argument |
| Input | `provider` | `str` | the route only (`query_routes.py:57`) | the four LLM nodes |
| Input | `ollama_model` | `str \| None` | the route only (`query_routes.py:58`) | the four LLM nodes |
| Planner | `retrieve` | `bool` | `planner.py:83`, fallback `:90` | `_route_planner` (`workflow.py:40`), `hybrid_node.py:29` |
| Planner | `use_external` | `bool` | `planner.py:84`, `:90`; **also `reflection.py:140`** | `_route_planner:42`, `web_node.py:24`, `reflection.py:104` |
| Planner | `query_type` | `str` | `planner.py:85`, `:90` | **only `reflection.py:163`** — see §5 |
| Retrieval | `vector_docs` | `List[Document]` | `hybrid_node.py:58`, skip `:34` | `aggregator.py:28` |
| Retrieval | `bm25_docs` | `List[Document]` | `hybrid_node.py:59`, skip `:34` | `aggregator.py:29` |
| Retrieval | `graph_docs` | `List[Document]` | `hybrid_node.py:60`, skip `:34` | `aggregator.py:30` |
| Retrieval | `web_docs` | `List[Document]` | `web_node.py:64`, skip `:29`, errors `:71`/`:75` | `aggregator.py:31` |
| Aggregation | `all_docs` | `List[Document]` | `aggregator.py:60` | `reranker.py:37` |
| Reranking | `context` | `List[Document]` | `reranker.py:70`, empty `:49`, fallback `:75` | `compressor.py:40`, `reasoning.py:47`, `reflection.py:57` |
| Compression | `compressed_context` | `str` | `compressor.py:91`, `:54`, `:72`, fallback `:95` | `reasoning.py:46` |
| Generation | `answer` | `str` | `reasoning.py:105`, `:83`, `:113`, `:115` | `reflection.py:56` |
| Generation | `sources` | `List[dict]` | `reasoning.py:105`, `:83`, `:113`, `:115` | `reflection.py:161`, `:179` |
| Reflection | `grounded` | `bool` | `reflection.py:71`, `:137`, `:157`, `:175` | the browser only, via `pipeline_metadata` |
| Reflection | `reflection_feedback` | `str` | `reflection.py:72`, `:138`, `:158`, `:176` | **nothing — see §5** |
| Reflection | `retry_count` | `int` | `reflection.py:73`, `:139` (+1), `:159`, `:177` | `reflection.py:58`, `:97` |
| Final | `final_answer` | `str` | **`reflection.py:160` and `:178` only** | `_route_reflection` (`workflow.py:50`), `query_routes.py:87` |
| Final | `final_sources` | `List[dict]` | `reflection.py:161`, `:179` | `query_routes.py:88` |
| Final | `pipeline_metadata` | `dict` | `reflection.py:162-169`, `:180` | `query_routes.py:89` → the browser's `metadata` |

Read the `final_answer` row carefully — **two write sites, both in `reflection.py`**, is what makes the
termination invariant (§7) checkable by inspection rather than by a runtime guard.

### 2.2 Every key is seeded before the graph runs

The route builds the full 21-key dict before invoking the graph (`query_routes.py:54-79`), so **no key
first appears mid-run**. The planner's three outputs are seeded with placeholder values under an
explicit comment:

```python
# routes/query/query_routes.py:59
# Planner will overwrite these:
"retrieve": True,
"use_external": False,
"query_type": "factual",
```

The seeds matter beyond tidiness. `"final_answer": ""` (`query_routes.py:76`) is falsy, which is why the
first arrival at `reflect` always evaluates the retry branch. `"retry_count": 0` is what the budget
check compares against. And seeding the four document lists to `[]` means the aggregator's
`.get(..., [])` calls never have to distinguish "not retrieved yet" from "retrieved nothing" — a
distinction the pipeline deliberately does not make.

---

## 🔀 3. MERGE SEMANTICS

### 3.1 Returned keys overwrite, they never accumulate

LangGraph merges a node's returned `dict` into the state key by key. Because `RAGState` declares no
reducer on any field, **the merge is a plain assignment**: the returned value replaces whatever was
there.

There is no way for a node to append to a state list. `aggregator_node` does not *add* to `all_docs`,
it *computes and returns a new* `all_docs`. The same is true of every list-valued key.

### 3.2 What that means on the loop edge

This is where the semantics stop being an implementation detail. When `reflect` sends control back to
`retrieval`, the second pass runs the same three store searches and returns fresh lists:

```python
# retrieval/hybrid_node.py:57
return {
    "vector_docs": vector_docs,
    "bm25_docs": bm25_docs,
    "graph_docs": graph_docs,
}
```

Those **discard** the first pass's documents rather than adding to them.

> [!WARNING]
> **A retry is a *replacement* retrieval, not an *augmenting* one** — despite `workflow.py:6`'s
> docstring saying *"back to retrieval with augmented context."* The only thing that genuinely augments
> across a retry is `web_docs`, and only when `escalate_external` flipped `use_external` on, adding a
> source of evidence that was not previously searched. The docstring is stale; the merge semantics are
> the contract.

### 3.3 An omitted key survives untouched

The corollary: a key a node does **not** return keeps its previous value. Two places in the pipeline
where that distinction is visible, and they behave differently on purpose:

| Node | Skip return | Effect on a retry |
|---|---|---|
| `retrieval` | `{"vector_docs": [], "bm25_docs": [], "graph_docs": []}` (`hybrid_node.py:34`) | **omits `web_docs`** — a previous pass's web results persist through it |
| `external_tools` | `{"web_docs": []}` (`web_node.py:29`) | **erases** them |

So on a retry that does not escalate, prior web results are wiped by the web node's own skip path; on
one that does escalate, they are replaced by a fresh search. Either way `web_docs` is never additive.

---

## 🚨 4. WHAT IS NOT ENFORCED AT RUNTIME

`RAGState` is a plain `typing.TypedDict`. Python performs **no runtime validation** of a `TypedDict`,
and LangGraph merges whatever dict a node hands back. Three consequences:

- **A misspelled return key is merged silently.** Returning `{"contex": top}` adds a new entry named
  `contex` to the state, leaves `context` at its previous value, and raises nothing. The next node
  reads the stale `context` and produces plausible-looking wrong output.
- **A wrong-typed value is accepted.** Nothing checks that `retry_count` is an `int` or that
  `all_docs` is a list of `Document`.
- **A static type checker would catch both — and the repo runs none.** `pyproject.toml` configures
  packaging only; there is no `mypy`, `ruff`, or `pyright` configuration in the backend.

Treat the `RAGState` declaration as **documentation of intent**, and the route's `initial_state` as the
**real contract** — that is the dict every key genuinely exists in. When adding a key, add it to both.

---

## 👻 5. THE WRITE-ONLY KEYS

Two declared keys are written on every relevant path and read by nothing that changes behaviour.
Verified by repo-wide search across `Backend/src` and `Frontend/src`:

**`reflection_feedback`** — declared at `state.py:53`, seeded at `query_routes.py:74`, written at four
sites in `reflection.py` (`:72`, `:138`, `:158`, `:176`), and **read by no node**. The critic's feedback
text does reach the browser, but only as the `reason` field of the `retry` SSE event
(`reflection.py:132`), copied from a local variable rather than from state.

> [!IMPORTANT]
> **The reflection loop does not feed its critique back into the next attempt.** No node reads
> `reflection_feedback`; the retrieval query is unchanged and the reasoning prompt is byte-identical
> between passes. The word "feedback" in the key name describes what the critic *produced*, not what
> the next pass *consumes*.

**`query_type`** — the planner's third output. Read in exactly one place, `reflection.py:163`, where it
is copied into `pipeline_metadata` for display. It steers no routing and enters no prompt.

---

## 🎲 6. THE DETERMINISM CONSEQUENCE

Chaining §3.2, §5, and one fact from the LLM factory produces the most important architectural
observation about this pipeline:

1. `get_llm()` defaults to `temperature=0` (`llm.py:24`) and **every node calls it without overriding
   that.**
2. `reflection_feedback` is read by nothing, so the retry's prompts are identical to the first pass's
   (§5).
3. Returned keys overwrite, so the retry re-retrieves the same corpus with the same query and gets the
   same documents (§3.2).

> [!CAUTION]
> **A non-escalating retry re-runs an identical deterministic pipeline and therefore cannot produce a
> different answer.** Same query → same documents → same `context` → same prompt → temperature 0 → the
> same completion, which the critic then judges the same way. It costs four more LLM calls and changes
> nothing.
>
> **The retry budget only does real work when `escalate_external` fires** and web documents that were
> not previously in play enter the evidence set. The two mechanisms that could otherwise break the tie —
> injecting the feedback into the next prompt, or raising the sampling temperature — are **both
> absent**. Anyone tuning `MAX_REFLECTION_RETRIES` upward without adding one of them is buying latency
> and token spend, not quality.

---

## 🔒 7. INVARIANTS

The rules that break the pipeline when violated. Each is a property of the code as it stands, not an
aspiration.

**`final_answer` is the termination signal, and only the terminating node may write it.**
`_route_reflection` (`workflow.py:47`) returns `END` **iff** `state.get("final_answer")` is truthy. Any
node that writes a non-empty value there silently ends the graph from `reflect`'s router. Today there
are exactly two write sites, both in `reflection.py`. Adding a third is how you get a run that ends in
the middle.

**The router holds no budget logic.** It tests `final_answer` and nothing else — not `grounded`, not
`retry_count`, not `MAX_REFLECTION_RETRIES`. The budget is `reflection.py:97`.

> [!WARNING]
> **`workflow.py:33` defines `MAX_RETRIES` and never references it — dead code.** It reads the same
> `MAX_REFLECTION_RETRIES` environment variable as the real one at `reflection.py:21`, so tuning the
> *variable* works; editing the *literal default in `workflow.py`* changes nothing observable. A reader
> who tunes the dead constant will see no behaviour change and reasonably conclude the retry loop is
> broken.

**A node returns only the keys it modifies.** Returning an unchanged key is harmless but noisy;
returning a key you did not intend to change silently reverts another node's work.

**`retry_count` increments on exactly one path** — the `will_retry` branch (`reflection.py:139`). Every
other reflection return passes it through unchanged, which is deliberate for the finalize paths and is
the known limitation below for the early return.

> [!CAUTION]
> **An empty `answer` loops the graph without spending retry budget.** When `answer` is falsy the
> reflection node returns early (`reflection.py:69-74`) with `grounded: False`, an unchanged
> `retry_count`, and **no `final_answer`** — so the router sends control back to `retrieval`, and
> because the early return sits *above* the budget check at `reflection.py:97`, the budget is never
> consulted. The realistic trigger is a small local model emitting `"answer": ""` in its JSON, which
> `result.get("answer", "No answer generated.")` returns unchanged because the key is present.
>
> The only in-graph bound is LangGraph's recursion limit, which this code never sets —
> `rag_graph.invoke(initial_state)` (`query_routes.py:83`) passes no `config`. **The installed LangGraph
> is 1.2.11, whose default recursion limit is `10007`** — not the widely-quoted `25`, and
> `pyproject.toml` pins only `langgraph>=0.1.0`, so the effective ceiling is resolved-version-dependent.
> In practice the 180-second per-event SSE timeout ends the *stream* long before that, but it frees the
> browser, never the daemon thread.

**One process, one worker.** The session registry backing `emit()` is a plain module dict, and every
store is a module singleton. Forking splits the SSE producer from its consumer *and* gives each worker a
divergent in-memory BM25 and graph copy.

**`emit()` must stay a no-op for an unknown session.** `if not session_id: return`, then `if q:`
(`events.py:31-37`). Make it raise and a disconnected browser becomes a pipeline crash.

---

## 🧰 8. HOW NODES READ CONFIGURATION

**The pipeline nodes do not import `Config`.** Only the three stores and the KB registry do. Every node
instead calls `os.getenv(...)` at module scope with **its own literal copy of the default** — 16 direct
`os.getenv` calls across the package:

```python
# retrieval/hybrid_node.py:22
TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "10"))

# ranking/reranker.py:20
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))
```

All 14 duplicated defaults currently agree with `config.py`. So this is a **maintenance hazard, not a
live bug** — but changing a default in `config.py` alone would silently fail to reach the node that
re-declares it, and nothing would report the divergence.

**These reads happen at import, not per request.** Module-scope `os.getenv` freezes each value when the
module first loads, and the LLM cache is likewise never invalidated (`llm.py:21`) — its key is the
4-tuple `(provider, temperature, json_mode, model)`, so a runtime environment change cannot reach an
already-constructed instance. **Restart the process to change a setting.**

The settings that reach this pipeline, with their real defaults:

| Env var | Default | Read at | Caps |
|---|---|---|---|
| `RETRIEVAL_TOP_K` | `10` | `hybrid_node.py:22` | per-store candidate width; graph gets `max(k // 2, 3)` |
| `RERANK_TOP_K` | `5` | `reranker.py:21` | the final `context` size |
| `MAX_CONTEXT_CHARS` | `4000` | `compressor.py:20` | the compression threshold |
| `MAX_REFLECTION_RETRIES` | `2` | `reflection.py:21` (and dead at `workflow.py:33`) | the retry budget |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `reranker.py:20` | the cross-encoder |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | `embeddings.py:11` | dense embeddings |
| `LLM_MODEL` | `gpt-4o-mini` | `llm.py:62` | the OpenAI chat model |
| `OLLAMA_MODEL` | `llama3.2` | `llm.py:53` | the Ollama chat model |

**Values that are hardcoded and cannot be tuned by environment at all:**

| Constant | Value | Where | What it caps |
|---|---|---|---|
| `WEB_RESULTS` | `5` | `web_node.py:17` | web results per search |
| compression input cap | `10_000` chars | `compressor.py:79` | what the compressor LLM can see |
| reflection context cap | `4000` chars | `reflection.py:85` | what the critic LLM can see — **unrelated to `MAX_CONTEXT_CHARS`** |
| reasoning fallback context | `3000` chars | `reasoning.py:111` | the second-attempt prompt |
| `content_preview` | `250` chars | `reasoning.py:68` | the source-card preview |
| web result `score` | `0.7` | `web_node.py:53` | every web document's raw score |
| graph hop weights | `2.0` / `0.5` | `graph_store.py:102`, `:108` | graph traversal scoring |
| LLM `temperature` | `0` | `llm.py:24` | all four LLM calls |
| SSE per-event wait | `180` s | `query_routes.py:28` | how long the stream waits between events |

**Continue reading:**

- [`README.md`](README.md) — the graph, the routers, the retry loop, and the ten-section deep dive
- [`nodes.md`](nodes.md) — the per-node reference for all eight nodes
- [`../hybrid-retrieval/README.md`](../hybrid-retrieval/README.md) — the three-store retrieval subsystem
- [`../hybrid-retrieval/stores.md`](../hybrid-retrieval/stores.md) — where `score` and `rerank_score` come from
