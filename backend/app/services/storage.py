"""Storage + MIME type handling for invoice uploads."""

from __future__ import annotations

import mimetypes
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import Settings
from ..utils.hashing import sha256_bytes, sha256_file


_ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg"}
_ALLOWED_MIMES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}


@dataclass
class StoredFile:
    stored_path: str
    original_filename: str
    file_hash: str
    mime_type: str
    size: int


class UnsupportedFileType(Exception):
    pass


def detect_mime(filename: str, head: bytes) -> str:
    """Best-effort MIME detection using extension + magic bytes."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf" or head.startswith(b"%PDF"):
        return "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _safe_filename(name: str) -> str:
    name = name.strip().replace("\x00", "")
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    return name[:200] or "upload"


def store_upload(
    settings: Settings,
    *,
    data: bytes,
    original_filename: str,
) -> StoredFile:
    """Validate, hash, and persist a single upload. Idempotent: same bytes → same hash → same stored file."""
    if not data:
        raise UnsupportedFileType("Empty file")

    ext = Path(original_filename).suffix.lower()
    if ext not in _ALLOWED_EXTS:
        raise UnsupportedFileType(
            f"Unsupported file type: {ext or '<none>'}. "
            f"Allowed: {sorted(_ALLOWED_EXTS)}"
        )

    mime = detect_mime(original_filename, data[:16])
    if mime not in _ALLOWED_MIMES:
        raise UnsupportedFileType(f"Unsupported MIME type: {mime}")

    settings.invoices_dir.mkdir(parents=True, exist_ok=True)
    digest = sha256_bytes(data)
    safe = _safe_filename(Path(original_filename).name)
    stored = settings.invoices_dir / f"{digest[:16]}_{uuid.uuid4().hex[:8]}_{safe}"
    stored.write_bytes(data)
    return StoredFile(
        stored_path=str(stored),
        original_filename=safe,
        file_hash=digest,
        mime_type=mime,
        size=len(data),
    )


def find_existing_file_by_hash(settings: Settings, file_hash: str) -> Optional[str]:
    """Look for a previously stored file with the same content hash (best-effort, not required for correctness)."""
    prefix = file_hash[:16]
    if not settings.invoices_dir.exists():
        return None
    for p in settings.invoices_dir.iterdir():
        if p.name.startswith(prefix + "_") and sha256_file(p) == file_hash:
            return str(p)
    return None
