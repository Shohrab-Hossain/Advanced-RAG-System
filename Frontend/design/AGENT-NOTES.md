# AGENT-NOTES — design/ master state

**Read this first when resuming any design or brand work.** It is the state file; everything else in this
folder is the material.

<br>

## Phase

**Scaffolded — no artwork, no chosen theme candidate.**

The folder structure exists and is documented. What does *not* exist yet: any logo master, any promoted
asset in `public/`, any theme candidate in a lab. The tokens in `theme/` are the **existing** app theme,
extracted verbatim from `tailwind.config.js` — they are a starting point that was already in production,
not a design decision made here.

<br>

## Scope

| | |
|---|---|
| **Surfaces** | the Vue 3 SPA at `Frontend/src/` — four pages: home · chat · knowledge-base · configuration |
| **Theme mode** | `darkMode: 'class'` — every colour utility is written as a light/`dark:` pair |
| **Type** | Plus Jakarta Sans (UI) · JetBrains Mono (code), loaded from Google Fonts in `public/index.html` |
| **Palette** | a warm neutral ramp (`warm.700`–`warm.950`), stone-derived |

<br>

## Discovered tools

None opted in. No visual-verification runner installed, no design tool wired.

<br>

## Active candidate

**None.** `theme/` holds the only theme, and it is the incumbent rather than a winner of any comparison.

<br>

## What's next

In the order the brand preference's own build sequence sets out:

1. 🔒 **Write THE ONE RULE** — the single thing about the brand's appearance that is never negotiated.
   It is the one slot the project must fill in for itself, and every layout decision follows from it.
   Currently recorded as **undecided** in `brand/logo/artifacts/meta/README.md`.
2. Put the original input in `brand/logo/artifacts/source/` and leave it there forever.
3. Author the master into `brand/logo/svg/`.
4. Add the generate + export scripts to `brand/logo/artifacts/scripts/`.
5. Decide the shipped surface, then write the promote script **with a reason per row**.
6. Write the drift checker — read-only, it reports and never repairs.

Until step 3, `public/brand-logo/`, `public/favicon/` and `public/images/og/` stay empty, and
`public/index.html` declares no icon links — there is nothing yet to point them at.

<br>

## Known gaps this folder does not close

- **`/favicon.ico` 404s today.** Browsers request it directly without parsing HTML, so no `<link>`
  declaration substitutes for the file being at the root path.
- **`index.html` has no `og:image`**, and `twitter:card` is `summary` rather than `summary_large_image`.
  Both wait on `public/images/og/og-cover.png`.
