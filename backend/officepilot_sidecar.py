"""Phase 8 — PyInstaller entry point for the OfficePilot AI sidecar.

This module is the *only* thing PyInstaller bundles into the
``officepilot-agent.exe`` sidecar. Its job is to:

1. Set up the runtime environment expected by the FastAPI app
   (CWD, env vars, frozen-aware data dir resolution).
2. Launch uvicorn against the bundled :mod:`app.main:app` object.

The Tauri supervisor (``desktop/tauri/src-tauri/src/agent.rs``)
calls this binary with two environment variables it cares about:

* ``OFFICEPILOT_SIDECAR=1``         — set by the Tauri supervisor so
                                      the agent can label itself as
                                      a bundled sidecar in /api/health.
* ``OFFICEPILOT_AGENT_HOST``       — bind host (default ``127.0.0.1``).
* ``OFFICEPILOT_AGENT_PORT``       — bind port (default ``8000``).
* ``OFFICEPILOT_DATA_DIR``         — where logs/cache/etc. live.
* ``OFFICEPILOT_STORAGE_ROOT``     — where invoice originals go.
* ``OFFICEPILOT_DB_URL``           — SQLAlchemy URL.

PyInstaller-specific notes:
* ``sys.frozen`` is ``True`` when running from a bundle, so the
  app can find its data files relative to ``sys._MEIPASS``.
* ``sys.argv[0]`` is the path to the bundled executable; we use
  it to write crash / supervisor logs alongside the binary when
  the supervisor has not configured a data dir.
* We never print to stdout without flushing; the Tauri supervisor
  captures stdout in a pipe and only re-emits it on crash.

Phase 8 explicitly does **not** add screen capture, mouse / keyboard
hooks, full desktop control, browser automation, or workflow
recording.
"""

from __future__ import annotations

import os
import sys
import traceback


def _emit(msg: str) -> None:
    """Write a line to stderr and flush, so the Tauri supervisor
    can see startup errors immediately even if the process
    crashes before uvicorn takes over stdout."""
    try:
        sys.stderr.write(f"[officepilot-sidecar] {msg}\n")
        sys.stderr.flush()
    except Exception:  # pragma: no cover - best effort
        pass


def _resolve_data_dir() -> str:
    """Pick a writable data dir for the bundled sidecar.

    Order of precedence:

    1. ``OFFICEPILOT_DATA_DIR`` env var (set by the Tauri shell).
    2. ``%LOCALAPPDATA%/OfficePilot AI/data`` on Windows.
    3. ``./data`` next to the executable.
    """
    explicit = os.environ.get("OFFICEPILOT_DATA_DIR")
    if explicit:
        return explicit
    if sys.platform.startswith("win"):
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            return os.path.join(local_app, "OfficePilot AI", "data")
    # Fallback: a ``data`` dir next to the executable.
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(here, "data")


def _ensure_data_subdirs(data_dir: str) -> None:
    for sub in ("logs", "cache", "audit", "recordings", "tmp"):
        try:
            os.makedirs(os.path.join(data_dir, sub), exist_ok=True)
        except OSError as exc:  # pragma: no cover - best effort
            _emit(f"could not create {sub}: {exc}")


def _write_crash_log(data_dir: str, exc: BaseException) -> None:
    """Best-effort crash log so the Tauri supervisor can show
    "why the sidecar failed" to the user."""
    try:
        os.makedirs(os.path.join(data_dir, "logs"), exist_ok=True)
        path = os.path.join(data_dir, "logs", "sidecar_crash.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n---- sidecar crash ----\n")
            fh.write(traceback.format_exc())
            fh.write("\n")
    except Exception:  # pragma: no cover - last-ditch
        pass


def main() -> int:
    os.environ.setdefault("OFFICEPILOT_SIDECAR", "1")
    # Force a stable data dir if the user has not configured one.
    data_dir = _resolve_data_dir()
    os.environ.setdefault("OFFICEPILOT_DATA_DIR", data_dir)
    _ensure_data_subdirs(data_dir)
    # Tame uvicorn's own log spam when running as a sidecar.
    os.environ.setdefault("OFFICEPILOT_LOG_LEVEL", "info")

    # PyInstaller puts data files under ``sys._MEIPASS``. The
    # backend package itself is bundled as source (.pyc), so
    # ``import app.main`` works the same way as in dev.
    try:
        import uvicorn  # type: ignore
    except Exception as exc:  # pragma: no cover - PyInstaller should include it
        _emit(f"uvicorn import failed: {exc!r}")
        _write_crash_log(data_dir, exc)
        return 2

    host = os.environ.get("OFFICEPILOT_AGENT_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("OFFICEPILOT_AGENT_PORT", "8000"))
    except ValueError:
        port = 8000
    log_level = os.environ.get("OFFICEPILOT_LOG_LEVEL", "info").lower()

    _emit(f"starting officepilot-agent (frozen={getattr(sys, 'frozen', False)}, "
          f"host={host}, port={port}, data={data_dir})")

    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            log_level=log_level,
            access_log=False,
        )
    except BaseException as exc:  # noqa: BLE001 - top-level guard
        _emit(f"uvicorn crashed: {exc!r}")
        _write_crash_log(data_dir, exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
