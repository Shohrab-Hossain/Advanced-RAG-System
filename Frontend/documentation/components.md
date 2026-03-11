# Frontend Components

This document describes every component in `src/components/`, including its rendered output, props, emitted events, and key behaviour.

---

## NavBar

**File:** `src/components/NavBar.vue`

The sticky top navigation bar, present on every page.

**Renders:**
- Left: Logo icon (🧬 gradient box) + "adRAG" brand name → links to `/`
- Center: Navigation links for Home, Chat, Knowledge Base, Configuration. Active link is highlighted in emerald.
- Right:
  - **Model badge** — shows the active LLM provider emoji and model name. If OpenAI is selected but no API key is configured, shows an amber ⚠ "No API key" warning instead.
  - **Connection dot** — green pulsing dot = backend reachable; gray = offline. Label "Connected" / "Offline" visible on large screens.
  - **Theme toggle** — sun (light mode) / moon (dark mode) icon button.

**On mount:**
1. `healthCheck()` → sets `connected = true/false`
2. `store.refreshStats()` — fetches index counts
3. `store.fetchProviders()` — fetches LLM provider availability
4. `store.fetchKnowledgeBases()` — fetches KB list

**No props, no emits.**

---

## ModalDialog

**File:** `src/components/ModalDialog.vue`

A reusable modal that renders alert or confirm dialogs. Driven entirely by the `ui` Pinia store — never used directly in templates by other components.

**Usage (from anywhere):**
```js
// Alert (one button)
await ui.alert('Something went wrong.')

// Confirm (two buttons, returns boolean)
const confirmed = await ui.confirm('Are you sure?', {
  danger:       true,               // Red confirm button
  confirmText: 'Yes, delete it',
  cancelText:  'No, keep it',
})
```

**Renders:**
- Backdrop (semi-transparent blur overlay)
- Dialog box with message text
- Cancel button (confirm only) — resolves promise with `false`
- Confirm/OK button — resolves promise with `true`

**Transitions:** Fade in/out via `<Transition name="fade">`.

**No props, no emits.** Reads `ui.modal` state directly.

---

## QueryInput

**File:** `src/components/QueryInput.vue`

The primary query entry area on the Chat page.

**Renders:**
- Auto-growing `<textarea>` (min 80px, max 400px height, auto-resizes on input)
- **Submit button** ("Run RAG Pipeline") — disabled while query is running
- **Cancel button** — appears while `store.isRunning`, calls `store.abortQuery()`
- Four **example query buttons** below the textarea

**Behaviour:**
- `Ctrl+Enter` / `Cmd+Enter` submits the query
- `localQuery` is a local ref that initialises from `store.query` so it persists when navigating back to the chat page
- Calling submit sets `store.query` then calls `store.runQuery()`

**No props, no emits.**

---

## PipelineTracker

**File:** `src/components/PipelineTracker.vue`

Shows real-time animated progress through all 8 pipeline stages during (and after) a query run.

**Renders:**
- Header row: "Pipeline" section label + spinner (when running) + "from history" badge (when `store.isHistoryResult`) + retry count badge (if > 0)
- Progress bar: teal while running, emerald when done. Width = `progressPct` computed from completed stages.
- Progress counter: "X / 8 stages"
- List of **8 `<StageRow>`** components, one per pipeline stage
- Error message block (if `store.error` is set)

**Computed:**
- `completedCount` — stages with status `complete` or `skipped`
- `progressPct` — `(completedCount + (hasActive ? 0.5 : 0)) / 8 * 100`

**No props, no emits.**

---

## StageRow

**File:** `src/components/StageRow.vue`

A single row in the pipeline tracker representing one stage.

**Props:**
| Prop | Type | Description |
|---|---|---|
| `stage` | Object | `{ id, label, icon, desc }` from the `STAGES` constant |
| `status` | Object | `{ status, message, details }` from `store.stageStatuses[stage.id]` |

**Renders:**
- **Status icon:** spinner (active), ✓ (complete), ✗ (error), – (skipped), stage emoji (idle)
- **Label** and **message** (or `stage.desc` if no message yet)
- **Skipped badge** (when status = skipped)
- **Detail chips** — small pill-shaped badges shown when `status.details` has relevant counts:
  - `vector_count`, `bm25_count`, `graph_count`, `web_count` — document counts from retrieval
  - `top_k` — documents after reranking
  - `confidence` — shown as percentage
  - `grounded` — green "grounded" or red "not grounded"
  - `compression_ratio` — shown if compression was applied

**Status colour coding:**
- `active` — teal/emerald animate-pulse
- `complete` — emerald
- `error` — red
- `skipped` — gray with strikethrough
- `idle` — gray

**No emits.**

---

## ResultDisplay

**File:** `src/components/ResultDisplay.vue`

Displays the final generated answer and its source documents.

