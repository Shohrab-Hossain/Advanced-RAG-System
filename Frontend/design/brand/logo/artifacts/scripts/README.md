# scripts/ — the generators

The scripts that move a file from one stage of the chain to the next. **The filenames are yours; the
roles are not** — a missing role means some part of the chain can only be done by hand, and by-hand is
where drift comes from.

<br>

## The roles

| Role | Does | Reads | Writes |
|---|---|---|---|
| **ingest** | turns an original into a workable vector | `../source/` | `../../svg/` |
| **generate** | emits the master + lockups from `tokens.json` | `../meta/tokens.json` | `../../svg/` |
| **export** | renders each master to raster at the fixed size | `../../svg/` | `../../png/` |
| **derive** | builds a downstream set — the icon ladder, the avatar badges | `../../svg/` | staged for promote |
| **promote** | copies the right derivatives into the shipped tree **and stamps the record** | the derived set | `../../../../../public/` |
| **verify** | re-derives and reports drift — 🔒 **read-only** | everything | stdout only |
| **sync** | regenerates the in-app component from the master | `../../svg/` | `../../../../src/` |

<br>

## The rules

- 🔒 **No script here is wired into the application build.** Not a `prebuild`, not a `postinstall`, not a
  `npm run serve` side effect. They are run deliberately, by a person, because regenerating a brand is a
  **decision**.
- 🔒 **Promotion is manual.** The moment promotion runs automatically, the shipped set stops being a set
  of decisions and becomes a mirror of whatever was last generated — and a wrong logo ships without
  anyone learning it changed.
- 🔒 **The verify script never repairs.** A checker that silently self-heals destroys the signal it exists
  to provide: its whole value is telling you a shipped file and its master diverged, which is information
  about a **process** that failed. Auto-fixing discards that and leaves the broken process in place.
  A green check that was green because something quietly rewrote a file is worse than a red one.
- 🔒 **Generation is idempotent.** Two runs, identical bytes.

<br>

## The promote script's mapping

🔒 **Every row carries a reason.** The mapping is not a copy list — it is the record the drift check
later reads to answer *"is this shipped file still what its master implies?"*. The mapping itself lives
in [`../meta/README.md`](../meta/README.md) alongside the identity it stamps.

<br>

## Status

**Empty** — no scripts written yet. They arrive in this order: `generate` and `export` first (once a
master exists), then `promote` with its mapping, then `verify`, which cannot be written before `promote`
because there is nothing to compare against.
