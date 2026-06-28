"""Phase 39, Task 2 — Google Drive Read-Only Integration.

Mock mode returns realistic fake files. Real mode structure is in place
for OAuth2 integration. All write operations (upload, delete, move, rename)
raise PermissionError to enforce read-only access.
"""

from __future__ import annotations

import io
import json
import logging
import random
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..config import get_settings

logger = logging.getLogger("officepilot.google_drive_adapter")

# ── Blocklist — any call here raises PermissionError ──────────────────────
BLOCKED_WRITE_OPERATIONS = frozenset({
    "upload", "delete", "move", "rename", "copy", "create",
    "update", "patch", "trash", "empty_trash", "add_permission",
    "remove_permission", "update_permission", "create_shortcut",
})


def _enforce_readonly(method_name: str) -> None:
    for blocked in BLOCKED_WRITE_OPERATIONS:
        if blocked in method_name.lower():
            raise PermissionError(
                f"Google Drive write operation blocked: '{method_name}'. "
                "OfficePilot only supports read-only Drive access."
            )


MOCK_FILES: list[dict[str, Any]] = [
    {"id": "mock_drive_001", "name": "Invoice_Acme_Oct.pdf", "mime_type": "application/pdf", "size": 245760, "modified_time": (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"},
    {"id": "mock_drive_002", "name": "Receipt_WeWork.pdf", "mime_type": "application/pdf", "size": 102400, "modified_time": (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"},
    {"id": "mock_drive_003", "name": "Monthly_Report_Sep.xlsx", "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 512000, "modified_time": (datetime.utcnow() - timedelta(days=5)).isoformat() + "Z"},
    {"id": "mock_drive_004", "name": "Tax_Summary_2025.pdf", "mime_type": "application/pdf", "size": 819200, "modified_time": (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"},
    {"id": "mock_drive_005", "name": "Vendor_List.xlsx", "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 20480, "modified_time": (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"},
    {"id": "mock_drive_006", "name": "Invoice_QuickBooks_Export.csv", "mime_type": "text/csv", "size": 35840, "modified_time": (datetime.utcnow() - timedelta(hours=6)).isoformat() + "Z"},
    {"id": "mock_drive_007", "name": "Bank_Statement_Q3.pdf", "mime_type": "application/pdf", "size": 1048576, "modified_time": (datetime.utcnow() - timedelta(days=10)).isoformat() + "Z"},
    {"id": "mock_drive_008", "name": "Expense_Report_Oct.xlsx", "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 65536, "modified_time": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"},
]

# Extensions for file type filtering
EXTENSION_MAP: dict[str, str] = {
    "pdf": "application/pdf",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
}


class GoogleDriveAdapter:
    """Read-only adapter for Google Drive.

    In mock mode, returns fake files. In real mode (when configured),
    uses OAuth2 to access the Drive API. All write operations raise
    PermissionError regardless of mode.
    """

    def __init__(self, user_id: int | None = None):
        self._user_id = user_id
        self._real_mode = self._check_real_mode()

    def _check_real_mode(self) -> bool:
        settings = get_settings()
        cid = getattr(settings, "drive_client_id", "") or ""
        csecret = getattr(settings, "drive_client_secret", "") or ""
        return bool(cid and csecret)

    def _get_download_dir(self) -> Path:
        settings = get_settings()
        dl_dir = settings.data_dir / "drive_downloads" / str(self._user_id or 0)
        dl_dir.mkdir(parents=True, exist_ok=True)
        return dl_dir

    # ── Read-only operations ─────────────────────────────────────────────

    def list_recent_files(self, days_back: int = 7, keywords: list[str] | None = None) -> list[dict[str, Any]]:
        if self._real_mode:
            return self._list_recent_files_real(days_back, keywords)
        return self._list_recent_files_mock(days_back, keywords)

    def download_file(self, file_id: str, target_folder: str | None = None) -> dict[str, Any]:
        if self._real_mode:
            return self._download_file_real(file_id, target_folder)
        return self._download_file_mock(file_id, target_folder)

    # ── Write operations — all blocked ───────────────────────────────────

    def upload_file(self, *args, **kwargs):
        _enforce_readonly("upload_file")

    def delete_file(self, *args, **kwargs):
        _enforce_readonly("delete_file")

    def move_file(self, *args, **kwargs):
        _enforce_readonly("move_file")

    def rename_file(self, *args, **kwargs):
        _enforce_readonly("rename_file")

    def copy_file(self, *args, **kwargs):
        _enforce_readonly("copy_file")

    def create_folder(self, *args, **kwargs):
        _enforce_readonly("create_folder")

    # ── Mock implementations ────────────────────────────────────────────

    def _list_recent_files_mock(self, days_back: int = 7, keywords: list[str] | None = None) -> list[dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        results = []
        for f in MOCK_FILES:
            mtime = datetime.fromisoformat(f["modified_time"].rstrip("Z"))
            if mtime < cutoff:
                continue
            if keywords:
                kw_lower = [k.lower() for k in keywords]
                name_lower = f["name"].lower()
                if not any(kw in name_lower for kw in kw_lower):
                    continue
            results.append(dict(f))
        return results

    def _download_file_mock(self, file_id: str, target_folder: str | None = None) -> dict[str, Any]:
        matched = [f for f in MOCK_FILES if f["id"] == file_id]
        if not matched:
            matched = [f for f in MOCK_FILES if f["id"] == f"mock_drive_00{random.randint(1, len(MOCK_FILES))}"]
        file_info = matched[0]

        dl_dir = Path(target_folder) if target_folder else self._get_download_dir()
        dl_dir.mkdir(parents=True, exist_ok=True)

        local_path = dl_dir / file_info["name"]
        fake_content = f"Mock content for {file_info['name']}\nFile ID: {file_info['id']}\nSize: {file_info['size']}\nGenerated: {datetime.utcnow().isoformat()}\n"
        local_path.write_text(fake_content, encoding="utf-8")

        return {
            "file_id": file_info["id"],
            "name": file_info["name"],
            "mime_type": file_info["mime_type"],
            "size": file_info["size"],
            "local_path": str(local_path.resolve()),
            "mode": "mock",
        }

    # ── Real mode placeholders ──────────────────────────────────────────

    def _list_recent_files_real(self, days_back: int = 7, keywords: list[str] | None = None) -> list[dict[str, Any]]:
        """Placeholder for OAuth2-based real Drive listing.

        Will use google-api-python-client with read-only scope.
        """
        raise NotImplementedError("Real Google Drive listing not yet implemented. Set DRIVE_CLIENT_ID and DRIVE_CLIENT_SECRET to configure, or use mock mode.")

    def _download_file_real(self, file_id: str, target_folder: str | None = None) -> dict[str, Any]:
        """Placeholder for OAuth2-based real Drive download.

        Will download file bytes via Drive API and save to local path.
        """
        raise NotImplementedError("Real Google Drive download not yet implemented. Use mock mode to test.")


def get_adapter(user_id: int | None = None) -> GoogleDriveAdapter:
    """Get the process-wide Drive adapter instance."""
    return GoogleDriveAdapter(user_id=user_id)