**Renders:**
- **Answer section:**
  - Markdown-rendered answer (via `marked` library) in a `prose-rag` styled container
  - Metadata badges: grounded indicator (green/red), confidence % (if available), retry badge (if retries > 0)
  - Copy button — copies `store.answer` to clipboard, shows "Copied!" for 2 seconds
- **Sources section:**
  - Toggle arrow to collapse/expand
  - 2-column grid of `<SourceCard>` components
  - **Source detail panel** — expands below when a card is selected, showing full content with metadata

**State:**
- `copied` — shows "Copied" confirmation
- `sourcesOpen` — sources section visibility (default: open)
- `selectedSource` — index of the expanded source card

**No props, no emits.** Reads `store.answer`, `store.sources`, `store.metadata`.

---

## SourceCard

**File:** `src/components/SourceCard.vue`

A single evidence card in the sources grid.

**Props:**
| Prop | Type | Description |
|---|---|---|
| `source` | Object | Source object from `store.sources` |
| `selected` | Boolean | Whether this card's detail panel is open |

**Source object fields used:**
- `index` — citation number `[1]`, `[2]`, etc.
- `file_name` — document filename
- `source` — `"vector"` | `"bm25"` | `"graph"` | `"web"`
- `rerank_score` — cross-encoder score
- `content_preview` — truncated passage text
- `page` — PDF page number (optional)
- `url` — web source URL (optional)

**Emits:** `select` — when the card is clicked (parent toggles the detail panel)

**Renders:**
- Header: citation index, `<FileTypeIcon>`, filename, source type badge, rerank score badge
- Content preview: 3-line clamp
- Footer: page number or clickable URL, expand/collapse arrow

**Source type badge colours:**
- `vector` — emerald
- `bm25` — sky
- `graph` — teal
- `web` — indigo

**Rerank score colour:** emerald if > 2.0, gray otherwise.

---

## LLMSelector

**File:** `src/components/LLMSelector.vue`

The provider and model picker used on the Configuration page.

**Renders:**
- Two provider cards: OpenAI and Local (Ollama)
  - Active provider has an emerald border and a green dot indicator
  - Each shows availability status (available/offline/not configured)
- **OpenAI card extras:**
  - API key status — shows model name if configured, "No key set" amber warning if not
- **Ollama card extras:**
  - Connection error message in red if Ollama is offline
  - Quick-start instructions when offline: `ollama serve` / `ollama pull llama3.2`
- **Model selector dropdown** — shows model list for the active provider
- **Active model footer** — small display of the currently selected provider + model
- **Refresh button** — re-checks provider availability

**Behaviour:**
- Polls Ollama availability every 15 seconds when offline (clears interval when online)
- Auto-selects the first available model when switching providers
- Calls `store.setOllamaModel()` / `store.setOpenaiModel()` on selection

**No props, no emits.**

---

## FileTypeIcon

**File:** `src/components/FileTypeIcon.vue`

A small icon that visually represents a file extension or a retrieval source type.

**Props:**
| Prop | Type | Default | Description |
|---|---|---|---|
| `filename` | String | `""` | e.g. `"report.pdf"` — drives file extension display |
| `type` | String | `""` | `"vector"` \| `"bm25"` \| `"graph"` \| `"web"` — drives source icon display |
| `size` | Number | `20` | Icon size in pixels |

**Renders (file mode — when `filename` is set):**
- Coloured pill with the file extension text:
  - `.pdf` — red
  - `.docx` / `.doc` — blue
  - `.txt` — gray
  - `.md` — purple
  - Unknown — generic file SVG

**Renders (source mode — when `type` is set):**
- SVG icon:
  - `web` — globe
  - `vector` — cylinder (database)
  - `bm25` — document
  - `graph` — network nodes

---

## StatBadge

**File:** `src/components/StatBadge.vue`

A minimal two-line stat display.

**Props:**
| Prop | Type | Description |
|---|---|---|
| `label` | String | Stat label (e.g. "Vectors") |
| `value` | Number \| String | The value to display prominently |

**Renders:** Large bold value on top, small gray label below.

---

## FileUpload *(legacy)*

**File:** `src/components/FileUpload.vue`

A standalone single-file upload widget. Superseded by the inline upload UI in `KnowledgeBaseView.vue` (which supports multiple files and the unified progress bar). Kept for potential reuse.

**Renders:**
- Drop zone
- Single upload + indexing progress bars (separate)
- Success/error status message

---

## KnowledgeBases *(legacy)*

**File:** `src/components/KnowledgeBases.vue`

A collapsible list of uploaded knowledge bases with per-file delete and a clear-all button. The functionality is now embedded directly in `KnowledgeBaseView.vue`. Kept for potential reuse.

**Renders:**
- Collapsible section header with file count
- KB card list with stats grid (vectors, entities, chunks) and delete buttons
- Clear all button
