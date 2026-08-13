# 🔌 API

The wire contracts between the Vue SPA and the Flask server. Everything is JSON over HTTP under `/api/*`,
except the query route, which is a Server-Sent Events stream.

<br>

---

<br>

## Index

| Surface | Holds |
|---|---|
| [`http/`](http/README.md) | All eight routes — method, path, request body, response shape, status codes |
| [`sse-events/`](sse-events/README.md) | Every event type streamed by `POST /api/query`, with its payload fields |

<br>

---

<br>

## Facts that apply to every route

- **Base:** `http://localhost:5001` by default (`PORT`, default `5001` at `config.py:68`; `.env.example:48`
  sets `5000`). Under `python dev.py` the port floats — the launcher probes upward from 5000 and prints the
  URL it chose (`dev.py:221-222`, `dev.py:248-249`). The frontend uses `VUE_APP_API_URL`, or relative paths
  through the Vue dev-server proxy when it is empty.
- **No authentication.** No token, cookie, or API key is required or accepted by any route — no decorator,
  no `before_request`, no check anywhere in `app.py:36-311`. `DELETE /api/clear` included.
- **No versioning.** Paths are unversioned, and nothing in the API reports a version:
  `GET /api/health` returns **exactly** `{"status": "healthy"}` (`app.py:309`) — one key, no `version`
  field.
- **CORS** is configured for `r"/api/*"` only (`app.py:43`), methods `GET, POST, DELETE, OPTIONS`, allowed
  header `Content-Type` (`app.py:45-46`). The origin list has **six** entries (`app.py:44`):

  ```python
  "origins": [Config.FRONTEND_URL, "http://localhost:3000", "http://localhost:5000",
              "http://localhost:8080", "http://localhost:8081", "*"]
  ```

  The trailing `"*"` makes the named entries decorative — every origin is permitted. Combined with the
  no-authentication line above, that is an over-permission trap rather than a broken control; see
  [`../security/trust-boundaries/README.md`](../security/trust-boundaries/README.md).
- **Errors** are `{"error": "<message>"}` with an appropriate status. Unhandled exceptions inside a route
  return `500` with `str(exc)` — the raw exception text reaches the client.
- **Request size** is capped at 50 MB (`Config.MAX_CONTENT_LENGTH`).
