<div align="center">

# 🗄️ Store Internals

### Chroma, FAISS, BM25 and the entity graph — how each one indexes, searches, scores and persists.

</div>

<br>

---

<br>

## Content Tree

<pre>
Store Internals
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-the-four-implementations">🧱 1. The four implementations</a>
│   ├── <a href="#11-files-classes-and-singletons">1.1 Files, classes and singletons</a>
│   └── <a href="#12-the-import-time-backend-branch">1.2 The import-time backend branch</a>
│
├── <a href="#-2-the-vector-store">🧲 2. The vector store</a>
│   ├── <a href="#21-chroma--the-default">2.1 Chroma — the default</a>
│   └── <a href="#22-faiss--opt-in">2.2 FAISS — opt-in</a>
│
├── <a href="#-3-the-bm25-store">🔤 3. The BM25 store</a>
│
├── <a href="#-4-the-graph-store">🧠 4. The graph store</a>
│   ├── <a href="#41-entity-extraction">4.1 Entity extraction</a>
│   ├── <a href="#42-the-graph-shape">4.2 The graph shape</a>
│   └── <a href="#43-two-hop-traversal-scoring">4.3 Two-hop traversal scoring</a>
│
├── <a href="#-5-what-each-score-actually-is">📏 5. What each score actually is</a>
│
├── <a href="#-6-persistence">💾 6. Persistence</a>
│
├── <a href="#-7-metadata-by-source">🧬 7. Metadata by source</a>
│
└── <a href="#-8-implementing-a-new-store">🧩 8. Implementing a new store</a>
</pre>

<br>

---

<br>

## 📖 Overview

Four store implementations live under
`Backend/src/adrag/custom_packages/rag_pipeline/retrieval/stores/`. Three are active on any given run —
one vector backend, plus BM25 and the graph — and all of them are module-level singletons constructed at
import.

This page is the implementation reference. The subsystem overview, the funnel, and the reasons the three
exist at all are in [`README.md`](README.md).

> [!IMPORTANT]
> **Every store seeds `rerank_score: 0.0` on every document it returns, and that is not decoration.**
> The reranker overwrites it; anything still carrying `0.0` downstream is a document the reranker never
> scored. The reflection node's web-search escalation test reads that field's **sign**, so a store that
> omits the seed, or seeds it to something else, silently changes retry behaviour.

---

## 🧱 1. THE FOUR IMPLEMENTATIONS

### 1.1 Files, classes and singletons

| Store | File | Class | Singleton | Constructed at |
|---|---|---|---|---|
| Vector — Chroma (default) | `vector_store.py` | `ChromaVectorStore` | `vector_store` | `vector_store.py:253` |
| Vector — FAISS (opt-in) | `vector_store.py` | `FaissVectorStore` | `vector_store` | `vector_store.py:251` |
| Sparse | `bm25_store.py` | `BM25Store` | `bm25_store` | `bm25_store.py:114` |
| Graph | `graph_store.py` | `GraphStore` | `graph_store` | `graph_store.py:185` |

All four use the identical singleton idiom:

```python
# retrieval/stores/bm25_store.py:20
class BM25Store:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        ...
        self._initialized = True
```

The `_initialized` guard matters because Python calls `__init__` on **every** construction, even when
`__new__` returns the existing instance — without it, `BM25Store()` called twice would reload the pickle
and discard in-memory state.

**Because the instance is constructed at module scope, importing the pipeline touches the disk.** Each
store creates its directory and loads its persisted state as a side effect of import:

| Side effect | Where |
|---|---|
| `os.makedirs(Config.VECTOR_ROOT, exist_ok=True)` | `vector_store.py:18` — module scope, unconditional |
| `os.makedirs(Config.CHROMA_PATH)` + `PersistentClient` + `get_or_create_collection` | `vector_store.py:49-55` |
| `os.makedirs(os.path.dirname(BM25_PATH))` + `_load()` | `bm25_store.py:32-36` |
| `os.makedirs(os.path.dirname(GRAPH_PATH))` + `_load()` | `graph_store.py:41-44` |

### 1.2 The import-time backend branch

Both vector classes are always *defined*; the choice of which to instantiate is made once, at import:

```python
# retrieval/stores/vector_store.py:250
if BACKEND == 'faiss':
    vector_store = FaissVectorStore()
else:
    vector_store = ChromaVectorStore()
```

