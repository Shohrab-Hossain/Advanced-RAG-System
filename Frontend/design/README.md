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

| | `brand/` | `theme/` + `theme-lab/` |
|---|---|---|
| **Holds** | the artwork — one authored master, everything else generated from it | the site's design tokens — colour, type, spacing, radius, elevation, motion |
| **Model** | master → derivative chain | token contract |
| **Consumed by** | the promote script → `public/` | `tailwind.config.js` → every component |
| **Changes when** | the mark is redrawn | the look is re-tuned |

Both hold a file called `tokens.json`, and that is **deliberate, not duplication**:

- `brand/logo/artifacts/meta/tokens.json` — the brand **identity**: `logoId`, `logoVersion`, and the
  generator's colour inputs. Read by the promote script and the drift check.
- `theme/tokens.json` — the **site tokens**. Read by `tailwind.config.js`.

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
└── theme/                 the CHOSEN theme — the single source of the design tokens
    ├── tokens.json        read by ../tailwind.config.js
    ├── tokens.css         the same tokens as CSS custom properties
    └── contract.md        the rules a theme guard/auditor enforces
```

### Three folders are deliberately absent

They are created when they first hold a real file, never before — the depth rule, which is not overridden
outside `brand/`:

| Folder | Appears when |
|---|---|
| `theme-lab/` | a design-studio run starts. It is **throwaway scratch and git-ignored** (`.gitignore` carries `Frontend/design/theme-lab/`) — candidates, the `_shared/` staging, the gallery shell |
| `library/` | a theme is saved for reuse |
| `reports/` | a theme audit first writes a conformance report |

<br>

## The rules that break something when violated

- 🔒 **Edits happen at the master and nowhere else.** Every other stage is an output; a change made
  downstream is destroyed by the next regeneration — silently, because regeneration succeeds.
- 🔒 **Promotion is manual.** Copying a derivative into `public/` never runs on a timer, never as a build
  step, never as a side effect. A human decides which asset ships.
- 🔒 **`source/` and `reference/` must never ship.** Originals at full resolution and every rejected
  direction — the two folders that would embarrass the project if served.
- 🔒 **Nothing here is wired into the app build.** Not a `prebuild`, not a `postinstall`. Regenerating a
  brand is a decision, not a build artifact.

<br>

## See also

- [`../public/`](../public/) — the shipped side. `brand-logo/` · `favicon/` · `images/og/`, each with its
  own README naming what belongs in it.
- [`theme/contract.md`](theme/contract.md) — the token rules the components must honour.
- [`brand/logo/artifacts/meta/README.md`](brand/logo/artifacts/meta/README.md) — which file is the true
  master, how to regenerate, and the promote mapping.
