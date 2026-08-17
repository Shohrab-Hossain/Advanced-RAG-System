# design/ — the design SOURCE

Everything in this folder is **source you edit**. Nothing in it is served, imported by the app, or
bundled into a build. The things that ship live in [`../public/`](../public/) and are **promoted** copies,
never authored in place.

> The build copies `public/` verbatim and nothing else, so this folder is outside the served tree for free.
> Keep it that way — it holds full-resolution originals and every direction that was tried and rejected.

<br>

## Two systems share this root

They are **neighbours, not parent and child**, and conflating them is the mistake this section exists to
prevent.

| | `brand/` | `theme-lab/` |
|---|---|---|
| **Holds** | the artwork — one authored master, everything else generated from it | a theme being *tried out* — colour, type, elevation, motion candidates |
| **Model** | master → derivative chain | throwaway scratch |
| **Consumed by** | the promote script → `public/` | **nothing.** It is git-ignored and holds no live data |
| **Changes when** | the mark is redrawn | a look is being explored |

Both hold a file called `tokens.json`, and that is **deliberate, not duplication**:

- `brand/logo/artifacts/meta/tokens.json` — the brand **identity**: `logoId`, `logoVersion`, and the
  generator's colour inputs. Read by the promote script and the drift check.
- `theme-lab/tokens.json` — a **candidate** theme. Read by nothing.

> [!IMPORTANT]
> **`theme-lab/` is not the design source, and the build does not read this folder at all.**
> It is a scratch space for trying a new theme out, it is git-ignored, and **it may be deleted at any
> time without consequence**.
>
> The live design system is **[`../src/assets/main.css`](../src/assets/main.css)** — its `@layer
> components` classes (`.card`, `.btn-primary`, `.section-label-*`, `.prose-rag`) and its `@layer
> utilities` animations — plus the two font families in `../tailwind.config.js`, which must stay in step
> with the Google Fonts `<link>` in `../public/index.html`.
>
> **Adopting a theme means writing its values into `src/`**, not pointing the build at the lab. A
> `design/theme/` folder used to be wired into `tailwind.config.js`; that require outlived the folder and
> broke `npm run serve` and `npm run build` outright until it was removed.

<br>

## The tree

```
design/
├── README.md              this file
├── AGENT-NOTES.md         master state — read FIRST when resuming design work
│
├── brand/                 THE WORKBENCH — dev-only, never served, never imported
│   └── logo/              the one subject; a second subject is a PEER folder, never a subfolder
│       ├── svg/           stage 2 · THE MASTERS — the only place edits happen
│       ├── png/           stage 3 · raster renders, never hand-edited
│       └── artifacts/     everything that is not a deliverable
│           ├── meta/      tokens.json (the identity) · README · the promote record
│           ├── scripts/   generate · export · derive · promote · verify
│           ├── source/    stage 1 · the originals — nothing is EVER deleted from here
│           └── reference/ labs, candidates — must be deletable without consequence
│
└── theme-lab/             THROWAWAY — git-ignored, read by nothing, deletable at any time
    ├── tokens.json        a candidate theme
    ├── tokens.css         the same candidate as CSS custom properties
    └── contract.md        the rules a theme guard/auditor would enforce
```

### Two folders are deliberately absent

They are created when they first hold a real file, never before — the depth rule, which is not overridden
outside `brand/`:

| Folder | Appears when |
|---|---|
| `library/` | a theme is saved for reuse |
| `reports/` | a theme audit first writes a conformance report |

`theme-lab/` is git-ignored (`.gitignore` carries `Frontend/design/theme-lab/`), so it is present on this
machine and absent from a clone. Nothing breaks either way — that is the point of it.

<br>

## The rules that break something when violated

- 🔒 **Edits happen at the master and nowhere else.** Every other stage is an output; a change made
  downstream is destroyed by the next regeneration — silently, because regeneration succeeds.
- 🔒 **Promotion is manual.** Copying a derivative into `public/` never runs on a timer, never as a build
  step, never as a side effect. A human decides which asset ships.
- 🔒 **`source/` and `reference/` must never ship.** Originals at full resolution and every rejected
  direction — the two folders that would embarrass the project if served.
- 🔒 **Nothing here is wired into the app build.** Not a `prebuild`, not a `postinstall`, and **not a
  `require()` in `tailwind.config.js`**. Regenerating a brand — or trying a theme — is a decision, not a
  build artifact. This rule was violated once and the build died with it: the config read
  `design/theme/tokens.json`, the folder was renamed, and both `npm run serve` and `npm run build` failed
  with `MODULE_NOT_FOUND`. A folder documented as *deletable at any time* must be one the build never
  touches.

<br>

## See also

- [`../public/`](../public/) — the shipped side. `brand-logo/` · `favicon/` · `images/og/`, each with its
  own README naming what belongs in it.
- [`../src/assets/main.css`](../src/assets/main.css) — **the live design system.** The shared classes and
  animations every component actually uses.
- [`theme-lab/contract.md`](theme-lab/contract.md) — the token rules a candidate theme is written against.
  Git-ignored, so this link resolves only on a machine that has run a design pass.
- [`brand/logo/artifacts/meta/README.md`](brand/logo/artifacts/meta/README.md) — which file is the true
  master, how to regenerate, and the promote mapping.