`BACKEND` is `Config.VECTOR_BACKEND` (`vector_store.py:16`), lower-cased in `config.py`. **The exported
name is `vector_store` either way**, which is precisely why nothing downstream — not `hybrid_node.py`,
not `services.py` — knows which backend is live.

The FAISS import itself is guarded at module scope:

```python
# retrieval/stores/vector_store.py:23
if BACKEND == 'faiss':
    try:
        import faiss
        import numpy as np
    except ImportError:
        raise RuntimeError("VECTOR_BACKEND=faiss requires faiss-cpu to be installed")
```

**This fails the app at startup rather than degrading.** Install the optional group with
`pip install -e ".[faiss]"`, or leave `VECTOR_BACKEND` unset.

---

## 🧲 2. THE VECTOR STORE

### 2.1 Chroma — the default

**Client and collection.** A `chromadb.PersistentClient(path=Config.CHROMA_PATH)` with one collection,
`COLLECTION_NAME = "rag_documents"`, created with an explicit distance metric:

```python
# retrieval/stores/vector_store.py:51
self.client = chromadb.PersistentClient(path=Config.CHROMA_PATH)
self.collection = self.client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)
```

**Embeddings are computed in the application, not by Chroma.** `add_documents` encodes the texts itself
and passes explicit `embeddings=`:

```python
# retrieval/stores/vector_store.py:64
if not texts:
    return
embeddings = self.embedder.encode(texts).tolist()
if ids is None:
    ids = [str(uuid.uuid4()) for _ in texts]
self.collection.add(
    embeddings=embeddings,
    documents=texts,
    metadatas=metadatas,
    ids=ids,
)
```

So `EMBEDDING_MODEL` is authoritative and **Chroma's own default embedder is never used**. The
`uuid4` fallback for `ids` exists but is never taken in practice — the ingest path always supplies
deterministic `f"{file_hash}_{i}"` ids.

**Search** early-returns `[]` when the collection is empty and clamps the request to the collection
size, which is what keeps Chroma from erroring on a small corpus:

```python
# retrieval/stores/vector_store.py:76
def search(self, query: str, top_k: int = 10) -> List[dict]:
    total = self.collection.count()
    if total == 0:
        return []
    query_emb = self.embedder.encode([query]).tolist()
    results = self.collection.query(
        query_embeddings=query_emb,
        n_results=min(top_k, total),
        include=["documents", "metadatas", "distances"],
    )
```

The score is `float(1.0 - results["distances"][0][i])` (`vector_store.py:91`). Because the collection
space is cosine, the distance is in `[0, 2]` and the score is formally in `[-1, 1]` — in practice ≈`0`–`1`
for anything the model considers related at all.

**Delete** is a metadata filter followed by a delete by id, returning the count removed
(`vector_store.py:97-102`). **`clear()` drops and recreates the collection** with the same cosine
metadata (`vector_store.py:107-112`) — recreating it is what preserves the distance metric, so do not
simplify that to a bare delete.

Persistence is Chroma's own sqlite. There is no pickle on this path, and no full-corpus rewrite on
write.

### 2.2 FAISS — opt-in

An `IndexFlatIP` over **L2-normalised** vectors, which makes inner product equal cosine similarity:

```python
# retrieval/stores/vector_store.py:171
def _ensure_index(self, dim: int):
    # Takes the DIMENSION, not a vector: the only caller has embs.shape[1] to hand, and
    # len() on that int raised TypeError — the first add_documents() always died here.
    if self.index is None:
        self.dim = dim
        # use inner product on normalized vectors for cosine
        self.index = faiss.IndexFlatIP(self.dim)
```

`add_documents` encodes, normalises, ensures the index exists at the embedding dimension, then adds and
saves (`vector_store.py:185-196`). The score is the raw inner product, `float(D[0][i])`
(`vector_store.py:211`) — in `[-1, 1]`.

Three differences from Chroma that matter operationally:

- **`_save()` runs on every write** (`vector_store.py:158-169`) and pickles `ids`, `documents`,
  `metadatas` plus an `index_file` **path pointer** to a sibling `.idx` written by `faiss.write_index`.
  **The pickle is therefore not self-contained** — moving the data directory breaks the store.
- **`delete_by_file` re-embeds and rebuilds the entire index** from the surviving documents
  (`vector_store.py:229-233`) — O(corpus) per delete, and it pays the embedding cost again.
