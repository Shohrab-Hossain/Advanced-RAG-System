# png/ — stage 3 · raster renders

Raster exports of every file in [`../svg/`](../svg/README.md), produced by the **export** script. This
folder is an **output**: it is deleted and regenerated without ceremony, and nothing depends on a file
here being older than its master.

<br>

## What belongs here

- One render per `svg/` file, at a **single fixed large size** (2048px on the long edge is the default),
  **respecting the master's aspect ratio** — never squashed to a square.

## What must never be here

🔒 **You never hand-edit a PNG.** Not to fix a stray pixel, not to nudge the padding, not to recolour one
for a slide deck. The next export overwrites it and the fix vanishes with no error — and in the meantime the
file disagrees with its own master while looking perfectly fine.

If a render is wrong, the master is wrong or the export script is wrong. Fix the cause and re-run.

Also never here: size-specific icon files. The favicon ladder (16, 32, 180, 192, 512, maskable) is a
**derived set** built by the `derive` script and promoted straight to `public/favicon/` — it is not a
selection from this folder.

<br>

## Why this stage exists at all

`svg/`, `png/` and the in-app component all exist because they serve consumers that cannot read each
other's format. A browser tab needs an `.ico` at a URL; a web manifest needs a 512px PNG; a navbar needs
something that inherits `currentColor` and animates. One file cannot be all three, so the master is
**projected** into each — which is why derivation is the model rather than copying.

<br>

## Regenerating

Run the **export** script in [`../artifacts/scripts/`](../artifacts/scripts/README.md).

🔒 **Generation is idempotent** — run it twice, get identical bytes. If an exporter ever embeds a
timestamp or a random id, every run produces a diff, the diff stops being read, and a real change hides
in the noise.

<br>

## Status

**Empty** — there is no master to export yet.
