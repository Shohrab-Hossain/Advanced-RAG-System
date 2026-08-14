# The theme contract

The rules a theme guard or theme auditor enforces against `Frontend/src/`. Written from what the code
**actually does** today, not from an ideal — a contract nobody can satisfy gets disabled wholesale.

<br>

## 1. One source

🔒 **[`tokens.json`](tokens.json) is the only place a design value is defined.** `tailwind.config.js`
reads it; it defines nothing. A new colour, font, shadow or motion value is added there and nowhere else.

`tokens.css` mirrors the same values as CSS custom properties for consumers that cannot run the Tailwind
config. It is a **mirror** — if the two disagree, `tokens.json` wins.

<br>

## 2. Every colour utility is written as a light/`dark:` pair

🔒 The app runs `darkMode: 'class'`, and the theme is toggled by the `ui` store. **A colour utility with
no `dark:` counterpart is a bug** — it renders correctly in exactly one theme and nobody notices in the
other until a screenshot.

```html
<!-- ✅ -->
<p class="text-stone-700 dark:text-stone-300">
<!-- ❌ — invisible on the dark ground -->
<p class="text-stone-700">
```

This applies to `text-`, `bg-`, `border-`, `ring-`, `divide-`, `placeholder-` and `shadow-`.

<br>

## 3. The palette in use

| Role | Tokens | Where |
|---|---|---|
| **Primary** | `emerald-400 · 500 · 600 · 700` | buttons, active states, section labels |
| **Accent** | `sky-*` · `amber-*` | secondary section labels, status chips |
| **Neutral (light)** | `stone-100 … stone-700` | the whole light theme |
| **Neutral (dark)** | `warm.700 … warm.950` + `white/[0.06…0.14]` overlays | the whole dark theme |

The `warm` ramp is this project's own — 850 and 750 are off-scale intermediates the default stone palette
does not provide, and they exist for layered surfaces in the chat and pipeline-tracker views.

> **`section-label-orange` and `section-label-indigo` are deliberate aliases** that resolve to emerald.
> They exist so older component references keep working after the palette moved to emerald. Do not
> "fix" them by reintroducing orange or indigo — remove the references instead, then the aliases.

<br>

## 4. Shared patterns are promoted, not repeated

🔒 A pattern used by more than one component becomes a class in `@layer components` in
[`../../src/assets/main.css`](../../src/assets/main.css) — `.card`, `.btn-primary`, `.section-label`.
🔒 **No `<style>` block in any component.** Styling is Tailwind utilities inline plus these shared
classes; a component-scoped stylesheet is a second place a design value can live.

<br>

## 5. Known escapes — the drift that already exists

An auditor will find these. They are **recorded, not sanctioned** — each is a raw value where a token
should be, and each is a candidate for the next tidy-up rather than a violation to be reported afresh
every run.

| Escape | Where | Should be |
|---|---|---|
| `dark:bg-[#1C1917]` | `.card`, `.card-sm` in `main.css` | `dark:bg-warm-900` — the token already holds that exact hex |
| `shadow-[0_1px_3px_0_rgb(0,0,0,0.07),…]` | `.card`, `.card-sm` | `shadow-card` — note the arbitrary value uses **0.07/0.05**, while the `card` token is **0.08/0.06**, so they are not currently the same shadow |
| `white/[0.06]` · `[0.07]` · `[0.10]` · `[0.14]` | dark surfaces + borders throughout | an `overlay` token group; the ladder is consistent enough to name |

🔒 **Do not silently reconcile the shadow mismatch.** The arbitrary value and the token genuinely differ;
picking one changes how every card looks, which is a design decision, not a cleanup.

<br>

## 6. What this contract does not cover

- **Layout and spacing** — the app uses Tailwind's default scale untouched, so there is nothing
  project-specific to enforce yet.
- **The brand mark.** That is a different system: [`../brand/`](../brand/) and its own rules.
- **Fonts as fetched.** `tokens.json` names the families; `public/index.html` fetches them. Changing one
  without the other leaves the family declared and unavailable.