- **No metadata filtering.** The delete is a linear scan over `self.metadatas` in Python.

> [!NOTE]
> **The historic first-upload failure is fixed.** `add_documents` calls
> `self._ensure_index(embs.shape[1])`, passing an `int`; the helper previously did `len(emb_vec)` on it
> and raised `TypeError`, so the very first upload after enabling `VECTOR_BACKEND=faiss` always died.
> `_ensure_index` now takes `dim: int` directly. Chroma was never affected and remains the default.

> [!WARNING]
> **Switching `VECTOR_BACKEND` does not migrate data.** It silently exposes a different, probably empty,
> index while the BM25 and graph stores keep their contents — leaving the corpus internally inconsistent
> with no error. Re-index after switching.

---

## 🔤 3. THE BM25 STORE

**Model.** `rank_bm25.BM25Okapi` over a tokenisation that is deliberately minimal:

```python
# retrieval/stores/bm25_store.py:41
def _tokenize(self, text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.lower())
```

Lowercase word characters, **no stemming and no stop-word removal**. *"Running"* does not match *"run"*,
and common words carry weight. That is a real quality limitation, and it is also why this store is fast
and has no language dependency.

**The index is rebuilt from scratch on every write.** `_rebuild()` re-tokenises the entire corpus and
constructs a new `BM25Okapi` (`bm25_store.py:44-47`); it is called from both `add_documents` and
`delete_by_file`. Ingest cost is therefore superlinear in corpus size.

**Search filters out non-positive scores:**

```python
# retrieval/stores/bm25_store.py:76
scores = self.bm25.get_scores(self._tokenize(query))
top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
results = []
for idx in top_indices:
    if scores[idx] > 0:
        results.append({
            "content": self.corpus[idx],
            "metadata": self.metadatas[idx],
            "score": float(scores[idx]),
            "source": "bm25",
            "rerank_score": 0.0,
        })
```

**So BM25 routinely returns fewer than `top_k` documents** — one for every corpus entry sharing at least
one query term, and never a zero-scoring one. A retrieval row reporting `BM25: 2` usually means low
vocabulary overlap, not a failure.

**Persistence.** `_save()` pickles `{"corpus": …, "metadatas": …}` on every write. **The `BM25Okapi`
object itself is not pickled** — it is recomputed from the corpus by `_rebuild()` on load, which is why
the store survives a `rank-bm25` upgrade that changes the model's internals.

**Surface divergence.** `add_documents(texts, metadatas)` takes **two parameters and no `ids`** — the
store is positional, keyed by list index, and has no notion of a document id. Deletion works by scanning
`metadatas` for a matching `file_hash`.

---

## 🧠 4. THE GRAPH STORE

A `networkx.Graph()` — **undirected** — holding a bipartite arrangement of document nodes and entity
nodes. It answers a question neither other store can: *which other chunks talk about the same things
this query mentions?*

### 4.1 Entity extraction

**Three regexes and no NLP model:**

```python
# retrieval/stores/graph_store.py:49
def _extract_entities(self, text: str) -> Set[str]:
    entities: Set[str] = set()
    # Multi-word proper nouns (e.g. "Google Cloud", "New York")
    for m in re.findall(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b", text):
        if m not in _STOP_WORDS and len(m) > 2:
            entities.add(m)
    # Acronyms (e.g. "LLM", "RAG", "API")
    for m in re.findall(r"\b[A-Z]{2,6}\b", text):
        entities.add(m)
    # camelCase technical terms
    for m in re.findall(r"\b[a-z]+(?:[A-Z][a-z]+)+\b", text):
        entities.add(m)
    return entities
```

A 26-word `_STOP_WORDS` set (`graph_store.py:22-26`) removes sentence-initial capitalised function words
— `The`, `This`, `With`, `When` and so on — that the first regex would otherwise treat as entities.

> [!IMPORTANT]
> **`search` returns `[]` immediately when the query contains no extractable entity**
> (`graph_store.py:89-91`). Because extraction is capitalisation-driven, a lowercase natural-language
> question — *"what does the report say about revenue"* — yields **nothing at all** from the graph. This
> is the normal case for conversational queries, not a malfunction, and it is why the graph row often
> reports `0`.

### 4.2 The graph shape

`add_document` indexes **one chunk per call** and links it to every entity it contains:

