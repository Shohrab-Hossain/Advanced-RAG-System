# images/og/ — consumed by OTHER PEOPLE'S SITES

The social share image. When someone pastes a link to this app into Slack, Discord, iMessage, LinkedIn
or X, **their** server fetches this file and renders the unfurl. You are not the consumer here, which
changes how it must be treated.

<br>

## What belongs here

```
images/og/
└── og-cover.png        1200×630 — the canonical Open Graph size
```

- **1200×630** (1.91:1) is what every major platform crops to. Anything else gets cropped by *them*,
  usually through the middle of your wordmark.
- **PNG or JPEG.** Several crawlers do not render SVG.
- **Keep it under ~1 MB.** Some fetchers give up on large files and fall back to no image at all.
- **Legible at thumbnail size.** The unfurl is often 400px wide in a chat sidebar; body text in the image
  disappears entirely.

<br>

## The wiring it needs

The file alone does nothing — [`../../index.html`](../../index.html) must declare it, with an
**absolute** URL. Relative `og:image` paths are not resolved by most crawlers.

```html
<meta property="og:image"   content="https://<host>/images/og/og-cover.png" />
<meta name="twitter:card"   content="summary_large_image" />
<meta name="twitter:image"  content="https://<host>/images/og/og-cover.png" />
```

⚠️ **Today `index.html` has `og:title` and `og:description` but no `og:image`, and `twitter:card` is
`summary` rather than `summary_large_image`** — so a shared link unfurls as a small text-only card. Both
are fixed as part of the first promotion, once this file exists.

<br>

## ⚠️ Crawlers cache aggressively, and may not re-fetch for weeks

This is the one operational difference from the other two shipped folders. Replacing `og-cover.png` does
**not** update existing unfurls: a platform that fetched the old image may keep serving it long after the
file changed, and there is no way to force most of them to re-fetch.

Consequences worth knowing before the first promotion:

- **Getting it right the first time matters more here** than for a favicon, which every browser re-fetches
  on its own schedule.
- **A new image is often better shipped under a new filename** (`og-cover-v2.png`) with the meta tag
  repointed — that sidesteps the cache entirely rather than waiting it out.

<br>

## The rule

> 🔒 **Nothing here is ever hand-edited.** It is a promoted derivative — composed by the `derive` script
> from the master and copied here by `promote`. Edit the master and re-promote.

<br>

## Status

**Empty.** No master exists yet, so there is no cover to compose.
