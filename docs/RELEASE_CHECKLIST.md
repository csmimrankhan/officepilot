# Release Checklist

Use this checklist before tagging a release.

## Pre-Release

- [ ] All backend tests pass: `cd backend && python -m pytest -q`
- [ ] All frontend tests pass: `cd frontend && npm test -- --run`
- [ ] No failing tests (0 failed)
- [ ] No pending migrations (SQLite schema auto-created)

## Build Verification

- [ ] Sidecar binary builds: `cd backend && pyinstaller scripts/officepilot_sidecar.spec --noconfirm`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Tauri builds: `cd desktop/tauri && cargo tauri build` (requires Rust)
- [ ] Installer builds (requires Rust + WiX Toolset + NSIS)
- [ ] Installer code signed (requires certificate)

## Sample Files

- [ ] `samples/invoices/` contains 5+ sample invoice files
- [ ] `samples/excel/` contains CSV export file
- [ ] `samples/audit/` contains JSON audit export
- [ ] `samples/workflows/` contains sample workflow recording
- [ ] `samples/accounting/` contains QuickBooks/Xero preview
- [ ] `samples/browser/` contains browser automation run
- [ ] `samples/README.md` exists

## Documentation

- [ ] `docs/CLEAN_WINDOWS_QA.md` exists
- [ ] `docs/DEMO_MODE.md` exists
- [ ] `docs/ONBOARDING.md` exists
- [ ] `docs/RELEASE_CHECKLIST.md` exists
- [ ] `.env.example` includes all environment variables
- [ ] `AGENTS.md` updated with current phase info

## Demo Mode

- [ ] `DEMO_MODE=true` — demo seed creates fake data
- [ ] `DEMO_MODE=false` — demo endpoints return empty state
- [ ] Sample files listed via `/api/demo/sample-files`
- [ ] Demo data clearly labeled as fake

## Security

- [ ] JWT secret auto-generated if not configured
- [ ] First owner bootstrap works
- [ ] Open registration disabled by default
- [ ] All protected endpoints require Bearer token
- [ ] X-User header removed from all routers

## Clean Install Test

- [ ] Install on clean Windows user profile
- [ ] Launch app
- [ ] Sidecar starts
- [ ] Register first owner
- [ ] Login
- [ ] Load demo data
- [ ] Invoice upload, review, approve
- [ ] Excel export
- [ ] Audit logs
- [ ] Backup
- [ ] Readiness dashboard
- [ ] Kill switch
- [ ] Close/reopen
- [ ] Data persists
- [ ] Uninstall

## Version Bump

- [ ] `backend/app/main.py` — version string updated
- [ ] `frontend/package.json` — version updated
- [ ] `desktop/tauri/src-tauri/Cargo.toml` — version updated (if applicable)
- [ ] `AGENTS.md` — app version updated
- [ ] Git tag created
