"""
Smoke Check
-----------
Drives every read-only route through Flask's test client, in-process.

    python infra/smoke.py            (needs Backend's venv on PATH, or call it directly)
    Backend/.venv/Scripts/python infra/smoke.py

This is a DEV TOOL, not a test suite — the project has no test framework and this
does not pretend to be one. It exists because a file-existence check cannot prove
that an import chain resolves or that a blueprint is still registered, which is
exactly what a large refactor breaks. It binds no port and writes nothing, so it
is safe to re-run.

Deliberately excludes POST /api/query and POST /api/upload: both would call an
LLM or mutate the index, and a check with side effects is one people stop running.

Exit 0 = every route answered as expected. Exit 1 = the first failure, named.
"""

import sys

# ── The contract each route is held to ────────────────────────────────────────
# (method, path, expected status, keys the JSON body must carry)
CHECKS = [
    ("GET", "/api/health",          200, ["status"]),
    ("GET", "/api/providers",       200, ["providers", "default"]),
    ("GET", "/api/documents",       200, ["vector_count", "bm25_count", "graph"]),
    ("GET", "/api/knowledge-bases", 200, ["knowledge_bases"]),
]


# ── Output helpers ────────────────────────────────────────────────────────────

def _ok(message: str) -> None:
    print(f"[smoke]   ok   {message}")


def _fail(message: str) -> None:
    print(f"[smoke]  FAIL  {message}", file=sys.stderr)


# ── Runner ────────────────────────────────────────────────────────────────────

def main() -> int:
    print("[smoke] importing adrag.app — this loads the embedding and reranker models…")
    try:
        from adrag.app import create_app
    except Exception as exc:
        _fail(f"cannot import adrag.app: {exc}")
        print("[smoke] install the package first:  cd Backend && pip install -e .", file=sys.stderr)
        return 1

    app = create_app()

    registered = {rule.rule for rule in app.url_map.iter_rules()}
    print(f"[smoke] {len(registered) - 1} routes registered")

    failures = 0
    with app.test_client() as client:
        for method, path, want_status, want_keys in CHECKS:
            if path not in registered:
                _fail(f"{method} {path} — not registered on the app at all")
                failures += 1
                continue

            response = client.open(path, method=method)
            if response.status_code != want_status:
                _fail(f"{method} {path} — status {response.status_code}, wanted {want_status}")
                failures += 1
                continue

            body = response.get_json(silent=True)
            if body is None:
                _fail(f"{method} {path} — body is not JSON")
                failures += 1
                continue

            missing = [key for key in want_keys if key not in body]
            if missing:
                _fail(f"{method} {path} — body is missing {', '.join(missing)}")
                failures += 1
                continue

            _ok(f"{method} {path}")

    if failures:
        print(f"[smoke] {failures} of {len(CHECKS)} checks FAILED", file=sys.stderr)
        return 1

    print(f"[smoke] all {len(CHECKS)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
