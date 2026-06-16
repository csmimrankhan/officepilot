# Bug Reporting

## How to Report a Bug

1. Click the "Report Bug" button in the sidebar
2. Enter a title and description
3. Select severity
4. Choose what to include:
   - Recent logs (last 200 lines, redacted)
   - Screenshot (explicit opt-in only)
   - Readiness status
5. Click Submit
6. Download the diagnostic package from the success screen

## Redaction Guarantees
- Passwords and tokens are [REDACTED]
- Email addresses are [REDACTED]
- API keys and secrets are [REDACTED]
- Invoice files are NEVER included
- Screenshots are NEVER included unless you check the box

## Privacy Safety
- No data is sent to external servers
- Packages are stored locally in `data/bug_reports/`
- You control what is included
- You can review the package before sharing

## API Endpoints
- POST /api/bug-reports
- GET /api/bug-reports
- GET /api/bug-reports/{id}
- GET /api/bug-reports/{id}/download
