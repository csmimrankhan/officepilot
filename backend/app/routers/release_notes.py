"""Phase 46A — Release Notes endpoint for v1.0.0 Grand Release."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

router = APIRouter(prefix="/api/app", tags=["app"])

_HIGHLIGHTS = [
    "Multi-Agent Swarm Architecture",
    "Semantic Bank Reconciliation",
    "Live Voice-Driven Excel Editing",
    "Autonomous Background Watchers",
    "Ollama Local LLM Brain",
]


@router.get("/release-notes")
def get_release_notes():
    return {
        "version": "1.0.0",
        "release_date": date.today().isoformat(),
        "highlights": _HIGHLIGHTS,
    }
