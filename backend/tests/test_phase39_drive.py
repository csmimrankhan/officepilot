"""Phase 39, Task 2: Google Drive Read-Only Integration tests."""
from __future__ import annotations

import json
import os
import time

os.environ["AGENT_PROVIDER"] = "mock"
os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase39_drive.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.services.accountant_agent import DRIVE_READONLY_BLOCKED_PATTERNS, classify_task_risk
from app.services.agent_tool_executor import execute_tool
from app.services.google_drive_adapter import GoogleDriveAdapter, BLOCKED_WRITE_OPERATIONS
from app.services.tool_registry import get_tool


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///./test_phase39_drive.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    try:
        Base.metadata.drop_all(bind=e)
    except Exception:
        pass
    e.dispose()
    import gc
    gc.collect()
    for _ in range(10):
        try:
            os.remove("test_phase39_drive.db")
            break
        except PermissionError:
            time.sleep(0.5)


@pytest.fixture
def db_session(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def user_token(client):
    resp = client.post("/api/auth/register", json={
        "email": "drive_test@example.com",
        "password": "Password123!",
        "full_name": "Drive Test",
        "confirm_password": "Password123!",
    })
    if resp.status_code in (200, 201):
        data = resp.json()
        tok = data.get("access_token") or data.get("token")
        if tok:
            return tok
    resp = client.post("/api/auth/login", json={
        "email": "drive_test@example.com",
        "password": "Password123!",
    })
    data = resp.json()
    return data.get("access_token") or data.get("token")


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ── Adapter Read-Only Enforcement ─────────────────────────────────────────


class TestDriveAdapterReadOnly:
    def test_list_recent_files_mock(self):
        adapter = GoogleDriveAdapter(user_id=1)
        files = adapter.list_recent_files(days_back=30)
        assert len(files) > 0
        names = [f["name"] for f in files]
        assert "Invoice_Acme_Oct.pdf" in names
        assert "Receipt_WeWork.pdf" in names

    def test_list_with_keywords_filters_correctly(self):
        adapter = GoogleDriveAdapter(user_id=1)
        files = adapter.list_recent_files(days_back=30, keywords=["Invoice"])
        assert len(files) >= 1
        for f in files:
            assert "invoice" in f["name"].lower()

    def test_list_with_no_match_returns_empty(self):
        adapter = GoogleDriveAdapter(user_id=1)
        files = adapter.list_recent_files(days_back=30, keywords=["ZZZZNOSUCHFILE"])
        assert len(files) == 0

    def test_list_respects_days_back(self):
        adapter = GoogleDriveAdapter(user_id=1)
        files_all = adapter.list_recent_files(days_back=365)
        files_recent = adapter.list_recent_files(days_back=1)
        assert len(files_all) >= len(files_recent)
        assert len(files_recent) > 0

    def test_download_file_mock(self):
        adapter = GoogleDriveAdapter(user_id=1)
        result = adapter.download_file("mock_drive_001")
        assert result["file_id"] == "mock_drive_001"
        assert result["name"] == "Invoice_Acme_Oct.pdf"
        assert "local_path" in result
        assert os.path.exists(result["local_path"])
        os.remove(result["local_path"])

    def test_download_file_with_target_folder(self, tmp_path):
        adapter = GoogleDriveAdapter(user_id=1)
        result = adapter.download_file("mock_drive_001", target_folder=str(tmp_path))
        assert result["file_id"] == "mock_drive_001"
        assert os.path.exists(result["local_path"])
        assert str(tmp_path) in result["local_path"]

    def test_upload_raises_permission_error(self):
        adapter = GoogleDriveAdapter(user_id=1)
        with pytest.raises(PermissionError, match="write operation blocked"):
            adapter.upload_file("dummy")

    def test_delete_raises_permission_error(self):
        adapter = GoogleDriveAdapter(user_id=1)
        with pytest.raises(PermissionError):
            adapter.delete_file("dummy")

    def test_move_raises_permission_error(self):
        adapter = GoogleDriveAdapter(user_id=1)
        with pytest.raises(PermissionError):
            adapter.move_file("dummy", "dest")

    def test_rename_raises_permission_error(self):
        adapter = GoogleDriveAdapter(user_id=1)
        with pytest.raises(PermissionError):
            adapter.rename_file("dummy", "newname")

    def test_copy_raises_permission_error(self):
        adapter = GoogleDriveAdapter(user_id=1)
        with pytest.raises(PermissionError):
            adapter.copy_file("dummy")

    def test_create_folder_raises_permission_error(self):
        adapter = GoogleDriveAdapter(user_id=1)
        with pytest.raises(PermissionError):
            adapter.create_folder("newfolder")

    def test_all_write_operations_blocked(self):
        assert "upload" in BLOCKED_WRITE_OPERATIONS
        assert "delete" in BLOCKED_WRITE_OPERATIONS
        assert "move" in BLOCKED_WRITE_OPERATIONS
        assert "rename" in BLOCKED_WRITE_OPERATIONS
        assert "copy" in BLOCKED_WRITE_OPERATIONS
        assert "create" in BLOCKED_WRITE_OPERATIONS


# ── Tool Executor Tests ────────────────────────────────────────────────────


class TestDriveToolExecutors:
    def test_drive_list_recent_files_tool(self, db_session):
        result = execute_tool("drive_list_recent_files", {"days_back": 30}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        output = result["output"]
        assert output["file_count"] > 0
        assert output["mode"] == "mock"

    def test_drive_list_with_keywords(self, db_session):
        result = execute_tool("drive_list_recent_files", {"days_back": 30, "keywords": ["Invoice"]}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        for f in result["output"]["files"]:
            assert "invoice" in f["name"].lower()

    def test_drive_download_file_tool(self, db_session):
        result = execute_tool("drive_download_file", {"file_id": "mock_drive_001"}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        output = result["output"]
        assert output["file_id"] == "mock_drive_001"
        assert output["name"] == "Invoice_Acme_Oct.pdf"
        assert os.path.exists(output["local_path"])
        os.remove(output["local_path"])

    def test_drive_download_missing_file_id(self, db_session):
        result = execute_tool("drive_download_file", {}, mode="live", db=db_session, user=None)
        assert result["status"] == "failed"

    def test_tools_registered_in_registry(self):
        for name in ("drive_list_recent_files", "drive_download_file"):
            tool = get_tool(name)
            assert tool is not None, f"Tool {name} not in registry"
            assert tool.risk_level == "low"
            assert tool.approval_required is False


# ── Safety Gate Tests ──────────────────────────────────────────────────────


class TestDriveSafetyGate:
    def test_blocked_upload_command(self):
        result = classify_task_risk("upload file to google drive")
        assert result["risk_level"] == "blocked"
        assert result["reason"] == "drive_write_not_supported"

    def test_blocked_delete_command(self):
        result = classify_task_risk("delete drive file invoice.pdf")
        assert result["risk_level"] == "blocked"
        assert result["reason"] == "drive_write_not_supported"

    def test_blocked_move_command(self):
        result = classify_task_risk("move drive file to folder")
        assert result["risk_level"] == "blocked"
        assert result["reason"] == "drive_write_not_supported"

    def test_blocked_rename_command(self):
        result = classify_task_risk("rename drive file")
        assert result["risk_level"] == "blocked"
        assert result["reason"] == "drive_write_not_supported"

    def test_allowed_read_commands(self):
        result = classify_task_risk("list my recent drive files")
        assert result["risk_level"] != "blocked"

    def test_allowed_download_command(self):
        result = classify_task_risk("download invoice from drive")
        assert result["risk_level"] != "blocked"

    def test_blocked_pattern_compiles(self):
        assert DRIVE_READONLY_BLOCKED_PATTERNS.search("upload to drive")
        assert DRIVE_READONLY_BLOCKED_PATTERNS.search("delete google drive file")
        assert DRIVE_READONLY_BLOCKED_PATTERNS.search("move drive file to trash")
        assert DRIVE_READONLY_BLOCKED_PATTERNS.search("rename drive file")
        assert DRIVE_READONLY_BLOCKED_PATTERNS.search("copy drive file")
        assert not DRIVE_READONLY_BLOCKED_PATTERNS.search("list drive files")
        assert not DRIVE_READONLY_BLOCKED_PATTERNS.search("download from drive")

    def test_dry_run_mode_returns_dry_run(self, db_session):
        result = execute_tool("drive_list_recent_files", {"days_back": 7}, mode="dry_run", db=db_session, user=None)
        assert result["status"] == "dry_run"

    def test_drive_list_returns_file_details(self, db_session):
        result = execute_tool("drive_list_recent_files", {"days_back": 365}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        for f in result["output"]["files"]:
            assert "id" in f
            assert "name" in f
            assert "mime_type" in f
            assert "size" in f
