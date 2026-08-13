---
id: 1
date: 2026-08-13
time: "10:11"
category: logic
summary: |-
  **The frontend's `retry` SSE handler is unreachable dead code, so the reflection retry counter never moves.** `_applyEvent` in `stores/rag.js` guards every event with `if (!stage || !(stage in stageStatuses)) return`, but the backend's `retry` frame (`reflection.py:129-135`) carries `attempt`/`max_attempts`/`reason`/`escalate_external`/`message` and **no `stage` key** — so the guard returns before `case 'retry'` at `rag.js:122` can run. `retryCount` stays 0 and the retrieval stages never reset to idle, meaning a self-reflection retry is invisible in the UI even though the pipeline genuinely re-ran. **OPEN — not fixed.** Found by documentation ground-truthing, not by a bug report. Takeaway: a payload-shape assumption applied as a blanket guard silently disables every event that legitimately lacks that field.
---

# SSE `retry` event silently dropped by the stage guard in `rag.js`
**Date:** 2026-08-13 · **Category:** logic · **Status:** OPEN — diagnosed, not fixed · **Refs:** `Frontend/src/stores/rag.js:97-133`, `Backend/src/rag_pipeline/generation/reflection.py:129-135`

## Symptom

The reflection retry loop is invisible in the UI. When the `reflect` node decides the answer is
insufficient and loops back for another attempt, the frontend shows nothing: `retryCount` stays at
`0`, and the retrieval stages keep their completed state instead of re-animating for the new pass.
The pipeline really did re-run — the backend emits the frame and the raw event lands in the store's
`events` array — but no piece of reactive state derived from it ever changes.

There is no error, no console warning, and no failed request. The only observable is an absence.

## Root cause

`_applyEvent` extracts `stage` from the payload and returns early on anything that lacks it
(`Frontend/src/stores/rag.js:100-101`):

```js
const stage = data?.stage
if (!stage || !(stage in stageStatuses)) return
```

That guard sits **above** the `switch (type)` block, so it applies to every event type uniformly.
Seven of the eight cases are per-stage events where the guard is correct. `retry` is not: it is a
**pipeline-level** event about the run as a whole, not about any single stage, and
`Backend/src/rag_pipeline/generation/reflection.py:129-135` emits it with exactly five keys —
`attempt`, `max_attempts`, `reason`, `escalate_external`, `message`. No `stage`.

So `case 'retry'` at `rag.js:122-127` is **structurally unreachable**. It is dead code that reads as
live code, which is why it survived review: the handler exists, is correct in isolation, and looks
wired up.

Note the ordering detail that makes this hard to spot from the outside — `events.value.push(...)` at
`rag.js:98` runs *before* the guard. The event is therefore visible in the raw event log while having
no effect on any derived state, so a debugging session that checks "did the event arrive?" answers
yes and moves on.

`Backend/documentation/api.md:49` compounds it by documenting `retry` as carrying a `stage` field.
It does not, and never did.

## Proposed fix (not yet applied)

Handle pipeline-level events before the stage guard rather than after it — e.g. dispatch `retry`
(and any future run-scoped event) in its own branch above line 100, leaving the guard to cover only
the per-stage cases it was written for.

Do **not** fix this by adding a `stage` key to the backend's `retry` payload. That would make the
frame lie about its own scope to satisfy a consumer-side assumption, and the next run-scoped event
would hit the same wall.

`api.md:49` should be corrected in the same change.

## Why that works (and what didn't)

The guard's real job is "don't index `stageStatuses` with a missing or unknown key" — a narrow
concern about three lines inside four of the cases. Applying it to the whole function turned a
lookup precondition into a delivery filter. Restoring it to the cases that actually index
`stageStatuses` fixes the class, not just the instance.

**Ruled out — adding `stage: 'reflection'` to the backend payload.** It would work, and it is the
smaller diff, but `retry` is genuinely not a per-stage event: its handler *resets all seven stages*,
which is precisely why it has no single stage of its own. Tagging it with one to slip past a guard
encodes the bug as a protocol requirement.

## Takeaway

A precondition check hoisted to the top of a dispatcher becomes a filter on everything it dispatches.
When a guard exists to protect one operation, scope it to that operation — otherwise every message
that legitimately lacks the field gets dropped in silence, and the handler for it still reads as
wired up during review.

Corollary for this codebase: `Backend/documentation/api.md`'s SSE table is not a reliable contract.
The ground truth is the `emit()` call sites, which were found to disagree with it in three places
(`retry`'s `stage`, `retrieval_result`'s `web_count`, and a missing `error` row).
