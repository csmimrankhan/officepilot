"""Phase 21 — In-memory release readiness checklist (no DB)."""

from __future__ import annotations

from typing import Optional

RELEASE_STEPS = [
    {"id": "backend_tests_pass", "label": "Backend tests pass"},
    {"id": "frontend_tests_pass", "label": "Frontend tests pass"},
    {"id": "sidecar_builds", "label": "Sidecar builds"},
    {"id": "desktop_launches", "label": "Desktop app launches"},
    {"id": "owner_registration", "label": "First owner registration works"},
    {"id": "demo_data_loads", "label": "Demo data loads"},
    {"id": "invoice_upload", "label": "Invoice upload works"},
    {"id": "excel_export", "label": "Excel export works"},
    {"id": "audit_export", "label": "Audit export works"},
    {"id": "backup_works", "label": "Backup works"},
    {"id": "kill_switch_works", "label": "Kill switch works"},
    {"id": "waitlist_works", "label": "Waitlist works"},
    {"id": "no_external_analytics", "label": "No external analytics"},
    {"id": "no_risky_automation", "label": "No risky automation enabled by default"},
]


class ReleaseChecklist:
    def __init__(self) -> None:
        self.completed: set[str] = set()

    def get_status(self) -> list[dict]:
        return [
            {
                "id": s["id"],
                "label": s["label"],
                "completed": s["id"] in self.completed,
            }
            for s in RELEASE_STEPS
        ]

    def complete_step(self, step_id: str) -> Optional[str]:
        ids = {s["id"] for s in RELEASE_STEPS}
        if step_id not in ids:
            return None
        self.completed.add(step_id)
        return step_id

    def reset(self) -> None:
        self.completed.clear()

    def progress(self) -> dict:
        status = self.get_status()
        done = sum(1 for s in status if s["completed"])
        total = len(status)
        return {
            "completed": done,
            "total": total,
            "percentage": round(done / total * 100, 1) if total else 0,
            "steps": status,
        }


_checklist = ReleaseChecklist()


def get_checklist() -> ReleaseChecklist:
    return _checklist
