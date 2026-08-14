"""
Dev Launcher
------------
Starts the Flask backend and the Vue dev server together on ports picked at
launch, and wires the frontend to whichever port the backend actually got.

Run from the repo root:
    python infra/dev.py                  proxy mode  — frontend calls /api/* through the dev proxy
    python infra/dev.py --direct         direct mode — frontend calls the backend cross-origin
    python infra/dev.py --no-reload      skip the Flask reloader (models load once, boots ~2x faster)
    python infra/dev.py --api-port 5000  pin a port instead of probing for one

Ctrl-C stops both.
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
# This file lives in infra/, so the repo root is one level up from its parent.
ROOT         = Path(__file__).resolve().parent.parent
BACKEND_DIR  = ROOT / "Backend"
# The backend runs with CWD=Backend and is launched as a module, because adrag is
# an installed package rather than a folder of scripts. The working directory no
# longer decides where data lands — config.py resolves DATA_ROOT from the package.
BACKEND_ENTRY = BACKEND_DIR / "src" / "adrag" / "main.py"
FRONTEND_DIR = ROOT / "Frontend"

# ── Port allocation ───────────────────────────────────────────────────────────
# Prefer a stable base and walk up, so a normal run keeps landing on the same
# port (curl / Postman / bookmarks keep working) and only floats on collision.
API_PORT_BASE  = 5000
UI_PORT_BASE   = 8080
PORT_SCAN_SPAN = 40

# ── Readiness ─────────────────────────────────────────────────────────────────
# Boot is slow: sentence-transformers and chroma load their models on import.
HEALTH_TIMEOUT  = 240
HEALTH_INTERVAL = 1.0

IS_WINDOWS = os.name == "nt"

_ANSI = {"api": "\033[36m", "ui": "\033[35m", "dev": "\033[32m", "warn": "\033[33m", "off": "\033[0m"}
_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None

# Vue CLI emits box-drawing and ✔/✖ glyphs; a cp1252 console would mangle them.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ── Output helpers ────────────────────────────────────────────────────────────

def _paint(text: str, key: str) -> str:
    return f"{_ANSI[key]}{text}{_ANSI['off']}" if _COLOR else text


def _say(message: str, key: str = "dev") -> None:
    sys.stdout.write(f"{_paint('[dev]', key)} {message}\n")
    sys.stdout.flush()


# ── Environment discovery ─────────────────────────────────────────────────────

def _find_free_port(base: int, span: int = PORT_SCAN_SPAN) -> int:
    """First port from `base` upward that nothing currently holds."""
    for port in range(base, base + span):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            # No SO_REUSEADDR on purpose — a port in TIME_WAIT is not free enough.
            try:
                probe.bind(("", port))
            except OSError:
                continue
            return port
    raise SystemExit(f"[dev] no free port in {base}-{base + span - 1}")


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("", port))
        except OSError:
            return False
        return True


def _resolve_python() -> str:
    """Backend interpreter — prefer the project venv over whatever ran this file.

    A venv is platform-specific: Windows builds `Scripts/python.exe`, POSIX builds
    `bin/python`. Running under WSL against a venv created on Windows finds neither,
    which is why the failure is reported in those terms rather than as "no venv".
    """
    leaf = ("Scripts", "python.exe") if IS_WINDOWS else ("bin", "python")
    for venv in (".venv", "venv", "env"):
        candidate = BACKEND_DIR / venv / leaf[0] / leaf[1]
        if candidate.exists():
            return str(candidate)

    other = "Scripts/python.exe" if not IS_WINDOWS else "bin/python"
    if any((BACKEND_DIR / v / other.split("/")[0]).exists() for v in (".venv", "venv", "env")):
        raise SystemExit(
            f"[dev] Backend/.venv exists but was built for the other platform "
            f"(found {other}, need {leaf[0]}/{leaf[1]}).\n"
            f"[dev] You are running on {'Windows' if IS_WINDOWS else 'POSIX/WSL'}. "
            f"Build a venv for this platform in a separate directory."
        )

    _say(f"no venv under Backend/ — falling back to {sys.executable}", "warn")
    return sys.executable


def _check_backend_deps(python: str) -> None:
    """Fail fast with the fix, rather than a traceback buried in the child's log."""
    # `import adrag` is the stronger probe: the package is only importable once
    # `pip install -e .` has run, which is also what installs Flask.
    probe = subprocess.run(
        [python, "-c", "import adrag, flask"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if probe.returncode != 0:
        # Assembled outside the f-string: a backslash in an f-string expression
        # is a SyntaxError before Python 3.12.
        activate = ".venv\\Scripts\\activate" if IS_WINDOWS else "source .venv/bin/activate"
        raise SystemExit(
            f"[dev] {python}\n"
            f"[dev] cannot import adrag — the backend would die on import. Install first:\n"
            f"[dev]   cd Backend && python -m venv .venv && {activate} "
            f"&& pip install -e ."
        )


def _resolve_npm() -> str:
    from shutil import which
    npm = which("npm")
    if npm is None:
        raise SystemExit("[dev] npm not found on PATH")
    return npm


# ── Process management ────────────────────────────────────────────────────────

def _spawn(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    kwargs: dict = {
        "cwd": str(cwd),
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if IS_WINDOWS:
        # Own the shutdown ourselves rather than letting the console Ctrl-C
        # race us to the children.
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def _pump(proc: subprocess.Popen, label: str) -> None:
    """Stream a child's merged output with a coloured prefix."""
    prefix = _paint(f"[{label}]", label)
    try:
        for line in proc.stdout:
            sys.stdout.write(f"{prefix} {line.rstrip()}\n")
            sys.stdout.flush()
    except (ValueError, OSError):
        pass   # pipe closed during teardown


def _terminate(proc: subprocess.Popen, label: str) -> None:
    """Kill the whole tree.

    Flask's reloader forks a child that holds the port — killing only the PID we
    spawned would leave the real server running and the port occupied.
    """
    if proc.poll() is not None:
        return
    _say(f"stopping {label}…")
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)


# ── Readiness probe ───────────────────────────────────────────────────────────

def _await_health(port: int, stop: threading.Event) -> None:
    url = f"http://127.0.0.1:{port}/api/health"
    started = time.monotonic()
    deadline = started + HEALTH_TIMEOUT
    while not stop.is_set() and time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as res:
                if res.status == 200:
                    _say(f"backend healthy after {time.monotonic() - started:.0f}s")
                    return
        except Exception:
            pass
        stop.wait(HEALTH_INTERVAL)
    if not stop.is_set():
        _say(f"backend did not answer /api/health within {HEALTH_TIMEOUT}s", "warn")


# ── Launcher ──────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="infra/dev.py", description="Run the RAG backend and frontend together.")
    parser.add_argument("--direct", action="store_true",
                        help="frontend calls the backend cross-origin instead of via the dev proxy")
    parser.add_argument("--no-reload", action="store_true",
                        help="disable the Flask reloader — models load once instead of twice")
    parser.add_argument("--api-port", type=int, default=None, help="pin the backend port")
    parser.add_argument("--ui-port", type=int, default=None, help="pin the frontend port")
    return parser.parse_args()


def _pick(requested: int | None, base: int, label: str) -> int:
    if requested is None:
        return _find_free_port(base)
    if not _port_is_free(requested):
        _say(f"{label} port {requested} looks busy — starting anyway", "warn")
    return requested


def main() -> int:
    args = _parse_args()

    for path in (BACKEND_ENTRY, FRONTEND_DIR / "package.json"):
        if not path.exists():
            raise SystemExit(f"[dev] expected {path} — run infra/dev.py from the repo root")

    python = _resolve_python()
    _check_backend_deps(python)
    npm = _resolve_npm()

    api_port = _pick(args.api_port, API_PORT_BASE, "backend")
    ui_port = _pick(args.ui_port, UI_PORT_BASE, "frontend")
    api_url = f"http://localhost:{api_port}"
    ui_url = f"http://localhost:{ui_port}"

    # ── Backend env ───────────────────────────────────────────────────────────
    # config.py calls load_dotenv() with override=False, so what we set here
    # wins over Backend/.env — no file needs editing.
    api_env = {
        **os.environ,
        "PORT": str(api_port),
        "FRONTEND_URL": ui_url,
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    if args.no_reload:
        api_env["FLASK_DEBUG"] = "false"

    # ── Frontend env ──────────────────────────────────────────────────────────
    # DEV_API_TARGET points the dev-server proxy at the port we just chose.
    # VUE_APP_API_URL is only set in --direct mode: api.js falls back to '' when
    # it is absent, which keeps every call relative and therefore proxied.
    ui_env = {**os.environ, "DEV_API_TARGET": api_url}
    if args.direct:
        ui_env["VUE_APP_API_URL"] = api_url

    mode = "direct (cross-origin)" if args.direct else "proxied"
    _say(f"backend  {api_url}   (python -m adrag.main)")
    _say(f"frontend {ui_url}   ({mode})")
    _say("starting — first boot loads the embedding and reranker models…")

    procs: list[tuple[str, subprocess.Popen]] = []
    stop = threading.Event()

    try:
        api = _spawn([python, "-m", "adrag.main"], BACKEND_DIR, api_env)
        procs.append(("api", api))

        ui = _spawn([npm, "run", "serve", "--", "--port", str(ui_port)], FRONTEND_DIR, ui_env)
        procs.append(("ui", ui))

        for label, proc in procs:
            threading.Thread(target=_pump, args=(proc, label), daemon=True).start()
        threading.Thread(target=_await_health, args=(api_port, stop), daemon=True).start()

        while True:
            for label, proc in procs:
                if proc.poll() is not None:
                    _say(f"{label} exited with code {proc.returncode} — shutting down", "warn")
                    return proc.returncode or 1
            time.sleep(0.3)

    except KeyboardInterrupt:
        _say("interrupted")
        return 0
    finally:
        stop.set()
        for label, proc in procs:
            _terminate(proc, label)


if __name__ == "__main__":
    sys.exit(main())
