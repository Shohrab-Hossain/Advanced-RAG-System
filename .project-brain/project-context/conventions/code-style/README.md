# Code style

Observed conventions, both sides. No linter or formatter enforces these — consistency is by hand.

<br>

## Shared

**Section comments** divide every non-trivial file. Python uses box-drawing rules padded to a fixed
width; JavaScript uses the same shape with `//`:

```python
# ── Routing functions ─────────────────────────────────────────────────────────
```

```js
// ── REST calls ────────────────────────────────────────────────────────────────
```

**Every module opens with a header docstring / block comment**: a title, an underline of dashes, and a
short statement of purpose. Pipeline nodes additionally end their header with an `Emits:` line naming the
events they produce — do not add a node without it.

```python
"""
Cross-Encoder Reranker Node
-----------------------------
...
Emits: stage_start → stage_complete | stage_error
"""
```

**Aligned assignments** are used where a block of related settings reads as a table — `package.json`
dependency values, `STAGES` entries, `EXT_MAP` literals. Keep the alignment when editing such a block.

<br>

## Python

| Rule | Detail |
|---|---|
| Naming | `snake_case` functions and variables; `PascalCase` classes; `UPPER_SNAKE` module constants; leading `_` for private helpers and module globals (`_reranker`, `_llm_cache`, `_sessions`, `_lock`) |
| Node functions | `def <name>_node(state: RAGState) -> dict` — always this shape, always returning only modified keys |
| Type hints | On signatures and class attributes; `TypedDict` for state shapes. Modern syntax is used (`str \| None`, `dict[str, queue.Queue]`) — Python 3.10+ |
| Config reads | `os.getenv("NAME", "<default>")` with the default written at the call site, cast immediately (`int(...)`) |
| Error handling | Nodes wrap risky work in `try/except Exception as e`, `emit(session_id, "stage_error", {...})`, then `return` a fallback. Stores use bare `except` around pickle loads and reset to empty |
| Singletons | `__new__` + `_instance` + an `_initialized` guard, then a module-level instance at the bottom of the file (`vector_store = ChromaVectorStore()`) |
| Imports | stdlib, then third-party, then local — local imports are relative inside `rag_pipeline` (`from ..state import RAGState`) and absolute for `config` (`from config import Config`). Heavy imports (`sentence_transformers`, `chromadb`, `faiss`, `langchain_openai`) are deferred **inside functions** to keep startup fast |
| Prompts | `ChatPromptTemplate.from_messages([("system", ...), ("human", ...)])` assigned to a module constant `_<NAME>_PROMPT`. JSON-output prompts end with an explicit "Respond ONLY with valid JSON" instruction and a literal shape using doubled braces |
| Strings | f-strings throughout; `"..."` double quotes are the norm |

<br>

## JavaScript / Vue

| Rule | Detail |
|---|---|
| Components | Always `<script setup>` Composition API. `PascalCase.vue` filenames; views end in `View.vue` |
| Semicolons | **Omitted.** Single quotes for strings |
| Naming | `camelCase` for functions and refs; `UPPER_SNAKE` for module constants (`STAGES`, `HISTORY_KEY`, `EXT_MAP`); leading `_` for store-private helpers (`_applyEvent`, `_persistHistory`, `_animateIndexing`) |
| Stores | Pinia **setup style** — `defineStore('name', () => { … return {…} })`, never the options object |
| Props | Object syntax with `type` and `default` (`{ filename: { type: String, default: '' } }`); shorthand `{ source: Object }` where no default applies |
| Derived state | `computed()` for anything derived; `watch()` only for cross-store synchronisation |
| Async | `async/await` with `try/catch`; a swallowed error is written as `catch { /* ignore */ }` with the comment, so it reads as deliberate |
| API layer | Every HTTP call lives in `services/api.js` and returns `data`, never the axios response. Components call store actions, not the service — the sole exception is `NavBar.vue` importing `healthCheck` |
| Styling | Tailwind utility classes inline; shared patterns are promoted to `@layer components` classes in `assets/main.css` (`.card`, `.btn-primary`, `.prose-rag`). No `<style>` blocks in components |
| Dark mode | Every color utility is written as a light/`dark:` pair inline |
| JSDoc | Used on the non-obvious exported functions in `services/api.js` (`streamQuery`'s callback contract) |

<br>

## Testing

There is no test suite, test runner, or test convention in the repository. TODO: decide and record the
testing approach before adding the first test — the choice of framework and layout is unmade.

<br>

## Commits and PRs

The working tree **is** git-versioned — branch `feature`, remote `origin` →
`git@github.com:Shohrab-Hossain/Advanced-RAG-System.git`, 74 tracked files.

TODO: no commit-message convention, PR template, branch policy, or `CONTRIBUTING.md` exists in the
repository, so the convention is undecided rather than inapplicable. Confirm with the owner.
