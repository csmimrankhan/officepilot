"""Text extraction (PyMuPDF + pdfplumber) and OCR fallback for images / weak text."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import Settings

logger = logging.getLogger(__name__)

WEAK_TEXT_THRESHOLD = 40  # characters


@dataclass
class ExtractionResult:
    text: str
    source: str  # "pymupdf" | "pdfplumber" | "ocr" | "image" | "empty"
    used_ocr: bool
    notes: list[str]


def _is_weak(text: str) -> bool:
    cleaned = "".join(ch for ch in text if ch.isalnum())
    return len(cleaned) < WEAK_TEXT_THRESHOLD


def extract_text_from_pdf(path: Path) -> tuple[str, str]:
    """Try PyMuPDF first, fall back to pdfplumber. Returns (text, source)."""
    text_chunks: list[str] = []
    source = "empty"
    try:
        import fitz  # PyMuPDF
        with fitz.open(path) as doc:
            for page in doc:
                text_chunks.append(page.get_text("text") or "")
        joined = "\n".join(text_chunks).strip()
        if joined:
            return joined, "pymupdf"
    except Exception as exc:  # pragma: no cover
        logger.warning("PyMuPDF failed for %s: %s", path, exc)

    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t:
                    text_chunks.append(t)
        joined = "\n".join(text_chunks).strip()
        if joined:
            return joined, "pdfplumber"
    except Exception as exc:  # pragma: no cover
        logger.warning("pdfplumber failed for %s: %s", path, exc)

    return "", "empty"


def _ocr_with_tesseract(image_path: Path, settings: Settings) -> str:
    """Run pytesseract on an image. Graceful if tesseract binary missing."""
    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        logger.warning("OCR libraries unavailable: %s", exc)
        return ""

    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    binary = (
        settings.tesseract_cmd
        or shutil.which("tesseract")
        or pytesseract.pytesseract.tesseract_cmd
    )
    if not binary or not Path(binary).exists() and not shutil.which(binary):
        logger.warning("Tesseract binary not found; OCR skipped.")
        return ""

    try:
        with Image.open(image_path) as img:
            return pytesseract.image_to_string(img) or ""
    except Exception as exc:  # pragma: no cover
        logger.warning("OCR failed for %s: %s", image_path, exc)
        return ""


def _ocr_pdf_pages(path: Path, settings: Settings) -> str:
    """Rasterize PDF pages and OCR each one."""
    try:
        import fitz
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        logger.warning("OCR pdf deps unavailable: %s", exc)
        return ""
    chunks: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            tmp = path.with_suffix(".ocrpage.png")
            try:
                img.save(tmp)
                txt = _ocr_with_tesseract(tmp, settings)
            finally:
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass
            if txt:
                chunks.append(txt)
    return "\n".join(chunks)


def extract_text(path: Path, mime: str, settings: Settings) -> ExtractionResult:
    """Top-level extractor: PDF → text libraries → OCR if weak; image → OCR if enabled."""
    notes: list[str] = []
    used_ocr = False

    if mime == "application/pdf":
        text, source = extract_text_from_pdf(path)
        if _is_weak(text):
            notes.append("Weak text from PDF libraries; attempting OCR fallback")
            if settings.ocr_enabled:
                ocr_text = _ocr_pdf_pages(path, settings)
                if ocr_text.strip():
                    text, source, used_ocr = ocr_text, "ocr", True
                else:
                    notes.append("OCR did not produce usable text (tesseract missing?)")
            else:
                notes.append("OCR disabled in settings")
        return ExtractionResult(text=text.strip(), source=source, used_ocr=used_ocr, notes=notes)

    if mime in {"image/png", "image/jpeg", "image/jpg"}:
        if not settings.ocr_enabled:
            return ExtractionResult(
                text="",
                source="image",
                used_ocr=False,
                notes=["Image upload received but OCR is disabled"],
            )
        text = _ocr_with_tesseract(path, settings)
        if text.strip():
            return ExtractionResult(text=text.strip(), source="ocr", used_ocr=True, notes=notes)
        return ExtractionResult(
            text="",
            source="image",
            used_ocr=True,
            notes=["Image OCR produced no text (tesseract missing?)"],
        )

    return ExtractionResult(text="", source="empty", used_ocr=False, notes=["Unsupported MIME"])
