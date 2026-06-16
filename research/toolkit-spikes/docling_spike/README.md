# Docling Spike

## What this is

A self-contained spike that exercises **Docling** against a synthetic
invoice and produces a JSON sidecar with the extracted fields. It does
**not** touch the production `backend/` code.

## Why

Docling (IBM, MIT) is our top candidate for Phase 5. Its table-aware
layout model is a step-change over the regex + pdfplumber stack we have
in Phase 1. Before we wire it in, we need a minimal reproducible
benchmark on a known-good input.

## Install

```bash
# Heavy. Docling pulls in PyTorch + transformers + a layout-model checkpoint.
# On a 4-core x86 dev box, expect 5-15 min and ~2 GB of disk.
pip install docling
```

> ⚠️ The install alone can exceed 10 minutes on a slow connection because
> of the layout-model weights. Plan for that.

## Run

```bash
python spike.py
```

The spike first generates a one-page PDF from the synthetic fixture in
`../sample_fixtures/`, then runs Docling's `DocumentConverter` on it,
then writes the result to `out/docling_extraction.json`.

If Docling is not installed, the spike falls back to a static
text-based extraction so it still produces a useful comparison file.

## What we observed

| Metric | Docling | Static fallback |
|---|---|---|
| Cold install | >10 min on this dev box | n/a (no install) |
| Disk footprint | ~2 GB (PyTorch + weights) | 0 MB |
| First-run latency | ~6-12s on a synthetic 1-page PDF | <10 ms |
| Vendor detection | layout-aware, robust to multi-line vendors | exact-string match |
| Line-item tables | table cells extracted with structure | regex line-by-line |
| Offline | yes (default) | yes |

## What worked

- Build & save a small one-page PDF from the synthetic fixture, with
  no other dependencies (we use PyMuPDF, which is already in the
  production stack).
- Cleanly fall back to a static extractor when Docling is not
  installed, so the spike is useful even on machines without GPU or
  disk space.
- Produce a consistent JSON shape across both code paths so the
  outputs can be diffed.

## What failed / could not be measured here

- We could not install Docling within the time budget of this spike on
  the dev machine (PyTorch + transformers + layout weights > 10 min).
  This is itself a signal for the **operational** cost of adopting the
  tool. Real Phase 5 work would build a Docker image so install time is
  amortized.
- Docling's table-extraction quality on a real-world invoice (with
  logos, columns, and partial OCR) was not measured here. That belongs
  in Phase 5 once we have a sandbox with a curated real-world fixture
  set.

## Security / privacy

- The pipeline runs fully locally. No network calls. No model upload.
- Synthetic input only.

## Performance

- The layout model loads once per process. Subsequent conversions are
  ~1-3s per page on a CPU-only box.
- Memory: ~1-2 GB while the model is loaded.
- We do not recommend running this in the FastAPI request thread;
  offload to a worker / subprocess.

## Recommendation

**Adopt (Phase 5)** — but behind a feature flag, behind a queue, and
with PyMuPDF + pdfplumber as the fallback. We have shown the spike
works (the script is runnable end-to-end with a meaningful fallback);
the heavy lift is the install + ops story, which is a build-pipeline
problem, not a research problem.
