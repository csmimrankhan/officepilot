# Toolkit Spikes — Phase 4 (Research Only)

> ⚠️ **This is a research deliverable.** No production code is changed. No tool
> listed here is integrated into OfficePilot AI. The goal is to evaluate open
> source toolkits on **paper and in isolated spike scripts** so future phases
> (5-10) can make informed integration decisions.

## Scope

OfficePilot AI is at **Phase 3** (Trust Layer — approval, audit, duplicate
detection, folder organizer). Before starting Phase 5+ work, we need to know
which toolkits are worth adopting, which are too risky, and which to skip.

This phase covers **eight** toolkits, each with a one-page note and (where it
makes sense) a minimal runnable spike that does not touch production code:

| # | Toolkit | Phase target | Has runnable spike |
|---|---------|--------------|--------------------|
| 1 | Docling | Phase 5 | ✅ (fallback) |
| 2 | PaddleOCR | Phase 5 | notes only (heavy) |
| 3 | LangGraph | Phase 6 | ✅ |
| 4 | Browser-Use + Playwright | Phase 8 | ✅ (smoke test) |
| 5 | OpenAdapt | Phase 9 | notes only (no desktop control) |
| 6 | self-operating-computer | Phase 10 | notes only (reference) |
| 7 | Open Interpreter | inspiration | notes only (**AGPL warning**) |
| 8 | TaskWeaver | optional 6/8 | notes only (heavy) |

## Hard rules for this phase

1. **No production code is changed.** Everything lives under `research/`.
2. **No real client data.** Use only the synthetic sample fixtures in
   `sample_fixtures/`. Do not put real invoices in the repo.
3. **No cloud uploads.** All spikes are local-only. Network calls are
   opt-in and disabled by default.
4. **No silent automation.** Spikes are read-only inspectors or generate
   JSON to stdout. They do not write to the production DB or storage.
5. **License discipline.** AGPL-3.0 (Open Interpreter) is treated as
   *inspiration only* unless legal review approves direct integration.
   See `LICENSE_NOTES.md`.

## How to read these notes

For every toolkit we document:

- **Install command** — exact install line(s) we tested or recommend.
- **License** — the SPDX identifier and any commercial implications.
- **Commercial risk** — clear, blunt assessment of "safe", "review needed",
  or "do not use directly".
- **What it does** — one-paragraph description.
- **What worked** — observed on a synthetic invoice (only when we ran a
  spike locally).
- **What failed** — observed on a synthetic invoice (only when we ran a
  spike locally).
- **Use now / later / never** — final call.
- **Integration difficulty** — small / medium / large.
- **Security risk** — what could go wrong if a malicious invoice or web
  page were processed.
- **Performance notes** — memory, model size, latency.
- **Recommendation** — concrete next step (or "do not adopt").

If a spike was **not** runnable on this machine (e.g. Tesseract is missing,
GPU required, large download, license not OK), the "What worked / failed"
fields are explicit about that and we provide the closest possible
static evaluation. We do **not** claim a tool works if it was not
exercised.

## Folder layout

```
research/toolkit-spikes/
├── README.md                       <- this file
├── LICENSE_NOTES.md                <- license-by-license review
├── TOOLKIT_DECISION_MATRIX.md      <- the table
├── .gitignore                      <- ignore spike artifacts
├── sample_fixtures/                <- synthetic invoices used by spikes
│   └── synthetic_invoice.py
├── docling_spike/                  <- ✅ runnable (with fallback)
│   ├── README.md
│   └── spike.py
├── paddleocr_notes/                <- notes only
│   └── NOTES.md
├── langgraph_spike/                <- ✅ runnable
│   ├── README.md
│   └── spike.py
├── browser_use_spike/              <- ✅ runnable (offline smoke test only)
│   ├── README.md
│   └── spike.py
├── openadapt_spike/                <- notes only
│   └── NOTES.md
├── self_operating_computer_notes/  <- notes only
│   └── NOTES.md
├── open_interpreter_notes/         <- notes only (AGPL)
│   └── NOTES.md
└── taskweaver_notes/               <- notes only
    └── NOTES.md
```

## Running the spikes

Each spike folder has its own README with the exact install + run
command. The spikes are designed to be optional — the deliverables
(notes, decision matrix) stand on their own.

If a spike fails to run on your machine, treat it as **data**: the note
in the folder explains why, and the decision matrix still reflects the
best-available information.

## What we explicitly do **not** do

- We do not add Docling/PaddleOCR/LangGraph/Browser-Use/OpenAdapt/Open
  Interpreter/TaskWeaver to `backend/requirements.txt`.
- We do not import these libraries from `app/`.
- We do not change the API contract.
- We do not run a browser automation against a real SaaS.
- We do not capture real screen content.
- We do not install Tesseract or a GPU stack just for spikes.

## See also

- `LICENSE_NOTES.md` — license-by-license review (read this before any
  legal review).
- `TOOLKIT_DECISION_MATRIX.md` — the one-page table.
- `backend/README.md` and `frontend/README.md` — production docs,
  unchanged.
