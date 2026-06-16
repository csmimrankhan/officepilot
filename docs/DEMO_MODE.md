# Demo Mode

OfficePilot AI includes a safe demo mode that uses only fake/sample data.
No real Gmail, QuickBooks, Xero, or user documents are touched.

## Enabling

Set environment variables:

```env
DEMO_MODE=true
DEMO_SEED_ON_FIRST_RUN=false   # seed automatically on first backend start
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/demo/status` | Returns whether demo mode is active and if data is seeded |
| POST | `/api/demo/seed` | Seeds fake invoices, audit logs, accounting previews, browser runs, workflow recordings |
| POST | `/api/demo/reset` | Removes all demo data (identified by `email_source=demo` or `actor=demo`) |
| GET | `/api/demo/sample-files` | Lists sample files in the `samples/` directory |

## Sample Files

The `samples/` directory contains:

- `samples/invoices/` — 5 sample invoice text files
- `samples/excel/sample_export.csv` — Sample CSV export
- `samples/audit/sample_audit_export.json` — Sample audit export
- `samples/workflows/sample_recording.json` — Sample workflow recording
- `samples/accounting/sample_quickbooks_preview.json` — Sample QuickBooks sync preview
- `samples/browser/sample_test_form_run.json` — Sample browser automation run

## Safety

- Demo data is clearly labeled as fake
- Demo mode never connects to real Gmail/QuickBooks/Xero
- Demo mode never sends emails
- Demo mode never uses real user documents
- Demo mode is safe for public demos
