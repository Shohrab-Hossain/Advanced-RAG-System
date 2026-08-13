# ADR-004: Embedded, file-backed stores instead of a database server
Date: 2026-08-13 · Status: accepted

> Reconstructed from the code on 2026-08-13, not recorded at decision time. Grounded in the three
> `retrieval/*/*_store.py` modules, `ingestion/registry.py`, and `config.py`.

## Context

adRAG is a local-first, single-user tool (no auth, no tenancy, CORS pinned to localhost). Every piece of
state it holds — embeddings, a keyword corpus, an entity graph, and a list of uploaded files — has to
survive a restart. Requiring the user to install and run Postgres, a vector database service, or a graph
database before they can ask a question would be most of the setup cost of the whole project.

## Decision

Persist everything to files in a configurable `DATA_ROOT`, with no server process of any kind:

| State | Mechanism |
|---|---|
| Vectors | Chroma `PersistentClient` at `CHROMA_PATH`, collection `rag_documents`, `hnsw:space=cosine` |
| Keyword corpus | a pickle of `{corpus, metadatas}` at `BM25_PATH`; the `BM25Okapi` object is rebuilt on load, not stored |
| Entity graph | a pickle of `{graph, doc_store}` at `GRAPH_PATH` |
| KB registry | a JSON file at `KB_REGISTRY_PATH`, guarded by a `threading.Lock` |

Each store is a module-level singleton (`__new__` + `_initialized` guard) that loads from disk at import
and saves after every mutation. A **FAISS** backend is implemented as an alternative to Chroma, selected by
`VECTOR_BACKEND=faiss`.

## Alternatives considered

- **FAISS instead of Chroma** — not rejected, but **not made the default**. Both are implemented; Chroma
  wins the default because it manages persistence, ids, and metadata filtering itself, whereas the FAISS
  path has to maintain parallel `ids`/`documents`/`metadatas` lists and rebuild the entire index to delete
  a file. `faiss-cpu` is marked "optional alternative backend" in `requirements.txt`.
- **A graph database for GraphRAG** — implicitly rejected; the graph is small enough for an in-memory
  `networkx.Graph` with plain neighbour iteration.
- **A relational database for the registry** — implicitly rejected; a JSON dict keyed by `file_hash` covers
  every access pattern the app has.
- TODO: no record of whether a hosted vector service was ever weighed.

## Consequences

**Makes easy**

- Zero-install persistence: `pip install -r requirements.txt` and run. Nothing to provision.
- Backup and reset are file operations — delete `databases/` to start clean.
- Each store is independently swappable behind a uniform surface (`add_documents`, `search`,
  `delete_by_file`, `count`/`get_stats`, `clear`), which is exactly what made the FAISS alternative cheap.

**Makes hard / watch out for**

- **Single process only.** The singletons are per-process memory; two workers would hold divergent copies of
  the BM25 corpus and the graph. This compounds the single-worker constraint from ADR-003.
- **The graph pickles once per chunk.** `add_document` saves at the end of every call, so a 1000-chunk
  document writes the whole graph file 1000 times — the dominant cost of ingesting a large file.
- **BM25 rebuilds its full index on every mutation.**
- **Pickle is unsafe and brittle.** A tampered store file executes arbitrary code on load; a pickle written
  by an incompatible version is silently discarded by the bare `except`, wiping that store without an
  error.
- **No transactions.** A failure partway through an upload leaves the three stores and the registry
  inconsistent; the registry is a denormalised snapshot that is never recomputed.
- **No cross-store locking.** Only the registry takes a lock; concurrent uploads mutating the same store are
  unsynchronised.
- **Switching `VECTOR_BACKEND` does not migrate data** — it silently exposes a different, probably empty,
  index.
- **Scale ceiling.** Everything but Chroma's index lives fully in RAM, and BM25 scores the entire corpus on
  every query.
