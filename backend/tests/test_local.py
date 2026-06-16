"""Phase 7 — /api/local/* endpoint tests."""

from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.audit_log import AuditLog


# --------------------------------------------------------------- /api/local/status


def test_local_status_includes_runtime_fields(client: TestClient):
    r = client.get("/api/local/status")
    assert r.status_code == 200
    body = r.json()
    assert body["app"] == "officepilot-ai"
    assert body["version"] == "0.36.1"
    assert body["phase"] == 12
    # Runtime fields
    assert "started_at" in body
    assert "uptime_seconds" in body
    assert "uptime_human" in body
    assert body["host"] == "127.0.0.1"
    assert body["port"] == 8000
    assert body["url"].endswith(":8000")
    assert body["pid"] == os.getpid()
    assert body["env"] == "development"
    assert body["parser_engine"] == "existing"
    # Database sub-snapshot is present (may be ok in tests).
    assert body["database"]["status"] in ("ok", "unknown", "error")


def test_local_status_reports_data_dir(client: TestClient):
    body = client.get("/api/local/status").json()
    # OFFICEPILOT_DATA_DIR was set by conftest to _TMP/data
    assert "data" in body["data_dir"].lower()
    assert Path(body["data_dir"]).exists()


# --------------------------------------------------------------- /api/local/settings


def test_local_settings_view_lists_mutable_keys(client: TestClient):
    r = client.get("/api/local/settings")
    assert r.status_code == 200
    body = r.json()
    assert "settings" in body
    assert "mutable" in body
    # Mutable allow-list is well-known.
    assert set(body["mutable"]) == {
        "agent_host", "agent_port", "ocr_enabled",
        "gmail_allow_real", "max_upload_mb",
    }


