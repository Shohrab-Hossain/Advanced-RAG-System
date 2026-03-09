# encoding/ — Model Initialisation

Centralises all ML model loading so models are initialised **once** at startup
and reused across every request.

## Files

### `embeddings.py` — SentenceTransformer Singleton
Provides `get_embedder()` which lazily loads the dense embedding model on first
call and returns the same instance on all subsequent calls.

```python
from rag_pipeline.encoding.embeddings import get_embedder
emb = get_embedder()
vectors = emb.encode(["hello world"]).tolist()
```

Model: controlled by `EMBEDDING_MODEL` env var (default: `all-MiniLM-L6-v2`).
Used by: `retrieval/vector.py`.

---

### `llm.py` — LLM Factory
Three public functions:

**`get_llm(provider, temperature=0, json_mode=False)`**
Returns a LangChain `BaseChatModel`:
- `provider="openai"` → `ChatOpenAI(model=LLM_MODEL)`
- `provider="ollama"` → `ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)`
- `json_mode=True` + Ollama → adds `format="json"` to constrain output

**`safe_json_parse(text)`**
Robustly extracts JSON from LLM output that may contain:
- Markdown code fences (` ```json ... ``` `)
- Prose before/after the JSON block
- Minor formatting quirks from smaller local models

Tries: direct parse → strip fences → find first `{...}` block.

**`check_ollama()`**
Probes the Ollama server at `OLLAMA_BASE_URL`:
- Calls `/api/tags` to get the available model list
- Falls back to a root ping for older Ollama versions
- Returns `{"available": bool, "models": [...], "base_url": "..."}`

Used by: `app.py` (`/api/providers` endpoint), all generation nodes.
