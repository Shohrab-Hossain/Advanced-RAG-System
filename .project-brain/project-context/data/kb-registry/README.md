# Entity: Knowledge-base registry

The list of what has been uploaded and indexed. Implemented as module functions over a single JSON file in
`Backend/src/rag_pipeline/ingestion/registry.py` — there is no class and no ORM.

<br>

## Storage

- **Path:** `KB_REGISTRY_PATH`, default `os.path.join(Config.DATABASE_ROOT, "kb_registry.json")` →
  `./data/databases/kb_registry.json`.
- **Format:** a JSON object keyed by `file_hash`, written with `indent=2`.
- **Concurrency:** every public function takes a module-level `threading.Lock`; each call does a full
  load–mutate–save cycle (no in-memory cache).
- **Legacy migration:** on import, if `./data/kb_registry.json` exists and `KB_REGISTRY_PATH` does not, the
  file is `shutil.move`d to the new path.
- **Corruption tolerance:** `_load()` swallows any exception and returns `{}` — a corrupt registry silently
  reads as empty.

<br>

## Entry shape

```json
{
  "id":          "<md5 hex>",
  "name":        "report.pdf",
  "uploaded_at": "2026-08-13T09:14:22.481+00:00",
  "chunks":      42,
  "vectors":     42,
  "entities":    137,
  "edges":       980
}
```

| Field | Type | Source |
|---|---|---|
| `id` | string | the `file_hash` (MD5 of file bytes); also the dict key |
| `name` | string | the `secure_filename`d upload name |
| `uploaded_at` | string | `datetime.now(timezone.utc).isoformat()` |
| `chunks` | int | `len(texts)` |
| `vectors` | int | equals `chunks` — one embedding per chunk |
| `entities` | int | `graph_store.count_entities_by_file(file_hash)` — **per file** |
| `edges` | int | `graph_store.get_stats()["edges"]` — **the whole graph**, not this file |

<br>

## Operations

| Function | Behaviour |
|---|---|
| `register(file_hash, file_name, stats)` | Upsert; stamps a fresh `uploaded_at`; returns the stored entry |
| `get(file_hash)` | The entry or `None` |
| `list_all()` | All entries sorted by `uploaded_at` **descending** (newest first) |
| `remove(file_hash)` | Deletes; returns `True` if it existed |
| `clear_all()` | Writes `{}` |

<br>

## Relationships

`1 registry entry ─── 1 uploaded file ─── N chunks` in each of the three stores, joined by `file_hash`.
The registry is a **denormalised snapshot**: it is written at index time and never recomputed, so its
counts drift from reality if a store is modified by any path other than the upload/delete routes.

<br>

## Constraints worth knowing

- **The registry is not the index.** Deleting `kb_registry.json` does not remove anything from the vector,
  BM25, or graph stores — it only makes the UI forget those files exist (and makes
  `DELETE /api/clear` unable to delete their uploaded files).
- **`edges` is global**, so entries written at different times report different values for the same graph.
- **A re-upload resets `uploaded_at`** and overwrites the entry under the same `id`.
- **`registry.py` imports `config.Config` at module level**, which is why it participates in the
  `src/`-as-root import convention.
