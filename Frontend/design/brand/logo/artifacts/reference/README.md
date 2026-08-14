# reference/ — labs, candidates, explorations

The workshop floor. Colourway explorers, candidate marks, direction studies, an HTML page that renders
twelve variants side by side so a human can pick one.

<br>

## The defining property

> 🔒 **This folder must be deletable without consequence.**

Nothing anywhere may depend on a file in here. Not a script, not a doc link, not a master that imports a
path from it. If deleting `reference/` would break something, that something is in the wrong folder —
move it to [`../meta/`](../meta/README.md) (if a script reads it) or [`../../svg/`](../../svg/README.md)
(if it is artwork that shipped).

That property is what lets this folder be genuinely messy, which is what makes it useful. A folder you
have to keep tidy is a folder you stop putting exploration into.

<br>

## What belongs here

- Rejected directions — **kept**, not deleted. Knowing what was tried is worth more than a clean folder,
  and re-exploring a direction someone already rejected is the cost of throwing them away.
- Candidate sets from a design run.
- A local lab page + its screenshots (the `lab` script role serves or shoots one).

## What must never be here

🔒 **Nothing in this folder ever ships.** Alongside `source/`, it is one of the two folders that would
embarrass the project if served — every direction that was tried and rejected, at a public URL.

The build only copies `public/`, so this is safe by default. Do not undermine it by symlinking or by
promoting a file straight out of here: a shipped asset comes from a **master**, via the promote script,
with a record.

<br>

## Status

**Empty** — no exploration has happened yet.