def test_local_settings_patch_rejects_unknown_keys(client: TestClient):
    r = client.patch(
        "/api/local/settings",
        json={"patch": {"data_dir": "/tmp/evil"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["applied"] == {}
    assert "data_dir" in body["rejected"]


def test_local_settings_patch_applies_mutable_keys(client: TestClient):
    r = client.patch(
        "/api/local/settings",
        json={"patch": {"ocr_enabled": False, "max_upload_mb": 99}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["applied"]["ocr_enabled"] is False
    assert body["applied"]["max_upload_mb"] == 99
    # The env var was updated for future get_settings() calls.
    assert os.environ.get("OFFICEPILOT_OCR_ENABLED") == "False"
    assert os.environ.get("OFFICEPILOT_MAX_UPLOAD_MB") == "99"


def test_local_settings_patch_writes_audit_log(client: TestClient):
    from app.db import SessionLocal
    client.patch(
        "/api/local/settings",
        json={"patch": {"ocr_enabled": True}},
    )
    # Read back via the same DB the client wrote to.
    db = SessionLocal()
    try:
        rows = (
            db.query(AuditLog)
            .filter(AuditLog.action == "local.settings.update")
            .order_by(AuditLog.id.desc())
            .all()
        )
        assert len(rows) >= 1
        assert "ocr_enabled" in rows[0].details
    finally:
        db.close()


# --------------------------------------------------------------- /api/local/storage


def test_local_storage_reports_all_subdirs(client: TestClient, tmp_path):
    # Create some content so file_count > 0
    from app.config import get_settings
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    cache = settings.data_dir / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "junk.bin").write_bytes(b"x" * 1024)
    storage = settings.storage_root
    inv = storage / "invoices"
    inv.mkdir(parents=True, exist_ok=True)
    (inv / "file.pdf").write_bytes(b"%PDF-1.4\n%fake\n")

    r = client.get("/api/local/storage")
    assert r.status_code == 200
    body = r.json()
    assert body["data_dir"] == str(settings.data_dir)
    assert body["storage_root"] == str(settings.storage_root)
    names = {d["name"] for d in body["dirs"]}
    assert {"data", "invoices", "exports", "audit", "recordings",
            "cache", "tmp", "gmail_state"}.issubset(names)
    # Cache dir had 1 file
    cache_info = next(d for d in body["dirs"] if d["name"] == "cache")
    assert cache_info["file_count"] == 1
    assert cache_info["total_bytes"] == 1024
    assert cache_info["protected"] is False
    # invoices dir is protected
    inv_info = next(d for d in body["dirs"] if d["name"] == "invoices")
    assert inv_info["protected"] is True


def test_local_storage_summarises_totals(client: TestClient):
    from app.config import get_settings
    settings = get_settings()
    body = client.get("/api/local/storage").json()
    assert "protected_total_bytes" in body
    assert "protected_total_human" in body
    assert "cache_total_bytes" in body
    assert "cache_total_human" in body
    # The protected total should be at least the size of any pre-existing
    # files; we don't assert an exact number because other tests may
    # leave files in the storage root.


# --------------------------------------------------------------- /api/local/clear-cache


def test_local_clear_cache_requires_confirm(client: TestClient):
    r = client.post("/api/local/clear-cache")
    assert r.status_code == 200
    body = r.json()
    assert body["cleared"] is False
    assert "confirm" in body["message"]


def test_local_clear_cache_only_touches_cache_dirs(client: TestClient):
    from app.config import get_settings
    settings = get_settings()
    cache = settings.data_dir / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    # Use unique names so the test is robust against other tests
    # that may have left files behind in the cache dir.
    a = cache / "phase7_keep_a.bin"
    a.write_bytes(b"a" * 256)
    sub = cache / "phase7_keep_sub"
    sub.mkdir(exist_ok=True)
    b = sub / "phase7_keep_b.bin"
    b.write_bytes(b"b" * 128)
    inv = settings.storage_root / "invoices"
    inv.mkdir(parents=True, exist_ok=True)
    keep = inv / "phase7_must_survive.pdf"
    keep.write_bytes(b"keep")

    r = client.post("/api/local/clear-cache?confirm=true")
    assert r.status_code == 200
    body = r.json()
    assert body["cleared"] is True
    # The two files we created are gone.
    assert not a.exists()
    assert not b.exists()
    # The invoices file must still be there.
    assert keep.exists()
    assert keep.read_bytes() == b"keep"


def test_local_clear_cache_refuses_path_outside_data_dir(client: TestClient, monkeypatch):
    """Defence in depth: if the cache dir somehow resolves outside
    data_dir, we must not delete it."""
    from app.config import get_settings
    settings = get_settings()
    cache = settings.data_dir / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    keep = cache / "keep.bin"
    keep.write_bytes(b"x")

    from app.services import storage_manager as sm
    monkeypatch.setattr(sm, "_is_within", lambda child, parent: False)

    r = client.post("/api/local/clear-cache?confirm=true")
    body = r.json()
    # The file should still be there.
    assert keep.exists()
    # The report should list the cache subdir under skipped.
    assert any(str(cache) in s for s in body["skipped"])


# --------------------------------------------------------------- /api/local/export-audit


def test_local_export_audit_writes_csv(client: TestClient):
    from app.db import SessionLocal
    from app.services.audit import log_action
    db = SessionLocal()
    try:
        log_action(
            db=db, actor="tester", action="phase7.test",
            entity_type="local", entity_id=1, details="unit test",
        )
        db.commit()
    finally:
        db.close()

    r = client.post("/api/local/export-audit?limit=100")
    assert r.status_code == 200
    body = r.json()
    assert body["rows_exported"] >= 1
    assert body["limit"] == 100
    assert body["path"].endswith(".csv")
    # The file exists and is a valid CSV.
    csv_path = Path(body["path"])
    assert csv_path.exists()
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert any(r["action"] == "phase7.test" for r in rows)


def test_local_export_audit_respects_limit(client: TestClient):
    from app.db import SessionLocal
    from app.services.audit import log_action
    db = SessionLocal()
    try:
        # Tag our rows so we can count them deterministically.
        for i in range(5):
            log_action(
                db=db, actor="t", action=f"phase7.limit.{i}",
                entity_type="x", entity_id=i, details="",
            )
        db.commit()
    finally:
        db.close()
    r = client.post("/api/local/export-audit?limit=2")
    body = r.json()
    assert body["rows_exported"] == 2
