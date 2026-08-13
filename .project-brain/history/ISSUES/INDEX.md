<div align="center">

<img src="https://api.iconify.design/ph/bug-beetle-fill.svg?color=%237c5cff&height=56" alt="Issues log" height="56" />

# Issues Log (ClaudeSH)

### Notable problems this kit hit and how they were solved — the postmortems behind the changelog.

</div>

<br>

> Newest first. Each entry is a small postmortem (symptom → root cause → fix → why → takeaway), stored
> under `entries/YYYY-MM-DD/`. The `#` column is a monotonic serial (1 = oldest); a new entry takes
> `max(#) + 1`. **This index is GENERATED** from each entry's frontmatter by
> `scripts/issues-index.py --render` -- never hand-written, so a row cannot disagree with its entry. See the
> [`csh-issues-logging`](../../../.claude/skills/csh-issues-logging/SKILL.md) skill for the format.

<br>

| #&nbsp; | Date | Time | Issue | Category |
|---|---|---|---|---|
| `1` | `2026-08-13` | `10:11` | [**The frontend's `retry` SSE handler is unreachable dead code, so the reflection retry counter never moves.** `_applyEvent` in `stores/rag.js` guards every event with `if (!stage || !(stage in stageStatuses)) return`, but the backend's `retry` frame (`reflection.py:129-135`) carries `attempt`/`max_attempts`/`reason`/`escalate_external`/`message` and **no `stage` key** — so the guard returns before `case 'retry'` at `rag.js:122` can run. `retryCount` stays 0 and the retrieval stages never reset to idle, meaning a self-reflection retry is invisible in the UI even though the pipeline genuinely re-ran. **OPEN — not fixed.** Found by documentation ground-truthing, not by a bug report. Takeaway: a payload-shape assumption applied as a blanket guard silently disables every event that legitimately lacks that field.](entries/2026-08-13/101128-sse-retry-event-dropped-by-stage-guard.md) | `logic` |
