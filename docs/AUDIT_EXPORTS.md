# Audit Exports

## Overview

The Audit Export system allows administrators to create downloadable packages
of all audit-relevant data for compliance and investigation purposes.

## Supported Formats

| Format | Description |
|--------|-------------|
| **JSON** | Structured JSON file with all log types as separate keys |
| **CSV** | Flat CSV file with log_type, field, value columns |
| **ZIP** | ZIP package containing one JSON file per log type |

## Log Types Included

- Audit Logs (`audit_logs`)
- Browser Actions (`browser_actions`)
- Browser Steps (`browser_steps`)
- Accounting Sync Logs (`accounting_sync`)
- Screen Actions (`screen_actions`)
- Screen Sessions (`screen_sessions`)
- Workflow Runs (`workflow_runs`)
- Restore Logs (`restore_logs`)

## How to Export

1. Open the **Audit Export** page.
2. Select the export format (JSON, CSV, or ZIP).
3. Optionally set date range filters.
4. Select which log types to include.
5. Click **Export**.
6. Wait for the export to complete (status: `completed`).
7. Click **Download** to save the file.

## API Endpoints

- `POST /api/audit/export` — Create a new export
- `GET /api/audit/exports` — List all exports
- `GET /api/audit/exports/{id}` — Get export details
- `GET /api/audit/exports/{id}/download` — Download export file
