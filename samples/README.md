# OfficePilot AI — Sample Files

This directory contains sample data files for use with OfficePilot AI's demo mode.

## Structure

- `invoices/` — Sample invoice text files (5 files)
- `excel/` — Sample CSV export
- `audit/` — Sample audit export JSON
- `workflows/` — Sample workflow recording JSON
- `accounting/` — Sample QuickBooks/Xero sync preview JSON
- `browser/` — Sample browser automation test-form run JSON

## Usage

1. Enable demo mode: `DEMO_MODE=true`
2. Start the backend
3. POST to `/api/demo/seed` to load demo invoice records
4. Use the Demo Mode page in the frontend to load sample data

All files in this directory are clearly labeled as demo/sample data.
They contain no real financial information, PII, or credentials.
