# Release Readiness Checklist (Phase 21)

## Purpose

Pre-flight checklist for shipping a new version of OfficePilot AI.
Ensures core functionality works before marking a release as ready.

## Checklist Items

| # | Step | Description |
|---|------|-------------|
| 1 | Backend tests pass | All 540+ pytest tests pass |
| 2 | Frontend tests pass | All 94 vitest tests pass |
| 3 | Sidecar builds | PyInstaller bundling succeeds |
| 4 | Desktop app launches | Tauri desktop shell starts |
| 5 | First owner registration | `/register` creates first user |
| 6 | Demo data loads | Demo mode seeds sample invoices |
| 7 | Invoice upload works | Single invoice can be uploaded & parsed |
| 8 | Excel export works | Approved invoices export to .xlsx |
| 9 | Audit export works | Audit log exports as CSV/JSON |
| 10 | Backup works | Local backup/restore functions |
| 11 | Kill switch works | Global automation kill switch engages |
| 12 | Waitlist works | Public waitlist form submits |
| 13 | No external analytics | `EXTERNAL_ANALYTICS_ENABLED` is `false` |
| 14 | No risky automation | All risky automation is disabled by default |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/system/release/checklist` | Get checklist progress |
| POST | `/api/system/release/checklist/complete-step` | Mark step complete |
| POST | `/api/system/release/checklist/reset` | Reset checklist |

## Frontend

Access the Release Readiness page at `/release/readiness` (authenticated).

The page shows:
- Progress bar with completion percentage
- 14 checkable steps
- "Mark Complete" buttons for pending steps
- "Reset All" button with confirmation dialog

## Before Every Release

1. Run `python -m pytest -q` (backend)
2. Run `npm test -- --run` (frontend)
3. Open Release Readiness page
4. Walk through each step manually
5. Mark steps complete as you verify them
6. Confirm all 14 steps are green before shipping
