"""Phase 16B/21 — System readiness, startup metrics, cleanup, release checklist."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.safety import ReadinessReport
from ..services.cleanup import build_cleanup_preview, get_storage_usage, run_cleanup
from ..services.readiness import build_readiness_report
from ..services.release_checklist import get_checklist
from ..services.startup_metrics import get_metrics
from ..services.system_resources import (
    clear_vector_memory,
    get_orphaned_excel_processes,
    get_python_memory_mb,
    get_vector_store_size_mb,
    kill_orphaned_excel,
)
from pathlib import Path

router = APIRouter(prefix="/api/system", tags=["system"])


def _require_admin(current_user: User) -> None:
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Requires owner or admin role")


# ── Readiness (Phase 16B) ──────────────────────────────────────────────────


@router.get("/readiness", response_model=ReadinessReport)
def get_readiness(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = build_readiness_report(db)
    return ReadinessReport(**report)


# ── Startup Metrics (Phase 21) ──────────────────────────────────────────────


@router.get("/startup-metrics")
def get_startup_metrics():
    return get_metrics().to_dict()


# ── Storage Usage (Phase 21) ────────────────────────────────────────────────


@router.get("/storage-usage")
def storage_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    return get_storage_usage(db)


# ── Cleanup Preview (Phase 21) ──────────────────────────────────────────────

class CleanupPreviewResponse(BaseModel):
    items: list[dict]
    total_bytes_estimate: int

    model_config = ConfigDict(from_attributes=True)


@router.get("/cleanup-preview", response_model=CleanupPreviewResponse)
def cleanup_preview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    return build_cleanup_preview(db)


# ── Cleanup Run (Phase 21) ──────────────────────────────────────────────────

class CleanupRunRequest(BaseModel):
    confirmed: bool = False


class CleanupRunResponse(BaseModel):
    status: str
    detail: str = ""
    removed: dict[str, int] = {}


@router.post("/cleanup-run", response_model=CleanupRunResponse)
def cleanup_run(
    body: CleanupRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    result = run_cleanup(db, confirmed=body.confirmed)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["detail"])
    return result


# ── Release Checklist (Phase 21) ────────────────────────────────────────────

class ReleaseStepResponse(BaseModel):
    id: str
    label: str
    completed: bool


class ReleaseProgressResponse(BaseModel):
    completed: int
    total: int
    percentage: float
    steps: list[ReleaseStepResponse]


class CompleteStepRequest(BaseModel):
    step_id: str


class CompleteStepResponse(BaseModel):
    id: str
    label: str
    completed: bool


@router.get("/release/checklist", response_model=ReleaseProgressResponse)
def get_release_checklist():
    checklist = get_checklist()
    return checklist.progress()


@router.post("/release/checklist/complete-step", response_model=CompleteStepResponse)
def complete_release_step(body: CompleteStepRequest):
    checklist = get_checklist()
    step_id = checklist.complete_step(body.step_id)
    if step_id is None:
        raise HTTPException(status_code=404, detail=f"Unknown step: {body.step_id}")
    steps = checklist.get_status()
    for s in steps:
        if s["id"] == step_id:
            return CompleteStepResponse(**s)
    raise HTTPException(status_code=500, detail="Step not found after completion")


@router.get("/downloads-path")
def get_downloads_path():
    home = Path.home()
    candidates = [
        home / "Downloads",
        home / "downloads",
        home / "Desktop" / "Downloads",
    ]
    for c in candidates:
        if c.is_dir():
            return {"path": str(c.resolve())}
    return {"path": str((home / "Downloads").resolve())}


@router.post("/release/checklist/reset")
def reset_release_checklist():
    checklist = get_checklist()
    checklist.reset()
    return {"status": "ok"}


# ── Resource Monitor (Phase 46B) ────────────────────────────────────────────


class ResourceMonitorResponse(BaseModel):
    python_memory_mb: float
    vector_store_mb: float
    orphaned_excel_count: int
    orphaned_excel_pids: list[int]

    model_config = ConfigDict(from_attributes=True)


class OptimizeResponse(BaseModel):
    status: str
    detail: str = ""

    model_config = ConfigDict(from_attributes=True)


@router.get("/resources", response_model=ResourceMonitorResponse)
def get_resources(
    current_user: User = Depends(get_current_user),
):
    count, pids = get_orphaned_excel_processes()
    return ResourceMonitorResponse(
        python_memory_mb=get_python_memory_mb(),
        vector_store_mb=get_vector_store_size_mb(),
        orphaned_excel_count=count,
        orphaned_excel_pids=pids,
    )


@router.post("/optimize/clear-memory", response_model=OptimizeResponse)
def optimize_clear_memory(
    current_user: User = Depends(get_current_user),
):
    result = clear_vector_memory()
    return OptimizeResponse(status=result["status"], detail=result["detail"])


@router.post("/optimize/kill-excel", response_model=OptimizeResponse)
def optimize_kill_excel(
    current_user: User = Depends(get_current_user),
):
    killed = kill_orphaned_excel()
    return OptimizeResponse(
        status="ok",
        detail=f"Terminated {killed} orphaned Excel process(es)",
    )
