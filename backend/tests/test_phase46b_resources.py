"""Phase 46B — Resource Monitor tests."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, PropertyMock, patch

os.environ["OFFICEPILOT_APP_VERSION"] = "1.0.0"

import psutil as psutil_module
from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()
client = TestClient(app)


def _auth_header():
    from app.services.auth import create_access_token

    from app.db import SessionLocal, init_db
    from app.models.user import User

    init_db()
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == "admin@test.com").first()
        if not u:
            from app.services.auth import hash_password

            u = User(
                email="admin@test.com",
                password_hash=hash_password("testpass"),
                role="admin",
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        token = create_access_token(u.id, u.email, u.role)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


def test_get_resources_returns_structure():
    headers = _auth_header()
    resp = client.get("/api/system/resources", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "python_memory_mb" in body
    assert "vector_store_mb" in body
    assert "orphaned_excel_count" in body
    assert "orphaned_excel_pids" in body
    assert isinstance(body["python_memory_mb"], (int, float))
    assert isinstance(body["vector_store_mb"], (int, float))
    assert isinstance(body["orphaned_excel_count"], int)
    assert isinstance(body["orphaned_excel_pids"], list)


@patch.object(psutil_module.Process, "memory_info")
def test_get_resources_includes_correct_values(mock_mem_info):
    mock_mem_info.return_value.rss = 256 * 1024 * 1024

    mock_proc_iter = MagicMock(spec=psutil_module.Process)
    mock_proc_iter.info = {"name": "EXCEL.EXE", "pid": 1234, "create_time": 100.0}

    with patch.object(psutil_module, "process_iter", return_value=[mock_proc_iter]):
        with patch("app.services.system_resources.time.time", return_value=10000.0):
            from app.services.system_resources import (
                get_orphaned_excel_processes,
                get_python_memory_mb,
            )

            mem = get_python_memory_mb()
            assert mem == 256.0

            count, pids = get_orphaned_excel_processes()
            assert count == 1
            assert pids == [1234]


def test_vector_store_size_zero_when_missing():
    from app.services.system_resources import get_vector_store_size_mb

    size = get_vector_store_size_mb()
    assert size == 0.0


def test_clear_memory_endpoint():
    headers = _auth_header()
    with patch("app.services.semantic_memory.reset_semantic_memory"):
        resp = client.post("/api/system/optimize/clear-memory", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_kill_excel_endpoint():
    mock_proc = MagicMock(spec=psutil_module.Process)
    mock_proc.info = {"name": "EXCEL.EXE", "pid": 1234, "create_time": 100.0}

    with patch.object(psutil_module, "process_iter", return_value=[mock_proc]):
        with patch("app.services.system_resources.time.time", return_value=10000.0):
            headers = _auth_header()
            resp = client.post("/api/system/optimize/kill-excel", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "Terminated" in body["detail"]


def test_get_resources_requires_auth():
    resp = client.get("/api/system/resources")
    assert resp.status_code == 401


def test_clear_memory_requires_auth():
    resp = client.post("/api/system/optimize/clear-memory")
    assert resp.status_code == 401


def test_kill_excel_requires_auth():
    resp = client.post("/api/system/optimize/kill-excel")
    assert resp.status_code == 401
