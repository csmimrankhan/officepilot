# Clean Windows Install QA

## Prerequisites

- Clean Windows 10/11 user profile
- No OfficePilot previously installed (or fully uninstalled)
- Python 3.11+ (for development mode)
- Node.js 18+ (for frontend dev server)
- Tesseract OCR (optional, for OCR features)

## QA Checklist

### 1. Installation

- [ ] App downloads and extracts without errors
- [ ] Sidecar binary exists at expected path
- [ ] All required DLLs are present
- [ ] No antivirus false positives (expected)

### 2. First Launch

- [ ] Backend starts without errors
- [ ] `GET /api/health` returns 200
- [ ] Sidecar reports online status
- [ ] Database file created at expected path
- [ ] Storage directory created
- [ ] Logs directory created

### 3. First Owner Registration

- [ ] `POST /api/auth/register` returns 200 for first user
- [ ] Role is set to "owner"
- [ ] Access and refresh tokens returned
- [ ] Duplicate email registration returns 400

### 4. Authentication

- [ ] `POST /api/auth/login` returns 200 with valid credentials
- [ ] Wrong password returns 401
- [ ] Protected endpoints return 401 without token
- [ ] Protected endpoints return 200 with valid token
- [ ] Logout returns 200

### 5. Data Persistence

- [ ] Register owner, stop backend, restart backend
- [ ] Login with same credentials still works
- [ ] Previously uploaded invoices still visible

### 6. Demo Mode

- [ ] `DEMO_MODE=true` enables demo mode
- [ ] `GET /api/demo/status` shows active state
- [ ] `POST /api/demo/seed` creates fake invoices
- [ ] `POST /api/demo/reset` removes demo data
- [ ] Demo data clearly labeled as fake

### 7. Invoice Upload

- [ ] Upload sample invoice file
- [ ] Extraction populates vendor, amount, invoice number
- [ ] Status shows "pending" for new uploads
- [ ] File stored at expected path

### 8. Excel Export

- [ ] Approved invoices export to Excel
- [ ] File downloads correctly
- [ ] Exported data matches invoices

### 9. Audit Export

- [ ] JSON export creates valid JSON file
- [ ] CSV export creates valid CSV file
- [ ] Export date filters work

### 10. Backup

- [ ] `POST /api/backup/run-local` returns success
- [ ] `GET /api/backup/status` shows disk info
- [ ] `POST /api/backup/test-restore` completes without errors

### 11. Kill Switch

- [ ] `POST /api/safety/kill-switch` activates
- [ ] Automation status shows blocked services
- [ ] `POST /api/safety/resume-automation` deactivates
- [ ] Kill switch persists after backend restart

### 12. Uninstall

- [ ] App removed without errors
- [ ] Data directory may remain (documented)
- [ ] Clean uninstall leaves no registry entries (if MSI)
- [ ] Reinstall after uninstall works cleanly

## Known Behaviors

- **Data directories are NOT removed on uninstall** — user data is preserved intentionally
- **Sidecar binary** is bundled with the installer; no separate install needed
- **OCR** requires Tesseract to be installed separately; backend runs fine without it
- **Browser automation** requires Playwright + Chromium; backend falls back to dry-run mode
- **First launch may take longer** while the sidecar boots and the database initializes
