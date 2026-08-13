# 🔐 Security

adRAG is built as a **single-user, localhost-bound tool**, and its security posture follows from that: no
authentication, no authorisation, and a single shared corpus. That is a deliberate scope choice, not an
oversight — but it means the threat model changes completely the moment the server is exposed beyond
`localhost`.

<br>

---

<br>

## Index

| Topic | Holds |
|---|---|
| [`trust-boundaries/`](trust-boundaries/README.md) | Where untrusted input enters, what is validated where, the invariants that must not break, and the risks that are currently accepted |

<br>

---

<br>

## The four invariants

1. **`OPENAI_API_KEY` never leaves the server.** It is read only in `Backend/src/config.py` and surfaces to
   clients solely as the boolean `available` on `/api/providers`.
2. **Uploads are extension-allowlisted and name-sanitised.** `Config.ALLOWED_EXTENSIONS` plus
   `werkzeug.utils.secure_filename`, before anything touches the filesystem. (The allowlist is **35**
   extensions wide — `config.py:62-65` — not the four loader types.)
3. **The frontend never calls an LLM or a search engine directly.** Every outbound model/search call is made
   server-side inside a pipeline node.
4. **CORS is scoped to `r"/api/*"` and should be an explicit origin list — and today it is not.** The
   scoping half holds (`app.py:43`). The origin half does not: `app.py:44` ends its six-entry list with a
   literal `"*"`, so every origin is permitted. CORS is working; it is simply configured wide open.

Invariants 1–3 hold. **Invariant 4 is breached in the code right now** — and because there is also no
authentication on any route (`app.py:36-311`), localhost binding is the only thing containing it. It costs
nothing today and everything on the first deployment that makes the port reachable. The full framing, the
multipliers, and how to close it are in
[`trust-boundaries/README.md`](trust-boundaries/README.md).
