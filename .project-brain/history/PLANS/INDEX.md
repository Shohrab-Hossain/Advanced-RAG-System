<div align="center">

<img src="https://api.iconify.design/ph/list-checks-fill.svg?color=%237c5cff&height=56" alt="Plans log" height="56" />

# Plans Log — adRAG

### Completed task plans — the record of how each piece of this project was actually built.

</div>

<br>

> Newest first. Each row links a **completed** plan stored under
> `entries/<creation-date>/HHMMSS-slug/plan.md`. The **Completed** column is the completion date/time,
> which legitimately differs from the creation date in the path. **Active** plans live in
> `.claude/workbench/contracts/`, not here — a plan only lands in this log once it is done. See the
> [`csh-task-planning`](../../../.claude/skills/csh-task-planning/SKILL.md) skill for the entry format and
> the archive procedure.

<br>

| &nbsp;&nbsp;&nbsp;Completed&nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Plan&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Category | Outcome |
|---|---|---|---|
| `2026-08-13 18:09` | [Reorganise Frontend/src/ onto the vue-file-tree preference](entries/2026-08-13/152630-frontend-src-reorganisation/plan.md) | `single-agent` | `Frontend/src/` moved off the stock Vue CLI similarity buckets (`components/` · `views/` · `stores/` · `services/`) onto the ownership rule — `store/` for app-shell state, `shared/components/` for the three genuinely cross-page components, `subsystems/{rag,knowledge-base}/` each holding its own api + store, and `pages/{home,chat,knowledge-base,configuration}/` each owning the components only it uses. `stores/rag.js` and `services/api.js` split along the same seam into `ragStore`/`ragApi` and `kbStore`/`kbApi`; three orphan components imported by nothing were dropped. `KnowledgeBaseView` 371→70 and `ChatView` 270→130, extracted into page-owned components with pure logic in camelCase siblings. `Frontend/documentation/` → `Documentation/`, and `.claude/CLAUDE.md`'s Layout + Conventions were rewritten so a fresh agent is not instructed to rebuild the buckets this plan removed. Behaviour-preserving: build exit 0, all four routes verified by the owner at 1.5 and 2.3. Merged fast-forward to `feature` as `1f177af`. `LLMSelector.vue` deliberately left at 204 lines — its script is entirely computeds and lifecycle, so it carries none of the logic G3 condemns. |
