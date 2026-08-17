# brand-logo/ — consumed by THIS app

The mark as the application's own UI uses it: the navbar, the footer, an empty state, a print
stylesheet. Requested **by our own code, at a path we control** — which is what makes this folder
different from its two neighbours.

<br>

## What belongs here

```
brand-logo/
├── logo.svg            the mark, theme-neutral if the design allows it
├── logo-light.svg      ┐ only if the mark must change per theme rather than
├── logo-dark.svg       ┘ the plate behind it changing — see THE ONE RULE
└── logo.png            a raster fallback, if anything needs one
```

The exact set follows from THE ONE RULE recorded in
[`../../design/brand/logo/artifacts/meta/README.md`](../../design/brand/logo/artifacts/meta/README.md).
A brand that varies the **plate** behind a fixed mark ships **one** file here; a brand that solves each
tint per theme ships **two**. Both are correct — the rule decides which.

<br>

## The rule

> 🔒 **Nothing here is ever hand-edited. Edit the master and re-promote.**

A hand-edit is reported as `REPLACED` by the drift check, because a shipped file that no longer matches
what its master implies is a broken *process*, not a broken file. Fixing the file quietly would hide the
process failure and guarantee the next divergence is just as invisible.

The masters live in
[`../../design/brand/logo/svg/`](../../design/brand/logo/svg/README.md); the promote script copies from
there and stamps the record.

<br>

## Why this is its own folder

Three folders under `public/`, three different consumers, and 🔒 **they must not be merged**:

| Folder | Consumed by | Requested how | Renameable? |
|---|---|---|---|
| **`brand-logo/`** | **our own app** | by our code, at a path we choose | ✅ yes — we control every reference |
| [`../favicon/`](../favicon/README.md) | browsers and platforms | by `<link>` and manifest declarations | ❌ no — the platforms dictate the names |
| [`../images/og/`](../images/og/README.md) | other people's sites | by an `og:image` URL, fetched by a crawler | ⚠️ technically, but crawlers cache for weeks |

<br>

## Status

**Empty.** No master exists yet, so there is nothing to promote. Nothing in `src/` references this path.
