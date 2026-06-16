"""Phase 16B — Local backup status and operations."""

from __future__ import annotations

import logging
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from ..config import get_settings
from ..db import engine

logger = logging.getLogger("officepilot.backup")

# In-memory restore test result
_last_restore_test_status: str = "unknown"


def get_backup_status() -> dict:
    settings = get_settings()
    db_path = _get_db_path()
    snap_path = settings.snapshots_dir

    last_backup = _find_latest_backup(snap_path)

    disk_info = _get_disk_info(settings.data_dir)

    return {
        "database_path": str(db_path) if db_path else "unknown",
        "snapshot_path": str(snap_path),
        "last_backup_time": last_backup,
        "last_restore_test_status": _last_restore_test_status,
        "disk_free_gb": round(disk_info["free_gb"], 1),
        "disk_total_gb": round(disk_info["total_gb"], 1),
        "disk_warning": disk_info["free_gb"] < 1.0,
    }


def run_local_backup() -> dict:
    settings = get_settings()
    backup_dir = settings.data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    db_path = _get_db_path()
    if not db_path or not db_path.exists():
        return {"status": "failed", "message": "Database file not found", "file_path": ""}

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"officepilot_backup_{ts}.db"

    try:
        # Use sqlite3 backup API for safe copy
        src_conn = sqlite3.connect(str(db_path))
        dst_conn = sqlite3.connect(str(backup_path))
        src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()
        logger.info("Local backup created: %s", backup_path)
        return {
            "status": "completed",
            "message": "Backup created successfully",
            "file_path": str(backup_path),
        }
    except Exception as e:
        logger.exception("Backup failed")
        return {"status": "failed", "message": str(e), "file_path": ""}


def test_restore() -> dict:
    global _last_restore_test_status

    settings = get_settings()
    backup_dir = settings.data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Find latest backup
    backups = sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        _last_restore_test_status = "no_backup"
        return {"status": "failed", "message": "No backup file found to test"}

    latest = backups[0]

    # Restore to a temp file to verify integrity
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        src_conn = sqlite3.connect(str(latest))
        dst_conn = sqlite3.connect(str(tmp_path))
        src_conn.backup(dst_conn)
        src_conn.close()
        dst_conn.close()

        # Verify the restored DB
        verify_conn = sqlite3.connect(str(tmp_path))
        cursor = verify_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        verify_conn.close()

        tmp_path.unlink()
        _last_restore_test_status = "passed"
        return {
            "status": "completed",
            "message": "Restore test passed (%d tables restored)" % len(tables),
        }
    except Exception as e:
        _last_restore_test_status = "failed"
        return {"status": "failed", "message": "Restore test failed: %s" % e}


def _get_db_path() -> Path | None:
    try:
        url = str(engine.url)
        if url.startswith("sqlite:///"):
            p = Path(url[len("sqlite:///"):])
            if not p.is_absolute():
                p = Path.cwd() / p
            return p.resolve()
    except Exception:
        pass
    return None


def _find_latest_backup(snapshots_dir: Path) -> str | None:
    backup_dir = snapshots_dir.parent / "backups"
    if not backup_dir.exists():
        return None
    backups = sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        return None
    return datetime.fromtimestamp(backups[0].stat().st_mtime).isoformat()


def _get_disk_info(path: Path) -> dict:
    try:
        total, used, free = shutil.disk_usage(path)
        return {"free_gb": free / (1024**3), "total_gb": total / (1024**3)}
    except Exception:
        return {"free_gb": 0.0, "total_gb": 0.0}
