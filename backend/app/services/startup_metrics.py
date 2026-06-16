"""Phase 21 — Startup timing metrics (in-memory, no DB)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StartupMetrics:
    marks: dict[str, float] = field(default_factory=dict)

    def mark(self, name: str) -> None:
        self.marks[name] = time.monotonic()

    def elapsed(self, name: str) -> Optional[float]:
        if name not in self.marks:
            return None
        start = self.marks.get("sidecar_launch_started") or self.marks.get("process_start")
        if start is None:
            return None
        return round(self.marks[name] - start, 3)

    def total_seconds(self) -> Optional[float]:
        """Total time from process_start to backend_ready."""
        s = self.marks.get("sidecar_launch_started") or self.marks.get("process_start")
        e = self.marks.get("backend_ready")
        if s is None or e is None:
            return None
        return round(e - s, 3)

    def to_dict(self) -> dict:
        return {
            "marks": dict(self.marks),
            "elapsed": {
                k: self.elapsed(k)
                for k in sorted(self.marks)
                if k != "sidecar_launch_started" and k != "process_start"
            },
            "total_startup_seconds": self.total_seconds(),
        }


_metrics = StartupMetrics()


def get_metrics() -> StartupMetrics:
    return _metrics


def mark_startup(name: str) -> None:
    _metrics.mark(name)
