# Pilot Launch Execution Checklist

## Pre-Launch Verification

### 1. Landing Page & CTA
- [ ] **landing.html** loads at `/landing.html` without errors
- [ ] **Landing.jsx** loads at `/welcome` and `/landing` without errors
- [ ] "Join the Early Pilot Program" CTA button is visible in hero section
- [ ] CTA scrolls to waitlist form on click
- [ ] "Learn More" / "View on GitHub" secondary CTA works
- [ ] FAQ section loads all 12 questions with toggle
- [ ] Safety & Trust section shows all 5 badges
- [ ] Demo Walkthrough section renders

### 2. Waitlist Form
- [ ] **Public waitlist** (`POST /api/public/waitlist`) accepts submissions
- [ ] Name (required) and Email (required) fields validated
- [ ] Optional fields: company, role, invoice_volume, current_workflow, interested_features, country, notes
- [ ] Duplicate email returns existing entry (idempotent)
- [ ] Success message shows after submission
- [ ] Fires `POST /api/public/page-event` for analytics (local-only)
- [ ] **Standalone waitlist page** (`Waitlist.jsx`) renders with all fields
- [ ] **Inline waitlist form** (`Landing.jsx`) renders with 4 fields
- [ ] **Static landing waitlist** (`landing.html`) renders with 5 fields

### 3. Demo Data
- [ ] `DEMO_MODE=true` env var enables demo mode
- [ ] `GET /api/demo/status` returns `demo_mode_enabled: true`
- [ ] `POST /api/demo/seed` creates 8 fake invoices
- [ ] Demo invoices use `email_source="demo"` marker
- [ ] Demo invoices have clearly fictional vendor names (Acme Corp, Globex, etc.)
- [ ] Demo audit logs use `actor="demo"` marker
- [ ] `POST /api/demo/reset` removes demo data only (not real data)
- [ ] `GET /api/demo/sample-files` lists sample files
- [ ] Seed is idempotent (re-running doesn't create duplicates)
- [ ] Demo data includes: 8 invoices, 5 audit logs, 1 accounting preview, 1 browser run, 1 workflow recording

### 4. Demo Walkthrough (15-step guided)
- [ ] `GET /api/demo/walkthrough` returns status when not started
- [ ] `POST /api/demo/walkthrough/start` begins walkthrough
- [ ] `POST /api/demo/walkthrough/complete-step` marks a step done
- [ ] `POST /api/demo/walkthrough/skip-step` skips a step
- [ ] `POST /api/demo/walkthrough/reset` resets progress
- [ ] `POST /api/demo/walkthrough/dismiss` dismisses permanently
- [ ] Frontend `DemoWalkthroughPanel` renders as sidebar widget
- [ ] Progress bar updates as steps are completed
- [ ] Unknown step IDs are rejected with 404

### 5. Health & Readiness
- [ ] `GET /api/health` returns `ok: true`
- [ ] Health response includes: version (0.22.0), phase (22), demo_mode, ocr_enabled, gmail_configured, browser_automation_enabled, screen_control_enabled
- [ ] `GET /api/about` returns app info (requires auth)
- [ ] `GET /api/pilot/readiness` returns checklist status (requires auth)
- [ ] `POST /api/pilot/readiness/complete-step` works
- [ ] `POST /api/pilot/readiness/reset` works

### 6. Feedback
- [ ] `POST /api/feedback` accepts submissions (requires auth)
- [ ] Feedback fields: feedback_type, title, message, severity, page_url
- [ ] `GET /api/feedback` lists feedback (owner sees all, user sees own)
- [ ] `PATCH /api/feedback/{id}` updates status/severity (owner only)
- [ ] Frontend `FeedbackModal` opens and submits
- [ ] Invalid feedback_type is rejected with 400

### 7. Bug Reports
- [ ] `POST /api/bug-reports` accepts submissions (requires auth)
- [ ] Bug report fields: title, description, severity, include_logs, include_screenshot, include_readiness
- [ ] `GET /api/bug-reports` lists bug reports
- [ ] `GET /api/bug-reports/{id}/download` returns diagnostic package
- [ ] Diagnostic package redacts sensitive data (passwords, tokens, emails, API keys)
- [ ] Frontend `BugReportModal` opens and submits

### 8. Security & Privacy
- [ ] No external analytics loaded (confirmed: zero external analytics scripts)
- [ ] No banking/payment automation (banking domains blocked by default)
- [ ] No real Gmail credentials required for demo
- [ ] No real QuickBooks/Xero credentials required (mock sandbox available)
- [ ] Browser automation disabled by default
- [ ] Screen control disabled by default (permission_level=0)
- [ ] Demo invoices clearly marked with `email_source="demo"`
- [ ] Demo audit logs clearly marked with `actor="demo"`
- [ ] Bug reports do not include invoice files or screenshots unless user opts in
- [ ] Kill switch can halt all automation
- [ ] All sensitive fields are redacted in logs and previews

### 9. API & Auth
- [ ] `POST /api/public/waitlist` does NOT require auth (public)
- [ ] `POST /api/public/page-event` does NOT require auth (public)
- [ ] `GET /api/admin/waitlist` requires auth (owner/admin)
- [ ] `PATCH /api/admin/waitlist/{id}` requires auth (owner/admin)
- [ ] `GET /api/admin/waitlist/summary` requires auth (owner/admin)
- [ ] `GET /api/admin/waitlist/export.csv` requires auth (owner/admin)
- [ ] Waitlist admin list supports status filter, search, pagination
- [ ] Waitlist admin status update validates against allowed statuses

### 10. Test Suite
- [ ] **Backend tests**: 548 passed (run `python -m pytest -q` in `backend/`)
- [ ] **Frontend tests**: 94 passed (run `npm test -- --run` in `frontend/`)
- [ ] Waitlist tests pass: submit, duplicate, case-insensitive, all-fields, no-auth
- [ ] Demo tests pass: status, seed, idempotent seed, reset, sample-files
- [ ] Feedback tests pass: create, list, update, invalid type
- [ ] Bug report tests pass: create, get, list, redaction
- [ ] Walkthrough tests pass: start, complete, skip, reset, dismiss
- [ ] Readiness tests pass: status, complete, reset
- [ ] Health endpoint tests pass: phase, version, startup_seconds
- [ ] Auth tests pass: register, login, protected routes

## Launch Day Checklist

- [ ] Set `DEMO_MODE=true` in production environment
- [ ] Verify backend starts without errors
- [ ] Verify frontend builds without errors (`npm run build`)
- [ ] Verify landing page loads on production URL
- [ ] Submit a test waitlist entry — confirm it appears in admin dashboard
- [ ] Seed demo data — confirm 8 invoices visible in review queue
- [ ] Approve a demo invoice — confirm audit log entry created
- [ ] Export demo invoice to Excel — confirm download works
- [ ] Submit test feedback — confirm it appears in admin inbox
- [ ] Create test bug report — confirm diagnostic package downloads
- [ ] Verify no error in browser console
- [ ] Verify mobile-responsive landing page layout
- [ ] Confirm all links point to correct URLs
- [ ] Confirm no external network requests to analytics services

## Blockers

| Issue | Status | Notes |
|-------|--------|-------|
| Port 8000 conflict with Docker | Workaround | Set `OFFICEPILOT_AGENT_PORT=8765` |
| Rust toolchain not available | Known | Build installers on Rust-capable machine |
