<div align="center">

# 🔎 Hybrid Retrieval

### Three local stores with three incomparable scoring scales, merged and then reduced to one comparable ranking by a cross-encoder.

<br>

[![Stores](https://img.shields.io/badge/stores-3%20%2B%20web-1c7ed6)](#%EF%B8%8F-3-architecture)
[![Reranker](https://img.shields.io/badge/reranker-cross--encoder-7c5cff)](#51-the-funnel)
[![Version](https://img.shields.io/badge/version-0.1.0-3fb950)](../../pyproject.toml)

[![Chroma](https://img.shields.io/badge/dense-Chroma-f59e0b)](https://www.trychroma.com/)
[![BM25](https://img.shields.io/badge/sparse-rank--bm25-f59e0b)](https://pypi.org/project/rank-bm25/)
[![NetworkX](https://img.shields.io/badge/graph-NetworkX-f59e0b)](https://networkx.org/)

</div>

<br>

---

<br>

## Content Tree

<pre>
Hybrid Retrieval
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│   ├── <a href="#11-why-three-stores">1.1 Why three stores</a>
│   └── <a href="#12-what-the-user-sees">1.2 What the user sees</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-the-four-evidence-sources">3.1 The four evidence sources</a>
│   ├── <a href="#32-the-store-surface--and-where-it-is-not-uniform">3.2 The store surface — and where it is not uniform</a>
│   └── <a href="#33-singletons-and-import-time-side-effects">3.3 Singletons and import-time side effects</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│   ├── <a href="#41-the-read-path">4.1 The read path</a>
│   └── <a href="#42-the-write-path">4.2 The write path</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-the-funnel">5.1 The funnel</a>
│   ├── <a href="#52-deduplication-by-content-hash">5.2 Deduplication by content hash</a>
│   ├── <a href="#53-score-is-not-comparable-across-stores">5.3 score is not comparable across stores</a>
│   └── <a href="#54-rerank_score-is--and-its-sign-matters">5.4 rerank_score is — and its sign matters</a>
│
├── <a href="#-6-wire-shape-cross-boundary-contracts">🔌 6. Wire shape (cross-boundary contracts)</a>
│
├── <a href="#%EF%B8%8F-7-edge-cases--gotchas">⚠️ 7. Edge cases &amp; gotchas</a>
│
├── <a href="#-8-failure-modes">💥 8. Failure modes</a>
│
├── <a href="#-9-extension-points">🧩 9. Extension points</a>
│
└── <a href="#-10-related-decisions--deeper-reading">🔗 10. Related decisions &amp; deeper reading</a>
</pre>

<br>

---

<br>

## 📖 Overview

Hybrid retrieval is the evidence-gathering half of the RAG pipeline. One query fans out across **three
local stores** — a dense vector index, a BM25 keyword index, and a NetworkX entity graph — plus an
optional DuckDuckGo web search. Their results are merged, deduplicated, and then reduced by a
cross-encoder to the five documents that actually reach the answer.

The design bet is that the three stores fail in **different** ways: dense retrieval misses exact
identifiers, keyword retrieval misses paraphrase, and graph traversal misses anything without a named
entity. Running all three and letting a reranker arbitrate is cheaper than tuning any one of them into
being sufficient.

> [!IMPORTANT]
> **The `score` field is not comparable across stores, and only `rerank_score` is.** Cosine similarity
> (≈0–1), raw BM25 (unbounded), graph traversal weight (unbounded), and a hardcoded `0.7` for every web
> result all share one `float` field named `score`. Ranking on it is meaningful **within** a store and
> meaningless **across** stores. The cross-encoder is the first and only point in the pipeline where a
> single comparable number exists.

**The companion page in this folder:**

| Page | What it covers |
|---|---|
| [`stores.md`](stores.md) | Per-store internals — Chroma, FAISS, BM25 and the graph, method by method, with their exact score expressions |

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

### 1.1 Why three stores

Each store answers a different question about the corpus, and each has a characteristic blind spot the
others cover:

| Store | Finds | Blind to |
|---|---|---|
| **Vector** (dense) | semantic similarity — paraphrases, synonyms, "the same idea in other words" | exact identifiers, rare tokens, and anything the embedding model was not trained to distinguish |
| **BM25** (sparse) | exact term overlap — product codes, error strings, proper nouns spelled the same way | any phrasing that shares no vocabulary with the query |
| **Graph** (entity) | documents that mention the same named entities as the query | any query with no extractable entity — it returns **nothing at all** |

A question like *"what did the Q3 report say about ARR?"* wants BM25 for `ARR` and `Q3`, vector for
*"revenue growth"* phrasing the report may use instead, and the graph for other chunks that mention the
same entities. No single store gets all three.

### 1.2 What the user sees

The retrieval row of the pipeline tracker reports each store's hit count as a single line —
`Vector: 10 | BM25: 7 | Graph: 3` — and the aggregator row reports how many survived deduplication:
`14 unique docs (from 20 total, 6 duplicates removed)`. The reranker row then reports the selected
scores and their source stores.

Once the answer arrives, each cited source becomes an expandable card showing its file name, page, the
originating store, its `rerank_score`, a 250-character preview, and the full chunk text. **Only sources
the model explicitly cited appear** — retrieval commonly surfaces documents the answer does not use.

On the knowledge-base page the same stores are reported as index statistics: a vector count, a BM25
count, and a graph triple of `{documents, entities, edges}`.

---

## 📍 2. WHERE IT LIVES

Paths are relative to the package root, `Backend/src/adrag/`.

| Concern | Path | Anchor |
|---|---|---|
| Fan-out node | `custom_packages/rag_pipeline/retrieval/hybrid_node.py:25` | `retrieval_node` |
| Web search node | `custom_packages/rag_pipeline/retrieval/web_node.py:20` | `external_tools_node` |
| Dense store | `custom_packages/rag_pipeline/retrieval/stores/vector_store.py` | `ChromaVectorStore`, `FaissVectorStore` |
| Sparse store | `custom_packages/rag_pipeline/retrieval/stores/bm25_store.py` | `BM25Store` |
| Graph store | `custom_packages/rag_pipeline/retrieval/stores/graph_store.py` | `GraphStore` |
| Merge + dedup | `custom_packages/rag_pipeline/ranking/aggregator.py:19` | `aggregator_node` |
| Cross-encoder | `custom_packages/rag_pipeline/ranking/reranker.py:34` | `reranker_node` |
| Embedding singleton | `custom_packages/rag_pipeline/models/embeddings.py:16` | `get_embedder` |
| Write path | `routes/knowledge_base/services.py:44` | `index_document` |

```text
custom_packages/rag_pipeline/retrieval/
│
├── 📁 stores/                 One module per backend — the persistence layer
│   ├── 📄 vector_store.py      Chroma (default) + FAISS (opt-in), one `vector_store` name
│   ├── 📄 bm25_store.py        rank-bm25 Okapi over a pickled corpus
│   └── 📄 graph_store.py       NetworkX bipartite document/entity graph
│
├── 📄 hybrid_node.py          The fan-out node — three searches, three lists
└── 📄 web_node.py             DuckDuckGo search, optional and always non-fatal
```

> [!NOTE]
> **The per-kind folders are gone.** `retrieval/vector/`, `retrieval/keyword/` and `retrieval/graph/`
> were retired when the backend was rebuilt around the `adrag` package; every store now lives flat under
> `retrieval/stores/`. A stale comment at `hybrid_node.py:18` still mentions *"the keyword
> subpackage"* — there is no such subpackage.

---

## 🏗️ 3. ARCHITECTURE

### 3.1 The four evidence sources

<p align="center">
  <img src="../../../.readme-lib/documentation/hybrid-retrieval/diagrams/svg/retrieval-rerank-funnel.svg" alt="The retrieval funnel: one query fans out to vector_store (Chroma cosine, top_k 10, score 0 to 1), bm25_store (Okapi BM25, top_k 10, unbounded score), graph_store (NetworkX 2-hop, top_k 5, unbounded weight), and — only if use_external — external_tools (DuckDuckGo, 5 results, score fixed at 0.7). All four feed aggregate, which dedups by MD5 of content and keeps the highest score. Up to 30 candidates on four non-comparable scales then reach rerank, where a cross-encoder scores every pair on one comparable scale, and the top 5 by rerank_score become the context." width="700">
</p>

<sub>Diagram source: <a href="../../../.readme-lib/documentation/hybrid-retrieval/diagrams/mermaid-source/retrieval-rerank-funnel.mmd"><code>retrieval-rerank-funnel.mmd</code></a> — edit it, then regenerate the SVG (don't hand-edit the SVG).</sub>

| Branch | Backend | Width | `score` expression | Scale |
|---|---|---|---|---|
| **Vector** | Chroma (default) or FAISS | `RETRIEVAL_TOP_K` = `10` | `1.0 - distance` | ≈ `0.0`–`1.0`, cosine |
| **BM25** | `rank_bm25.BM25Okapi` | `RETRIEVAL_TOP_K` = `10` | the raw Okapi score | `> 0`, **unbounded above** |
| **Graph** | `networkx.Graph` traversal | `max(TOP_K // 2, 3)` = `5` | a sum of hop weights | `> 0`, **unbounded above** |
| **Web** *(conditional)* | DuckDuckGo via `ddgs` | `WEB_RESULTS` = `5`, hardcoded | the literal `0.7` | constant |

**The graph store gets half the budget, floored at three.** That asymmetry is deliberate — graph hits
are noisier than the other two — and it is stated nowhere but in that one `max(TOP_K // 2, 3)`
expression at `hybrid_node.py:43`.

### 3.2 The store surface — and where it is not uniform

A new retriever is expected to implement `add_documents`, `search`, `delete_by_file`, `count`, and
`clear`, plus a module-level singleton. That description is **approximately true and precisely wrong in
four places**, and the divergences are structural rather than cosmetic:

| Method | Chroma | FAISS | BM25 | Graph |
|---|---|---|---|---|
| `add_documents(texts, metadatas, ids=None)` | ✅ `:58` | ✅ `:179` | ⚠️ `:67` — **two params, no `ids`** | ❌ **absent** |
| `add_document(doc_id, content, metadata)` | ❌ | ❌ | ❌ | ✅ `:65` — **singular, one chunk per call** |
| `search(query, top_k=…)` | ✅ `:76` (`=10`) | ✅ `:198` (`=10`) | ✅ `:73` (`=10`) | ✅ `:87` — **default `5`, not `10`** |
| `delete_by_file(file_hash)` | ✅ `:97` → `int` | ✅ `:217` → `int` | ✅ `:90` → `int` | ⚠️ `:123` → **`None`** |
| `count()` | ✅ `:104` | ✅ `:239` | ✅ `:104` | ❌ **absent** |
| `get_stats()` | ❌ | ❌ | ❌ | ✅ `:153` → `{documents, entities, edges}` |
| `clear()` | ✅ `:107` | ✅ `:242` | ✅ `:107` | ✅ `:162` |
| `count_entities_by_file(file_hash)` | ❌ | ❌ | ❌ | ✅ `:140` — graph-only |

> [!IMPORTANT]
> **A new retriever that copies the BM25 store's shape drops into the existing call sites; one that
> copies the graph store's shape does not.** The graph store indexes **one chunk per call**, so the
> ingest path loops it explicitly while the other two take the whole batch in one call. And because it
> exposes `get_stats()` instead of `count()`, the statistics aggregator special-cases it. Copy the
> divergent shape and you will be editing two call sites you did not expect to touch.

### 3.3 Singletons and import-time side effects

All four store classes use the identical idiom — a `_instance` class attribute, a `__new__` guard, and
an `_initialized` flag checked at the top of `__init__` — with the instance constructed at module scope
at the bottom of the file. The consequence is that **importing the pipeline touches the disk**:

- `os.makedirs(Config.VECTOR_ROOT, exist_ok=True)` runs at module scope (`vector_store.py:18`).
- `ChromaVectorStore.__init__` creates its directory, opens a `chromadb.PersistentClient`, and calls
  `get_or_create_collection` (`vector_store.py:49-55`) — at import, because the singleton is constructed
  at `vector_store.py:253`.
- The BM25 and graph stores each create their directory and immediately `_load()` their pickle
  (`bm25_store.py:32-36`, `graph_store.py:41-44`).

**Backend selection is an import-time branch.** Both vector classes are always *defined*; only one is
instantiated:

```python
# retrieval/stores/vector_store.py:250
if BACKEND == 'faiss':
    vector_store = FaissVectorStore()
else:
    vector_store = ChromaVectorStore()
```

**The name `vector_store` is the same either way**, which is exactly why nothing downstream knows or
cares which backend is live. Setting `VECTOR_BACKEND=faiss` without `faiss-cpu` installed raises a
`RuntimeError` at import (`vector_store.py:23-28`) — **the app fails to start, it does not degrade.**

---

## 🔄 4. LIFECYCLE & STATE MACHINE

### 4.1 The read path

Retrieval has no state machine of its own — it is a straight fan-out and funnel that runs once per
pipeline pass:

1. **Gate.** `retrieval_node` checks `state["retrieve"]`. When false it emits `stage_skip` and returns
   three empty lists without touching a store.
2. **Fan-out.** Three sequential synchronous searches (`hybrid_node.py:41-43`). Despite the module
   docstring's claim of parallelism, there is no thread pool and no `asyncio`.
3. **Report.** One `retrieval_result` event carrying the three counts.
4. **Optional web search.** `external_tools_node` runs next on a static edge and decides for itself
   whether to search.
5. **Merge.** `aggregator_node` concatenates `vector_docs + bm25_docs + graph_docs + web_docs`,
   deduplicates by content hash, and sorts.
6. **Reduce.** `reranker_node` scores every survivor with the cross-encoder and slices to
   `RERANK_TOP_K`.

On a reflection retry the whole sequence runs again, and — because returned state keys overwrite rather
than accumulate — the second pass's documents **replace** the first pass's rather than adding to them.

### 4.2 The write path

Documents reach the three stores through one function, `index_document`
(`routes/knowledge_base/services.py:44`), in a fixed order:

1. **Load and chunk** — `load_file(file_path)` returns `(texts, metadatas)`. An empty result raises
   `ValueError`, which the upload route turns into a `422`. Chunking is a
   `RecursiveCharacterTextSplitter` at `chunk_size=500`, `chunk_overlap=50`.
2. **Derive deterministic ids** — `chunk_ids = generate_chunk_ids(file_hash, len(texts))` producing
   `f"{file_hash}_{i}"`. **Deterministic ids mean a re-upload upserts rather than duplicates.**
3. **Delete first** — `remove_document(file_hash)` always runs before writing, so re-indexing is
   idempotent.
4. **Write all three stores** — `vector_store.add_documents(texts, metadatas, chunk_ids)`, then
   `bm25_store.add_documents(texts, metadatas)`, then a **per-chunk loop** into
   `graph_store.add_document(...)` (`services.py:63-66`).
5. **Register** — `kb_registry.register(...)` with the chunk, vector, entity and edge counts.

> [!CAUTION]
> **There is no transaction and no cross-store lock** — the module docstring says so explicitly
> (`services.py:6-9`). A failure between steps leaves the three stores disagreeing with **nothing
> surfaced**: the vector index may hold a document the BM25 index does not, and the registry may claim
> counts that no longer match either. Every ingest and every delete must touch **all three stores and
> the registry** or the corpus is inconsistent.

`remove_document` mirrors the same order, and `clear_everything` wipes all three stores plus the
registry plus the uploaded files. The full ingestion story — loaders, chunking, hashing, the registry
shape — is in [`../ingestion/README.md`](../ingestion/README.md).

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 The funnel

**The problem:** four sources produce up to 30 candidates on four unrelated scales, and the generator
can only usefully read about five. Something has to choose, and nothing about the inbound numbers
supports choosing.

The funnel resolves it in two steps that are easy to conflate but do very different jobs:

| Step | What it does | What it ranks on |
|---|---|---|
| **aggregate** | collapses exact duplicates, produces a single list | the raw `score` — **provisional and biased** |
| **rerank** | scores every survivor against the query with one model | `rerank_score` — **the first comparable number** |

The reranker builds `(query, content)` pairs for **every** candidate and makes a single batched
`predict()` call, then sorts descending and slices:

```python
# ranking/reranker.py:53
pairs = [(query, doc["content"]) for doc in all_docs]
scores = reranker.predict(pairs)

scored = [
    {**doc, "rerank_score": float(score)}
    for doc, score in zip(all_docs, scores)
]
scored.sort(key=lambda d: d["rerank_score"], reverse=True)
top = scored[:RERANK_TOP_K]
```

Cost is one cross-encoder forward pass per candidate — **the pipeline's dominant local-compute step**,
scaling linearly with `RETRIEVAL_TOP_K`. The model (`cross-encoder/ms-marco-MiniLM-L-6-v2` by default)
is loaded through a lazy singleton that defers `from sentence_transformers import CrossEncoder` into the
function body, so importing the pipeline does not pay for it.

The aggregator's ordering is therefore **provisional on the happy path** — the reranker re-sorts
everything. It only survives when the reranker fails (§8).

### 5.2 Deduplication by content hash

```python
# ranking/aggregator.py:34
# Keep the copy with the highest score for each unique content hash
best: dict[str, dict] = {}
for doc in raw:
    h = hashlib.md5(doc["content"].encode("utf-8", errors="replace")).hexdigest()
    if h not in best or doc["score"] > best[h]["score"]:
        best[h] = doc
```

**The key is an MD5 of the content string — exact identity.** This is the right key for the case it
targets: vector and BM25 routinely return the *same chunk*, byte for byte, and one copy should survive.
It is a limitation for everything else — a chunk differing by one character, or the same passage chunked
at a different offset, does **not** collapse.

The tie-break `doc["score"] > best[h]["score"]` compares across incomparable scales (§5.3), so when
vector and BM25 both return the same chunk, **the BM25 copy essentially always wins** — unbounded beats
≈1. The retained document's `content` and `metadata` are identical either way, so **retrieval quality is
unaffected**. But its `source` field is not, and `source` is what the aggregator's event reports and
what reflection copies into `pipeline_metadata["sources_used"]`. **The "which retriever found this?"
attribution shown in the UI is therefore systematically biased toward BM25 and graph.** It is an
attribution artifact, not a retrieval bug — but it will mislead anyone tuning the stores by watching
that distribution.

### 5.3 `score` is not comparable across stores

| Source | Expression | Where | Range | What it is |
|---|---|---|---|---|
| `vector` (Chroma) | `float(1.0 - distances[i])` | `vector_store.py:91` | ≈ `0.0`–`1.0` | a normalised cosine similarity |
| `vector` (FAISS) | `float(D[0][i])` | `vector_store.py:211` | `-1.0`–`1.0` | inner product of L2-normalised vectors = cosine |
| `bm25` | `float(scores[idx])` | `bm25_store.py:84` | `> 0`, **unbounded** | an unnormalised term-weighting sum |
| `graph` | `float(score)` | `graph_store.py:117` | `> 0`, **unbounded** | a sum of traversal path weights |
| `web` | the literal `0.7` | `web_node.py:53` | constant | nothing — a placeholder |

> [!WARNING]
> **These are three different mathematical objects and one placeholder sharing a single `float` field.**
> A BM25 score of `8.2` and a cosine score of `0.82` are not on different scales of the same quantity —
> one is a normalised similarity, one is an unnormalised term-weighting sum, and one is a graph path
> count. **Never rank, threshold, or filter on `score` across sources.** Within a single store's result
> list it is meaningful; the moment two stores' results are in the same list it is not.

### 5.4 `rerank_score` is — and its sign matters

`rerank_score` is produced in exactly one place, `reranker.py:57`, as `float(score)` from
`CrossEncoder.predict(pairs)`. Because one model scores every candidate against the same query, the
resulting numbers **are** mutually comparable.

Three properties follow, and all three are load-bearing:

- **It is a raw unnormalised logit, not a probability.** The default `ms-marco` cross-encoder emits
  logits; **negative values are normal and mean "irrelevant."** The code says so in a comment at
  `reflection.py:100`.
- **`0.0` means "not scored."** Every store seeds `rerank_score: 0.0` on every document it returns
  (`vector_store.py:93`, `:213`; `bm25_store.py:86`; `graph_store.py:119`; `web_node.py:55`), and the
  reranker overwrites it. So `0.0` unambiguously identifies a document the reranker never touched.
- **The sign drives web-search escalation.** The reflection node treats *"the best `rerank_score` is
  negative"* as *"the knowledge base had nothing useful"* and escalates to web search on the next retry.

> [!CAUTION]
> **Swapping `RERANKER_MODEL` for a model with a different score range silently breaks escalation.** A
> sigmoid-output or otherwise normalised reranker never produces a negative score, so
> `kb_insufficient` becomes permanently `False` for any non-empty context and the pipeline stops
> escalating — with no error, no warning, and no visible change other than worse answers on
> out-of-corpus questions. If you change the model, re-derive the threshold at `reflection.py:102`
> against its actual range.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

Retrieval crosses two boundaries: it reads and writes the **local filesystem**, and — only when web
search is on — it makes an **outbound HTTP call**.

| Direction | Channel | Shape | Triggered by |
|---|---|---|---|
| Store → disk | Chroma sqlite | `${VECTOR_ROOT}/chroma_db/` | every `add_documents` / `delete_by_file` / `clear` |
| Store → disk | pickle | `${KEYWORD_ROOT}/bm25_store/bm25_store.pkl` | **every** BM25 write |
| Store → disk | pickle | `${GRAPH_ROOT}/graph_store/graph_store.pkl` | **every** graph write, including each chunk |
| Store → disk | pickle + `.idx` | `${VECTOR_ROOT}/faiss_db` (+ a sibling `.idx`) | every FAISS write, opt-in only |
| Registry → disk | JSON | `${DATABASE_ROOT}/kb_registry.json` | every ingest and delete |
| Node → internet | HTTPS | DuckDuckGo text search, no API key | `use_external=True` |
| Node → SSE | in-process queue | `retrieval_result`, `stage_skip`, `stage_start` | each retrieval pass |

All four data paths default under `DATA_ROOT`, which is **anchored to the package** — `config.py`
computes the backend root from `__file__` rather than from the process working directory, so where the
server is started from does not decide where the databases land.

> [!WARNING]
> **Setting a relative `DATA_ROOT` in `.env` reintroduces working-directory dependence**, because a
> relative value *is* resolved against the cwd. `.env.example` therefore ships its whole storage block
> commented out. Note also that `DATA_ROOT` feeds `DATABASE_ROOT` and `UPLOAD_FOLDER`, which feed the
> four store paths — uncommenting a parent without its children leaves them expanding to `""`.

> [!NOTE]
> **The pickle stores are not portable and not concurrent.** They are rewritten in full on every write,
> loaded under a bare `except`, and hold no schema version. See [`stores.md`](stores.md) §5.

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **The graph store returns nothing for a query with no extractable entity.** `search` extracts entities
  from the *query* and returns `[]` immediately when the set is empty (`graph_store.py:89-91`). Entity
  extraction is three regexes — capitalised proper nouns, 2–6 letter acronyms, and camelCase — so a
  lowercase natural-language question like *"what does the report say about revenue"* gets **zero**
  graph results. This is the normal case, not a malfunction.

- **The graph's "two-hop" traversal is effectively one hop.** `add_document` creates only document↔entity
  edges, so an entity node's neighbours are always documents and the second-hop branch's
  `type == "entity"` test never passes. The `+0.5` path term never contributes. It is a uniform
  omission rather than a ranking distortion, but the store surfaces fewer related chunks than its
  docstring promises — see [`stores.md`](stores.md) §4.3.

- **BM25 returns fewer than `top_k` whenever fewer documents share a query term.** `search` filters to
  `scores[idx] > 0` (`bm25_store.py:80`), so it never returns a zero-scoring document. A retrieval row
  reporting `BM25: 2` on a ten-document corpus usually means the query vocabulary barely overlaps the
  corpus, not that something failed.

- **BM25 has no stemming and no stop-word removal.** Tokenisation is
  `re.findall(r"\b\w+\b", text.lower())` and nothing else, so *"running"* does not match *"run"* and
  common words carry weight.

- **Every BM25 and graph write rewrites the whole store.** BM25 re-tokenises the entire corpus and
  constructs a new `BM25Okapi` on every `add_documents` and every `delete_by_file`; the graph pickles
  itself on **every single chunk** because it indexes one chunk per call. Ingest cost is superlinear in
  corpus size, which is fine at the scale this is built for and will not be at ten thousand documents.

- **A re-upload of the same file replaces rather than duplicates**, because chunk ids are
  `f"{file_hash}_{i}"` and the write path deletes before writing. A file whose *content* changed gets a
  new hash and is therefore a new document, leaving the old one indexed until it is deleted explicitly.

- **Switching `VECTOR_BACKEND` does not migrate data.** It silently exposes a different, probably empty,
  index. The BM25 and graph stores are unaffected, so the corpus becomes internally inconsistent — two
  stores full, one empty — with no error.

- **Chroma does not compute the embeddings.** The application encodes them and passes explicit
  `embeddings=` (`vector_store.py:66`), so `EMBEDDING_MODEL` is authoritative and Chroma's own default
  embedder is never used. Changing that setting invalidates every existing vector without any version
  check noticing.

- **Document metadata and web metadata are disjoint key sets.** Document sources carry `file_name`,
  `file_path`, `file_hash`, `chunk_index`, `total_chunks`, `source_type`, and `page` only when the
  loader supplied one. Web results carry `url`, `title`, `source_type: "web"`, and `file_name` set to
  the **href**. This is why every consumer reads metadata defensively —
  `meta.get("file_name") or meta.get("title") or …`.

- **A `page` key exists only for PDFs.** The loader adds it only when it has one, so a `page` field
  rendered as empty in the UI is expected for `.txt`, `.md` and `.docx` sources.

---

## 💥 8. FAILURE MODES

| Failure | Symptom | Recovery |
|---|---|---|
| A store raises during `search` | **No `stage_error`** — the retrieval node has no `try`/`except` | The exception escapes the graph and reaches the browser as an in-band `error` event on a `200` |
| `VECTOR_BACKEND=faiss` without `faiss-cpu` | `RuntimeError` **at import** | The app does not start. Install `pip install -e ".[faiss]"` or unset the variable |
| A pickle store is unreadable or version-incompatible | **Silence** — the store resets to empty | A bare `except` discards the file and starts fresh (`bm25_store.py:61-63`, `graph_store.py:180-182`). **A silent data-loss path** |
| The FAISS pickle's sibling `.idx` is missing or moved | The FAISS store resets to empty | The pickle stores an `index_file` **path pointer**, so it is not self-contained — moving the data directory breaks it |
| Cross-encoder cannot load or predict | `stage_error` on the reranker row | Falls back to sorting by the raw `score` — **and this disables escalation too, see below** |
| `ddgs` not installed | `stage_error` on `external_tools` | Returns no web documents; the run continues |
| Web search raises for any other reason | `stage_error` on `external_tools` | Returns no web documents; web failure is always non-fatal |
| An ingest fails partway through | **Nothing surfaced** | The three stores disagree. Re-upload the file — the write path deletes before writing, so re-indexing repairs it |
| `VECTOR_BACKEND=faiss` on a first upload | *(historically a `TypeError`)* | **Fixed** — `_ensure_index(dim: int)` now takes the dimension directly instead of calling `len()` on it |

> [!CAUTION]
> **A broken reranker fails two features at once.** The fallback sorts by the incomparable raw `score`
> (`reranker.py:74`), so BM25's unbounded scale dominates the selection. And because those documents
> keep the `rerank_score: 0.0` their stores seeded, the reflection node's escalation test
> `max_rerank < 0` evaluates `0.0 < 0` → `False` — so the pipeline **stops escalating to web search
> exactly when its local ranking is least trustworthy.** The only signal is one `stage_error` on the
> reranker row.

---

## 🧩 9. EXTENSION POINTS

**Add a retrieval backend.** Four edits, in this order:

1. **Create `retrieval/stores/<name>_store.py`.** Implement `add_documents(texts, metadatas, ids=None)`,
   `search(query, top_k=10)`, `delete_by_file(file_hash) -> int`, `count() -> int`, and `clear()`, with
   the `_instance` / `__new__` / `_initialized` singleton idiom and the module-level instance at the
   bottom. **Copy the BM25 store's shape, not the graph store's** (§3.2) — the graph store's singular
   `add_document` and `get_stats` require special-casing at both call sites.
2. **Return the standard `Document` shape** — `content`, `metadata`, `score`, `source` (your own literal),
   and `rerank_score: 0.0`. Seeding `rerank_score` to `0.0` is not optional; the escalation heuristic
   depends on that sentinel.
3. **Wire it into `hybrid_node.py`** — one search call and one entry in the returned dict — and add the
   matching `List[Document]` key to `RAGState`.
4. **Append it to the aggregator's concatenation** (`aggregator.py:27-32`) before the dedup runs.

Nothing else in the pipeline needs editing. The reranker, compressor, reasoning and reflection nodes all
work off `all_docs` and `context` and never name a store.

**Add a store to the write path.** `index_document`, `remove_document` and `clear_everything`
(`services.py`) each touch all three stores explicitly — a fourth store needs a line in each, plus a
figure in the registry payload if it produces a countable statistic.

**Tune the widths.** `RETRIEVAL_TOP_K` (default `10`) sets the vector and BM25 widths and, halved, the
graph width. `RERANK_TOP_K` (default `5`) sets the final context size. Both are read at **module scope**,
so a change requires a process restart. **`WEB_RESULTS` is hardcoded at `web_node.py:17`** and cannot be
tuned by environment at all.

**Change the embedding model.** `EMBEDDING_MODEL` feeds a single lazily-constructed singleton
(`get_embedder`, `embeddings.py:16`). Changing it invalidates every stored vector, and **nothing detects
the mismatch** — clear and re-index the corpus.

**What not to touch.** Do not rank on `score` anywhere downstream of the aggregator. Do not remove the
`rerank_score: 0.0` seed from a store. Do not change `RERANKER_MODEL` without re-deriving the negative
threshold in `reflection.py`.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **Three stores instead of one tuned retriever.** Dense, sparse and graph retrieval fail on different
  queries, and the cross-encoder that arbitrates between them is cheap relative to the LLM calls that
  follow. Running all three and reranking is less work than tuning any one of them into sufficiency —
  and it degrades gracefully, since two stores returning nothing still leaves a usable candidate set.
  The cost is a merge step whose inputs are not comparable, which is the source of most of this page.

- **Embedded, file-backed stores instead of a database server.** Chroma's sqlite, a BM25 pickle and a
  graph pickle mean the project clones and runs with no infrastructure — no Postgres, no Elasticsearch,
  no vector-database service. The trade is explicit and accepted: no transactions, no concurrency, no
  migrations, one process only, and full-file rewrites on every write. It is the right shape for a
  single-user local system and the wrong one for anything shared.

- **A cross-encoder rather than score fusion.** Reciprocal-rank fusion or weighted score blending would
  avoid a second model — but both require the inbound scores to be at least rank-comparable, and one of
  the three "scores" here is a graph path count and another is a hardcoded constant. Re-scoring every
  candidate against the query with one model side-steps normalisation entirely. It costs one forward
  pass per candidate, which is why `RETRIEVAL_TOP_K` is the setting that most directly controls latency.

- **The knowledge base is trusted to describe itself.** File extensions are trusted to describe their
  bytes — content is never sniffed — and retrieved chunks are interpolated into prompts unescaped. Both
  are accepted risks on a localhost-only deployment, and both widen the moment the port is reachable off
  the machine.

**Continue reading:**

- [`stores.md`](stores.md) — the four store implementations in detail, method by method
- [`../rag-pipeline/README.md`](../rag-pipeline/README.md) — the eight-node pipeline this feeds
- [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md) — the retrieval, aggregate and rerank nodes
- [`../rag-pipeline/state-model.md`](../rag-pipeline/state-model.md) — the `Document` shape and merge semantics
- [`../ingestion/README.md`](../ingestion/README.md) — how documents get into the stores in the first place
- [`../../../Frontend/Documentation/chat/pipeline-tracker.md`](../../../Frontend/Documentation/chat/pipeline-tracker.md) — where the three per-store hit counts surface as the retrieval row's chips
