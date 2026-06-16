# OfficePilot AI — Internal Development Reference

> Detailed phase-by-phase documentation for maintainers.
> See [README.md](../README.md) for the public-facing project overview.

## Layout

```
backend/                            FastAPI + SQLite + SQLAlchemy
├── app/services/                   Business logic, agent, tools
├── app/routers/                    API endpoints
├── app/models/                     SQLAlchemy ORM models
├── app/schemas/                    Pydantic schemas
├── app/workflows/                  LangGraph workflow graphs
├── tests/                          Backend tests
frontend/                           Vite + React + JSX
├── src/pages/                      Route pages
├── src/components/                 Reusable components
├── src/hooks/                      Custom React hooks
├── src/utils/                      Utility functions
├── tests/                          Frontend tests (Vitest)
desktop/tauri/                      Tauri 2 desktop shell (Rust)
├── src-tauri/src/                  Rust source (main, lib, agent, tray)
├── src-tauri/binaries/             Bundled Python sidecar
scripts/                            Build + signing automation
docs/                               Documentation
samples/                            Sample data for evaluation
releases/                           CI-generated release artifacts
```

## Phase History

### Phases 1-9: Foundation
- **1-3**: Invoice upload, parser, trust layer (review, audit, approval, Gmail dry-run)
- **5**: Parser engine adapter (existing / tesseract / paddle)
- **6**: LangGraph workflow orchestration
- **7**: Tauri desktop shell, storage, settings, audit export
- **8**: PyInstaller sidecar binary, Tauri supervisor
- **9**: Installer hardening, code signing, auto-updater

### Phases 10-22: Enterprise & Pilot
- **10**: Version history, file snapshots, restore
- **11**: Sidecar startup UX, boot diagnostics
- **12**: Browser automation (Playwright, allowlist, dry-run)
- **13**: QuickBooks/Xero read-only sync
- **14**: Workflow recording (raw events, replay, approval)
- **15**: Screen control (OCR, click/type, emergency stop)
- **16A**: Real UI automation executor (tesseract, uiautomation, pyautogui)
- **16B**: Enterprise team hardening (roles, permissions, kill switch)
- **17**: Production auth (PBKDF2, JWT), user sessions
- **18**: Demo mode, sample data, onboarding
- **19**: Pilot demo script, feedback, bug reports, usage tracking
- **20**: Public landing page, waitlist, marketing
- **21**: Performance, startup speed, UI polish
- **22**: Demo videos, founder pitch, outreach, FAQ polish

### Phases 23-31: Universal Agent & Excel
- **23**: Universal Voice Accountant Agent, workflow memory
- **24**: AutoPilot tray agent, 4 modes, agent-first dashboard
- **25**: Local folder invoice workflow, Daily_Invoices Excel
- **26**: Chat-first agent UX (ChatGPT-style)
- **27**: Windows voice layer (whisper.cpp)
- **28**: Voice EXE hardening, global shortcuts, model download
- **29**: Automation-first agent refocus (7 tool categories)
- **31**: Real Excel execution, file picker, dry-run, backup

### Phases 32-38: Email, Recorder, Polish
- **32B**: Browser cards in chat timeline
- **33**: Workflow recorder MVP (DB sessions, redaction, skill drafts)
- **34**: Gmail read-only email automation (6 endpoints, 6 tools)
- **34C**: Gmail safety gate (write-block in planner + executor + registry)
- **35**: Desktop update + license foundation (AppRelease, Subscription, FeatureEntitlement)
- **36**: Version consistency (0.36.1), Tauri auto-updater integration
- **37.8C-D**: SVG icons (lucide-react), sidebar polish, admin route fixes
- **38**: Roman Urdu Excel downloads intent detection, file finder

## Key Conventions

- **No emojis in UI** (unless user requests them)
- **No comments in code** (unless explaining "why", not "what")
- **Restore requires a reason string** (validated by modal)
- **Blocklist wins over allowlist** (safety by default-deny)
- **Sensitive values** (password, token, OTP, CVV, PIN, SSN) redacted in all logs

## Testing

```bash
cd backend && python -m pytest -q
cd frontend && npm test -- --run
```

- Backend: ~100 passing tests (12 pre-existing KeyError failures)
- Frontend: 523+ tests (29 files)

## See Also

- [BUILD.md](../BUILD.md) — Full build guide
- [CONTRIBUTING.md](../CONTRIBUTING.md) — Contribution guidelines
- [SECURITY.md](../SECURITY.md) — Security policy
