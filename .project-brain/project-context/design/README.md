# 🎨 Design

adRAG's visual identity: a warm, stone-tinted dark-first interface with a single emerald accent. There is
no design-system package and no CSS framework beyond Tailwind — the identity lives in exactly two files,
`Frontend/tailwind.config.js` (the token layer) and `Frontend/src/assets/main.css` (the component layer).

<br>

---

<br>

## Index

| Topic | Holds |
|---|---|
| [`theme/`](theme/README.md) | The full token set — palette, typography, radii, shadows, motion, the dark/light mechanism, and the reusable component classes |

<br>

---

<br>

## The identity in five rules

1. **Dark by default.** `stores/ui.js` initialises the theme to `'dark'` unless `localStorage['rag-theme']`
   says otherwise, and applies it by toggling the `dark` class on `<html>` (Tailwind `darkMode: 'class'`).
2. **Warm neutrals, not cool greys.** Everything neutral uses Tailwind's `stone` scale plus a custom
   `warm` palette; the darkest surfaces are near-black browns (`#0C0A09`, `#1C1917`), never blue-greys.
3. **One accent: emerald.** Primary actions, active pipeline stages, links, inline code, and the brand
   gradient are all emerald. Legacy `indigo`/`orange` section-label classes are kept as **aliases that
   resolve to emerald**, so no second accent survives.
4. **Soft, rounded, low-contrast chrome.** `rounded-xl`/`rounded-2xl` surfaces, hairline borders
   (`stone-200/80` light, `white/[0.07]` dark), and shadows that are present in light mode and removed
   entirely in dark.
5. **Fast, small motion.** Every transition is 150–220 ms with small translate distances (4–8 px). Nothing
   animates further or longer than that.
