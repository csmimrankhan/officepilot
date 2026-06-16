# Pre-Demo Preparation Checklist for OfficePilot AI

Every item must be checked before any live demo.

## Before Every Demo

| # | Item | Check | Notes |
|---|------|-------|-------|
| 1 | Seed demo data | ☐ | Run app with DEMO_MODE=true or click "Load Sample Data" |
| 2 | Login as owner | ☐ | Register fresh owner account |
| 3 | Verify sidecar is online | ☐ | Check GET /api/health returns "ok": true |
| 4 | Check readiness dashboard | ☐ | Green on all readiness checks |
| 5 | Open sample invoice | ☐ | Verify extraction (vendor, amount, date, tax, line items) |
| 6 | Verify Excel export works | ☐ | Approve invoice, export, confirm .xlsx downloads |
| 7 | Verify QuickBooks/Xero in mock mode | ☐ | Check Accounting Integrations shows mock/sandbox |
| 8 | Verify no real data visible | ☐ | Only demo/sample invoices shown |
| 9 | Verify kill switch works | ☐ | Toggle kill switch on, confirm it engages |
| 10 | Verify feedback button works | ☐ | Click Feedback, submit test feedback |
| 11 | Verify audit log shows actions | ☐ | Check Audit Logs has entries from demo walkthrough |
| 12 | Verify version history shows versions | ☐ | Open Version History for the sample invoice |
| 13 | Verify browser automation is NOT enabled | ☐ | Default should be disabled |
| 14 | Verify screen control is NOT enabled | ☐ | Default permission level should be 0 |
| 15 | Mute notifications | ☐ | Turn off system notifications during demo |
| 16 | Close other apps | ☐ | Close browser tabs, email, other windows |
| 17 | Set screen resolution | ☐ | 1280x800 or higher recommended |
| 18 | Test audio if recording | ☐ | Microphone level, background noise |

## Demo Outline (3-Minute Walkthrough)

1. Landing page → "This is OfficePilot. Invoice automation with approval, audit, and restore."
2. Login → "Register as the first owner."
3. Demo data → "Pre-loaded sample invoices."
4. Open invoice → "The parser extracts vendor, date, amount, line items."
5. Review → "Confidence score, warnings, extracted fields."
6. Approve → "One click. Audit logged immediately."
7. Export to Excel → "Structured export with line items."
8. Accounting preview → "Draft entries for QuickBooks/Xero."
9. Audit log → "Every action timestamped and attributed."
10. Version history → "Full change history with one-click restore."
11. Safety → "Approval gates, kill switch, role permissions."
12. CTA → "Join the pilot. Free during pilot. No credit card."

## Demo Outline (5-Minute Walkthrough)

1. Landing page + value prop (30s)
2. Quick login with existing demo account (15s)
3. Dashboard overview — pending invoices, recent activity (30s)
4. Open sample invoice — parser fields highlighted (30s)
5. Review confidence + warnings (30s)
6. Approve + audit log popup (30s)
7. Excel export — show structured output (30s)
8. Accounting preview — QuickBooks/Xero draft entries (30s)
9. Version history — show versions + restore from earlier version (30s)
10. Safety features — kill switch toggle, role permissions (30s)
11. Feedback button — show how to submit (15s)
12. CTA + pilot sign-up (30s)

## Demo Outline (15-Minute Walkthrough)

1. Landing page + value prop (1m)
2. Register fresh owner account (1m)
3. Browse pre-loaded sample dataset (1m)
4. Open invoice — walk through extraction fields in detail (2m)
5. Review — confidence score breakdown, warnings explanation (1m)
6. Edit extraction — fix a field, show version history capture (1m)
7. Approve — show audit log entry in real time (1m)
8. Excel export — download and inspect line items (1m)
9. Accounting preview — toggle between QuickBooks and Xero (1m)
10. Version history — change timeline, restore previous version (1m)
11. File snapshots — show snapshot list, restore a file (1m)
12. Restore activity log — show every restore action (1m)
13. Safety settings — approval gates, role permissions, kill switch (1m)
14. Audit log — filter by action type, search, export (1m)
15. Browser automation settings — confirm disabled state (30s)
16. Screen control settings — confirm disabled state (30s)
17. Feedback + bug report demo (30s)
18. CTA + pilot waitlist sign-up (30s)

