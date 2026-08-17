# svg/ — stage 2 · THE MASTERS

**This is the only folder in the brand system a human edits.** Every other file — the PNGs, the icon
ladder, the promoted copies in `public/`, the in-app component — is *derived* from what lives here by a
repeatable step.

<br>

## What belongs here

- **The bare mark** — the true master, one file.
- **Composed lockups** — the mark set against the wordmark, or arranged for a different shape of space
  (horizontal, stacked, square). 🔒 **Lockups are composed by a script, not hand-drawn.** They are not
  separate logos; one mark composed for several spaces is one brand.

## What must never be here

| Never | Why | Where it goes instead |
|---|---|---|
| a work-in-progress | this folder is what the promote step ships wholesale | `../artifacts/reference/` |
| a rejected variant | same — the promote script takes the whole folder and trusts it is artwork | `../artifacts/reference/` |
| a size-specific export | that is a derivative, and it is regenerated | `../png/` |

<br>

## The rule that makes this folder work

🔒 **Edits happen here and nowhere else.** A change made to a PNG, to a file in `public/`, or to the
in-app component is destroyed by the next regeneration — **silently**, because regeneration succeeds.

That single split — `svg/` and `png/` are deliverables, `artifacts/` is everything else — is what makes
the promote step expressible at all: it can take the whole of `svg/` and know it is shipping artwork
rather than someone's colourway explorer.

<br>

## Status

**Empty.** No master has been authored yet. Before one is, write THE ONE RULE — see
[`../artifacts/meta/README.md`](../artifacts/meta/README.md).
