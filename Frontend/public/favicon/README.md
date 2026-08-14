# favicon/ — consumed by BROWSERS AND PLATFORMS

The icon set. 🔒 **These filenames are not ours to choose** — browsers, operating systems and install
prompts request them by names *they* dictate, which is why this folder can never be merged with
[`../brand-logo/`](../brand-logo/README.md).

<br>

## What belongs here

```
favicon/
├── site.webmanifest        name, theme colour, and the icon list for install prompts
├── favicon.svg             the modern tab icon
├── favicon-16x16.png       ┐ classic tab sizes
├── favicon-32x32.png       ┘
├── apple-touch-icon.png    180×180 — iOS home screen
├── android-chrome-192x192.png
├── android-chrome-512x512.png
└── android-chrome-maskable-512x512.png    safe-zone padded, for adaptive icons
```

<br>

## 🔒 `favicon.ico` goes at the ROOT, not in here

It lives at [`../favicon.ico`](../) — one level up, served at `/favicon.ico`.

**This is a routing requirement, not a file requirement.** Browsers, crawlers, feed readers and
link-preview bots request `/favicon.ico` **directly, without parsing your HTML**. Declaring a modern SVG
icon does not stop this. The failure mode is specific and easy to miss: the file exists, the build hashes
it into an asset directory, the root request 404s — and **nothing in your own site notices**, because your
own site uses the `<link>` you declared.

🔒 It must be a **real multi-image ICO** (16/32/48), never a renamed PNG. The clients that ignore your
PNG `<link>`s are exactly the ones that read this file.

Shipping a copy inside this folder as well is fine; the **root copy is the non-negotiable one**.

<br>

## Toning — only where a surface actually has a theme

If the tab icon should adapt to the browser's colour scheme, split **only the tab files** by tone:

```
favicon/light/{favicon.svg, favicon.ico, favicon-16x16.png, favicon-32x32.png}
favicon/dark/{…the same four…}
```

🔒 **Leave `apple-touch-icon`, both `android-chrome` sizes and the maskable icon flat**, at the top
level. A home screen is full-bleed and opaque and **has no browser theme to adapt to** — an OS does not
tell your icon which scheme the user picked. Toning them doubles the file count and the promote mapping
for zero behaviour.

<br>

## The rule

> 🔒 **Nothing here is ever hand-edited.** Every file is a promoted derivative, built by the `derive`
> script from the master and copied here by `promote`. Edit the master and re-promote.

<br>

## Status

**Empty, and `/favicon.ico` currently 404s.** [`../index.html`](../index.html) declares no icon links at
all — correctly, since there is nothing yet to point them at. Wiring the `<link>` tags and the manifest
reference is part of the first promotion, not of this scaffold.
