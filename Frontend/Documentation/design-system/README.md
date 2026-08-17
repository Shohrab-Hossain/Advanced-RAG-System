<div align="center">

# 🎨 Design System

### 118 lines of CSS, two font families, 381 hand-written `dark:` pairs — and a token file that nothing reads.

<br>

[![Live source](https://img.shields.io/badge/live%20source-src%2Fassets%2Fmain.css-1c7ed6)](#-2-where-it-lives)
[![CSS variables](https://img.shields.io/badge/CSS%20custom%20properties-0-7c5cff)](#31-there-are-no-design-tokens)
[![Manifest](https://img.shields.io/badge/manifest-package.json-3fb950)](../../package.json)

[![Dark pairs](https://img.shields.io/badge/dark%3A%20utilities-381%20across%2018%20files-f59e0b)](#54-dark-mode)
[![Component classes](https://img.shields.io/badge/%40layer%20components-6%20families-f59e0b)](#52-layer-components)
[![theme-lab](https://img.shields.io/badge/design%2Ftheme--lab-throwaway-ef4444)](#33-the-theme-lab-is-not-a-source)

</div>

<br>

---

<br>

## Content Tree

<pre>
Design System
│
├── <a href="#-overview">📖 Overview</a>
│
├── <a href="#-1-purpose--user-visible-behavior">🎯 1. Purpose &amp; user-visible behavior</a>
│
├── <a href="#-2-where-it-lives">📍 2. Where it lives</a>
│
├── <a href="#%EF%B8%8F-3-architecture">🏗️ 3. Architecture</a>
│   ├── <a href="#31-there-are-no-design-tokens">3.1 There are no design tokens</a>
│   ├── <a href="#32-the-build-chain">3.2 The build chain</a>
│   └── <a href="#33-the-theme-lab-is-not-a-source">3.3 The theme lab is not a source</a>
│
├── <a href="#-4-lifecycle--state-machine">🔄 4. Lifecycle &amp; state machine</a>
│
├── <a href="#%EF%B8%8F-5-key-algorithms--data-structures">⚙️ 5. Key algorithms &amp; data structures</a>
│   ├── <a href="#51-layer-base">5.1 @layer base</a>
│   ├── <a href="#52-layer-components">5.2 @layer components</a>
│   ├── <a href="#53-layer-utilities--the-three-animations">5.3 @layer utilities — the three animations</a>
│   ├── <a href="#54-dark-mode">5.4 Dark mode</a>
│   └── <a href="#55-the-font-chain">5.5 The font chain</a>
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

**The live design system is `Frontend/src/assets/main.css`** — 118 lines — **plus the two font families
declared in `tailwind.config.js`.** That is the whole of it. Everything else on screen is Tailwind's own
utilities, written inline in components, including arbitrary values like `dark:bg-[#1C1917]`,
`shadow-[0_1px_3px_0_rgb(0,0,0,0.07)]` and `text-[10px]`.

There is no token file in the loop. **`main.css` contains zero CSS custom properties**, and
`tailwind.config.js` — 32 lines — reads nothing from anywhere: it declares two font stacks, a content
glob, `darkMode: 'class'`, and an empty plugin array.

`Frontend/design/theme-lab/` exists and is **not** part of this. It is a git-ignored scratch space for
trying a theme out; nothing in the build or the application reads it, and it may be deleted at any time
(§3.3).

So the shape to hold in your head is small and honest: **six families of component classes, three
animations, two fonts, a class-based dark mode, and 381 hand-written light/dark pairs.**

---

## 🎯 1. PURPOSE & USER-VISIBLE BEHAVIOR

What the design system delivers, from a reader's point of view:

- **One card surface everywhere.** `.card` is white in light mode and `#1C1917` in dark, with a two-part
  shadow in light and **no shadow at all** in dark — because a shadow on a dark surface reads as mud.
- **A consistent small-caps heading** above every card region — `.section-label`, at 10 px with
  0.1 em tracking, in one of a few accent colours.
- **Two button shapes** — an emerald solid and a stone outline, both with a disabled treatment.
- **A Markdown answer stylesheet**, `.prose-rag`, covering twelve element types.
- **Three motion primitives** — a fade-in, a slide-up and an infinite shimmer — plus a route transition.
- **Dark mode by default**, toggled from the navbar, remembered across reloads.
- **Two typefaces** — Plus Jakarta Sans for prose, JetBrains Mono for every number, model name, score
  and JSON dump.

---

## 📍 2. WHERE IT LIVES

Paths are relative to `Frontend/`.

| Concern | Path | Note |
|---|---|---|
| **Every shared style decision** | `src/assets/main.css` | 118 lines — the live design system |
| Font families | `tailwind.config.js:26-27` | the only theme extension that exists |
| Purge scope, dark-mode strategy | `tailwind.config.js:18-22` | `content` glob + `darkMode: 'class'` |
| Font delivery | `public/index.html:21-23` | `preconnect` + the Google Fonts `<link>` |
| Theme toggle + persistence | `src/store/index.js:4-22` | `applyTheme`, `setTheme`, `toggleTheme` |
| PostCSS wiring | `postcss.config.js` | 6 lines — `tailwindcss` + `autoprefixer` |
| Throwaway theme scratch | `design/theme-lab/` | **git-ignored, read by nothing** |

```text
Frontend/
│
├── 📁 src/assets/
│   └── 📄 main.css              THE design system — @layer base / components / utilities + transitions
├── 📄 tailwind.config.js        32 lines: content glob, darkMode 'class', two fontFamily stacks
├── 📄 postcss.config.js         tailwindcss + autoprefixer. Vue CLI 5 picks it up automatically
├── 📁 public/
│   └── 📄 index.html            The Google Fonts <link> that makes both families reachable
└── 📁 design/
    └── 📁 theme-lab/            Scratch. Git-ignored. NOT a source — see §3.3
```

---

## 🏗️ 3. ARCHITECTURE

### 3.1 There are no design tokens

This is the fact that most needs saying, because the repository looks like it has them.

- **`main.css` declares zero CSS custom properties.** No `--color-*`, no `--space-*`, nothing to swap at
  runtime.
- **`tailwind.config.js` extends exactly one thing** — `fontFamily.sans` and `fontFamily.mono`. There is
  no colour scale, no shadow scale, no custom animation registered in the config, and no `require()` of
  any file.
- **The palette is written inline, per component.** Emerald as the primary, stone as the neutral ramp,
  `#0C0A09` and `#1C1917` as the two dark surfaces, teal/sky/amber/red as accents — and every one of
  those is a Tailwind utility or an arbitrary value typed into a template.

The practical consequence is direct: **there is no single place to change a colour.** Retheming means a
find-and-replace across templates, not editing a variable. What *is* centralised is **structure** —
surfaces, labels, buttons and prose — through the `@layer components` classes in §5.2, and that is where
a shared decision belongs.

### 3.2 The build chain

```text
postcss.config.js       →  { plugins: { tailwindcss: {}, autoprefixer: {} } }
tailwind.config.js      →  content glob + darkMode 'class' + two fontFamily stacks
src/assets/main.css     →  @tailwind base/components/utilities + the three @layer blocks
Vue CLI 5 (webpack)     →  picks up postcss.config.js automatically; no PostCSS wiring in vue.config.js
```

The purge scope is `content: ['./public/index.html', './src/**/*.{vue,js,ts}']`
(`tailwind.config.js:18-21`). **`.js` being in that glob is load-bearing**, and not for an obvious
reason: `pages/knowledge-base/views/knowledgeBaseView.js` holds 24 `dark:` class pairs in a view-model,
and they survive a production build only because the scanner reads `.js` files too.

The corollary is the usual Tailwind one, and it bites harder here: **a class assembled by string
concatenation is invisible to the scanner and will be purged.** Every class in that view-model file is a
complete literal, deliberately.

Both build commands run clean today. `npm run build` emits one advisory — an entrypoint-size notice, the
app bundle at 266 KiB against a 244 KiB recommendation — which is a **warning, not a failure**.

### 3.3 The theme lab is not a source

> [!CAUTION]
> **`Frontend/design/theme-lab/` is throwaway scratch. Nothing reads it, and it may be deleted at any
> time.** It is git-ignored, it holds no live data, and no part of the build, the config or `src/`
> references it — a repository-wide search for `design/` across `src/`, `vue.config.js`,
> `tailwind.config.js`, `postcss.config.js` and `package.json` finds exactly **one hit, and it is a
> comment**.
>
> **Do not add a token there expecting it to reach the app.** It will not. Adopting a theme means
> writing the values into `src/` — into `main.css` for a shared class, or into the templates for a
> palette change.
>
> The folder contains a `tokens.json` whose own header still describes itself as *"THE SINGLE SOURCE of
> this app's design tokens"* and claims that `tailwind.config.js` reads it. **That header is false
> today.** It is git-ignored scratch and out of scope to correct here — but do not quote it, and do not
> be misled by it.

The evidence that the token layer was never live even when it was wired: the colour scale it defined
(`warm-*`) is used **nowhere** in `src/`, the shadow scale (`shadow-card`) is used **nowhere**, and the
animations the app actually renders are the hand-defined ones in `main.css`, not the token ones. The
only thing the app ever consumed from that direction was the font stack — which now lives in the config
directly.

> [!NOTE]
> **This reverses an older documented rule** that said a design token belongs in `design/theme/tokens.json`
> and that `tailwind.config.js` reads it. That is no longer true in either half. Some project notes
> elsewhere in the repository may still carry the old rule; the code is the authority, and the code reads
> nothing from `design/`.

---

## 🔄 4. LIFECYCLE & STATE MACHINE

Only one part of the design system has runtime behaviour: the theme.

```text
store creation        → theme = localStorage['rag-theme'] || 'dark'
                      → applyTheme(theme)  → documentElement.classList.toggle('dark', …)
App.vue:20            → useUiStore()  called BARE, for that side effect only
NavBar toggle         → toggleTheme() → setTheme() → ref + localStorage + applyTheme
Tailwind              → darkMode: 'class' resolves every dark: utility against <html class="dark">
```

Three details:

- **Dark is the default** on a machine with no stored preference.
- **`applyTheme` runs at store-creation time**, not in a lifecycle hook — which is why `App.vue` calls
  `useUiStore()` and discards the result. The call *is* the initialisation.
- **The class goes on `<html>`**, not on a wrapper element, so it is in scope for portals, the scrollbar
  rules in `@layer base`, and anything rendered outside the app root.

Route transitions are the other piece of motion with a lifecycle: `App.vue:7` wraps the router view in
`<Transition name="page" mode="out-in">`, and the four `page-*` classes it needs are defined at file
scope in `main.css:106-118`.

---

## ⚙️ 5. KEY ALGORITHMS & DATA STRUCTURES

### 5.1 `@layer base`

`main.css:5-15` — two rules and nothing else:

- **A custom scrollbar** (`:6-9`): 5 px wide, `bg-stone-300 dark:bg-stone-700`, one step darker on
  hover. Narrow enough to read as a hairline in both themes.
- **The body rule** (`:11-14`):

  ```css
  body {
    @apply font-sans antialiased;
    font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
  }
  ```

  Those four are Plus Jakarta Sans character variants, and this is the **only raw CSS property in the
  layer** — everything else is `@apply`. It is also the reason `font-sans` appears exactly once in the
  entire codebase: applied to `body`, it covers the whole document.

### 5.2 `@layer components`

`main.css:17-85` — six families, and this is where genuinely shared decisions live:

| Class | Line | What it is |
|---|---|---|
| `.card` | `:20-26` | the app's primary surface — `bg-white dark:bg-[#1C1917]`, `rounded-2xl p-5`, a two-part shadow in light and **`dark:shadow-none`** |
| `.card-sm` | `:28-34` | the same surface at `rounded-xl p-4` |
| `.section-label` | `:37-39` | `text-[10px] font-semibold uppercase tracking-[0.1em]` — the small-caps heading on every card |
| `.section-label-{orange,indigo,emerald,sky,amber,muted}` | `:41-46` | the colour variants |
| `.btn-primary` / `.btn-secondary` | `:49-64` | emerald solid / stone outline, both with `disabled:opacity-40 disabled:cursor-not-allowed` |
| `.prose-rag` + 12 descendant rules | `:67-84` | the Markdown answer stylesheet — `p`, `strong`, `h1`–`h3`, `ul`, `ol`, `code`, `pre`, `pre code`, `blockquote`, `a` |

> [!NOTE]
> **`.section-label-orange` and `.section-label-indigo` are aliases that both resolve to emerald**
> (`:42`). They are kept so existing references keep working after a palette consolidation, and the
> comment above them says so. Two names, one colour — expected, not a bug.

`.prose-rag` is the only stylesheet in the project that styles elements it does not control: the answer
arrives as Markdown, is parsed to HTML at runtime, and is injected with `v-html`. Twelve descendant
rules is the price of not shipping a general-purpose typography plugin for one component.

### 5.3 `@layer utilities` — the three animations

`main.css:87-104` — three animation utilities, each with **its own `@keyframes` defined inside the
layer** and suffixed `-anim` so the keyframe name cannot collide with the utility name:

| Utility | Line | Keyframes | Motion | Used by |
|---|---|---|---|---|
| `.animate-fade-in` | `:88` | `fade-in-anim` (`:92-95`) | opacity + a 4 px rise, 0.2 s | `ResultDisplay.vue:2`, `HomeView.vue:5` |
| `.animate-slide-up` | `:89` | `slide-up-anim` (`:96-99`) | an 8 px rise, 0.22 s | `HomeView.vue:25` |
| `.animate-shimmer` | `:90` | `shimmer-anim` (`:100-103`) | background-position 200 % → −200 %, 1.4 s **infinite** | `UploadPanel.vue:62` |

**All three are used**, and only these three are hand-defined. The other `animate-*` classes in the
codebase — `animate-spin` (four uses), `animate-pulse` (two), `animate-ping` (one) — are **Tailwind
built-ins**, not part of this file.

The shimmer is the interesting one: it is the indeterminate segment of the upload bar, the state that
deliberately makes no numeric claim about progress. See
[`../knowledge-base/README.md`](../knowledge-base/README.md).

Below the layers, at file scope (`:106-118`), sit `.page-enter-active`, `.page-leave-active`,
`.page-enter-from` and `.page-leave-to` — the Vue route transition. **They are outside every `@layer` on
purpose**, so they cannot be reordered or purged along with layered content.

### 5.4 Dark mode

**Mechanism:** `darkMode: 'class'` (`tailwind.config.js:22`) plus
`document.documentElement.classList.toggle('dark', …)` in the `'ui'` store. **Dark is the default.**

**Scale: 381 `dark:` utilities across 18 files.** Every colour utility in the project is written as a
light/`dark:` pair, by hand, with no variable to swap:

| File | `dark:` count |
|---|---|
| `LLMSelector.vue` | 51 |
| `ConfigView.vue` | 40 |
| `ChatView.vue` | 30 |
| `HomeView.vue` | 29 |
| **`knowledgeBaseView.js`** | **24** |
| `ResultDisplay.vue` | 23 |
| `StageRow.vue` · `SourceCard.vue` · `KnowledgeBaseList.vue` | 20 each |
| `ChatHistorySidebar.vue` · `NavBar.vue` | 19 each |
| `UploadPanel.vue` | 18 |
| `PipelineTracker.vue` | 12 |
| `KnowledgeBaseView.vue` · `ModalDialog.vue` | 5 each |
| `IndexStats.vue` | 3 |
| `App.vue` | 2 |

> [!IMPORTANT]
> **`knowledgeBaseView.js` is the outlier and the trap.** Twenty-four dark-mode pairs live in a **`.js`
> view-model**, not a template — which is exactly why `IndexStats.vue`, the component that renders them,
> has only three. Looking for the statistic cards' colours in the `.vue` file finds nothing. See
> [`../knowledge-base/README.md`](../knowledge-base/README.md) §3.2.

**The recurring palette**, read off the source since there is no token file to cite: **emerald** as the
primary (`emerald-500/600` for actions, `emerald-50` and `emerald-500/[0.07]` for tints); **stone** as
the neutral ramp (`stone-50` page, `white` cards, `stone-200` borders); **`#0C0A09`** as the dark page
background and **`#1C1917`** as the dark card; **teal, sky, amber and red** as accents.

> **`slate-*` appears alongside `stone-*` for muted text.** Two neutral families are genuinely mixed in
> this codebase. It is a real inconsistency, not a subtlety — worth knowing before adding a third.

### 5.5 The font chain

Four links, and **breaking any one of them fails silently** — the browser falls back and nothing errors:

```text
public/index.html:23              Google Fonts <link>  →  downloads Plus Jakarta Sans + JetBrains Mono
tailwind.config.js:26-27          fontFamily.sans / .mono  →  exposes them as font-sans / font-mono
src/assets/main.css:12            body { @apply font-sans }  →  applies sans document-wide
24 × font-mono across 11 files    numerals, model names, scores, JSON dumps
```

The `<link>` requests `Plus+Jakarta+Sans:wght@400;500;600;700` and `JetBrains+Mono:wght@400;500` with
`display=swap`, preceded by two `preconnect` hints at `:21-22`.

**`font-mono` is used 24 times across 11 files** — `main.css` plus ten components — which is what makes
the `fontFamily` extension load-bearing rather than decorative. Monospace here is semantic: it marks
every place a value is *data* rather than prose, which is why scores, counts, model names and the
metadata dump all carry it.

**`font-sans` is used exactly once** — `main.css:12` — and that one use is the entire document.

> Rename a family in the config without updating the `<link>` and the font quietly falls back to
> `ui-sans-serif` or `ui-monospace`. The config's own header comment says so.

---

## 🔌 6. WIRE SHAPE (CROSS-BOUNDARY CONTRACTS)

The design system has three boundaries, and each is a place where a change on one side breaks the other
silently:

| Boundary | Contract | Failure if broken |
|---|---|---|
| `public/index.html` ↔ `tailwind.config.js` | the family names must match exactly | silent fallback to a system font |
| `tailwind.config.js` `content` glob ↔ every file writing classes | a class must be a complete literal in a scanned file | the class is purged; the element renders unstyled |
| `store/index.js` ↔ `darkMode: 'class'` | the class name must be `dark`, on `<html>` | every `dark:` utility stops resolving |

**One external dependency at runtime:** the Google Fonts stylesheet, requested by the browser from the
`<link>` in `public/index.html:23`. An offline machine degrades to the fallback stacks — system sans and
system monospace — with no error and no other effect on the app.

**Where CSS lives that is not Tailwind** — the convention is *no `<style>` blocks in components*, and
there are exactly three exceptions, **all of them Vue `<transition>` class sets**, which cannot be
expressed as utilities because Vue applies them by generated class name:

| File | Line | Transition | Form |
|---|---|---|---|
| `ChatHistorySidebar.vue` | `:132` | `sidebar` + `backdrop` | `<style scoped src="./chatHistorySidebar.css">` — **an external sidecar** |
| `ResultDisplay.vue` | `:128-131` | `slide` | inline `<style scoped>` |
| `ModalDialog.vue` | `:36-39` | `fade` | inline `<style scoped>` |

Plus the global `page` transition in `main.css:106-118`. **Five transitions, four style locations.** The
sidecar file explains its own existence in a header comment: the `scoped` attribute is kept because
those class names are generic enough to collide.

---

## ⚠️ 7. EDGE CASES & GOTCHAS

- **`design/theme-lab/` is not a source, and its own `tokens.json` header says otherwise** (§3.3). The
  single most likely wrong turn on this page.

- **There is no variable to change a colour.** Retheming is a template-wide edit, not a config edit.

- **Colours for three cards live in a `.js` file** — `knowledgeBaseView.js`, 24 `dark:` pairs (§5.4).

- **A concatenated class name will be purged.** The scanner reads text, not intent. Every class must be
  a complete literal.

- **`.section-label-orange` and `.section-label-indigo` both render emerald.** Aliases, kept
  deliberately.

- **`.card` has no shadow in dark mode.** `dark:shadow-none` is explicit — the surface is separated by
  colour there, not elevation.

- **The route transition classes sit outside every `@layer`.** Moving them inside risks reordering or
  purging.

- **`animate-spin`, `animate-pulse` and `animate-ping` are not defined here.** They are Tailwind
  built-ins; only the three `-anim` utilities are local.

- **Two neutral families are mixed** — `stone-*` and `slate-*` (§5.4).

- **`npm run lint` rewrites files.** `vue-cli-service lint` runs with `--fix` by default, so invoking it
  to *check* the code silently reformats it. **`npm run lint -- --no-fix` is the read-only form.** This
  matters for CSS-adjacent work because template class-attribute edits are exactly what the auto-fixer
  will touch.

---

## 💥 8. FAILURE MODES

| Failure | Symptom | Why |
|---|---|---|
| Google Fonts unreachable | The app renders in system fonts | `display=swap` plus a fallback stack; nothing errors |
| A family renamed in the config only | The same silent fallback | The `<link>` still requests the old family |
| A class built by concatenation | The element renders unstyled in production, fine in dev | Purge scope only keeps complete literals |
| `dark` class not applied to `<html>` | Every `dark:` utility is inert | `darkMode: 'class'` has nothing to match |
| A `<style scoped>` block added for a non-transition style | It works, and it breaks the convention | Nothing enforces the rule |
| `main.css` layer order changed | Utilities may lose to components or vice versa | `@layer` order determines cascade precedence |
| A bundle-size advisory on build | A warning line, exit code 0 | 266 KiB against a 244 KiB recommendation — **not** a failure |

---

## 🧩 9. EXTENSION POINTS

**Add a shared surface or control.** `main.css`, under `@layer components`, following `.card` /
`.btn-primary`. That is the correct home for anything repeated across pages — and the only place a
shared visual decision is currently centralised.

**Add an animation.** `@layer utilities` in `main.css`, with its `@keyframes` defined **inside the same
layer** and suffixed `-anim` to match the existing three. Do not register it in `tailwind.config.js`;
the config carries no animation configuration and adding one would split the animation story across two
files.

**Add a font weight or family.** Two edits, and both are required: the Google Fonts `<link>` in
`public/index.html`, and the matching stack in `tailwind.config.js`. Either alone fails silently.

**Adopt a theme from the lab.** Copy the values **into `src/`** — into `main.css` for a shared class,
into the templates for a palette change. Do not point the build at `design/`; that folder is documented
as deletable at any time, and a build that depends on it is a build that can be deleted out from under
you.

**Introduce real tokens.** The honest version is CSS custom properties declared in `@layer base` on
`:root` and `.dark`, consumed through arbitrary values, which would collapse 381 hand-written pairs into
one declaration block. It is a large, mechanical change and it is the single highest-leverage
improvement available to this layer — but it is a decision, not a cleanup, and nothing today depends on
it.

**What not to touch.** Do not move the `page-*` transition classes into a layer. Do not remove the
`-anim` suffix from a keyframe name. Do not add a `<style>` block for anything other than a Vue
transition. Do not treat `design/theme-lab/` as live.

---

## 🔗 10. RELATED DECISIONS & DEEPER READING

- **Utilities inline, structure in `@layer components`.** The line drawn here is *repetition*, not
  *complexity*: a surface used on every page becomes `.card`, while a one-off spacing decision stays in
  the template. It keeps the shared stylesheet at 118 lines and makes any given component readable
  without cross-referencing a stylesheet — at the cost of long class attributes and no central palette.

- **No CSS custom properties.** Tailwind's `dark:` variant already handles theme switching at build
  time, so variables would be redundant for the one theme axis that exists. The cost is 381 hand-written
  pairs and a palette that can only be changed by search-and-replace — a cost that grows with every
  component and is the reason §9's token suggestion exists.

- **The theme lab kept, but disconnected.** A scratch space for trying a palette without touching the
  app is genuinely useful; wiring the build to it was not. Git-ignoring it and reading nothing from it
  keeps the experiment cheap and makes the deletion of the folder a non-event.

- **Monospace as a semantic signal.** `font-mono` marks values rather than prose — scores, counts, model
  names, JSON. That is why the font extension is load-bearing rather than cosmetic, and why 24 uses
  across 11 files is a convention rather than an accident.

**Continue reading:**

- [`../chat/README.md`](../chat/README.md) — `.prose-rag` and `.animate-fade-in` in use
- [`../knowledge-base/README.md`](../knowledge-base/README.md) — `.animate-shimmer`, and the 24 `dark:` pairs in a view-model
- [`../state/README.md`](../state/README.md) — the `'ui'` store, the theme toggle and its persistence
- [`../README.md`](../README.md) — the frontend area index, build and structure
