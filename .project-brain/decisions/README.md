# ◆ decisions — the durable ADR bucket

Architecture Decision Records: one file per load-bearing choice, capturing the **why** that the code
itself can never show — the constraint that forced the decision, the options that were on the table, and
what the choice made easy or hard afterwards.

<br>

---

<br>

## The never-rewrite rule

This bucket is **durable and append-only**. It sits outside `project-context/` precisely so that a
"regenerate the brain from scratch" — which re-derives everything from the code *as it stands now* — is
physically unable to discard it. A from-scratch run would reconstruct *what* the system does and silently
lose *why*, including every alternative that was tried and rejected and no longer appears in the code.

So:

- **Add** a record; never regenerate the folder.
- **Never delete** a record. A decision that no longer holds is **superseded** by a new ADR that links back
  to it, and the old record's `Status` line is updated to say so — that is the only permitted edit to an
  existing entry.
- **Update `ADRs/INDEX.md` in the same edit** that adds a record. An unindexed ADR is invisible.

<br>

---

<br>

## Layout

```
decisions/
├── 📄 README.md              You are here — the bucket charter
└── 📁 ADRs/
    ├── 📄 INDEX.md            All decisions + one-line summaries (stays at this level)
    └── 📁 entries/            Flat, numbered records — never topic-nested
        ├── 📄 001-<slug>.md
        └── 📄 …
```

Records are **flat and numerically ordered** inside `entries/`. The number *is* the order; topic-grouping
would fight it, since one decision often touches several areas and renumbering on a move would break
inbound references. `entries/` is a single holding folder, not a grouping scheme — it exists so `INDEX.md`
stays visible as the list grows.

<br>

---

<br>

## Record shape

```markdown
# ADR-00N: <Title>
Date: YYYY-MM-DD · Status: accepted | superseded by ADR-0NN

## Context
What forced a decision — the constraint, requirement, or problem. The options on the table.

## Decision
The choice, stated plainly.

## Alternatives considered
- <option> — rejected: <why>

## Consequences
What this makes easy, what it makes hard, what to watch out for later.
```

Start at [`ADRs/INDEX.md`](ADRs/INDEX.md).
