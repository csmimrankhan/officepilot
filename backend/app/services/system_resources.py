"""Phase 46B — System resource monitoring and memory optimization."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from ..config import get_settings

logger = logging.getLogger("officepilot.system_resources")

ORPHANED_EXCEL_MIN_AGE_SECONDS = 300


def get_python_memory_mb() -> float:
    import psutil

    process = psutil.Process()
    return round(process.memory_info().rss / 1024 / 1024, 1)


def get_vector_store_size_mb() -> float:
    settings = get_settings()
    vector_dir = settings.data_dir / "vector_store"
    if not vector_dir.is_dir():
        return 0.0
    total = 0
    for root, dirs, files in os.walk(str(vector_dir)):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                continue
    return round(total / 1024 / 1024, 2)


def get_orphaned_excel_processes() -> tuple[int, list[int]]:
    import psutil

    now = time.time()
    pids: list[int] = []
    for proc in psutil.process_iter(["name", "pid", "create_time"]):
        try:
            if proc.info["name"] and proc.info["name"].upper() == "EXCEL.EXE":
                age = now - (proc.info["create_time"] or now)
                if age >= ORPHANED_EXCEL_MIN_AGE_SECONDS:
                    pids.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return len(pids), pids


def clear_vector_memory() -> dict:
    from .semantic_memory import reset_semantic_memory

    reset_semantic_memory()
    return {"status": "ok", "detail": "Semantic memory cache cleared"}


def kill_orphaned_excel() -> int:
    import psutil

    count, pids = get_orphaned_excel_processes()
    killed = 0
    for pid in pids:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1)
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed
