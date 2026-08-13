---
id: 3
date: 2026-08-13
time: "18:19"
category: dependency
summary: |-
  **`.md` uploads are advertised, accepted, then fail at ingest — the `markdown` package is missing from `requirements.txt`.** `md` is in `Config.ALLOWED_EXTENSIONS` (`config.py:63`) and the UI lists Markdown in its drop-zone copy and `accept` attribute, so the route's `_allowed()` check passes and the file is saved; the loader then raises `No module named 'markdown'` and `POST /api/upload` returns `{"error": "No module named 'markdown'"}`. The dependency is a transitive requirement of `unstructured`'s Markdown partitioner and is not declared anywhere — `Backend/requirements.txt` lists `unstructured>=0.14.0` but none of its per-format extras. The failure is a **runtime** one on a format the system claims to support, and it surfaces as an import error rather than an unsupported-type message, so it reads as a crash rather than a setup gap. **OPEN — not fixed** (found while seeding the knowledge base to verify a frontend refactor; `Backend/` was out of that plan's scope). Takeaway: an extension allow-list is a promise about capability, and it is validated independently of the loaders that must honour it — nothing ties the two together, so a format can be advertised in three places while being installable in none.
---

# `.md` upload passes the extension gate, then dies on a missing dependency

**Date:** 2026-08-13 18:19 · **Category:** dependency · **Status:** OPEN — diagnosed, not fixed
**Refs:** `Backend/src/config.py:62-65`, `Backend/src/app.py:56-59,167-173`, `Backend/src/rag_pipeline/ingestion/loader.py`, `Backend/requirements.txt`

## Symptom

Uploading a Markdown file returns a `200` carrying an error payload:

```bash
curl -X POST -F "file=@notes.md" localhost:5000/api/upload
{"error":"No module named 'markdown'"}
```

The identical file renamed to `.txt` ingests fine:

```bash
curl -X POST -F "file=@notes.txt" localhost:5000/api/upload
{"chunks_indexed":2,"file_name":"notes.txt","success":true, ...}
```

So the content is not the problem and the pipeline is not the problem — only the extension is.

The user-facing surface makes this worse than a plain unsupported-format error: the knowledge-base
page lists *"PDF · DOCX · TXT · **MD** · JSON · CSV · HTML · Code files"* twice in its drop-zone copy,
and `.md` is in the file picker's `accept` attribute, so the UI actively invites the file it cannot
process. Per ADR-003 a pipeline failure is an in-band `error` event on a `200`, so nothing in the HTTP
status hints at a server-side misconfiguration either.

## Root cause

Three independent places agree that `.md` is supported, and none of them is the thing that has to
work:

1. `Config.ALLOWED_EXTENSIONS` (`config.py:63`) contains `"md"`.
2. `_allowed()` (`app.py:56-59`) checks the filename against that set and lets it through.
3. The frontend's `ACCEPT_ATTR` (`pages/knowledge-base/views/knowledgeBaseView.js`) mirrors the set.

The actual loader is chosen afterwards by `_get_loader()`, which routes `.md` to `unstructured`'s
Markdown partitioner. That partitioner imports `markdown` at call time. `Backend/requirements.txt`
declares `unstructured>=0.14.0` but no per-format extra — `unstructured` ships its format handlers as
optional dependencies (`unstructured[md]`, `[pdf]`, `[docx]`…), so a plain install gets the dispatcher
without the backends.

The two checks that exist are both about the *name* of the file. Nothing anywhere asserts that the
loader for a given extension can actually be imported, and the allow-list is maintained by hand in a
file that has no reason to know what is installed. CLAUDE.md's guardrail — *"Keep both extension
checks… Content is never sniffed — the extension is trusted to describe the bytes"* — is about
trusting the extension to describe the *content*; it does not cover trusting it to describe the
*runtime*.

This has almost certainly been broken since `md` was added to the set. It went unnoticed because the
obvious test file for a docs-heavy project is a PDF or a `.txt`, and because the error text names a
Python module rather than the feature.

## Proposed fix (not yet applied)

Declare the dependency:

```
# Backend/requirements.txt
markdown>=3.6
```

or, preferring the upstream idiom that pulls the whole handler set for the formats claimed:

```
unstructured[md]>=0.14.0
```

Then audit the rest of `ALLOWED_EXTENSIONS` the same way — the set names 35 extensions and this is the
first one anybody tried. `docx` (`docx2txt`) and `pdf` (`pypdf`) are declared; `html`/`htm`, `json`
and `csv` route through `unstructured` on the same optional-extra mechanism and should be checked
before being trusted.

**Do not** fix it by removing `md` from `ALLOWED_EXTENSIONS`. Markdown is a format this project has
every reason to ingest, and the UI advertises it in three places; dropping it turns a one-line
dependency gap into a capability regression.

## Why that works (and what didn't)

The allow-list is a *statement of intent* and the installed packages are the *capability*. They drifted
because nothing forces them to agree. Declaring the dependency makes the capability match the intent
that was already written down, which is the direction that keeps the promise.

**Ruled out — catching `ImportError` in `_get_loader()` and returning "unsupported format".** It turns
a loud, accurate error into a quiet, misleading one: the format *is* supported, the deployment is
incomplete, and an operator reading "unsupported file type" has no path to the fix.

**Ruled out — sniffing content and falling back to the plain-text loader for `.md`.** It would make
this file work, and it would silently degrade every other partitioner the same way. It also runs
straight into the documented guardrail that content is never sniffed.

## Takeaway

An allow-list validates the *request*, never the *system's ability to serve it*. Here three artifacts
— a config set, a route guard, and a frontend `accept` attribute — all agreed a format was supported,
and all three were downstream of the same hand-maintained list; none was evidence about the installed
runtime. When a capability is declared in configuration, something must tie that declaration to the
code path that fulfils it, or the declaration is just a comment that happens to be executable.

Practical corollary for this codebase: `ALLOWED_EXTENSIONS` has 35 entries and exactly two of them
(`pdf`, `docx`) have a matching explicit line in `requirements.txt`. Treat the rest as unverified
until one is tried.
