# AGENTS.md — operating the adRAG project brain

This folder is the project's long-term memory. You are reading the agent-facing half of its cookbook:
how to read it, how to navigate it, and what you are allowed to write where. The human-facing
introduction is [`README.md`](README.md).

<br>

---

<br>

## Read order

1. **[`project-context/README.md`](project-context/README.md)** then
   **[`project-context/AGENTS.md`](project-context/AGENTS.md)** — what adRAG is, and how the
   regeneratable knowledge is organised.
2. **[`project-context/overview/`](project-context/overview/README.md)** — mission, non-goals,
   glossary, stack and the reason for each piece. Read this before you touch anything; the rest of the
   brain assumes its vocabulary.
3. **[`project-context/architecture/`](project-context/architecture/README.md)** and
   **[`project-context/runtime/`](project-context/runtime/README.md)** — the static structure, then the
   dynamic flows (backend startup, query pipeline, SSE bus, ingestion).
4. **The area you actually need** — `features/`, `api/`, `data/`, `design/`, `conventions/`,
   `operations/`, `security/`.
5. **[`decisions/ADRs/INDEX.md`](decisions/ADRs/INDEX.md)**,
   **[`history/ISSUES/INDEX.md`](history/ISSUES/INDEX.md)**, and
   **[`history/PLANS/INDEX.md`](history/PLANS/INDEX.md)** — reference only. Consult them for *why* a path
   was chosen and *what has already been solved*; do not re-derive either from the code.

To actually reconstruct the project, go to
**[`project-context/build-from-scratch.md`](project-context/build-from-scratch.md)** — the single
source of the ordered rebuild steps. Nothing else in this brain carries those steps.

<br>

---

<br>

## What you may write where

| Location | Contract |
|---|---|
| `project-context/**` | **Regeneratable.** Edit and refresh freely so it matches the code. A "rebuild the brain from scratch" touches only this bucket. |
| `decisions/**` | **Append only.** Add a new `ADRs/entries/NNN-<slug>.md` and its `ADRs/INDEX.md` row in the same edit. Edit an existing ADR only to mark it superseded. |
| `history/**` | **Append only**, owned by the `issues-logging` and `task-planning` skills. Never retro-edit an entry — the entries are dated snapshots, so links inside them going stale after a move is expected, not a bug. |
| `.claude/CLAUDE.md` | Operating rules — run/build/test commands, overrides, never-do rules. They live there, **not** here; this brain may reference `CLAUDE.md` but never restates it. |

<br>

---

<br>

## Rules that keep this brain trustworthy

- **The code is the source of truth.** When a doc and the code disagree, the code wins — then fix the
  doc in the same pass. Stale context is worse than missing context, because it is trusted.
- **Every concrete claim traces to a file you read.** Real paths, real env-var names, real hex tokens,
  real endpoint shapes. If you cannot verify it, leave an explicit `TODO:` rather than guessing.
- **Edit in place; never append an update log.** These docs read as current truth; git is the changelog.
- **Keep the indexes synced.** Adding, renaming, or moving a doc updates the owning area's `README.md`
  and, when the tree changes, `project-context/README.md` in the same edit. An unlinked doc is invisible
  to anyone reading top-down.
- **Keep this cookbook honest.** If a bucket or area is added, renamed, or removed, refresh the affected
  `README.md` + `AGENTS.md` so the self-description stays true.
- **Never link out to `Backend/documentation/` or `Frontend/documentation/`.** Those are the separate,
  publishable engineering-report layer. Read them freely as input, but write the brain's version from
  the source code — this folder is loaded into context every session and must stay self-contained.
