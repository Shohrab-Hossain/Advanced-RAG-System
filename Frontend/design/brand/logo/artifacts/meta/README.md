# logo/ — the subject README

The first thing to open, and the only place the reasoning survives.

<br>

## THE ONE RULE

> 🔒 **Write down the single thing about this brand's appearance that is never negotiated — and state
> what follows from it.**

### ⚠️ Status: NOT YET DECIDED

This is the one slot the project must fill in **for itself**, and it is deliberately left blank rather
than guessed. It is not a formality: the rule is what the folder layout, the promote mapping and the
toning decision are all *consequences* of.

Two real examples, from two different projects, arrived at independently:

- *"The gold mark is the brand. It is **never recoloured** — not to navy, not to brown, not to a darker
  gold. Gold's relative luminance makes it illegible on any light ground, so what changes per theme is
  the **background plate behind the gold**, never the gold."*
- *"Every tint is **solved** against a 3.0:1 contrast floor. Change `hue`/`saturation` and re-run the
  generator; a hand-picked hex silently breaks the guarantee."*

Note what both do: they state an invariant, then **derive the rest of the system from it**. The first
ships one mark file and varies the plate. The second ships two mark files with different palettes.
**Opposite layouts, both correct** — because each follows from its own rule.

🔒 **So do not copy another project's file layout and hope. Find the rule first; the layout is a
consequence.** A layout copied without its rule is the most common way a brand system becomes incoherent
while every individual file looks fine.

**Until this is written**, `tokens.json` leaves `colourway`, `hue`, `saturation` and `contrastFloor`
null — filling them in would be exactly the copy-and-hope this section warns against.

<br>

---

<br>

## Which file is the true master

**None yet.** When one exists it will be the bare mark in [`../../svg/`](../../svg/README.md) — a single
file. Lockups sitting beside it are *composed from* it by a script and are not additional masters.

<br>

## How to regenerate

| To rebuild | Run | Reads | Writes |
|---|---|---|---|
| the masters + lockups | `generate` | `tokens.json` | `../../svg/` |
| the rasters | `export` | `../../svg/` | `../../png/` |
| the icon ladder | `derive` | `../../svg/` | staged for promote |
| the shipped copies | `promote` | the derived set | `../../../../../public/` |
| a drift report | `verify` | everything | stdout — 🔒 read-only |

None exist yet. See [`../scripts/README.md`](../scripts/README.md) for the order they arrive in.

<br>

## The promote mapping

🔒 **Every row carries a REASON.** The mapping is not a copy list — it is the record the drift check
later reads to answer *"is this shipped file still what its master implies?"*. A row without a reason is
a row nobody can evaluate when it later looks wrong.

Destinations are relative to `Frontend/public/`.

| Derivative | → Ships to | Why this file exists at all |
|---|---|---|
| `logo.svg` | `brand-logo/logo.svg` | our own UI — navbar, footer, print. The one path we control and can rename |
| `favicon.svg` | `favicon/favicon.svg` | the modern tab icon in browsers that prefer SVG |
| `favicon.ico` | **`favicon.ico`** — 🔒 **at the ROOT** | browsers, crawlers, feed readers and link-preview bots request `/favicon.ico` **directly, without parsing HTML**. A `<link>` declaration does not substitute. 🔒 A real multi-image ICO (16/32/48), never a renamed PNG — the clients that ignore the PNG `<link>`s are exactly the ones that read this file |
| `favicon.ico` | `favicon/favicon.ico` | 🎛 optional second copy for tidiness; the root one is the non-negotiable one |
| `favicon-16x16.png` | `favicon/favicon-16x16.png` | classic tab size, still requested by older clients |
| `favicon-32x32.png` | `favicon/favicon-32x32.png` | classic tab size — the one most desktop browsers actually draw |
| `apple-touch-icon.png` | `favicon/apple-touch-icon.png` | 180×180, iOS home screen. Full-bleed and opaque, so it is **left untoned** — a home screen has no browser theme to adapt to |
| `android-chrome-192x192.png` | `favicon/android-chrome-192x192.png` | Android home screen + install prompt. Untoned, same reason |
| `android-chrome-512x512.png` | `favicon/android-chrome-512x512.png` | the manifest's large icon; splash screens read it |
| `android-chrome-maskable-512x512.png` | `favicon/…-maskable-512x512.png` | adaptive icons crop to a platform-chosen shape — needs its own safe-zone padding, so it cannot be the same bytes as the 512 above |
| `site.webmanifest` | `favicon/site.webmanifest` | declares name, theme colour and the icon list to install prompts |
| `og-cover.png` | `images/og/og-cover.png` | 1200×630 link unfurl. ⚠️ Crawlers cache for weeks and may never re-fetch — a replacement is usually shipped under a **new filename** rather than overwritten |

### What must NEVER be promoted

| Never ships | Why |
|---|---|
| anything in [`../source/`](../source/README.md) | full-resolution originals — 🔒 the folder that would embarrass the project if served |
| anything in [`../reference/`](../reference/README.md) | every direction that was tried and rejected, at a public URL |
| a work-in-progress from `../../svg/` | the promote step takes that folder wholesale and trusts it is finished artwork |

### The stamp

🔒 The promote script **records what it did** — `logoId`, `logoVersion`, and a hash of each input and
output — into this folder. That record is what makes the `verify` script possible at all: without it
there is nothing to compare a shipped file against, and drift is undetectable rather than merely
unreported.

<br>

## The identity, and why it is written before the artwork

[`tokens.json`](tokens.json) carries `logoId` + `logoVersion` **now**, while there is one brand and the
value is constant. They are what a drift check compares **first** — the difference between *"this favicon
is stale"* and *"this favicon is from a brand we no longer use."*

Added later, that is a migration across every record and every shipped file. Written on day one, it costs
one line.

<br>

## What is deliberately NOT here

| Not here | Where it lives | Why |
|---|---|---|
| the **site's** design tokens — palette, type, spacing | [`../../../../theme/`](../../../../theme/) | this system starts once *artwork* exists; the theme is a different system sharing the `design/` root |
| the provenance of a **commissioned** asset — model · prompt · date · rights | the `graphic-designing` skill | that record answers *"where did these bytes come from?"*; the promote record here answers *"is this shipped file still what its master implies?"* Neither subsumes the other |
| a second subject (avatars, an email banner) | a **peer** folder beside `logo/` | nesting it here would make this folder mean two things, and nothing later could tell them apart |

<br>

## Note on prose vs code

⚠️ **When this README and a script disagree, the script is what runs.** A subject's own prose drifts from
its code — one reference project describes its checker three different ways across a header, its docs and
its actual emissions. Trust the code, then fix the prose.
