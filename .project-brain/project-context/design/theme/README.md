# Theme tokens

Defined in `Frontend/tailwind.config.js` (extends) and `Frontend/src/assets/main.css` (`@layer base` /
`components` / `utilities`). Modes: **dark (default) + light**, switched by the `dark` class on
`<html>`.

<br>

## Custom color scale — `warm`

The only palette added to Tailwind's defaults. Real hex values, from `tailwind.config.js`:

| Token | Hex |
|---|---|
| `warm-950` | `#0C0A09` |
| `warm-900` | `#1C1917` |
| `warm-850` | `#231F1D` |
| `warm-800` | `#292524` |
| `warm-750` | `#302B28` |
| `warm-700` | `#44403C` |

Two of these are also written as arbitrary literals in `main.css` and `App.vue`: `#0C0A09` (app
background, `pre` background in dark) and `#1C1917` (card surface in dark). Prefer the `warm-*` tokens for
new work.

<br>

## Semantic color roles

| Role | Light | Dark |
|---|---|---|
| App background | `bg-stone-50` | `bg-[#0C0A09]` (= `warm-950`) |
| Body text | `text-stone-900` | `text-stone-100` |
| Card surface | `bg-white` | `bg-[#1C1917]` (= `warm-900`) |
| Card border | `border-stone-200/80` | `border-white/[0.07]` |
| Primary accent | `emerald-600` | `emerald-400` |
| Primary button | `bg-emerald-600`, hover `emerald-500`, active `emerald-700` | same |
| Secondary button | `bg-stone-100`, hover `stone-200`, active `stone-300` | `bg-white/[0.06]`, hover `/[0.10]`, active `/[0.14]` |
| Muted text | `text-stone-400` / `text-slate-400` | `text-stone-500` / `text-slate-600` |
| Error | `red-600`, `bg-red-50/60` | `red-400`, `bg-red-500/[0.06]` |
| Scrollbar thumb | `bg-stone-300`, hover `stone-400` | `bg-stone-700`, hover `stone-600` |

Section labels (`.section-label-*`): `emerald` is primary; **`-orange` and `-indigo` are aliases that also
resolve to emerald**, kept so older markup keeps working. `-sky` → `sky-500`/`sky-400`, `-amber` →
`amber-600`/`amber-400`, `-muted` → `stone-400`/`stone-500`.

**Data-source colors** (`FileTypeIcon.vue`) — these encode meaning, not decoration:

| Meaning | Hex |
|---|---|
| Vector source | `#10B981` |
| BM25 source | `#0EA5E9` |
| Graph source | `#14B8A6` |
| Web source | `#6366F1` |
| PDF badge | `#EF4444` |
| DOC/DOCX badge | `#3B82F6` |
| TXT badge | `#6B7280` |
| MD badge | `#8B5CF6` |
| Unknown / fallback | `#A8A29E` |

**Brand gradient** (`HomeView.vue` hero tile): `bg-gradient-to-br from-emerald-500 via-emerald-600
to-teal-600`, with `shadow-[0_8px_32px_rgba(99,102,241,0.35)]`. The app mark is the emoji **🧬** on that
tile. Note the shadow's rgba is an indigo left over from an earlier accent; it reads as a neutral glow
under the emerald gradient.

<br>

## Typography

Loaded from Google Fonts in `Frontend/public/index.html`.

| Family | Stack (`tailwind.config.js`) | Weights loaded |
|---|---|---|
| `font-sans` | `"Plus Jakarta Sans"`, `ui-sans-serif`, `system-ui`, `sans-serif` | 400, 500, 600, 700 |
| `font-mono` | `"JetBrains Mono"`, `ui-monospace`, `monospace` | 400, 500 |

`body` gets `font-sans antialiased` plus
`font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11'` — the Plus Jakarta Sans character variants.

Notable sizes in use: hero `text-4xl font-bold tracking-tight`; answer prose `text-sm leading-relaxed`;
inline code `text-[13px]`; section labels `text-[10px] font-semibold uppercase tracking-[0.1em]`; small
metadata `text-[11px]`.

<br>

## Radius, shadow, spacing

