"""Tests for the storage service."""

import io
import os
import tempfile
from pathlib import Path

import pytest

from app.config import get_settings
from app.services.storage import UnsupportedFileType, detect_mime, store_upload


def test_store_upload_writes_file_and_hash(tmp_path):
    settings = get_settings()
    settings.invoices_dir.mkdir(parents=True, exist_ok=True)
    data = b"%PDF-1.4\n%fake test pdf content"
    stored = store_upload(settings, data=data, original_filename="Hello.pdf")
    assert Path(stored.stored_path).exists()
    assert stored.size == len(data)
    assert stored.file_hash  # non-empty
    assert stored.mime_type == "application/pdf"


def test_store_upload_rejects_unknown_extension(tmp_path):
    settings = get_settings()
    with pytest.raises(UnsupportedFileType):
        store_upload(settings, data=b"hello", original_filename="a.txt")


def test_store_upload_rejects_empty():
    settings = get_settings()
    with pytest.raises(UnsupportedFileType):
        store_upload(settings, data=b"", original_filename="a.pdf")


def test_detect_mime_by_magic():
    assert detect_mime("a.pdf", b"%PDF-1.7\n") == "application/pdf"
    assert detect_mime("a.png", b"\x89PNG\r\n\x1a\nxxxx") == "image/png"
    assert detect_mime("a.jpg", b"\xff\xd8\xff\xe0xxxx") == "image/jpeg"


def test_duplicate_hash_detected_by_recomputation(tmp_path):
    settings = get_settings()
    settings.invoices_dir.mkdir(parents=True, exist_ok=True)
    data = b"%PDF-1.4\nxyz"
    s1 = store_upload(settings, data=data, original_filename="a.pdf")
    s2 = store_upload(settings, data=data, original_filename="a-different.pdf")
    assert s1.file_hash == s2.file_hash
    assert Path(s1.stored_path).read_bytes() == data
