"""DEPRECATED — Legacy Phase 5 parser / benchmark endpoints.

OfficePilot is an automation agent, not a parser product.
These endpoints are kept for backward compatibility only.

Use automation tools (browser_open_url, screen_read_text, file_open, etc.)
instead of parser tools for all new workflows.

GET  /api/parser/engines                  — list available engines
GET  /api/parser/benchmark?engines=...&format=json|csv
                                          — run the benchmark; JSON
                                            (default) returns the full
                                            report, CSV returns a flat
                                            spreadsheet
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from ..config import get_settings
from ..services.benchmark import run_benchmark, to_csv
from ..services.engines.registry import list_engines

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/parser", tags=["parser"])


@router.get("/engines", summary="List available parser engines")
def get_engines() -> dict:
    """List the engines that are registered and importable on this
    machine. Engines that fail to import are reported as
    ``available: false`` with a short reason, so the operator can
    see what's missing without reading logs.
    """
    return {"engines": list_engines()}


@router.get("/benchmark", summary="Run the parser benchmark on golden fixtures")
def get_benchmark(
    engines: Optional[str] = Query(
        default=None,
        description="Comma-separated engine names. Defaults to all available.",
    ),
    fmt: Optional[str] = Query(
        default=None,
        description="Response format: json or csv. Alias: format.",
    ),
    format: Optional[str] = Query(default=None, include_in_schema=False),
):
    """Run the parser benchmark. By default returns a JSON report;
    pass ``?fmt=csv`` (or ``?format=csv``) to get a flat CSV
    suitable for spreadsheets."""
    raw = fmt if fmt is not None else format
    fmt_normalised = (raw or "json").lower()
    if fmt_normalised not in ("json", "csv"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"Unsupported format: {raw!r}")
    settings = get_settings()
    engine_list = (
        [e.strip() for e in engines.split(",") if e.strip()]
        if engines
        else None
    )
    report = run_benchmark(settings=settings, engines=engine_list)

    if fmt_normalised == "csv":
        return PlainTextResponse(
            content=to_csv(report),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=parser_benchmark.csv"
            },
        )
    return JSONResponse(content=report)
