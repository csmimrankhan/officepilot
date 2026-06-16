"""Parser engine registry and factory (Phase 5).

The registry is the single source of truth for which engines are
available in this deployment. ``PARSER_ENGINE`` selects the engine by
name; the default is ``existing`` so production behavior is
unchanged.
"""

from __future__ import annotations

import logging
from typing import Optional

from . import InvoiceParserEngine

logger = logging.getLogger(__name__)


def _lazy_engines() -> dict[str, type]:
    """Return engine classes, imported lazily so heavy deps
    (PaddleOCR, Docling) are not loaded at app startup."""
    from .docling_engine import DoclingParserEngine
    from .existing_engine import ExistingParserEngine
    from .hybrid_engine import HybridParserEngine
    from .ocr_engine import OCRParserEngine

    return {
        "existing": ExistingParserEngine,
        "docling": DoclingParserEngine,
        "ocr": OCRParserEngine,
        "hybrid": HybridParserEngine,
    }


AVAILABLE_ENGINES: dict[str, type] = {}  # populated on first call


def _ensure_engines() -> None:
    if not AVAILABLE_ENGINES:
        AVAILABLE_ENGINES.update(_lazy_engines())


def get_engine(name: str, settings) -> InvoiceParserEngine:
    """Instantiate the engine by name. Unknown names fall back to
    ``existing`` and emit a warning."""
    _ensure_engines()
    cls = AVAILABLE_ENGINES.get(name)
    if cls is None:
        logger.warning("Unknown parser engine %r; falling back to 'existing'", name)
        from .existing_engine import ExistingParserEngine
        cls = ExistingParserEngine
    return cls(settings)


def list_engines() -> list[dict]:
    """Return a small JSON-serialisable description of the registered
    engines. Used by the benchmark endpoint and the frontend.

    Each entry includes the class name, a one-line description, and a
    ``available`` flag (always True here; concrete engines may
    report False at runtime if their optional dependencies are
    missing — see :func:`probe_engines`)."""
    _ensure_engines()
    descriptions = {
        "existing": "Phase 1-3 PyMuPDF/pdfplumber/OCR + regex pipeline (default).",
        "docling": "Docling layout-aware parser; falls back to existing when not installed.",
        "ocr": "OCR-first engine (PaddleOCR or Tesseract).",
        "hybrid": "Reconciles existing + docling + ocr by per-field confidence.",
    }
    return [
        {
            "name": name,
            "class": cls.__name__,
            "description": descriptions.get(name, ""),
        }
        for name, cls in AVAILABLE_ENGINES.items()
    ]
