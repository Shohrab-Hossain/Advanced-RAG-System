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

The rule holds on the JavaScript side too, including for the split sibling files — even
`chatHistorySidebar.css` opens with one. **The single exception is `Frontend/src/store/index.js`, which
has no header**; it arrived as a byte-identical rename of the pre-reorganisation `ui` store module, which
never had one. Treat
that as a gap to close when the file is next touched, not as licence to omit a header in a new module.

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
| API layer | Every HTTP call lives in its **subsystem's** client — `subsystems/rag/ragApi.js` (3 exports) or `subsystems/knowledge-base/kbApi.js` (5 exports) — and returns `data`, never the axios response. Each client builds its own axios instance; there is no shared one. Components call store actions, not a client — the sole exception is `NavBar.vue:111` importing `healthCheck` |
| Styling | Tailwind utility classes inline; shared patterns are promoted to `@layer components` classes in `assets/main.css` (`.card`, `.btn-primary`, `.prose-rag`). A `<style scoped>` block is the last resort — see below |
| Dark mode | Every color utility is written as a light/`dark:` pair inline |
| JSDoc | Used on the non-obvious exported functions: `streamQuery`'s callback contract (`ragApi.js:30-39`) as a full block, and one-liners on the pure helpers that return a built shape (`knowledgeBaseView.js:37,49`, `chatHistorySidebar.js:7`) |

<br>

## Splitting a Vue component

A component lives in a folder of its own name (`<Name>/<Name>.vue`), and anything extracted from it stays
in that folder as a **camelCase sibling** of the same base name. Three files exist today:
`pages/chat/views/chatView.js`, `pages/knowledge-base/views/knowledgeBaseView.js`, and
`pages/chat/components/ChatHistorySidebar/chatHistorySidebar.js`.

**What may move into a sibling is only what is pure.** Each of the three states the contract in its own
header, and the wording is the rule:

```js
/**
 * Chat History Sidebar — pure helpers
 * ------------------------------------
 * Pure formatting for ChatHistorySidebar.vue — no store, no refs, no lifecycle.
 */
```

```js
/**
 * Knowledge Base View — pure helpers
 * -----------------------------------
 * Formatting and view-model builders for KnowledgeBaseView.vue.
 * Everything here is a pure function of its arguments — no store, no refs,
 * no lifecycle. Reactivity stays in the .vue.
 */
```

So: **constants and pure functions of their arguments go to the `.js`; reactivity stays in the `.vue`.** A
`ref`, a `computed`, a `watch`, an `onMounted`, or a store import in a sibling module breaks the contract —
if the logic needs any of those, it belongs in the component. That test is also why
`LLMSelector.vue` is 204 lines with no sibling: its script (`:167-204`) is computeds plus a mount/unmount
poll timer, so there is nothing pure to extract. Size alone is not a reason to split.

A sibling module carries the same shape of header as any other module, and its exports are `UPPER_SNAKE`
for constants (`ACCEPT_ATTR`, `PIPELINE_STEPS`) and `camelCase` for functions (`formatDate`, `kbStats`,
`buildKbCards`, `buildIndexStats`, `formatTime`).

<br>

## Styling — where CSS is allowed to live

Three tiers, in order. Do not skip to a later one before the earlier ones fail:

1. **Tailwind utilities inline** — the default for everything, with each color utility written as a
   light/`dark:` pair.
2. **`@layer components` in `src/assets/main.css`** — for a pattern that repeats across components
   (`.card`, `.card-sm`, `.section-label`, `.btn-primary`, `.btn-secondary`, `.prose-rag`).
3. **A scoped block on the component** — only where neither of the above can express the rule (keyframed
   overlay transitions, deep selectors into `marked`-generated HTML). Three exist:
   `ChatHistorySidebar.vue:132`, `ResultDisplay.vue:128`, `ModalDialog.vue:36`.

When a scoped block grows past a few rules, move the CSS to a camelCase sibling and link it — **keeping
the `scoped` attribute**:

```html
<style scoped src="./chatHistorySidebar.css"></style>
```

`scoped` is kept deliberately: the extracted class names are generic enough to collide, and the sibling
file says so in its own header. The filename is `<name>.css`, matching the pure-logic sibling
convention — **the `<name>.style.css` form is never used.**

> [!NOTE]
> **This supersedes a rule the brain previously recorded as absolute.** Earlier versions of this file and
> of [`../project-layout/README.md`](../project-layout/README.md) stated flatly that components carry no
> `<style>` blocks. That was never true: `ResultDisplay.vue:128` and `ModalDialog.vue:36` carried
> `<style scoped>` at those same line numbers before the `Frontend/src/` reorganisation, so this is a
> pre-existing wrong claim being corrected, not a convention that changed. The tiering above is the rule
> the code has actually followed all along; the `src`-attribute form is the only genuinely new part.

<br>

## Testing

There is no test suite, test runner, or test convention in the repository. TODO: decide and record the
testing approach before adding the first test — the choice of framework and layout is unmade.

<br>

## Commits and PRs

The working tree **is** git-versioned — branch `feature`, remote `origin` →
`git@github.com:Shohrab-Hossain/Advanced-RAG-System.git`, 141 tracked files as of 2026-08-13.

TODO: no commit-message convention, PR template, branch policy, or `CONTRIBUTING.md` exists in the
repository, so the convention is undecided rather than inapplicable. Confirm with the owner.