| Token | Value |
|---|---|
| `.card` radius | `rounded-2xl` (1rem) with `p-5` |
| `.card-sm` radius | `rounded-xl` (0.75rem) with `p-4` |
| Buttons | `rounded-xl`; primary `px-5 py-2.5`, secondary `px-4 py-2` |
| `shadow-card` (config) | `0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.06)` |
| `shadow-card-md` (config) | `0 4px 12px 0 rgb(0 0 0 / 0.08), 0 2px 4px -1px rgb(0 0 0 / 0.05)` |
| `.card` shadow (css) | `0 1px 3px 0 rgb(0,0,0,0.07), 0 1px 2px -1px rgb(0,0,0,0.05)`, and **`dark:shadow-none`** |
| Scrollbar | 5px wide/tall, transparent track, `rounded-full` thumb |

Spacing follows Tailwind's default scale; no custom spacing tokens are defined.

<br>

## Motion

| Name | Definition | Where |
|---|---|---|
| `fade-in` | `fadeIn 0.2s ease-out` — opacity 0→1, `translateY(4px)`→0 | `tailwind.config.js` + a duplicate `@keyframes fade-in-anim` in `main.css` |
| `slide-up` | `slideUp 0.2s ease-out` — opacity 0→1, `translateY(8px)`→0 | config; `main.css` uses `0.22s` |
| `shimmer` | `shimmer-anim 1.4s linear infinite` — `background-position` 200%→-200% | `main.css` only; drives the indeterminate upload bar |
| Page transition | `.page-enter-active/.page-leave-active { transition: opacity .18s ease, transform .18s ease }`; enter from `translateY(6px)`, leave to `translateY(-4px)` | `main.css`, used by `App.vue`'s `<Transition name="page" mode="out-in">` |
| Buttons | `transition-colors duration-150` | `.btn-primary`, `.btn-secondary` |
| App shell | `transition-colors duration-200` | `App.vue` root, for theme switching |

Note the duplication: `fade-in` and `slide-up` exist both as Tailwind `animation` entries and as
hand-written `@layer utilities` classes in `main.css`. The utilities layer wins where both apply.

<br>

## Component classes (`@layer components`)

| Class | Purpose |
|---|---|
| `.card`, `.card-sm` | the two surface sizes |
| `.section-label` + `.section-label-{orange,indigo,emerald,sky,amber,muted}` | small uppercase eyebrow labels |
| `.btn-primary`, `.btn-secondary` | the two button styles, both with `disabled:opacity-40 disabled:cursor-not-allowed` |
| `.prose-rag` | markdown answer styling: `p` `mb-3`; `strong` bolded to `stone-900`/`stone-100`; `h1–h3` bold `mt-5 mb-2`; `ul`/`ol` `list-inside` with `space-y-1`; `code` emerald on `emerald-50`/`emerald-950/30`, `rounded-md`, mono 13px; `pre` on `stone-100`/`#0C0A09`, `rounded-xl`, `overflow-x-auto`; `blockquote` with a 2px emerald left border, italic, muted; `a` emerald underlined, hover no-underline |

<br>

## Dark/light mechanism

`store/index.js` is the whole implementation — the app-shell store, id `'ui'` (`:8`), exported as
`useUiStore`:

```js
function applyTheme(t) { document.documentElement.classList.toggle('dark', t === 'dark') }
const theme = ref(localStorage.getItem('rag-theme') || 'dark')
```

`applyTheme` runs at store creation, and `setTheme`/`toggleTheme` persist to `localStorage['rag-theme']`.
There is no system-preference (`prefers-color-scheme`) detection and no per-route override — every
component pairs its light classes with `dark:` variants inline.

<br>

## Gotchas

- **Two sources of truth for `fade-in`/`slide-up`** (config + `main.css`) with slightly different
  durations (0.2s vs 0.22s). Change both or neither.
- **Arbitrary hex literals bypass the `warm` tokens** in `main.css` and `App.vue`. They are the same
  values today; a token change would not propagate to them.
- **Dark mode removes shadows entirely** (`dark:shadow-none`) — depth in dark comes from the border and
  surface lightness, so a component that relies on shadow for hierarchy will read flat.
- **The `indigo`/`orange` label aliases are intentional dead ends**, not an unfinished migration: they map
  to emerald so no second accent can creep back in.
