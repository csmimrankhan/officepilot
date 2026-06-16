"""OCR-first parser engine (Phase 5).

This engine always goes through OCR — it bypasses the PyMuPDF/pdfplumber
shortcut and rasterises the document first. The motivation:

1. Some invoices are scans of paper documents. The Phase 1 OCR
   fallback only fires when PyMuPDF text is *weak*; the OCR engine
   *always* goes through OCR, which gives us a consistent comparison
   point against Docling and the existing engine.

2. PaddleOCR is the upgrade path noted in Phase 4. We support both
   backends behind a single interface; on a machine with neither
   installed, the engine falls back to the existing Tesseract binary
   if it is on PATH, otherwise it returns an empty :class:`ParsedInvoice`
   with a clear warning.

The engine never breaks Phase 1-3 behavior. If OCR is not available,
it reports a warning and returns an empty parse, leaving the
:class:`app.services.validator` to mark the invoice as
``needs_review`` so it still goes through the human review flow.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..parser import ParsedInvoice, parse_invoice_text
from . import EngineResult, InvoiceParserEngine, ParserConfidence, time_call

logger = logging.getLogger(__name__)


class OCRParserEngine:
    """OCR-first engine. Uses PaddleOCR if installed, else Tesseract.

    Supports PDFs (rasterised then OCR'd) and images (direct OCR).
    """

    name = "ocr"

    _SUPPORTED = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}

    def __init__(self, settings) -> None:
        self._settings = settings
        self._last_confidence: dict = {}
        self._backend: str = "unknown"
        # Parse OCR language configuration. For Tesseract, this is a
        # plus-separated code like "eng+fra+spa". For PaddleOCR, it is
        # a two-letter code like "en", "fr", "es". Empty = English.
        self._tesseract_lang = self._resolve_tesseract_lang()
        self._paddle_lang = self._resolve_paddle_lang()

    def _resolve_tesseract_lang(self) -> str:
        """Resolve Tesseract language parameter from config or default."""
        raw = (self._settings.ocr_languages or "").strip()
        if raw:
            # Accept comma or plus separator, convert to Tesseract plus format
            parts = [p.strip() for p in raw.replace(",", "+").split("+") if p.strip()]
            if parts:
                return "+".join(parts)
        return "eng"

    def _resolve_paddle_lang(self) -> str:
        """Resolve PaddleOCR language code from config or default."""
        raw = (self._settings.ocr_languages or "").strip()
        if raw:
            # Take first language code, convert Tesseract 3-letter to 2-letter if needed
            first = raw.replace(",", "+").split("+")[0].strip()
            _TESS_TO_PADDLE = {
                "eng": "en", "fra": "fr", "fre": "fr",
                "spa": "es", "deu": "de", "ger": "de",
                "ara": "ar", "hin": "hi", "urd": "ur",
                "chi_sim": "ch", "jpn": "ja", "kor": "ko",
            }
            return _TESS_TO_PADDLE.get(first, first)
        return "en"

    # ----------------------------------------------------------- backend selection

    def _detect_backend(self) -> str:
        """Return ``"paddleocr"``, ``"tesseract"``, or ``"unavailable"``."""
        if self._backend and self._backend != "unknown":
            return self._backend
        try:
            import paddleocr  # noqa: F401
            self._backend = "paddleocr"
        except Exception:
            # Probe for tesseract binary.
            try:
                import pytesseract  # noqa: F401
                import shutil

                if shutil.which("tesseract"):
                    self._backend = "tesseract"
                else:
                    self._backend = "unavailable"
            except Exception:
                self._backend = "unavailable"
        return self._backend

    # ----------------------------------------------------------- protocol

    def supports(self, file_type: str) -> bool:
        return (file_type or "").lower() in self._SUPPORTED

    def extract_text(self, file_path: Path, mime_type: str) -> str:
        return self._ocr(file_path, mime_type)

    def extract_structure(self, file_path: Path, mime_type: str) -> EngineResult:
        import time as _time

        notes: list[str] = []
        warnings: list[str] = []
        started = _time.perf_counter()
        text = self._ocr(Path(file_path), mime_type, notes, warnings)
        runtime_ms = (_time.perf_counter() - started) * 1000.0

        backend = self._detect_backend()
        used_ocr = backend != "unavailable"

        parsed, _parse_ms = time_call(parse_invoice_text, text)
        conf = ParserConfidence(
            vendor_name=0.7 if parsed.vendor_name else 0.0,
            invoice_number=0.7 if parsed.invoice_number else 0.0,
            invoice_date=0.7 if parsed.invoice_date else 0.0,
            due_date=0.6 if parsed.due_date else 0.0,
            currency=0.7 if parsed.currency else 0.0,
            subtotal=0.6 if parsed.subtotal is not None else 0.0,
            tax=0.6 if parsed.tax is not None else 0.0,
            total_amount=0.7 if parsed.total_amount is not None else 0.0,
            line_items=0.5 if parsed.line_items else 0.0,
        )
        # OCR-derived parses are slightly less reliable; we mark a
        # note in the result so the benchmark can see the source.
        notes.append(f"ocr_backend={backend}")
        warnings.extend(parsed.warnings)
        if backend == "unavailable":
            warnings.append(
                "OCR engine unavailable: install Tesseract or PaddleOCR to enable the OCR parser"
            )

        self._last_confidence = conf.as_dict()
        return EngineResult(
            parsed=parsed,
            confidence=conf,
            runtime_ms=round(runtime_ms, 2),
            used_ocr=used_ocr,
            text_source=f"ocr:{backend}",
            raw_text=text,
            notes=notes,
            warnings=warnings,
        )

    def extract_invoice_fields(self, file_path: Path, mime_type: str) -> ParsedInvoice:
        return self.extract_structure(file_path, mime_type).parsed

    def confidence_report(self) -> dict:
        return {
            "engine": self.name,
            "backend": self._detect_backend(),
            "per_field": self._last_confidence or {},
        }

    # ----------------------------------------------------------- internals

    def _ocr(self, file_path: Path, mime_type: str, notes: list | None = None, warnings: list | None = None) -> str:
        if notes is None:
            notes = []
        if warnings is None:
            warnings = []

        backend = self._detect_backend()
        if backend == "paddleocr":
            return self._ocr_paddleocr(file_path, mime_type, notes, warnings)
        if backend == "tesseract":
            return self._ocr_tesseract(file_path, mime_type, notes, warnings)
        warnings.append("No OCR backend available")
        return ""

    def _ocr_tesseract(self, file_path: Path, mime_type: str, notes: list, warnings: list) -> str:
        """Reuse the Phase 1 Tesseract path. Rasterise PDF pages if needed.
        Supports multilingual OCR via configurable language codes.
        """
        try:
            import pytesseract
            from PIL import Image
        except Exception as exc:  # pragma: no cover
            warnings.append(f"pytesseract unavailable: {exc}")
            return ""

        lang = self._tesseract_lang
        notes.append(f"tesseract_lang={lang}")

        if mime_type == "application/pdf":
            try:
                import fitz
            except Exception as exc:
                warnings.append(f"PyMuPDF unavailable: {exc}")
                return ""
            chunks: list[str] = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    try:
                        chunks.append(pytesseract.image_to_string(img, lang=lang) or "")
                    except Exception as exc:
                        warnings.append(f"OCR page failed: {exc}")
            return "\n".join(chunks)

        # Image input
        try:
            with Image.open(file_path) as img:
                return pytesseract.image_to_string(img, lang=lang) or ""
        except Exception as exc:
            warnings.append(f"OCR image failed: {exc}")
            return ""

    def _ocr_paddleocr(self, file_path: Path, mime_type: str, notes: list, warnings: list) -> str:
        """PaddleOCR path. We only import the module lazily so that a
        machine without PaddleOCR installed does not pay the import
        cost. Supports multilingual OCR via configurable language code.
        """
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except Exception as exc:
            warnings.append(f"PaddleOCR import failed: {exc}")
            return ""

        lang = self._paddle_lang
        notes.append(f"paddleocr_lang={lang}")
        try:
            ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
            if mime_type == "application/pdf":
                # PaddleOCR takes image paths; rasterise first.
                import fitz
                from PIL import Image
                chunks: list[str] = []
                with fitz.open(file_path) as doc:
                    for i, page in enumerate(doc):
                        pix = page.get_pixmap(dpi=200)
                        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                        tmp = file_path.with_suffix(f".paddle.page{i}.png")
                        try:
                            img.save(tmp)
                            res = ocr.ocr(str(tmp), cls=True)
                            chunks.extend(self._flatten_paddle(res))
                        finally:
                            try:
                                tmp.unlink(missing_ok=True)
                            except Exception:
                                pass
                return "\n".join(chunks)
            res = ocr.ocr(str(file_path), cls=True)
            return "\n".join(self._flatten_paddle(res))
        except Exception as exc:
            warnings.append(f"PaddleOCR failed: {exc}")
            return ""

    @staticmethod
    def _flatten_paddle(res) -> list[str]:
        out: list[str] = []
        if not res:
            return out
        for line in res:
            if line and isinstance(line, list):
                for box in line:
                    try:
                        out.append(box[1][0])
                    except Exception:
                        continue
        return out
