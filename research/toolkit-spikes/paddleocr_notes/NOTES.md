# PaddleOCR — Notes Only

> Phase 5 candidate. We are **not** shipping a runnable spike in
> Phase 4 because PaddleOCR's install footprint is large
> (~1 GB of model weights) and our Phase 1 stack already ships
> Tesseract (Apache-2.0) for OCR.

## What it is

PaddleOCR (PaddlePaddle, Apache-2.0) is a multi-language OCR
toolkit. It handles printed text, handwriting, tables, formulas,
and layout. It is one of the strongest open-source OCR engines for
noisy / scanned documents.

## License

**Apache-2.0.** Clean, with an explicit patent grant. Safe for
commercial products. See `LICENSE_NOTES.md`.

## Install

```bash
pip install paddleocr paddlepaddle
```

The Python package is small; the model weights are downloaded
on first use (~100-200 MB per language model, more for layout
models). On a 4-core dev box the first run is ~30-60s for the
download + warm-up; subsequent runs are 0.5-2s per page.

## Why we are not adopting it now

We already ship **Tesseract** in the Phase 1 stack:

- Tesseract is Apache-2.0 (same license as PaddleOCR).
- Tesseract is mature, transparent, and small.
- PaddleOCR's main advantage is on **noisy / handwritten** scans.
  Our Phase 3 user base is mostly small businesses with printed
  PDFs and Tesseract already gets >90% of those.

If a future user need emerges — e.g. handwritten receipts, or
faxes, or low-resolution photos of paper invoices — PaddleOCR is
the upgrade path.

## When we *would* adopt it

- A user submits a high-volume of low-quality scans and Tesseract's
  confidence drops below an acceptable threshold.
- We add a "handwritten notes" feature that requires handwriting
  recognition.
- We add a non-Latin script (CJK, Arabic, Cyrillic) where
  Tesseract's quality is materially worse than PaddleOCR's.

When that happens, the rollout is straightforward: PaddleOCR can
replace Tesseract as the OCR backend behind our existing
`app/services/extraction.py` interface, with Tesseract kept as a
fallback for low-memory environments.

## Security / privacy

- The pipeline runs locally. No network calls once the model is
  downloaded.
- The model weights themselves are large binary downloads. We
  recommend pinning the version and verifying SHA-256 on first
  download.

## Performance

- Cold start (first invocation): 5-15s on CPU.
- Steady-state: 0.3-1s per page on CPU for printed text; 1-3s for
  handwriting.
- Memory: ~500 MB-1 GB while the model is loaded.
- GPU optional; CPU is fine for our use case.

## Recommendation

**Adopt, optional (Phase 5).** Keep Tesseract as the default and
add PaddleOCR as a settings option for users who need higher
accuracy on noisy scans. The migration is small and behind the
existing extraction interface.