## Voice Intent Demo Flow

If demonstrating voice intents, follow this sequence:

1. "what is on my screen" → Screen context readout
2. "open invoice folder" → File explorer opens to invoices directory
3. "read current window" → OCR reads active window text
4. "stop automation" → Clean stop (not emergency)

Do NOT demonstrate during live demos:
- "emergency stop" (reserved for real incidents)
- Browser automation fill/submit (requires approval flow)
- Accounting sync write operations

## Demo Environment Setup

```bash
# Terminal 1: Start backend
cd backend
set OFFICEPILOT_ENV=development
set DEMO_MODE=true
python -m uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd frontend
npm run dev
```

Open http://localhost:5173/ in browser.

## Common Demo Problems

| Problem | Fix |
|---------|-----|
| Port 8000 in use | Set OFFICEPILOT_AGENT_PORT=8765 |
| Sidecar not starting | Run backend directly with uvicorn |
| Demo data not loading | Set DEMO_MODE=true, restart |
| Excel export fails | Check storage/exports directory exists |
| QuickBooks/Xero shows error | Ensure mock mode (default) |
| Frontend shows blank page | Check Vite dev server is running on :5173 |
| CORS errors in browser console | Backend must allow http://localhost:5173 origin |
| Invoice upload fails | Check file format (PDF/PNG/JPG only) |
| Parser returns empty fields | Verify Tesseract is installed (parser engine 1) or check PaddleOCR model path |
| Health check returns false | Sidecar not running or agent port mismatch |
| Login fails | New demo = register fresh account; login works only for registered users |
| Audit log empty | Ensure you performed actions (approve, reject, upload) before checking |
| Version history empty | Capture requires at least one edit or transition |
| Waitlist API returns 404 | Ensure backend has Phase 20 routers registered |
| Demo reset fails | Stop and restart backend with DEMO_MODE=true |

## Demo Script Readiness Checklist

Before running a scheduled live demo, confirm each of these:

- [ ] Demo environment is isolated (no production data or credentials)
- [ ] Sample invoices are loaded and visible on the dashboard
- [ ] At least one invoice is in "pending_review" status
- [ ] Excel export directory exists and is writable
- [ ] QuickBooks/Xero mock services return valid preview data
- [ ] Audit log contains recent entries from setup walkthrough
- [ ] Version history has at least 2 versions of the sample invoice
- [ ] File snapshots directory exists with at least one snapshot
- [ ] Kill switch toggles on/off without error
- [ ] Browser automation is disabled (policy page confirms)
- [ ] Screen control is disabled (policy page confirms)
- [ ] Feedback modal opens and submits successfully
- [ ] Bug report modal creates a downloadable package
- [ ] Pilot waitlist form accepts a test submission
- [ ] Landing page (/landing.html) renders correctly
- [ ] All nav links in sidebar resolve without 404
- [ ] Role-based nav items visible only to owner account
- [ ] Onboarding checklist shows on first login
- [ ] Diagnostics page reports all 10 components green
- [ ] About page shows correct version and build info

## Demo Environment Safety Rules

- NEVER connect to production QuickBooks/Xero during a demo
- NEVER display real customer invoices or data
- NEVER leave the demo environment open to the internet
- ALWAYS use DEMO_MODE=true for demos
- ALWAYS register a fresh owner account for each demo
- ALWAYS close the demo environment after the session
- ALWAYS verify no real data persisted after demo reset

## Post-Demo

- [ ] Send thank-you email within 24 hours
- [ ] Record pilot qualification score
- [ ] Add notes to Admin Waitlist
- [ ] Schedule follow-up if interested
- [ ] Log feedback in Feedback Inbox
- [ ] Reset demo environment (delete test accounts, clear demo data)
- [ ] Review usage analytics for the demo session
- [ ] Note any questions or objections raised during demo
- [ ] Update demo script with improvements based on feedback
- [ ] Check that no real data was accidentally exposed