```python
# retrieval/stores/graph_store.py:65
def add_document(self, doc_id: str, content: str, metadata: dict) -> None:
    """Index a document chunk and connect it to its entities."""
    entities = self._extract_entities(content)
    self.graph.add_node(
        doc_id, type="document",
        content_preview=content[:200], metadata=metadata,
    )
    self.doc_store[doc_id] = {"content": content, "metadata": metadata}

    for entity in entities:
        eid = f"entity:{entity.lower()}"
        if not self.graph.has_node(eid):
            self.graph.add_node(eid, type="entity", name=entity, count=0)
        self.graph.nodes[eid]["count"] = self.graph.nodes[eid].get("count", 0) + 1

        if self.graph.has_edge(doc_id, eid):
            self.graph[doc_id][eid]["weight"] += 1
        else:
            self.graph.add_edge(doc_id, eid, weight=1)

    self._save()
```

Three structural details:

- **Node types.** `type="document"` keyed by chunk id, `type="entity"` keyed `f"entity:{name.lower()}"`.
  The lowercased key is what merges `RAG`, `Rag` and `rag` into one node.
- **Edge `weight` counts co-occurrences**; entity nodes carry their own `count`.
- **Full content lives outside the graph.** Graph nodes hold only a 200-character `content_preview`; the
  full text is in a parallel `doc_store: Dict[str, dict]`, and both are pickled together. Keeping the
  bodies out of the graph is what stops traversal from dragging the whole corpus into memory.

**`_save()` runs at the end of every `add_document` call** — so ingesting a 40-chunk document pickles the
entire graph 40 times.

**Deletion garbage-collects orphans.** `delete_by_file` removes the matching document nodes, then removes
every entity node whose degree has dropped to zero (`graph_store.py:133-137`), so the entity space does
not accumulate dead nodes. It returns `None`, unlike the other stores' `int`.

### 4.3 Two-hop traversal scoring

```python
# retrieval/stores/graph_store.py:95
for entity in query_entities:
    eid = f"entity:{entity.lower()}"
    if not self.graph.has_node(eid):
        continue
    # 1st hop: documents directly connected to this entity
    for nbr in self.graph.neighbors(eid):
        if self.graph.nodes[nbr].get("type") == "document":
            doc_scores[nbr] += self.graph[eid][nbr].get("weight", 1) * 2.0
    # 2nd hop: documents sharing related entities
    for nbr in list(self.graph.neighbors(eid)):
        if self.graph.nodes[nbr].get("type") == "entity":
            for doc_nbr in self.graph.neighbors(nbr):
                if self.graph.nodes[doc_nbr].get("type") == "document":
                    doc_scores[doc_nbr] += 0.5
```

- **First hop** — a document directly mentioning a query entity scores `edge_weight * 2.0`, so mentioning
  it repeatedly scores higher.
- **Second hop** — intended to give every document reachable through a *neighbouring entity* a flat
  `+0.5` per path, so that a chunk sharing context with a direct match still surfaces.
- The result is `sorted(doc_scores.items(), …)[:top_k]`, and the raw sum becomes the document's `score`.

> [!WARNING]
> **The second-hop branch cannot fire as the graph is currently built.** `add_document` creates exactly
> one kind of edge — `self.graph.add_edge(doc_id, eid, weight=1)` at `graph_store.py:83` is the only
> `add_edge` call in the file — so the graph is strictly bipartite and **every neighbour of an entity
> node is a document node**. The second-hop loop tests `self.graph.nodes[nbr].get("type") == "entity"`
> on those neighbours (`graph_store.py:105`), which is never true. There are no entity–entity edges for
> it to walk.
>
> So the traversal is **effectively one hop**: scoring is entirely the `weight × 2.0` term, and the
> `+0.5` term never contributes. Ranking is unaffected in a relative sense — it is a uniform omission,
> not a distortion — but the store surfaces fewer documents than its docstring's *"queries traverse up
> to 2 hops"* promises. Connecting co-occurring entities to each other at ingest time is what would
> activate the branch; nothing else in the pipeline needs to change for it to work.

Either way, the resulting number is a **path-weight sum with no upper bound and no relationship to a
similarity**.

**`get_stats()`** (`graph_store.py:153`) is the store's `count()` substitute, returning
`{documents, entities, edges}` — which is why the knowledge-base statistics endpoint special-cases this
store. `count_entities_by_file` (`graph_store.py:140`) exists solely to fill the registry's entity count
at ingest time.

