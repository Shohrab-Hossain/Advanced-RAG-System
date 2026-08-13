# 📐 Conventions

How code in adRAG is written and where it goes. These are the patterns the existing code holds
consistently — new code should match them so the codebase stays predictable.

Every rule here is **observed from the source**, not imported from a style guide: the repository has no
linter configuration beyond the `vue-cli-service lint` script, no formatter config, no `.editorconfig`,
and no type checker.

<br>

---

<br>

## Index

| Topic | Holds |
|---|---|
| [`code-style/`](code-style/README.md) | Python and Vue/JS style — naming, docstrings, error handling, section comments, import order |
| [`project-layout/`](project-layout/README.md) | Where a new file goes on each side, and the layering rules that must not be broken |

<br>

---

<br>

## The four that matter most

1. **Every module opens with a docstring or block comment** stating what it is and how it fits — including
   the `Emits:` line on every pipeline node.
2. **Pipeline nodes never raise.** Catch, `emit` a `stage_error`, return a usable fallback.
3. **Section comments** — `# ── Name ─────` in Python, `// ── Name ────` in JS — divide every file longer
   than a screen.
4. **Real values over abstractions.** Configuration is env-driven with an explicit default at every read
   site.