---

## 📏 5. WHAT EACH SCORE ACTUALLY IS

| Source | Expression | Where | Range | The quantity |
|---|---|---|---|---|
| `vector` (Chroma) | `float(1.0 - distances[i])` | `vector_store.py:91` | ≈ `0.0`–`1.0` | normalised cosine similarity |
| `vector` (FAISS) | `float(D[0][i])` | `vector_store.py:211` | `-1.0`–`1.0` | inner product of L2-normalised vectors = cosine |
| `bm25` | `float(scores[idx])` | `bm25_store.py:84` | `> 0`, **unbounded** | unnormalised term-weighting sum |
| `graph` | `float(score)` | `graph_store.py:117` | `> 0`, **unbounded** | sum of `weight × 2.0` and `+0.5` path terms |
| `web` | the literal `0.7` | `web_node.py:53` | constant | nothing — a placeholder |

> [!CAUTION]
> **Three different mathematical objects and one placeholder share a single `float` field named
> `score`.** A BM25 score of `8.2` and a cosine score of `0.82` are not the same quantity at different
> scales. **Never rank, threshold, or filter on `score` once two stores' results are in the same list.**
>
> Two places in this codebase do exactly that, deliberately and with known consequences: the
> aggregator's dedup tie-break and sort (`aggregator.py:38`, `:41`), where the effect is limited to
> **source attribution** because the reranker re-sorts everything; and the reranker's own error fallback
> (`reranker.py:74`), where the effect is a genuinely worse context.

**`rerank_score` is the comparable one.** Produced only at `reranker.py:57` as `float(score)` from
`CrossEncoder.predict(pairs)` — one model, one query, every candidate, therefore one scale.

- **Raw unnormalised logits, not probabilities.** Negative values are normal and mean "irrelevant." The
  code records the reason in a comment at `reflection.py:100`.
- **`0.0` means "the reranker has not run on this document"** — every store seeds it, and only the
  reranker overwrites it.
- **Consumers:** the sort and slice (`reranker.py:60-61`), the `scores` array in the SSE payload
  (`reranker.py:66`), the per-source figure on each UI source card (`reasoning.py:65`), and the
  escalation heuristic (`reflection.py:101-102`).

**Do not describe `rerank_score` as a 0–1 relevance probability anywhere.** That single error invalidates
the escalation mechanism's explanation and will lead someone to "fix" a negative score.

---

## 💾 6. PERSISTENCE

| Store | Format | Default path | Written |
|---|---|---|---|
| Chroma | sqlite (Chroma-managed) | `${VECTOR_ROOT}/chroma_db` | incrementally, by Chroma |
| FAISS | pickle + a sibling `.idx` | `${VECTOR_ROOT}/faiss_db` | **in full, on every write** |
| BM25 | pickle | `${KEYWORD_ROOT}/bm25_store/bm25_store.pkl` | **in full, on every write** |
| Graph | pickle | `${GRAPH_ROOT}/graph_store/graph_store.pkl` | **in full, on every `add_document`** |
| KB registry | JSON | `${DATABASE_ROOT}/kb_registry.json` | on every ingest and delete |

All paths default under `DATA_ROOT`, which `config.py` anchors to the package by computing the backend
root from `__file__` — **not** from the process working directory. That is why the server can be started
from anywhere without the databases moving.

> [!CAUTION]
> **The pickle stores load under a bare `except`, and a failure resets them to empty — silently.**
>
> ```python
> # retrieval/stores/graph_store.py:173
> def _load(self) -> None:
>     if os.path.exists(GRAPH_PATH):
>         try:
>             with open(GRAPH_PATH, "rb") as f:
>                 data = pickle.load(f)
>                 self.graph = data["graph"]
>                 self.doc_store = data["doc_store"]
>         except Exception:
>             self.graph = nx.Graph()
>             self.doc_store = {}
> ```
>
> `bm25_store.py:53-63` has the identical shape. An unreadable, truncated, or version-incompatible
> pickle is **discarded without an error, a log line, or any startup warning** — the store simply starts
> empty and the app runs normally. This is a real data-loss path: a `networkx` upgrade that changes
> `Graph`'s pickled representation would wipe the knowledge graph on the next restart with no signal
> other than the index statistics dropping to zero.
>
> The stores carry **no schema version**, so there is nothing to check even if the handler wanted to.

Three further properties follow from full-file pickling:

- **No concurrency.** Two simultaneous writes race on the same file. The system is single-worker by
  design, which is what makes this survivable.
- **No partial write.** A crash mid-`pickle.dump` leaves a truncated file, which the bare `except` then
  treats as an empty store on the next start.
- **The FAISS pickle is not self-contained** — it stores a *path* to its `.idx` sibling, so moving or
  copying the data directory breaks it in a way the other stores' pickles are immune to.

---

## 🧬 7. METADATA BY SOURCE

All three knowledge-base stores carry the loader's metadata **verbatim** — they add nothing and strip
nothing. Web results carry a **disjoint** set built by the web node.

| Key | Documents | Web | Notes |
|---|---|---|---|
| `file_name` | ✅ | ✅ | For a web result this is the **href**, not a filename |
| `file_path` | ✅ | ❌ | The stored upload path |
| `file_hash` | ✅ | ❌ | The delete key for all three stores |
| `chunk_index` | ✅ | ❌ | Position within the source document |
| `total_chunks` | ✅ | ❌ | How many chunks the document produced |
| `source_type` | ✅ | ✅ (`"web"`) | |
| `page` | ⚠️ **PDFs only** | ❌ | Present only when the loader supplied one |
| `url` | ❌ | ✅ | |
| `title` | ❌ | ✅ | |

**This is why every consumer reads metadata defensively** — the `meta.get("file_name") or
meta.get("title") or …` chains in the compressor (`compressor.py:59`) and the reasoning node
(`reasoning.py:61`) exist because the two key sets barely overlap. A `page` field rendering as empty in
the UI is expected for `.txt`, `.md` and `.docx` sources, not a bug.

---

## 🧩 8. IMPLEMENTING A NEW STORE

**Copy the BM25 store's shape.** It is the closest thing to the canonical surface, and it drops into the
existing call sites without editing them. **Do not copy the graph store's shape** — its singular
`add_document` and its `get_stats()` instead of `count()` each require a special case at a call site.

The surface to implement:

| Method | Signature | Returns |
|---|---|---|
| `add_documents` | `(texts: List[str], metadatas: List[dict], ids: Optional[List[str]] = None)` | `None` |
| `search` | `(query: str, top_k: int = 10)` | `List[dict]` in the `Document` shape |
| `delete_by_file` | `(file_hash: str)` | `int` — the count removed |
| `count` | `()` | `int` |
| `clear` | `()` | `None` |

Plus the singleton idiom — `_instance`, the `__new__` guard, the `_initialized` flag — and the
module-level instance at the bottom of the file.

**Every returned document must carry all five `Document` keys:**

```python
{
    "content": <the chunk text>,
    "metadata": <the loader's metadata, verbatim>,
    "score": <your own scale — document what it is>,
    "source": "<your literal>",
    "rerank_score": 0.0,      # NOT optional — the escalation heuristic reads this sentinel
}
```

**Then wire it in, in four places:**

1. `retrieval/hybrid_node.py` — one search call and one entry in the returned dict.
2. `state.py` — a `List[Document]` key on `RAGState`, and a matching `[]` seed in the route's
   `initial_state`.
3. `ranking/aggregator.py:27-32` — append your list to the concatenation, before dedup.
4. `routes/knowledge_base/services.py` — a write in `index_document`, a delete in `remove_document`, and
   a wipe in `clear_everything`.

Nothing downstream of the aggregator needs editing. The reranker, compressor, reasoning and reflection
nodes work off `all_docs` and `context` and never name a store.

**Two things to get right that are easy to miss.** Persist on every write if you follow the file-backed
pattern — the pipeline assumes a restart loses nothing. And **document your `score`'s scale in the
module docstring**, because the aggregator will compare it against three others that are already
mutually incomparable.

**Continue reading:**

- [`README.md`](README.md) — the hybrid retrieval subsystem overview and the funnel
- [`../rag-pipeline/README.md`](../rag-pipeline/README.md) — the eight-node pipeline this feeds
- [`../rag-pipeline/nodes.md`](../rag-pipeline/nodes.md) — the retrieval, aggregate and rerank nodes
- [`../rag-pipeline/state-model.md`](../rag-pipeline/state-model.md) — the `Document` shape in full
- [`../ingestion/README.md`](../ingestion/README.md) — loading, chunking, and the KB registry
