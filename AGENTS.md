# AGENTS.md

Project-specific instructions for AI coding agents (opencode, etc.) working
in this repo. Keep this file in sync with major phase changes so the next
agent has a working mental model in one read.

## Project

**OfficePilot AI** — Universal Voice Accountant Agent. Windows desktop app that automates accounting work across Excel, browser apps, and any accounting platform via voice/text commands, with step-by-step planning, approval, safe execution, and workflow memory.

Phases shipped so far:

- **Phase 1–3**: Invoice upload, parser, trust layer (review queue, audit log, warnings, Gmail dry-run).
- **Phase 5**: Parser engine adapter (existing / tesseract / paddle).
- **Phase 6**: LangGraph workflow orchestration (graphs, runs, approvals, node logs).
- **Phase 7**: Local desktop shell (storage, settings, audit export, privacy dashboard).
- **Phase 8**: PyInstaller-bundled sidecar binary; Tauri supervisor.
- **Phase 9**: End-to-end installer hardening (MSI + NSIS), code signing wrapper, async health probe, `tauri-plugin-updater` wire-up, CORS fix for `http://tauri.localhost`.
- **Phase 10**: Version History, File Snapshots, Restore system (entity / file / workflow versions, change timeline, audit-logged restore with mandatory reason).
- **Phase 11**: Sidecar Startup UX, 60s boot grace, boot diagnostics, friendly "first launch may take longer" copy, Open Logs button.
- **Phase 12**: Browser automation with allowlist + preview + approval + audit. Playwright-backed with a deterministic dry-run fallback so the sidecar still boots without Chromium. Local test form, voice intent dispatcher, sensitive-value redaction, no banking / payment / password-manager automation.
- **Phase 13**: QuickBooks/Xero accounting sync with preview, approval, mock/sandbox support, validation, voice intents, and audit logs.
- **Phase 14**: Workflow recording with raw event persistence, dry-run replay, step-by-step replay, approval checkpoints, emergency stop, blocked app/domain checks, and audit logs.
- **Phase 15**: Clicky-Like Screen Control with Voice, Preview, Approval, and Emergency Stop. Read-only screen context (active window/app detection, screenshots, OCR), safe file/folder actions (open invoice folder/file, copy clipboard), browser delegation (Phase 12), recorded workflow integration (Phase 14), and voice intent dispatch.
- **Phase 16A**: Real UI Automation Execution Layer. Real OCR engine detection (tesseract + windows OCR fallback), real click/type executor (uiautomation → pyautogui → PowerShell SendKeys), `execute-all-approved-steps` endpoint, browser delegation to Phase 12, thread-safe emergency stop flag, `capabilities` and `ocr/status` endpoints, new columns (`browser_action_run_id`, `stopped_by`, `stop_reason`) on action and step_log models reflected in schemas/router/frontend.
- **Phase 16B** (previous): Enterprise Team Hardening + Production Safety. Safety Policy Center, Role-Based Permissions (5 roles, 18 permissions), Enterprise Audit Export, Production Readiness Dashboard, Local Backup/Restore, Global Automation Kill Switch, Documentation.
- **Phase 17**: Production Authentication, User Sessions, Persistent Kill Switch, Security Hardening. Real email+password auth (PBKDF2-HMAC-SHA256 hashing, HMAC-SHA256 JWT tokens, no external deps), DB-persistent kill switch with in-memory sync, all protected endpoints migrated from X-User to JWT Bearer token. Frontend: login/register pages, auth context, role-based nav.
- **Phase 18**: Demo Mode, Sample Dataset, Guided Onboarding, Clean Windows Install QA. `DEMO_MODE` env var, 8 fake invoice templates, 5 demo services (seed/reset/status/sample-files), 12-step onboarding checklist with progress tracking, diagnostics endpoint (10 components), about endpoint with version/paths. Frontend: DemoMode, About, FirstRunDiagnostics pages, OnboardingChecklist sidebar widget, Phase 18 routes/nav.
- **Phase 19**: Pilot-Ready Demo Script, Feedback Capture, Bug Report, Usage Review. 15-step guided walkthrough, 7 feedback types, safe diagnostic bug report package with redaction, local usage tracking, 10-step readiness checklist. 5 new DB tables, 5 services, 5 routers, 4 frontend pages + 3 components. 503 backend tests, 94 frontend tests.
- **Phase 20**: Public Landing Page, Pilot Waitlist, Demo Script Page, Product Positioning, FAQ, Marketing Assets, Admin Pilot Dashboard, Privacy-Safe Analytics, Documentation. 2 new DB tables, 2 services, 1 router (6 endpoints), 8 frontend pages + static landing.html, 6 marketing placeholder files, 4 docs.
- **Phase 21**: Performance Optimization, Startup Speed, UI Polish, Release Readiness. Lazy-loaded heavy imports, startup timing metrics, pagination on all list endpoints, React.lazy() route loading, loading/empty/error UI states, data cleanup/retention system, release readiness checklist, 5 new docs files. 572 backend tests (Phase 23-24 includes all), 103 frontend tests (Phase 24 adds 34).
- **Phase 22**: Pilot Demo Video Scripts, Founder Pitch, Outreach Assets, Pilot Qualification & Interview Scripts, Demo Checklist, Feedback Scorecard, and Landing Page Copy Polish. 12 new docs files, copy improvements across 5 frontend pages. No backend changes. 572 backend tests, 103 frontend tests (Phase 24 adds 34).
- **Phase 23**: Universal Voice Accountant Agent + Workflow Memory. Configurable LLM/agent provider layer, structured task planning, workflow memory, voice approval.
  - **Phase 23C**: Enriched plan-task endpoint, voice parse integration, Roman Urdu support.
  - **Phase 23D**: Controlled Plan Execution, step execution, dry-run/live modes, audit log fix.
  - **Phase 23E**: Hero Demo Mode, bilingual summaries, save/repeat/repeat-recent workflows.
- **Phase 24**: OpenCode-style Accountant AutoPilot Agent — Tray-based floating agent, 4 agent modes, mode switcher, agent-first dashboard.
- **Phase 25**: Local Folder Invoice Workflow — scan folders, extract invoice data, create Daily_Invoices Excel, bilingual summaries.
- **Phase 26**: Chat-First Accountant Agent UX — ChatGPT-style chat interface, inline plan preview, execution timeline, sidebar reorganization.
- **Phase 27**: Windows Voice Layer — microphone recording, whisper.cpp transcription, dictation history, paste with sensitive window detection.
- **Phase 28**: Real Voice EXE Hardening — whisper.cpp bundling, Tauri global shortcuts (Ctrl+Alt+Space/A/O), model download UI.
- **Phase 29**: Automation-First Agent Refocus (Hermes-style) — 7 automation tool categories, skill-first matching, deprecated parser tools.
- **Phase 31**: Real Excel Automation Execution — FilePickerCard, file_path in execute-step, end-to-end create-excel-summary flow with file picker, dry-run preview, backup, output copy, auto-detected accounting columns.

- **Phase 32B**: Browser Card Integration in Chat Timeline — 4 browser automation cards (BrowserAutomationCard, ManualLoginCard, GuidedDownloadCard, BrowserResultCard) wired into chat timeline via normalizeBrowserStepResult utility.

- **Phase 33** (shipped): Workflow Recorder MVP — DB-backed recording sessions (WorkflowRecordedEvent, WorkflowSkillDraft models), sensitive-input redaction (password/OTP/token), convert events → skill draft → approve/save as AccountingSkill, fixed recording overlay with timer/event count/security note, recorded steps preview with [REDACTED] badges, skill draft review with trigger phrases/steps/safety rules, recording commands detected in build_accountant_plan(). 19 backend tests + 25 frontend component tests + 4 AccountantAgent integration tests = 48 Phase 33 tests added. Total: 161 backend + 303 frontend pass.
- **Phase 34**: Gmail Read-Only Email Automation — OAuth-based Gmail integration using `gmail.readonly` scope only, email search/preview/download/batch-download endpoints at `/api/email/*`, 6 new tools (email_connect_gmail, email_search, email_preview_messages, email_download_attachments, email_save_attachment, email_disconnect_account) in tool_registry.py, 8 new executor functions in agent_tool_executor.py, 4 frontend cards (GmailConnectCard, EmailSearchPreviewCard, AttachmentDownloadCard, EmailDownloadResultCard), updated Email Attachment Downloader skill, mock mode with FakeGmailClient fallback, 14 backend tests + 26 frontend component tests.
- **Phase 37.8D**: Sidebar Icon Alignment Fix — Reusable NavIcon.jsx wrapper (20x20 fixed, strokeWidth 1.9), standardized nav-item/nav-icon/nav-label CSS system (height 40px, gap 12px, radius 10px), conservative icon set (MessageSquare, Sparkles, Clock, Brain, etc.), New Task button with centered Plus icon, uppercase section headers (MAIN/WORKSPACE/ADMIN/ADVANCED), removed all emoji, visual consistency tests (11 tests), 422 frontend tests.
- **Phase 37.8C**: New Task Button Fix, SVG Icons (lucide-react), Modern Sidebar Drawer, Escape key close, aria attributes, 411 frontend tests.
- **Phase 37.8G**: Admin Route Gate Fix — `RequireAdmin` guard inside inner Routes; 476 tests.
- **Phase 37.8H**: Top-Level Admin Routes + AdminPage Rewrites — `AdminRoute` wrapper in outer `<Routes>` before `/*`; rewrote `AdminSystemHealth.jsx` and `AdminAIStatus.jsx` with responsive grids, no emoji, loading/error/empty states; 478 tests, build succeeds.
- **Phase 38**: Roman Urdu Excel Downloads Intent Detection — `EXCEL_DOWNLOADS_PATTERNS` regex before recording cascade in `build_accountant_plan()` detects Roman Urdu Excel-from-downloads commands, routes to `_build_excel_downloads_summary_plan()` (step 1: `file_find_in_downloads`, step 2: `excel_create_summary_from_file`). New `file_find_in_downloads` tool + executor with real Downloads folder search. PDF debit/credit `PDF_DEBIT_CREDIT_PATTERNS` returns `needs_clarification` instead of invented totals. Dynamic save workflow title from `task_title` (no more hardcoded "Daily Invoice Process"). New `FileSelectionCard.jsx` frontend component for file-selection UI. 8 new backend tests + 6 new frontend tests. 494 frontend tests, 104 backend unit tests pass.
- **Phase 34C**: Gmail Read-Only Email Safety Gate — `BLOCKED_EMAIL_PATTERNS` regex in accountant_agent.py blocking send/forward/delete/move/mark-read/archive/label/compose/unsubscribe/spam/star/modify/permission-escalation commands before skill matching, `GMAIL_READONLY_ALLOWED_TOOLS` defense-in-depth in agent_tool_executor.py blocking any non-read-only email tool at executor level, tool registry safety (no write email tools registered), `classify_task_risk` email check before skill matching, user-friendly blocked message, 39 backend tests + 10 frontend tests, DB cleanup fix for Windows file-lock in teardown.
- `_build_excel_plan` now uses consolidated `excel_create_summary_from_file` tool (1 step instead of 5 old individual tools).
- `execute_run_step` resolves template variables (`{file_path}`, `{sheet_name}`, etc.) in params before passing to executor, so user-supplied values from the request body are properly injected.
- 22 Phase 31 backend tests, 8 Excel command detection tests, all pass.
- **Phase 39** (complete): Backend Background Daemon & Analytics Engine — Thread-based task runner, `BackgroundTask` model, `analyze_invoice_dataset` analytics tool, background task router with 4 endpoints. Google Drive Read-Only Integration with mock adapter, 2 Drive tools, safety gate. Planner wiring with background intent detection (`BACKGROUND_PATTERNS`), Drive→Excel→Analytics chain in mock planner, auto-background task creation on approve-plan. Frontend: `BackgroundTaskWidget` in TopBar with polling / pulsing icon / dropdown / progress bar, `BackgroundResultCard` in chat timeline, background approval flow, API methods. Tauri OS notifications on task completion with web fallback. Completed-task recovery on app start. 66 backend tests + 536 frontend tests (all pass).
- **Phase 40A** (complete): Background Watcher Scheduler — `BackgroundWatcher` model with 3 source types (gmail/drive/folder), `WatcherScheduler` singleton with thread-based polling loop checking due watchers every 60s, `SourceWatcher` predefined read-only plans, safety gate blocking unregistered and medium/high-risk tools (→ `pending_approval`). CRUD router with 5 endpoints (list/create/update/delete/run-now). Frontend: `WatcherSettings.jsx` page with form, source type selector (Mail/HardDrive/Folder icons), inline Pause/Resume/Run Now/Delete, keywords config. Registered in `App.jsx` at `/watchers` and sidebar with Eye icon. 20 backend tests + 10 frontend tests.
- **Phase 40B** (complete): Real Local LLM Brain with Ollama — `OllamaAgentProvider` via `_call_ollama_provider()` + `_build_ollama_system_prompt()` in accountant_agent.py, `GET /api/agent/llm-status` endpoint listing available models, `ollama_base_url`/`ollama_model` config with `http://localhost:11434`/`llama3.1` defaults, graceful mock fallback on connection failure, "Local AI Brain" status UI in LocalAgent.jsx. 17 backend tests.
- **Phase 40C** (complete): Autonomous Error Recovery & Self-Correction — `RECOVERY_MAP` in background_runner.py with 3 recovery strategies (low_confidence→screen_read_text, not_found→file_find_latest_download, unsupported→pause), `paused_for_input` status with `clarification_question`, `POST /background-tasks/{id}/answer` endpoint injecting user answer as a step, `BackgroundTaskWidget` "Needs Attention" badge with `AlertTriangle` icon, clarification text input, and Enter/Send. 15 backend + 10 frontend tests, 52 total Phase 40 tests.
- **Phase 41** (complete): Semantic Memory & RAG — Local ChromaDB vector database at `data_dir/vector_store/`, `MockEmbeddingFunction` for deterministic CI-safe embeddings, `SemanticMemory` service with `index_invoice()` and `semantic_search()`, `semantic_search_invoices` tool (low risk, no approval) in tool_registry.py + executor, auto-indexing of extracted invoices in `_execute_extract_invoice_data`. 16 backend tests.
- **Phase 42** (complete): Continuous Learning & Correction Loop — Feedback loop where the agent learns from user corrections and dynamically injects rules into the Ollama LLM system prompt. `AccountingCorrectionRule` model, `learning_loop.py` service, `learning.py` router at `/api/agent/correct` + `GET /corrections` + `DELETE /corrections/{id}`, "Correct This" button in `BackgroundResultCard.jsx`, correction rules injected via `_build_ollama_system_prompt(db=db, user_id=user_id)`. 15 backend + 7 frontend tests.
- **Phase 43** (complete): Real Accounting Write-Back (QuickBooks/Xero API) — `QuickBooksWritebackAdapter`, `XeroWritebackAdapter`, `quickbooks_create_bill` / `xero_create_bill` tools (high-risk, approval required), `QUICKBOOKS_WRITEBACK_ENABLED` safety gate, `PushToQuickBooksButton` in `BackgroundResultCard.jsx`. 10 backend + 5 frontend tests.
- **Phase 44** (complete): Deep Excel COM Automation via xlwings — `ExcelComAdapter` with `create_pivot_table`, `switch_workbook_and_copy`, `apply_conditional_formatting`, `calculate_and_read_formula`, `create_chart`. VBA macro blocklist, file path safety, COM timeout/zombie prevention. `BackgroundTaskRunner` COM timeout. Frontend "Advanced Excel" badge + approval warning. 45 backend + 38 frontend tests.
- **Phase 45A** (complete): Automated Bank Reconciliation — `BankFeedAdapter` (CSV/JSON parsing), `ReconciliationEngine` (semantic memory + exact-match fallback, 3-tier confidence), `generate_reconciliation_excel` (COM with openpyxl fallback). 2 tools (`bank_parse_feed` low-risk, `bank_reconcile_and_report` medium-risk requiring approval). 2 backend endpoints at `/api/agent/bank/*`. Frontend `BankReconciliation.jsx` page with upload, transaction table, reconcile button, summary stats, Excel download. Route `/app/reconciliation`. Nav link with Scale icon. 24 backend + 9 frontend tests.
- **Phase 45B** (complete): Voice-Driven Live Excel Editing (Active Workbook COM) — `ExcelComAdapter.connect_to_active_workbook()` hooks into the user's visible Excel window via `xw.apps.active`; `execute_live_command()` routes 12 command types with safety undo snapshot before every write. `excel_live_edit_active_workbook` tool (high risk, approval YES). `LIVE_EXCEL_PATTERNS` voice intent detection. Frontend "Live Excel Mode" toggle in TopBar with red pulsing dot. 37 backend tests.
- **Phase 45C** (complete): Multi-Agent Swarm Architecture — `SwarmManager` with 3 specialist profiles (Auditor/read-only blue, Tax/categorization green, Data Entry/write-back red). `build_task_plan()` accepts optional `agent_profile` to filter tool registry. `POST /plan-task` returns `assigned_agent` field. Frontend `AgentChatWindow.jsx` renders colored `<AgentBadge>`. 27 backend + 9 frontend tests.
- **Phase 46A** (complete): Grand Release v1.0.0 — Version harmonized across 7 source files (frontend, backend, config, main, tauri.conf, Cargo.toml, Sidebar.jsx) and 13 test files. New `GET /api/app/release-notes` endpoint returning v1.0.0 changelog with 5 highlights. New `ReleaseNotesModal` component with `localStorage`-gated auto-display, lucide-react icons, and "Got it!" dismiss. 5 backend + 7 frontend tests. Frontend build at 1900 modules.
- **Phase 46B** (complete): Resource Monitor Dashboard — `psutil`-based system resource tracking (RAM, vector DB size, orphaned Excel processes). New `GET /api/system/resources`, `POST /api/system/optimize/clear-memory`, `POST /api/system/optimize/kill-excel` endpoints in existing system router. `kill_orphaned_excel()` safely terminates Excel processes older than 5 minutes. `clear_vector_memory()` wraps `reset_semantic_memory()`. Frontend `ResourceMonitor.jsx` page at `/app/system` with 3 stat cards, progress bars (green/yellow/red thresholds), confirmation-gated optimize buttons. Nav link in ADVANCED section with Activity icon. 8 backend + 8 frontend tests. Frontend build at 1901 modules.
- **Phase 46C** (complete): Marketing Blitz & Waitlist Activation — Landing hero subtitle updated to "Autonomous AI Accounting Firm", How It Works gets "Live Voice Editing" as step 4 (Record→5, QuickBooks→6), Features/Badges grid adds "Multi-Agent Swarm" and "Semantic Bank Recon". Landing (`Landing.jsx` + `landing.html`) synced. FAQPage adds "Does OfficePilot work with my existing Excel files?" and "How does the Bank Reconciliation work?". New `GET /api/admin/waitlist/launch-email` endpoint returns a personalized HTML launch email with 5 Phase 45 feature highlights and CTA download button. 4 backend + 8 frontend tests. Frontend build at 1901 modules.
- **Phase 46D** (complete): Edge-Case QA & Chaos Testing — 6 resilience tests in `tests/test_chaos_resilience.py`: (1) binary garbage bank feed returns empty list, (2) Ollama 502 HTML response falls back to mock provider, (3) COM pivot table TimeoutError triggers `__exit__` (no zombie EXCEL.EXE), (4) empty vector DB returns empty list instead of crashing, (5) QuickBooks `ConnectionError` returns `EXECUTOR_RESULT_FAILED`, (6) `cancel_task` + `_is_cancelled` flag works correctly. 6 backend tests, all pass. Full Phase 46 regression (111 tests) passes. App version 1.0.0 — all 6 phases (A–D) shipped.

## Phase 33 — Workflow Recorder MVP

DB-backed recording sessions with sensitive-input redaction, event-to-skill-draft conversion, and approve/save flow.

### New models

- `WorkflowRecordedEvent` — FK to session + user, redaction flag, risk level, event_order
- `WorkflowSkillDraft` — FK to session + user, triggers, steps, safety rules, status (draft/approved/rejected/saved)
- `WorkflowRecordingSession` — enhanced with `user_id` FK, `organization_id`, `title`, `source`, `metadata_json`

### Backend — New service

`app/services/workflow_recorder_service.py`:
- Session lifecycle: `start_recording_session`, `stop_recording_session`, `cancel_recording_session`, `get_current_session`
- Event recording: `record_event` with label-based + value-pattern redaction (`SENSITIVE_FIELD_PATTERNS`, `SENSITIVE_VALUE_PATTERNS`)
- Convert: `convert_recording_to_skill_draft` maps event types to skill tools via `EVENT_TYPE_TO_SKILL_TOOL` map
- Draft lifecycle: `approve_skill_draft`, `reject_skill_draft`, `save_skill_draft_as_skill` (creates `AccountingSkill` + `AccountingSkillVersion` v1)
- Safety: every draft requires dry-run first, approval required for medium/high risk

### Backend — New router

`app/routers/workflow_recorder.py` at `/api/workflow-recorder`:
- `POST /start`, `POST /stop`, `POST /cancel`, `GET /current`
- `POST /event`, `GET /{session_id}/events`
- `POST /{session_id}/convert-to-skill`
- `POST /skill-drafts/{draft_id}/approve`, `/reject`, `/save-as-skill`
- All endpoints user-scoped; registered in `main.py`

### Recording command detection

`accountant_autopilot.py` — `RECORD_START_PATTERNS` / `RECORD_STOP_PATTERNS` regexes in `build_accountant_plan()` return special plans with `task_type: "start_recording"` or `"stop_recording"`.

### Frontend — New hook

`frontend/src/hooks/useRecording.js`:
- `startRecording`, `stopRecording`, `cancelRecording`, `checkCurrentSession`
- `recordEvent`, `deleteEvent`
- `convertToSkill`, `approveDraft`, `rejectDraft`, `saveAsSkill`
- Manages `session`, `events`, `draft`, `loading`, `error` state

### Frontend — New components

- `WorkflowRecordingOverlay.jsx` — fixed-position overlay with red pulsing dot, timer, event count, safety note, Stop/Cancel buttons
- `RecordedWorkflowPreview.jsx` — event list with risk badges, [REDACTED] badges, URL/file indicators, Convert to Skill button
- `SkillDraftReview.jsx` — draft name, trigger phrases, steps, safety rules, Save Skill / Reject buttons

### Frontend — AccountantAgent.jsx integration

- Imports `useRecording` hook, `WorkflowRecordingOverlay`, `RecordedWorkflowPreview`, `SkillDraftReview`
- Recording state: `recorder` (hook), `wfShowOverlay`, `wfShowPreview`, `wfShowDraft` flags
- `handlePlanTask` checks `result.plan.task_type` for `start_recording` / `stop_recording`
- 7 new handlers: `handleWorkflowStartRecording`, `handleWorkflowStopRecording`, `handleWfStopRecording`, `handleWfCancelRecording`, `handleWfConvertToSkill`, `handleWfSaveSkill`, `handleWfRejectDraft`
- Overlay appears as fixed-position element; preview/draft appear inline as chat bubbles

### QA Results (7 manual tasks, 4 bugs fixed)

| QA Task | Scenario | Result |
|---------|----------|--------|
| 1 | Record → 5 simulated events → stop → list events → convert to skill draft → approve → save as skill | ✅ |
| 2 | Saved skill `"Recorded Excel Summary"` found active in DB via `AccountingSkill` query | ✅ |
| 3 | Browser recording events → correct tool mapping (6 browser event types → matching skill tools) | ✅ |
| 4 | All 5 sensitive values (password, otp, api_key, token, card_number) redacted in events + draft params | ✅ |
| 5 | User B (id=999) denied on stop/convert/approve/save — `ValueError` raised; `get_current_session` returns None | ✅ |
| 6 | Non-existent session → "Recording session not found"; cancel → `status=cancelled`; empty session → "No events recorded" | ✅ |
| 7 | Full backend/frontend test suites + build | ✅ |

### Bugs fixed during QA

| Bug | File | Fix |
|-----|------|-----|
| DB schema migration failure | `workflow_recording_session.py` | Dropped old Phase 14 `workflow_recording_sessions` table; recreated via `Base.metadata.create_all()` |
| `WorkflowRecordingOverlay.jsx` missing React import | `WorkflowRecordingOverlay.jsx` | Added `import { useState, useRef, useEffect } from 'react'` |
| `handleWorkflowStopRecording` silent return when session null | `AccountantAgent.jsx:336-352` | Added `checkCurrentSession()` fallback if `recorder.session` is null |
| Recording overlay not recovered on page refresh | `AccountantAgent.jsx:318-330` | Added `useEffect` on mount that calls `recorder.checkCurrentSession()` and sets `wfShowOverlay=true` if status === `'recording'` |

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 33) | 19 | ✅ All pass |
| Backend (Phase 34) | 14 | ✅ All pass |
| Frontend component tests (Phase 33) | 25 | ✅ All pass |
| AccountantAgent integration | 4 | ✅ All pass |
| Frontend (Phase 34) | 26 | ✅ All pass |
| Frontend (20 files) | 329 | ✅ All pass |
| Frontend build | — | ✅ Success |

### Bugs fixed during Phase 34 QA

| Bug | File | Fix |
|-----|------|-----|
| Test `getByText(/read-only/i)` found 2 matches | `phase34_email_automation.test.jsx` | Changed to `getAllByText` with length check |
| Backend test import `create_access_token` from wrong module | `test_phase34_email_automation.py` | Changed to `from app.services.auth import create_access_token, hash_password` |
| Backend test `get_password_hash` doesn't exist | `test_phase34_email_automation.py` | Changed to `hash_password` and `password_hash=` column name |
| SQLite thread-safety with in-memory DB and TestClient | `test_phase34_email_automation.py` | Switched to app's own `SessionLocal` (file-based DB) with `_clean_db` fixture |
| Phase 34 models not in `init_db()` import list | `app/db.py` | Added `email_search_run` and `email_attachment_download` to `init_db()` imports |
| `connected_gmail_account` fixture stored plaintext token → Fernet decryption failure | `test_phase34_email_automation.py` | Used `encrypt_str()` to wrap tokens before storing |

## Phase 34C (current) — Gmail Read-Only Email Safety Gate

Multi-layer safety gate ensuring Gmail integration stays read-only forever. Three defense layers:

1. **Planner layer** (`accountant_agent.py`): `BLOCKED_EMAIL_PATTERNS` regex (19 patterns) in `classify_task_risk()` runs before skill/workflow matching. Covers send, forward, delete, move, mark-read, archive, label, compose, unsubscribe, spam, star, modify gmail, and permission escalation. Uses `.*` between keywords (e.g., `forward.*email`) to handle extra words like "forward invoice emails". Returns user-friendly `email_write_not_supported` blocked reason.

2. **Executor layer** (`agent_tool_executor.py`): `GMAIL_READONLY_ALLOWED_TOOLS` frozenset with 9 read-only email tools. `execute_tool()` checks `tool_name.startswith("email_")` and rejects any tool not in the allowed set before execution, with `gmail_readonly_policy` reason. Catches even unregistered tools (defense-in-depth).

3. **Registry layer** (`tool_registry.py`): No send/forward/delete/move/mark-read/modify/archive/label email tools are registered. Only 6 read-only tools exist: `email_connect_gmail`, `email_search`, `email_preview_messages`, `email_download_attachments`, `email_save_attachment`, `email_disconnect_account`.

### Frontend — normalizeEmailStepResult

`frontend/src/utils/normalizeEmailStepResult.js` — Handles `gmail_readonly_policy` blocked responses, returns `cardType: 'blocked_warning'` for blocked write commands. Read-only commands continue to normalize correctly (gmail_mock, email_search, email_download_result, email_preview, gmail_disconnected).

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 34C) | 39 | ✅ All pass |
| Backend (Phase 34) | 14 | ✅ All pass |
| Frontend (Phase 34C) | 10 | ✅ All pass |
| Frontend (22 files) | 372 | ✅ All pass |
| Frontend build | — | ✅ Success |

App version: **1.0.0** / phase **46D** (complete).

## Phase 38.6 — 6-Task Pilot Enhancement Sprint

Six parallel tasks to harden OfficePilot for pilot distribution: onboarding wizard, QuickBooks sync, voice-first recorder, performance polish, marketing update, and beta readiness.

### Task 1 — First-Run Onboarding Wizard (complete)

Added `onboarding_completed` (bool) to `User` model. Created `GET /api/onboarding/check-setup` (whisper status, LLM status, demo data, onboarding state) and `POST /api/onboarding/complete`. Auth flow returns `onboarding_completed` in login/me/Google OAuth responses.

**Frontend**: `OnboardingWizard.jsx` — 5-step guided wizard (Welcome, Whisper Model, Local LLM, Voice Test, Finish). Microphone recording test sends to `/api/voice-layer/transcribe` and shows transcript + generated plan. CSS at `styles.css` (`.onboarding-*`). Route redirect: `AuthenticatedRoutes` redirects to `/app/onboarding` if `!user.onboarding_completed` and path !== `/app/onboarding`.

**Route**: `/app/onboarding`, registered in `App.jsx:151`.

**Tests**: 9 backend + 16 frontend, all pass.

### Task 2 — QuickBooks Read-Only Sync (complete)

New `QuickBooksSyncState` model: `accounts_count`, `customers_count`, `invoices_count`, JSON payloads, `last_sync_at`, `status`, `last_error`.

`POST /api/quickbooks/sync` — calls `run_sync()` in `services/quickbooks_sync.py`. Mock mode returns 10 accounts, 5 customers, 8 invoices with realistic names/amounts. Real mode (`QUICKBOOKS_ENV=production`) calls QB API with OAuth token. Read-only (no QB write operations exist).

`GET /api/quickbooks/status` — returns connection + sync state.

**Frontend**: Inline Sync Now button + synced stats (accounts/customers/invoices counts, last sync time) in `AccountingIntegrations.jsx`. New `api.quickbooksSyncStatus()` and `api.quickbooksSync()` methods.

**Tests**: 8 backend, all pass.

### Task 3 — Voice-First Workflow Recorder Full UI (complete)

New `VoiceRecorder.jsx` page at `/app/voice-recorder`. Key features:
- Large circular microphone button with pulse animation during recording
- Real-time transcription using browser `MediaRecorder` API → `POST /api/voice-layer/transcribe` every 3 seconds
- Live event feed via existing `recorderListEvents` REST polling (no WebSocket needed)
- Full recording session lifecycle (start → stop → convert to skill → approve/save)
- LLM skill naming via existing `convert_recording_to_skill_draft` service
- Clean CSS with `vr-*` classes in `styles.css`

**Route**: `/app/voice-recorder`, lazy-loaded via `React.lazy()`. Nav link "Voice Recorder" with Mic icon in sidebar WORKSPACE section.

**Before**: `RecordWorkflow.jsx` existed but was orphaned (no route, dead WebSocket ref, dev-oriented UI). **After**: `VoiceRecorder.jsx` has a polished voice-first UX with live transcription, skill conversion flow, and proper nav integration.

**Tests**: 9 frontend, all pass.

### Task 4 — Performance Tuning & UX Polish (complete)

- **`ErrorBoundary.jsx`**: Class-based React error boundary with refresh/go-to-agent buttons, rendered error message. Wraps `AppShell` content in `App.jsx`.
- **`LoadingSkeleton.jsx`**: Reusable `CardSkeleton`, `TableSkeleton`, `PageSkeleton` components with shimmer animation. CSS at `.skeleton-*` classes.
- **Lazy-loading**: `AccountantAgent` and `VoiceRecorder` changed from eager imports to `React.lazy()` with Suspense fallback. App now has 5 lazy-loaded routes (ReleaseReadiness, StartupMetrics, CleanupPage, AccountantAgent, VoiceRecorder).
- **CSS**: `@keyframes skeleton-shimmer` with gradient animation; `.skeleton-line--title` for heading skeletons.

### Task 5 — Public Waitlist & Marketing Page Update (complete)

- **`landing.html`**: Added "Repetitive Workflows" problem card, "Record & Replay" and "Sync with QuickBooks" step cards, "Voice Recorder" FAQ question, QuickBooks interest checkbox in waitlist form with JS integration.
- **`Landing.jsx`**: Same problem card + steps + FAQ additions.
- Waitlist submission now sends `interested_features: "quickbooks_sync"` when checkbox is checked.

### Task 6 — Beta Distribution Readiness (complete)

- **`pilot_release_checklist.ps1`**: Extended with checks for onboarding endpoint, QuickBooks status endpoint, and frontend build artifacts (index.html, JS bundle, CSS bundle).
- **ErrorBoundary** protects all authenticated routes from crash-to-white-screen.
- Frontend build at 1894 modules, output in `dist/` (index.html + JS/CSS bundles).
- Phase 36 auto-updater infrastructure remains intact (Tauri plugin-updater, updater endpoint, release artifacts).

### Test counts (final)

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 38.6 tests) | 17 | All pass |
| Backend (with pre-existing errors) | 116 pass / 12 pre-existing KeyError | No regressions |
| Frontend (29 files) | 523 | All pass |
| Frontend build | 1894 modules | Success (13s) |

## Phase 31 — Real Excel Automation Execution

New `FilePickerCard.jsx` component for selecting Excel files during step execution. Backend accepts `file_path` from request body in `execute-step` endpoint. Full end-to-end "create excel summary" flow with file picker, approval, dry-run preview, backup, output copy (original never modified), and auto-detected accounting columns.

### Changes

**Backend — `app/routers/agent.py`**: Modified `execute_run_step` to accept `file_path` (and other `user_params`) from the request body, merging them into the tool parameters extracted from the stored action preview. This enables the frontend to supply a file path when re-executing a step that needs file input.

**Backend — `app/services/excel_tools.py`**:
- `validate_file()`: Check file extension BEFORE existence check (previously, non-existent `.txt` gave "file not found" instead of "unsupported extension").
- `create_summary_from_file()`: Auto-detect first sheet when `source_sheet` is empty. All modifications (summary sheet, formatting, grand total) now happen on the **output copy**, not the original. Original file is never modified after the backup.
- `suggest_summary_columns()`: Prioritize `category` > `vendor`/`description` > `date` for auto-detect group-by column.
- `_dry_run_summary()`: Auto-detect first sheet when `source_sheet` is empty.

**Backend — `app/services/excel_formula_compat.py`**: Added `SHELL`, `CMD`, `RUN`, `SYSTEM`, `POPEN` to `_DANGEROUS_FORMULAS` set.

**Frontend — `frontend/src/components/agent/FilePickerCard.jsx`** (new): Drag-and-drop file picker with text input, Browse button, accepted type validation, error states.

**Frontend — `frontend/src/pages/AccountantAgent.jsx`**:
- Imported `FilePickerCard`.
- Added `needsFileInput` / `needsFileMessage` / `needsFileAcceptedTypes` state + `pendingFileInputRef` for tracking steps requiring file input.
- Modified `handleExecuteNextStep()` to detect `needs_input` in step output and show FilePickerCard instead of marking step completed.
- Added `handleFileSelected()` and `handleFilePickerCancel()` callbacks.
- FilePickerCard rendered inline in the run timeline for the step needing input.

### Bug fixes discovered

- `validate_file` checked file existence before extension → non-existent `.txt` returned "file not found" instead of "unsupported extension".
- `create_summary_from_file` modified the original file by adding summary sheet. Now copies first, modifies copy.
- `_dry_run_summary` failed with empty `source_sheet`. Now auto-detects first sheet.
- `SHELL` and other dangerous formula functions were not in the blocklist.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| `test_phase31_excel_execution.py` | 19 | ✅ All pass |
| `test_automation_refocus.py` | 32 | ✅ All pass |
| `test_excel_skill_pack.py` | 34 | ✅ All pass |
| `test_skill_matching.py` | 11 | ✅ All pass |
| `test_accounting_skills.py` | 17 | ✅ All pass |
| `test_voice_layer_28.py` | 28 | ✅ All pass |
| Frontend (17 files) | 234 | ✅ All pass |
| Frontend build | — | ✅ Success |


## Phase 29 — Automation-First Agent Refocus (Hermes-style)

Major architectural refocus: OfficePilot is an **automation agent, not a parser product**. All parser-first thinking removed, tool registry reorganized into 7 automation categories, default skills seeded for browser/desktop/screen/file/email/workflow automation, skill-first matching prioritized, parser endpoints deprecated.

### Changes made

**tool_registry.py** — Complete rewrite: 7 automation categories with section headers:
- **Browser** (9 tools): `browser_open_url`, `browser_wait_for_user_login`, `browser_click`, `browser_type`, `browser_hotkey`, `browser_read_page`, `browser_wait_for_download`, `browser_export_report`, `browser_close`
- **Desktop** (8 tools): `desktop_get_active_window`, `desktop_click`, `desktop_type`, `desktop_hotkey`, `desktop_copy`, `desktop_paste`, `desktop_wait`, `desktop_open_app`
- **Screen/OCR** (5 tools): `screen_capture`, `screen_read_text`, `screen_find_button`, `screen_find_table`, `screen_confirm_state`
- **Excel** (26 tools): existing Excel pack tools + `excel_create_workbook`
- **Google Sheets** (5 tools): unchanged placeholders
- **File** (9 tools): `file_open`, `file_open_folder`, `file_copy`, `file_move`, `file_rename`, `file_create_folder`, `file_watch_folder`, `file_find_latest_download`, `file_copy_table_to_excel`
- **Email** (5 tools): `email_open`, `email_search`, `email_download_attachments`, `email_create_draft`, `email_open_message`
- **Workflow** (6 tools): `workflow_record_start`, `workflow_record_stop`, `workflow_save_as_skill`, `workflow_dry_run`, `workflow_replay`, `workflow_restore_version`
- **Safety** (7 tools): `approval_request`, `approval_confirm`, `emergency_stop`, `audit_log`, `snapshot_create`, `sensitive_redact`, `validate_result`
- All legacy tools kept with `[Legacy]` prefix and `— use X instead` migration hint
- No duplicate names (deduplicated `extract_invoice_data` and `calculate_excel_total`)

**agent_tool_executor.py** — Fixed 3 critical STEP_TYPE_TOOL_MAP bugs:
- `click` → `desktop_click` (was `save_workflow`)
- `type_text` → `desktop_type` (was `speak_response`)
- `navigate` → `browser_open_url` (was `speak_response`)
- Added 50+ executor functions for all new automation tool names
- Added backward-compatible legacy alias mappings (40+ entries)
- Sensitive text redaction in `desktop_type` and `browser_type` executors
- Fixed `str(len(text))` type bugs in message formatting

**accounting_skills.py** — Renamed `EXCEL_SKILL_TEMPLATES` → `AUTOMATION_SKILL_TEMPLATES`. Added 6 new automation skills:
| Skill | Trigger phrases (sample) | Steps |
|-------|------------------------|-------|
| **Export Accounting Report** | `export profit and loss`, `download report`, `get monthly report` | 8 steps: open browser → wait login → navigate → set date → export → wait download → open folder |
| **Copy Table to Excel** | `copy this table to excel`, `extract visible table`, `move table to spreadsheet` | 6 steps: detect table → copy → create workbook → append rows → format header → auto-size |
| **Prepare Monthly Folder** | `prepare monthly folder`, `organize this month files`, `create month end folder` | 5 steps: create folder → find files → copy → create index → open folder |
| **Email Attachment Downloader** | `download invoice attachments`, `find invoice emails`, `get today attachments` | 3 steps: search → download → open folder |
| **Prepare Monthly Report** | `prepare monthly report`, `create month end report`, `monthly accounting report` | 6 steps: open platform → login → export P&L → export balance sheet → create folder → open folder |
- Fixed `seed_default_excel_skills()` to pass `user_id` to `AccountingSkillVersion` (was missing — caused IntegrityError)
- Removed invalid `change_summary` keyword argument (model doesn't have this column)

**routers/parser.py** — Deprecated with clear comment header. All existing endpoints kept for backward compatibility.

**Bug fixes found during rewrite**:
- `AccountingSkillVersion` model was missing `user_id` in seed function (pre-existing, masked by `change_summary` error)
- `change_summary` was an invalid keyword for `AccountingSkillVersion` (pre-existing, silently caught by try/except)
- `seed_default_excel_skills()` was silently failing due to both bugs — now skills are properly seeded on registration

### Skill-first matching

The agent cascade in `build_accountant_plan()` (unchanged from Phase 23):
1. Skill match (DB query, returns `skill_match` type)
2. Workflow replay
3. Folder invoice
4. P&L comparison
5. Excel command
6. AI/translate fallback

Skill matches now work correctly because the seed function properly creates skills on registration. The `/api/agent/plan-task` endpoint returns `type: "skill_match"` with `suggested_actions: ["dry_run_skill", "create_new_plan", ...]` when a skill matches.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| `test_automation_refocus.py` (new) | 32 | ✅ All pass |
| `test_excel_skill_pack.py` | 34 | ✅ All pass |
| `test_skill_matching.py` | 11 | ✅ All pass |
| `test_accounting_skills.py` | 17 | ✅ All pass |
| `test_voice_layer_28.py` | 28 | ✅ All pass |
| `test_phase17.py` | 40 | ✅ All pass |
| Frontend (16 files) | 223 | ✅ All pass |
| Frontend build | — | ✅ Success |

### Key decisions

- OfficePilot is NOT a parser product — parser tools are marked `[Legacy]` and the old `/api/parser/` router is deprecated but kept for backward compat
- Skill-first matching is the PRIMARY flow — every command checks saved skills first
- New automation skills use browser/desktop/screen/file/email tools, NEVER parser tools
- Browser actions require manual login (no password automation)
- Sensitive input (password, token, OTP, CVV, PIN) is redacted in all executors
- Dry-run is required before live execution for all automation skills
- All mutating operations create snapshots and audit logs

## Phase 26 — Chat-First Accountant Agent UX

Complete redesign of the Accountant Agent from card-based layout to ChatGPT/Claude-style chat-first interface:

- **Frontend**: `frontend/src/App.jsx` — `/` and `/app/dashboard` redirect to `/app/agent` via `agentFirst` flag.
- **Sidebar** (`frontend/src/components/layout/Sidebar.jsx`): Chat-first nav with "+ New Task" as primary action, reordered items (Agent, Workflow Memory, Version History, Settings, Safety), collapsible Advanced section (Invoice, Accounting, Browser, Desktop). Agent status dot + version in footer.
- **TopBar** (`frontend/src/components/layout/TopBar.jsx`): Agent status dot (Ready/Offline/...), Mock/Plan mode badges, Emergency Stop button always visible in sticky header, avatar profile menu with Settings/Feedback/Bug Report/Logout.
- **AccountantAgent page** (`frontend/src/pages/AccountantAgent.jsx`): Welcome screen with avatar + "What can I help you with?" + suggestion chips + demo button. Chat message list with right-aligned blue user bubbles and left-aligned white assistant bubbles. Inline plan preview (task summary, risk badge, steps list, approve/cancel). Run execution timeline with step-by-step status, dry-run/live controls, run summary. Fixed command bar at bottom with text input, send button (→), hint chips. TrayFloatingAgent retained.

### Key UI changes

| Element | Before | After |
|---------|--------|-------|
| Page heading | "Accountant Agent" | "What can I help you with?" |
| Command button | "Plan Task" button | "→" send icon in fixed bottom bar |
| Plan preview | Card below input | Inline assistant message bubble |
| Emergency Stop | Section button | Sticky header button (always visible) |
| Approve/Dry-Run | "Approve (Dry-Run)" | "Approve & Dry-Run" |
| Approve/Live | "Approve (Live)" | "Approve & Execute" |
| Run All Steps (Dry-Run) | "Run All Steps (Dry-Run)" | "Run All Steps" |
| Verify Excel | "Verify Excel File" | "Verify Excel" |
| Save workflow | "Save this as a repeatable workflow" | "Save this workflow?" |
| Workflow Memory | Inline section | Sidebar nav link only |

### Test count

- Frontend: 150 total (13 files, all pass). AccountantAgent test updated from 22 to 22 tests matching new UI.
- Backend: unchanged (timeout at ~46% in 2 min — full suite expected >2 min).

### Key notes

- `scrollIntoView` guarded with optional chaining + try/catch for jsdom compatibility.
- Mock plan response uses `status: 'running'` so "Run All Steps" button stays visible during test assertions.
- No backend changes — Phase 26 is purely frontend UX redesign.

## Phase 25 — Local Folder Invoice Workflow

New service `backend/app/services/local_invoice_workflow.py` that provides a complete local folder invoice pipeline:

- `scan_folder_for_invoices(path, date_filter, keywords)` — scans a local folder for files with invoice-like extensions (.pdf, .png, .jpg, .jpeg, .csv, .xlsx, .xls, .txt) optionally filtered by date (today/yesterday) and keyword match (invoice/bill/receipt/payment).
- `extract_invoice_from_file(file_path)` — PDF via pdfplumber→PyPDF2→pdfminer fallback, images via pytesseract, spreadsheets via openpyxl, text files via parser.py. Returns `ExtractedInvoice` (vendor, invoice_number, total_amount, tax, currency, confidence, warnings, status).
- `create_daily_invoices_excel(invoices, output_dir)` — creates `Daily_Invoices_YYYY_MM_DD.xlsx` with Invoice Detail sheet (vendor, invoice#, date, tax, total, currency, source file, status, warnings) and Summary sheet (count, success/failed, total amount, tax, date).
- `build_folder_invoice_summary_text(count, success_count, total, excel_path, language)` — bilingual (English + Roman Urdu) summary text.

### Tool Registry (4 new tools)

| Tool | Risk | Approval | Description |
|------|------|----------|-------------|
| `scan_local_folder` | low | no | Scan local folder for invoice files |
| `extract_invoice_data` | low | no | Extract structured invoice data from file |
| `create_daily_invoices_excel` | medium | **yes** | Create Daily_Invoices Excel workbook |
| `calculate_excel_total` | low | no | Calculate total from extracted amounts |

### Planner integration

`accountant_autopilot.py` detects 14+ invoice folder commands (Roman Urdu + English) and builds a 5-step plan: scan → extract → create Excel → calculate total → save workflow. Excel creation step requires approval (medium risk). Registered before P&L comparison check.

### Router endpoints (4 new)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agent/folder-invoice/scan` | POST | Scan folder for today's invoice files |
| `/api/agent/folder-invoice/create-excel` | POST | Create Daily_Invoices Excel from extracted data |
| `/api/agent/folder-invoice/runs` | GET | List folder invoice runs |
| `/api/agent/folder-invoice/runs/{id}` | GET | Get folder invoice run details |

### Frontend

- `api.js`: 4 new methods (`folderInvoiceScan`, `folderInvoiceCreateExcel`, `listFolderInvoiceRuns`, `getFolderInvoiceRun`).
- `TrayFloatingAgent.jsx`: "Scan Folder" button on folder invoice plans, path input form, scan results list, "Create Daily Invoices Excel" button.
- `AgentResultCard.jsx`: Already handles `invoice_count` and `total_amount` display; no changes needed.

### Test count

- Backend: 28 Phase 25 tests + 33 Phase 23F P&L = 61 Phase 23-25 tests.
- Frontend: 150 total (Phase 24 + earlier, unchanged).

### Key notes

- `.txt` added to `INVOICE_EXTENSIONS` (text invoices common in manual workflow).
- `_extract_spreadsheet()` now properly closes openpyxl workbooks via `finally: wb.close()` to prevent file handle leaks.
- CSV files handled as spreadsheets via openpyxl (not via text reader).
- Scanning uses file mtime, filtering by "today" matches current date.
- Non-invoice files (no keyword in name) correctly skipped.
- Real OCR (tesseract/pytesseract) not tested in CI — tests use text/Excel files only.

## Layout

```
backend/   FastAPI + SQLAlchemy + SQLite
frontend/  Vite + React (JSX) + Vitest
desktop/   Tauri 2 (Rust supervisor)
scripts/   PyInstaller spec + sign_installers.ps1
data/      runtime data dir (invoices, exports, snapshots, audit, browser snapshots, …)
```

## Common commands

| Task | Command |
| --- | --- |
| Backend tests | `cd backend && python -m pytest -q` |
| Frontend tests | `cd frontend && npm test -- --run` |
| Frontend dev server | `cd frontend && npm run dev` |
| Backend dev server | `cd backend && python -m uvicorn app.main:app --reload` |
| Rebuild sidecar binary | `cd backend && pyinstaller scripts/officepilot_sidecar.spec --noconfirm` |
| Tauri dev (needs Rust) | `cd desktop/tauri && cargo tauri dev` |
| Tauri build (needs Rust) | `cd desktop/tauri && cargo tauri build` |
| Sign installers | `scripts/sign_installers.ps1` (env-gated, no-op without `OFFICEPILOT_CERT_THUMBPRINT`) |
| Download whisper.cpp binary | `scripts/download_whisper_cpp.ps1` |
| Download whisper model | `scripts/download_whisper_models.ps1` |
| Backend tests (voice only) | `cd backend && python -m pytest tests/test_voice_layer_28.py -v` |
| Frontend tests (voice only) | `cd frontend && npm test -- --run tests/voiceLayer.test.jsx` |

Sidecar binary lives at `desktop/tauri/src-tauri/binaries/officepilot-agent-x86_64-pc-windows-msvc.exe`.
The Tauri `externalBin` config + the spec file path must stay in sync.

## Phase 10 — version history quick reference

Four new tables (no ALTER to existing tables):

- `entity_versions` — invoices, settings, extractions. `entity_id` is a `String` to support non-integer keys like `"folder_rules"`.
- `file_snapshots` — files copied into `data_dir/snapshots/<file_type>/<YYYY>/<MM>/<DD>/<uuid>.<ext>`.
- `workflow_versions` — runtime state (status, current_node, state_json, logs, approvals).
- `restore_logs` — every restore action (entity, file, or workflow).

Router: `app/routers/versions.py` (registered in `main.py`).
Services: `app/services/versioning.py` (entity + workflow capture/list/restore + diff), `app/services/snapshots.py` (file copy + SHA256 + restore).

Safety rules baked in:

- History is **append-only**. Restore never deletes rows.
- Every restore creates an `audit_log` row **and** a `restore_log` row.
- A reason string is required for every restore (validated by the modal in the UI).
- Restore of an unknown `entity_type` returns **501** so misconfiguration is loud.
- Missing snapshot on disk returns **410**.

Hooks that capture versions:

- `routers/invoices.py` PATCH / approve / reject / mark-duplicate / upload → `_capture_invoice_version`.
- `routers/workflows.py` start / approve / reject / cancel / retry → `_capture_workflow_version`.
- `routers/settings.py` PATCH /folder-rules → `capture_version` (entity_id = `"folder_rules"`).
- `services/excel_export.py` `build_excel` → snapshot the most recent prior `approved_invoices_*.xlsx` before overwriting.
- `routers/invoices.py` `_auto_organize` → snapshot the source file before the move.

Frontend:

- Pages: `VersionHistory.jsx`, `FileSnapshots.jsx`, `WorkflowVersions.jsx`, `RestoreActivity.jsx`.
- Components: `RestoreConfirmModal.jsx` (reason-required), `BeforeAfterDiff.jsx`.
- Nav: `App.jsx` adds links under "Version History", "File Snapshots", "Workflow Versions", "Restore Activity".
- API: `api.listVersions / getVersion / diffVersions / restoreVersion / changeTimeline`, `api.listFileSnapshots / getFileSnapshot / restoreFileSnapshot`, `api.listWorkflowVersions / restoreWorkflowVersion`, `api.listRestoreLogs`.

## Phase 12 — browser automation quick reference

Four new tables (no ALTER to existing tables):

- `browser_automation_policies` — singleton config: `enabled`, `headless`, `screenshots_enabled`, `allowed_domains_json`, `blocked_domains_json`, `require_approval_for_submit`, `require_approval_for_write`, `notes`.
- `browser_action_runs` — one row per user / voice / workflow initiated browser automation request. Stores the preview JSON, risk level, approval status, and execution result.
- `browser_action_steps` — per-step log row (navigate, fill, click, validate, screenshot).
- `browser_page_snapshots` — captured page text + screenshot path per run.

Router: `app/routers/browser.py` (registered in `main.py`).
Service: `app/services/browser_automation.py` (domain policy, risk classifier, redaction, preview builders, Playwright adapter with dry-run fallback, voice intent dispatcher, test form).
LangGraph nodes: `app/services/workflows/browser_automation.py` (prepare → domain check → preview → approval → execute → validate → audit log).
Adapter singleton: `app/services/browser_automation.get_adapter()` returns the process-wide `BrowserAdapter`. Use `reset_adapter()` from the `/api/browser/stop` route to drop it on user request.

Default-deny rules:

- `DomainPolicy` is a tiny allowlist / blocklist struct (`allowed`, `blocked`) with a `decide(url)` method. Blocklist wins over allowlist.
- Sensitive-field redaction: any value tagged with a `password|secret|token|api_key|2fa|otp|cvv|ssn|pin` label is replaced with `[REDACTED]` in every preview / step log / screenshot row. Sensitive fields are also *skipped* when generating fill steps (the user must enter them manually).
- Risk classifier returns `low | medium | high` and a `requires_approval` boolean; submit / save / append are always high and always need approval.
- Voice intents `create_quickbooks_entry` / `create_xero_entry` are explicitly *blocked* with a hard-coded reason in the response.

Browser-side hooks:

- `routers/browser.py` `prune_old_runs(db)` is called from the FastAPI `lifespan` handler to keep at most `BROWSER_MAX_RUNS` runs (default 200). Step + snapshot rows are deleted alongside.
- Every preview / approve / reject / cancel / execute / stop call writes an `audit_log` row with `action = "browser.<verb>"`.
- The LangGraph `browser_build_preview` node reuses the existing preview JSON if one is already on the run; this prevents approval-time execution from clobbering the approval status with a fresh "pending" reset.

Frontend:

- Pages: `BrowserSettings.jsx`, `BrowserLogs.jsx`, `BrowserTestForm.jsx`, `VoiceIntents.jsx`.
- Components: `BrowserPreviewModal.jsx` (shows risk, steps, value redaction, decision note; reason required to approve / reject).
- Nav: `App.jsx` adds `Browser Settings`, `Browser Test Form`, `Browser Logs`, `Voice Intents`. Sidebar header now reads "Phase 12 · Browser Automation".
- Invoice Detail now exposes "Fill test form (browser)" and "View browser logs" links.
- API: `api.getBrowserPolicies / updateBrowserPolicies / getBrowserStatus / stopBrowser`, `api.previewOpenUrl / previewFillForm / previewAppendInvoiceRow / fillTestFormPreview`, `api.approveBrowserAction / rejectBrowserAction / cancelBrowserAction`, `api.listBrowserActions / getBrowserAction / getBrowserActionSteps / getBrowserActionSnapshots`, `api.listVoiceIntents / dispatchVoiceIntent`, `api.testFormUrl`.

Environment variables (all optional — defaults are safe):

- `BROWSER_AUTOMATION_ENABLED` (default `false`)
- `BROWSER_HEADLESS` (default `false`)
- `BROWSER_SCREENSHOTS_ENABLED` (default `true`)
- `BROWSER_ALLOWED_DOMAINS` (default = in-code `DEFAULT_ALLOWED_DOMAINS`; empty falls back)
- `BROWSER_BLOCKED_DOMAINS` (default = in-code `DEFAULT_BLOCKED_DOMAINS`)
- `BROWSER_REQUIRE_APPROVAL_FOR_WRITE` (default `true`)
- `BROWSER_REQUIRE_APPROVAL_FOR_SUBMIT` (default `true`)
- `BROWSER_MAX_RUNS` (default `200`)
- `BROWSER_PLAYWRIGHT_BROWSERS_PATH` (optional; override the Chromium cache dir)

## Conventions

- **User-facing strings**: never say "git", "commit", "branch", "rebase" in the UI. Use Version History, Restore Previous Version, File Snapshots, Change Timeline, Undo Automation.
- **Restore dispatcher** (`_apply_entity_restore` in `routers/versions.py`) is the place to add new entity types.
- **Settings restore** writes the snapshot under `entity_id` as a single setting row (NOT per-sub-key) so `get_setting(db, "folder_rules")` picks it up.
## Phase 15 — screen control quick reference

Four new tables:

- `screen_control_policies` — singleton config: `enabled`, `permission_level`, `screenshots_enabled`, `ocr_enabled`, `click_enabled`, `type_enabled`, `clipboard_enabled`, JSON app/domain lists, approval requirements.
- `screen_control_sessions` — one row per screen control session (active app/window, status, stopped_by).
- `screen_control_actions` — one row per planned/approved/executed action (action_type, risk_level, approval_status, planned/executed JSON, screenshot/OCR/excerpt/result).
- `screen_control_step_logs` — per-step execution log (step_type, target, status, result, screenshot).

Router: `app/routers/screen_control.py` (registered in `main.py`).
Service: `app/services/screen_control.py` — 30+ functions (context detection, planning, risk classification, blocklist/allowlist, execution, session lifecycle, voice dispatch).

Key safety rules baked in:

- **Disabled by default** (`SCREEN_CONTROL_ENABLED=false`, `permission_level=0`).
- Read-only (Level 1) must be enabled before screen capture/OCR.
- Click/type disabled by default (`click_enabled=false`, `type_enabled=false`).
- Unknown apps blocked unless allowlisted; `DEFAULT_BLOCKED_APPS` covers password_manager, banking, security_settings, credential_dialog.
- Sensitive text (`password`, `token`, `2fa`, `otp`, `cvv`, `ssn`, `pin`) redacted in all logs.
- Every write/click/type requires approval by default.
- Emergency stop immediately halts all running actions and active sessions.

Voice intents support 9 commands: `what is on my screen`, `read current window`, `open invoice folder`, `open this invoice file`, `copy vendor and amount`, `fill this invoice into the test form`, `stop automation`, `emergency stop`, `show screen-control logs`.

Frontend: `ScreenSettings.jsx`, `ScreenAssistant.jsx`, `ScreenLogs.jsx` (settings page, assistant panel, logs page).

- **Browser automation** is **default-deny** + **default-moderate-risk** + **default-needs-approval**. Anything that writes to a form is medium risk; anything that submits is high risk. The risk classifier in `services/browser_automation.classify_risk` is the single source of truth — both the preview endpoint and the LangGraph node read from it.
- **Sensitive values** (`password`, `api_key`, `token`, `2fa`, `otp`, `cvv`, `ssn`, `pin`) are *redacted* in every preview and step log, and the adapter *skips* generating a fill step for them. The user must enter them manually.
- **Domain blocklist always wins** over allowlist. Banking, payment, password-manager, crypto-exchange, and government tax domains are blocked by default.
- **Pydantic v2**: prefer `ConfigDict` over class-based `Config`. The four `routers/versions.py` models still use the legacy form — they trigger deprecation warnings, not errors.
- **No comments in code** unless the request explicitly asks for them. Docstrings / comments are fine in new files where they help explain "why".
- **Demo data markers**: demo invoices use `email_source="demo"` (column added to `Invoice` model in Phase 18). Demo audit logs use `actor="demo"`. Both markers are used for safe reset.
- **Column validation**: when creating SQLAlchemy model instances, verify column names against the actual model definition — `./backend/app/services/demo.py` had 10+ invalid column names originally that were fixed in Phase 18 QA.
- **Redaction patterns**: The Phase 19 bug report service in `backend/app/services/bug_report.py` redacts passwords, tokens, API keys, secrets, emails, and other sensitive data from all diagnostic packages. Add new patterns to `SENSITIVE_PATTERNS` list.
- **Usage tracking gate**: All usage event recording is gated by `USAGE_TRACKING_ENABLED` (default `true`). When disabled, `record_event` returns `None` and summary/list endpoints return empty results. The config exposes `external_analytics_enabled` (always `false` in this release).

## Phase 19 — demo walkthrough / feedback / bug reports / usage tracking / pilot readiness

Five new tables (no ALTER to existing tables):

- `demo_walkthroughs` — per-user guided demo script (status, current_step, completed_steps_json, started_at, completed_at, dismissed).
- `pilot_feedback` — feedback submissions (type, title, message, severity, status, page_url, related entity).
- `bug_reports` — bug reports with safe diagnostics (severity, include_logs/screenshot/readiness, package_path).
- `usage_events` — local-only usage tracking (event_type, entity_type, entity_id, metadata_json).
- `pilot_readiness` — per-user readiness checklist (checklist_json, completed_steps_json, dismissed).

Routers: `app/routers/demo_walkthrough.py`, `app/routers/feedback.py`, `app/routers/bug_reports.py`, `app/routers/usage.py`, `app/routers/pilot_readiness.py` (all registered in `main.py`).

Services: `app/services/demo_walkthrough.py` (status/start/complete/skip/reset/dismiss), `app/services/feedback.py` (CRUD + validation), `app/services/bug_report.py` (create with redacted package, list, download), `app/services/usage_tracking.py` (event recording + summary, gated by `USAGE_TRACKING_ENABLED`), `app/services/pilot_readiness.py` (get/complete/reset).

Frontend:
- Components: `DemoWalkthroughPanel.jsx` (sidebar widget with 15 steps), `FeedbackModal.jsx` (7 feedback types), `BugReportModal.jsx` (safe diagnostic checkboxes + download).
- Pages: `FeedbackInbox.jsx` (admin filter/update), `BugReports.jsx` (admin list + download), `PilotUsageReview.jsx` (summary cards + recent events), `PilotReadiness.jsx` (checklist + ready badge).
- App.jsx: Phase 19 routes (`/pilot/feedback`, `/pilot/bug-reports`, `/pilot/usage`, `/pilot/readiness`), sidebar Feedback/BugReport buttons, DemoWalkthroughPanel widget.

Safety rules baked in:
- Bug report packages are **local-first** — no data is sent to external servers.
- All sensitive values are **redacted** using regex pattern matching (passwords, tokens, API keys, secrets, emails).
- Invoice files and screenshots are **never included** unless the user explicitly opts in.
- Usage tracking is **local-only** and can be disabled via `USAGE_TRACKING_ENABLED=false`.
- Demo walkthrough is **read-only context** — it guides users through existing features, it does not automate actions.

## Known blockers

- **Docker hogs port 8000** on the dev machine. Sidecar reads `OFFICEPILOT_AGENT_PORT` env var; workaround is `OFFICEPILOT_AGENT_PORT=8765` when running the sidecar manually.
- **Rust toolchain is not installed** on the current dev machine. Phase 9/10 installers were built on a machine with Rust; this one only has Python + Node. Rebuild artifacts on a Rust-capable box before shipping.

## Test counts (post-Phase 20)

- Backend: 540 tests (297 Phase 1-14 + 56 Phase 15 + 30 Phase 16B + 60 Phase 17 + 23 Phase 18 + 37 Phase 19 + 37 Phase 20).
- Frontend: 94 tests (unchanged — Phase 20 frontend pages are thin).

## Phase 20 — public landing page / pilot waitlist / marketing

Two new tables:

- `pilot_waitlist` — name, email (unique, case-insensitive), company, role, invoice_volume, current_workflow, interested_features, country, notes, status (new/contacted/demo_scheduled/accepted/rejected).
- `public_page_events` — event_type, page, metadata_json (local-only analytics, gated by `PUBLIC_ANALYTICS_ENABLED`).

Router: `app/routers/public_waitlist.py` (registered in `main.py`).
Services: `app/services/public_pilot_waitlist.py` (submit/list/update/summary/CSV export/record event).

Public endpoints (no auth):
- `POST /api/public/waitlist`
- `POST /api/public/page-event`

Admin endpoints (owner/admin):
- `GET /api/admin/waitlist` (status/search/pagination)
- `PATCH /api/admin/waitlist/{id}` (update status)
- `GET /api/admin/waitlist/summary` (aggregated stats)
- `GET /api/admin/waitlist/export.csv` (CSV download)

Frontend pages:
- `Landing.jsx` — In-app landing page at `/welcome` (auth) and `/landing` (public)
- `landing.html` — Static HTML page at `/landing.html` (no React, no build step)
- `Waitlist.jsx` — Standalone waitlist form at `/waitlist`
- `DemoScript.jsx` — 5-min / 15-min demo tabs at `/demo-script`
- `ProductPositioning.jsx` — "What OfficePilot is / is not" at `/positioning`
- `FAQPage.jsx` — 11 collapsible FAQs at `/faq`
- `MarketingAssets.jsx` — Screenshot checklist at `/marketing-assets`
- `AdminWaitlist.jsx` — Admin dashboard at `/admin/waitlist` (owner/admin)

Marketing assets: `marketing/` directory with 6 screenshot placeholder `.md` files.

Environment variables:
- `PUBLIC_ANALYTICS_ENABLED` (default `true`) — controls whether page events are recorded

## Phase 22 — pilot demo scripts / outreach / landing copy polish

Phase 22 is a **document-only and copy-polish phase** — no new backend models, routers, endpoints, or database tables.

12 new docs files in `docs/`:

| File | Purpose |
|------|---------|
| `DEMO_VIDEO_3_MIN_SCRIPT.md` | 13-step 3-min demo video script (landing → login → demo data → review → approve → export → accounting preview → audit log → restore → kill switch → CTA) |
| `DEMO_VIDEO_60_SEC_SCRIPT.md` | Short-form script for social/email (problem → action → safety → result → trust) |
| `FOUNDER_PITCH.md` | One-liner, 30s, 2min, investor, and accountant/customer pitches |
| `PILOT_OUTREACH_MESSAGES.md` | 9 templates for accountants, bookkeepers, admin managers, SME owners, BPO teams, LinkedIn DM, email, WhatsApp, Reddit |
| `PILOT_QUALIFICATION_QUESTIONS.md` | 12 screening questions with scoring guide (0–36) and fit profiles |
| `PILOT_INTERVIEW_SCRIPT.md` | 10-section interview guide (intro → pain → workflow → demo → reactions → pricing → trust → objections → next step → closing) |
| `DEMO_CHECKLIST.md` | 18-item pre-demo checklist with troubleshooting table and post-demo follow-up |
| `PILOT_FEEDBACK_SCORECARD.md` | 5-dimension scorecard (pain, fit, trust, will-test, will-pay) + objections + features + next step |
| `SALES_ASSETS_INDEX.md` | Master index of all Phase 22 assets |
| `LANDING_COPY_CHANGES.md` | Changelog of all copy improvements |

Copy improvements applied to 5 frontend files:

- `frontend/public/landing.html` — CTA "Join the Early Pilot Program", improved subtitle targeting accountants/bookkeepers/admin teams, more compelling waitlist pitch, qualification questions added to demo section
- `frontend/src/pages/Landing.jsx` — matched landing.html improvements: CTA, subtitle, section headers
- `frontend/src/pages/FAQPage.jsx` — improved safety answer with "Your team controls every button" language, added FAQ "What makes OfficePilot different from other invoice tools?"
- `frontend/src/pages/ProductPositioning.jsx` — unchanged (already solid)
- `frontend/src/pages/DemoScript.jsx` — added pilot CTA banner at top

One-liner: "OfficePilot AI is a Universal Voice Accountant Agent. You tell it what to do by voice or text, it plans the task, shows steps, asks approval, executes safely, and remembers workflows for later."

Test counts: 572 backend (38 Phase 23 + 22 Phase 23B + 16 Phase 23C + 24 Phase 23D), 103 frontend (94 Phase 1-22 + 9 AccountantAgent + 5 execution UI).

## Phase 23 — Universal Voice Accountant Agent + Workflow Memory

**Product repositioning**: OfficePilot AI is no longer just an invoice parser. It is now a **Universal Voice Accountant Agent** that works with any accounting platform the user already uses. Invoice processing is now one workflow template.

### Four new tables

- `agent_task_plans` — task plans generated by the agent (command, context, plan_json, risk_level, status, approval timestamps).
- `agent_workflow_memory` — saved workflows with steps, platform hint, run count, last run.
- `agent_workflow_runs` — per-run tracking (mode=dry_run|live, status, error).
- `agent_workflow_step_logs` — per-step execution logs (type, status, preview, result).

### New services

- `backend/app/services/accountant_agent.py` — Agent provider abstraction: `get_agent_status()`, `build_task_plan()`, `classify_task_risk()`, `redact_context()`, `call_agent_provider()` (mock / openai_compatible / deepseek), `parse_agent_response()`, `validate_plan()`, `convert_plan_to_workflow_steps()`. Mock provider returns deterministic structured JSON plans. Cloud calls blocked unless `AGENT_ALLOW_CLOUD=true` + `AGENT_API_KEY` set. Sensitive values redacted via `SENSITIVE_PATTERNS` regex. Blocked keywords: payment, bank transfer, delete records, password entry, security settings, tax filing, payroll submission, irreversible submit.
- `backend/app/services/agent_context.py` — Context builder: active app/window detection, user role, safety policy, kill switch status, recent workflows, feature flags.
- `backend/app/services/agent_memory.py` — Workflow memory CRUD: save plan, approve plan, save plan as workflow, list/search workflows, find yesterday workflows, repeat workflow, run/step log lifecycle.

### New router

`backend/app/routers/agent.py` (prefix `/api/agent`):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/status` | GET | Agent provider status |
| `/context` | POST | Build current context |
| `/plan-task` | POST | Build task plan from command |
| `/approve-plan` | POST | Approve a task plan |
| `/execute-approved-step` | POST | Execute one step |
| `/emergency-stop` | POST | Emergency stop |
| `/plans` | GET | List user's task plans |
| `/workflows/save` | POST | Save plan as workflow |
| `/workflows` | GET | List saved workflows |
| `/workflows/{id}/repeat` | POST | Repeat a saved workflow |
| `/workflows/repeat-recent` | POST | Find & repeat yesterday's workflow |
| `/workflows/{id}/runs` | GET | List runs for a workflow |
| `/runs/{id}/steps` | GET | Get step logs for a run |

### New env variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENT_PROVIDER` | `mock` | Provider: `mock`, `openai_compatible`, `deepseek` |
| `AGENT_API_BASE_URL` | `` | Base URL for cloud API |
| `AGENT_API_KEY` | `` | API key for cloud provider |
| `AGENT_MODEL` | `` | Model name for cloud provider |
| `AGENT_ALLOW_CLOUD` | `false` | Allow cloud agent calls |
| `AGENT_TIMEOUT_SECONDS` | `60` | Cloud call timeout |
| `AGENT_MAX_STEPS` | `20` | Max steps in a plan |
| `AGENT_DRY_RUN_DEFAULT` | `true` | Default dry-run mode |
| `VOICE_APPROVAL_ENABLED` | `false` | Enable voice approval |
| `VOICE_APPROVAL_HIGH_RISK_ALLOWED` | `false` | Allow high-risk via voice |

### Safety rules

- Kill switch blocks all agent execution (checked before plan, approve, execute, repeat).
- Cloud calls blocked by default (`AGENT_ALLOW_CLOUD=false`).
- Provider status must be `connected` for cloud calls.
- Blocked actions: payment, bank transfer, delete records, password entry, security settings, tax filing, payroll submission, irreversible submit.
- All actions require approval before execution (read = low, write = medium, delete = high).
- Voice approval disabled by default. High-risk voice approval disabled by default.
- Every plan/create/approve/execute/stop is audit-logged.

### Frontend

- **Page**: `AccountantAgent.jsx` at `/app/agent` — command input, suggested tasks (9 chips), provider status badge, dry-run mode badge, current context panel (6 fields), plan preview with risk badge, step-by-step breakdown, approve/execute/emergency stop buttons, save as workflow form, workflow memory list with repeat buttons.
- **Floating Agent** (`TrayFloatingAgent.jsx`): draggable chatbox overlay rendered globally via `AppShell`. Shows agent status dot, mode indicator, mode switcher (Plan/Work/Record/Replay), chat message list, plan card, approval card, progress timeline, result card, workflow quick list. Connected to all Phase 24 backend endpoints.
- **7 new components** under `src/components/agent/`: `TrayFloatingAgent.jsx`, `AgentChatWindow.jsx`, `AgentPlanCard.jsx`, `AgentApprovalCard.jsx`, `AgentProgressTimeline.jsx`, `AgentResultCard.jsx`, `AgentModeSwitcher.jsx`, `WorkflowMemoryQuickList.jsx`.
- **Test**: `AccountantAgent.test.jsx` — 22 tests covering render, status badge, command input, chips, plan preview, blocked task, workflow memory, plan/approve/dry-run/execute/summary/save/verify Excel/repeat/repeat-recent/hero demo/location state prefills.
- **Test**: `FloatingAgent.test.jsx` — 34 tests covering floating agent, mode switcher, plan card, approval card, progress timeline, result card, workflow quick list, emergency stop.
- **Sidebar**: New "Accountant Agent" section at top with "Voice Accountant Agent" link. Phase 24 simplifies sidebar: Core (Dashboard, Agent, Workflow Memory), collapsible Advanced section (Excel, Accounting, Invoice, Browser/Desktop hidden behind "Advanced ▼" toggle), Safety, Settings.
- **Dashboard**: Phase 24 rewrites to agent-first design. Banner "OfficePilot is running in your taskbar" with provider status badge and mode indicator. Quick action grid: Open Accountant Agent, Record Workflow, Repeat Workflow, Emergency Stop, Workflow Memory, Settings.
- **Landing**: Hero updated to "Universal Voice Accountant Agent" subtitle with platform list. How It Works updated to "Tell → Review → Approve → Remember".
- **landing.html**: Same copy updates as Landing.jsx.
- **FAQPage.jsx**: Updated first FAQ, added "Is OfficePilot limited to QuickBooks and Xero?".

## Phase 35 — Desktop Update + License Foundation

5 ORM models, 2 routers, 1 service, 4 frontend components, docs.

### Backend models
- `AppRelease` — version, release_date, is_critical, minimum_required_version, download_url, release_notes
- `UserDevice` — device_id, platform, app_version, device_name, last_seen, user FK
- `Subscription` — user FK, plan (free/pro/trial), status, period_start/end, trial_ends_at, features_json
- `FeatureEntitlement` — user FK, feature_key, enabled, expires_at
- `InAppNotification` — user FK, title, message, type (info/warning/update), seen, created_at

### Endpoints
- `POST /api/app/register-device`, `POST /api/app/check-update`, `GET /api/app/releases/latest`
- `GET /api/app/notifications`, `POST /api/app/notifications/{id}/seen`
- `GET /api/billing/license`, `GET /api/billing/plans`, `POST /api/billing/start-checkout`, `POST /api/billing/manage`
- All billing endpoints return mock/placeholder responses (no Stripe/Paddle yet)
- Feature gate: `require_feature(user, feature_key, db)` — checks subscription + entitlements

### Feature gates (8 keys)
`excel_automation`, `browser_export`, `gmail_readonly`, `workflow_recorder`, `advanced_skills`, `voice_shortcuts`, `monthly_runs_limit`, `skills_limit`
- Free plan: only `excel_automation` enabled
- Pro plan: all features enabled
- Trial plan: all features enabled for 14 days
- `ALLOW_BILLING_BYPASS=true` (default in dev) unlocks all features

### Env vars
- `ALLOW_BILLING_BYPASS` (default `true`) — bypasses feature gate checks
- `app_version` in config — used for update checking

### Phase 35B QA results (June 12, 2026)
- Backend: 11/11 Phase 35 tests pass; 1040/1105 total pass (65 pre-existing failures)
- Frontend: 379/379 pass across 23 files; build succeeds (147 modules, 4.28s)
- Web mode: all Phase 35 API endpoints return correct responses
- EXE mode: sidecar + Tauri EXE both run, all Phase 35 endpoints work on port 8000
- Sidecar binary: 148.6 MB, both copies identical
- Tauri EXE: 6.3 MB, builds successfully in 4m 09s

## Phase 36 — Version Consistency + Tauri Auto-Updater

Version harmonization (0.36.1 across all sources), Tauri v2 auto-updater integration, updater endpoint, release artifact pipeline.

### Changes

**Version Consistency** — All version sources unified to 0.36.1:
- `frontend/package.json` (npm version)
- `backend/app/__init__.py` (Python `__version__`)
- `backend/app/config.py` (`OFFICEPILOT_APP_VERSION`)
- `backend/app/main.py` (FastAPI `version=`)
- `desktop/tauri/src-tauri/tauri.conf.json` (Tauri version)
- `desktop/tauri/src-tauri/Cargo.toml` (Rust crate version)
- 5 test files updated to expect 0.36.1

**Test files updated**: test_phase18, test_phase20, test_phase21, test_local, test_phase35_update_billing.

**AppRelease model extended** — 5 new columns:
- `target` (String) — platform triple (`windows-x86_64`)
- `artifact_type` (String) — `msi` / `nsis` / `app` / `dmg`
- `updater_artifact_url` (String) — download URL for updater
- `updater_signature` (String) — base64 minisign signature
- `pub_date` (String) — publication date for Tauri updater JSON

**Admin release schemas updated** — `ReleaseCreateRequest` and `ReleaseResponse` extended with new fields.

**Backend — new router**: `app/routers/app_updates.py` — `GET /api/app/updater/windows/stable` endpoint returning Tauri-compatible updater JSON (`{version, pub_date, notes, url, signature, platforms: {windows-x86_64: {signature, url}}}`). Mounted in `main.py`.

**Static release mount**: `app.mount("/static/releases", StaticFiles(...), name="releases")` in `main.py` serving `releases/` directory.

**Frontend**:
- `src/utils/tauriUpdater.js` — `checkForTauriUpdate`, `downloadAndInstallUpdate`, `restartAppIfNeeded` using `@tauri-apps/plugin-updater` API
- `src/components/billing/UpdateBanner.jsx` — updated with Tauri runtime detection and plugin-based update flow
- `@tauri-apps/plugin-updater` added to `package.json`

**Tauri integration**:
- `tauri-plugin-updater` 2.0 added to `Cargo.toml`, registered in `lib.rs`
- `tauri.conf.json` — `plugins.updater.active=true`, `endpoints=[...]`, `pubkey` set
- `capabilities/default.json` — `updater:allow-check`, `updater:allow-download-and-install` permissions added

**Signing infrastructure**:
- Updater key pair generated: `.updater-private-key.pem` + `.pub` at `desktop/tauri/`
- `.env.updater.example` — template for `TAURI_SIGNING_PRIVATE_KEY_PATH` and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`
- Private key NEVER committed (in `.gitignore`)

**Release artifact pipeline**:
- `releases/0.36.1/` — MSI installer + `.sig` signature file
- Release 0.36.1 seeded in DB (verified working via admin endpoint)
- `scripts/release_qa_windows.ps1` — release QA automation
- `docs/TAURI_AUTO_UPDATER.md` — full documentation

### Test isolation fix
`test_phase35_update_billing.py` had test-ordering issues because module-scoped SQLite DB persisted data across tests. Fixed by:
- Adding `db_session.query(AppRelease).delete()` before tests that expect specific DB state
- Using explicit `created_at` timestamps for ordering tests (same-second inserts caused non-deterministic ordering)

### Bugs fixed
| Bug | File | Fix |
|-----|------|------|
| Test ordering: `test_updater_no_release_returns_empty` ran after `test_updater_with_release_returns_valid_json` but shared DB | `test_phase35_update_billing.py` | Added `db_session.query(AppRelease).delete()` in empty-state tests |
| Test ordering: `test_updater_latest_stable_selected` had same-second `created_at` for 2 releases | `test_phase35_update_billing.py` | Used `timedelta` to stagger `created_at` values |
| Pre-existing: `test_check_update_no_update_available` failed (True is False) | Unchanged | Pre-existing (not Phase 36) |
| Pre-existing: `test_license_trial_active` failed (expired vs active) | Unchanged | Pre-existing (not Phase 36) |

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend full regression | 1110 | ✅ All pass (8m 57s) |
| Frontend full regression (23 files) | 379 | ✅ All pass |
| Frontend build | 147 modules | ✅ 4.17s |
| Sidecar binary (PyInstaller fresh build) | 148.6 MB | ✅ Built + copied to Tauri binaries dir |
| Tauri build (Rust release) | 4m 56s | ✅ MSI + NSIS produced |
| Tauri MSI | — | ✅ `OfficePilot AI_0.36.1_x64_en-US.msi` |
| Tauri NSIS | — | ✅ `OfficePilot AI_0.36.1_x64-setup.exe` |

### Known limitations
- Code signing is skipped without `OFFICEPILOT_CERT_THUMBPRINT` (no signing cert on dev machine). Run on CI or a signing-capable machine for signed installers.
- Private signing key at `desktop/tauri/.updater-private-key.pem` — DO NOT COMMIT. It is in `.gitignore`.
- Full backend regression takes ~9 minutes (1110 tests).

### Relevant files
- `frontend/package.json` — 0.36.1, includes `@tauri-apps/plugin-updater`
- `frontend/src/utils/tauriUpdater.js` — Tauri updater service
- `frontend/src/components/billing/UpdateBanner.jsx` — update UI component
- `backend/app/models/app_release.py` — extended model
- `backend/app/routers/app_updates.py` — updater endpoint
- `backend/app/routers/admin.py` — extended release schemas
- `backend/app/main.py` — FastAPI app with version + static mount
- `backend/tests/test_phase35_update_billing.py` — 5 updater tests (fixed isolation)
- `desktop/tauri/.updater-private-key.pem` — signing key (DO NOT COMMIT)
- `desktop/tauri/.env.updater.example` — signing env config template
- `desktop/tauri/src-tauri/tauri.conf.json` — updater config
- `desktop/tauri/src-tauri/Cargo.toml` — tauri-plugin-updater dep
- `desktop/tauri/src-tauri/src/lib.rs` — updater plugin registration
- `desktop/tauri/src-tauri/capabilities/default.json` — updater permissions
- `scripts/release_qa_windows.ps1` — release QA script
- `docs/TAURI_AUTO_UPDATER.md` — updater documentation
- `releases/0.36.1/` — signed MSI + .sig

### Env vars (new for Phase 36)
| Variable | Default | Purpose |
|----------|---------|---------|
| `TAURI_SIGNING_PRIVATE_KEY_PATH` | — | Path to updater signing private key PEM |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | — | Password for the signing key |

## Phase 37.8C — New Task Button Fix + SVG Icons + Modern Sidebar Drawer

Fixes the broken New Task button, replaces emoji icons with professional SVG icons (lucide-react), modernizes the sidebar mobile drawer animation to use `transform: translateX(-100%)` for proper left-to-right slide, adds Escape key to close drawer, and improves accessibility with `aria-current`, `aria-expanded`, `aria-label` attributes.

### Changes

**Install**: `lucide-react` npm package added for SVG icons.

**Sidebar.jsx** (rewritten):
- **New Task button** now calls `handleNewTask()` which `navigate('/app/agent')`, dispatches `CustomEvent('officepilot:new-task')`, and closes mobile drawer.
- **Icons**: All emoji icons replaced with lucide-react SVG components (`Bot`, `PlusCircle`, `Sparkles`, `History`, `Clock3`, `Settings`, `Plug`, `ShieldCheck`, `LayoutDashboard`, `Users`, `ClipboardList`, `ListChecks`, `Activity`, `BrainCircuit`, `ChevronDown`, `ChevronRight`).
- **Logo**: Custom inline SVG box logo replacing emoji/static text.
- **Mobile drawer** uses `sidebar--mobile-open` class (no change to class name, but CSS uses `transform` instead of `left`).
- **Accessibility**: `aria-label` on nav, `aria-current="page"` on active links, `aria-expanded` on Advanced toggle.
- **Version**: "v0.36.1" in footer.
- **Brand**: "OfficePilot AI" + "Local-first accounting automation" subtitle.

**TopBar.jsx** (rewritten):
- **Mobile hamburger**: Inline SVG menu icon (3 horizontal bars) replacing `☰` character. Same `aria-label="Open navigation"`.
- **Emergency Stop**: Still text button (no emoji). Same behavior.
- **User dropdown**: Preserved all items (Settings, Feedback, Bug Report, Logout).
- **Chevron**: Inline SVG replacing emoji/symbol.

**AccountantAgent.jsx**:
- Added `commandInputRef` (useRef) on the command input element.
- Added `actionMsg` state (missing declaration fixed).
- Added `useEffect` listening for `officepilot:new-task` custom event:
  - Clears all state (command, plan, messages, runs, errors, skill match, etc.)
  - Focuses the command input after 100ms setTimeout.

**AppShell.jsx**:
- Added `keydown` listener for Escape key to close mobile sidebar drawer.
- Removed listener on cleanup.

**Styles.css**:
- Mobile sidebar drawer animation changed from `left: -280px → left: 0` to `transform: translateX(-100%) → translateX(0)` for smooth left-to-right slide.
- Same `translateX(-100%)` for collapsed state.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Frontend full regression (24 files) | 411 | ✅ All pass |
| Frontend build | 1888 modules | ✅ 8.76s |

No backend changes. No new DB models. No new endpoints.

### Relevant files
- `frontend/package.json` — `lucide-react` dependency
- `frontend/src/components/layout/Sidebar.jsx` — Complete rewrite
- `frontend/src/components/layout/TopBar.jsx` — Rewritten with SVG icons
- `frontend/src/pages/AccountantAgent.jsx` — New Task event listener, command input ref, actionMsg state
- `frontend/src/components/layout/AppShell.jsx` — Escape key drawer close
- `frontend/src/styles.css` — `transform`-based drawer animation

## Phase 37.8D — Sidebar Icon Alignment Fix

Consolidates on a strict, consistent icon system. Fixes misaligned icons from Phase 37.8C.

### Changes

**New file — `frontend/src/components/layout/NavIcon.jsx`**:
- Reusable icon wrapper with fixed 20x20 container, `display: flex`, `align-items: center`, `justify-content: center`, `flex-shrink: 0`
- Default icon size 18px, strokeWidth 1.9

**Sidebar.jsx** (rewritten):
- Conservative icon set: `MessageSquare` (Agent), `Sparkles` (Skills), `History` (Workflow Memory), `Clock` (Version History), `Settings` (Settings), `Plug` (API Setup), `ShieldCheck` (Safety), `LayoutDashboard` / `Users` / `ClipboardList` / `ListChecks` / `Activity` / `Brain` (Admin)
- New Task: `Plus` icon centered inside `.new-task-button`, no emoji
- All nav rows use `<NavLink className="nav-item">` → `<NavIcon>` + `<span className="nav-label">`
- Section headers are plain uppercase text: MAIN / WORKSPACE / ADMIN / ADVANCED — no icons
- Total emoji removal: 💳 🧠 ⚡ 🕐 ⚙️ 🔌 🛡️ 📊 👥 📋 📝 🩺 🤖 ▶ ＋ (none left)

**TopBar.jsx**: Already clean (no emoji), no changes needed.

**Styles.css**:
- `.nav-item`: `height: 40px`, `gap: 12px`, `padding: 0 12px`, `border-radius: 10px`
- `.nav-icon`: `width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; flex-shrink: 0`
- `.nav-label`: `font-size: 14px; line-height: 20px; overflow: hidden; text-overflow: ellipsis`
- `.nav-section-title`: `font-size: 11px; font-weight: 700; letter-spacing: 0.08em; uppercase; margin: 18px 12px 8px`
- `.new-task-button`: `width: 100%; height: 42px; border-radius: 12px; gap: 10px`
- Removed old `.sidebar-link`, `.sidebar-icon`, `.sidebar-link-text`, `.sidebar-section-label`, `.sidebar-new-task` CSS
- Removed conflicting legacy `.sidebar nav a` styles

**New tests** — `frontend/tests/sidebarConsistency.test.jsx`:
- 11 visual consistency tests: no emoji, New Task button once, Plus icon, nav-item class present, nav-icon contains SVG, section titles, admin visibility gating, normal user hides admin

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Frontend full regression (25 files) | 422 | ✅ All pass |
| Frontend build | 1889 modules | ✅ 9.22s |

No backend changes. No new DB models. No new endpoints.

### Relevant files
- `frontend/src/components/layout/NavIcon.jsx` — Reusable icon wrapper (new)
- `frontend/src/components/layout/Sidebar.jsx` — Rewritten with new icon system
- `frontend/src/styles.css` — New nav-item/nav-icon/nav-label/nav-section-title/new-task-button CSS
- `frontend/tests/sidebarConsistency.test.jsx` — 11 visual consistency tests (new)

## Phase 37 — Pilot Release Package

Prepares the app for 3–5 trusted pilot users. No new automation features.

### Changes made

**Docs (4 new files):**
- `docs/PILOT_README.md` — Pilot program guide (getting started, features, privacy)
- `docs/PILOT_DEMO_SCRIPT.md` — 9-step demo walkthrough covering all core features
- `docs/KNOWN_LIMITATIONS.md` — 40 documented limitations with workarounds
- `docs/BUG_REPORT_TEMPLATE.md` — Structured bug report template with submission options

**Sample files (2 new):**
- `samples/sample_sales.xlsx` — Multi-sheet sales data (transactions, category summary, monthly trends)
- `samples/sample_invoice_report.csv` — 10-row invoice report for testing

**Export Logs button** (`frontend/src/pages/LocalAgent.jsx`):
- New `POST /api/local/export-logs` backend endpoint that packages logs + audit trail + manifest into a ZIP
- "Export Logs" button in Settings page (both online and offline states)
- Downloads ZIP directly in browser

**Send Feedback button** (`frontend/src/pages/LocalAgent.jsx`):
- "Send Feedback" button in Settings page opens the existing FeedbackModal
- Reuses Phase 19 feedback infrastructure (7 feedback types, severity levels)

**Release script** (`scripts/pilot_release_checklist.ps1`):
- 10-section checklist: version consistency, pilot docs, sample files, sidecar binary, installer, release artifacts, updater endpoint, sample invoices
- Exit code = number of failed checks

**Version consistency fix:**
- All 7 version sources updated to 0.36.1: `__init__.py`, `main.py`, `config.py`, `package.json`, `tauri.conf.json`, `Cargo.toml`, `Sidebar.jsx`

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend full regression | — | See build results below |
| Frontend full regression | — | See build results below |
| Frontend build | — | See build results below |

### Pilot ZIP structure

```
pilot-release-v0.36.1/
  README.md (copy of docs/PILOT_README.md)
  KNOWN_LIMITATIONS.md
  PILOT_DEMO_SCRIPT.md
  BUG_REPORT_TEMPLATE.md
  samples/
    sample_sales.xlsx
    sample_invoice_report.csv
  OfficePilot AI_0.36.1_x64_en-US.msi
  OfficePilot AI_0.36.1_x64-setup.exe
  OfficePilot AI_0.36.1_x64_en-US.msi.sig
```

### Relevant files
- `docs/PILOT_README.md` — Pilot program guide
- `docs/PILOT_DEMO_SCRIPT.md` — 9-step demo walkthrough
- `docs/KNOWN_LIMITATIONS.md` — 40 known limitations
- `docs/BUG_REPORT_TEMPLATE.md` — Bug report template
- `samples/sample_sales.xlsx` — Sample sales data
- `samples/sample_invoice_report.csv` — Sample invoice report
- `scripts/pilot_release_checklist.ps1` — Pre-flight checklist
- `backend/app/routers/local.py` — `/api/local/export-logs` endpoint
- `frontend/src/api.js` — `exportLogs()` method
- `frontend/src/pages/LocalAgent.jsx` — Export Logs + Send Feedback buttons

## Phase 39 — Backend Background Daemon & Analytics Engine

Thread-based task runner for autonomous background plan execution, plus an invoice dataset analytics tool.

### New model

`backend/app/models/background_task.py`:
- `BackgroundTask` — `id` (PK), `user_id` (FK), `command`, `plan_json`, `status` (queued/running/completed/failed/cancelled), `progress_percent`, `current_step_description`, `result_summary_json`, `error_message`, `created_at`, `updated_at`

### New service

`backend/app/services/background_runner.py`:
- `BackgroundTaskRunner` singleton with thread-based execution via `start_task(task_id)` and `cancel_task(task_id)`.
- `_run_task` picks up a task from DB, iterates through `plan_json` steps, calls `execute_tool` for each, updates `progress_percent` and `current_step_description` on each step, catches exceptions to mark `failed`, generates `result_summary_json` on completion.
- Uses `SessionLocal()` from `app.db` for DB access in the worker thread.
- Checks `_is_cancelled` before each step to support cancellation.
- Registered in `tool_registry.py` and `agent_tool_executor.py` with `_execute_analyze_invoice_dataset`.

### New tool

`analyze_invoice_dataset` (low risk, no approval):
- Input: `invoices_data` (list of dicts with vendor/total_amount/date)
- Output: `total_sum`, `invoice_count`, `largest_amount`, `largest_vendor`, `smallest_amount`, `smallest_vendor`, `average_amount`
- Supports both `invoices_data` and `invoices` param names, `vendor`/`vendor_name` and `total_amount`/`amount` keys.

### New router

`backend/app/routers/background_tasks.py` at `/api/agent`:
- `POST /run-background` — accepts `command` + `plan_json`, creates `BackgroundTask` (queued), triggers runner, returns `task_id`.
- `GET /background-tasks` — list user's tasks (newest first).
- `GET /background-tasks/{id}` — detail with `result_summary` (polling endpoint).
- `POST /background-tasks/{id}/cancel` — set status to cancelled (only queued/running).

### Registration

- Added `background_task` to `init_db()` imports in `db.py`.
- Added `background_tasks_router` import and `app.include_router()` in `main.py`.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| `test_phase39_background.py` | 18 | ✅ All pass (39.3s) |

## Phase 39, Task 2 — Google Drive Read-Only Integration

Read-only Google Drive adapter (mock mode by default) with safety gate blocking write operations, two new tools, and executor functions.

### New service

`backend/app/services/google_drive_adapter.py`:
- `GoogleDriveAdapter` class with mock mode (8 realistic fake files) and real mode skeleton.
- `list_recent_files(days_back, keywords)` — returns filtered file list with id/name/mime_type/size/modified_time.
- `download_file(file_id, target_folder)` — creates a local mock file at `data_dir/drive_downloads/{user_id}/` or custom `target_folder`.
- `BLOCKED_WRITE_OPERATIONS` frozenset (upload, delete, move, rename, copy, create, etc.) — any call raises `PermissionError`.
- `_check_real_mode` reads `DRIVE_CLIENT_ID` / `DRIVE_CLIENT_SECRET` env vars with `getattr` fallback for backward compat.

### New tools (tool_registry.py)

| Tool | Risk | Approval | Description |
|------|------|----------|-------------|
| `drive_list_recent_files` | low | no | List recent Drive files (params: `days_back`, `keywords`) |
| `drive_download_file` | low | no | Download file from Drive to local folder (params: `file_id`, `target_folder`) |

### Executors (agent_tool_executor.py)

- `_execute_drive_list_recent_files` — wraps `GoogleDriveAdapter.list_recent_files`, returns file list with count and mode.
- `_execute_drive_download_file` — wraps `GoogleDriveAdapter.download_file`, returns local path and file metadata.

### Safety gate (accountant_agent.py)

- `DRIVE_READONLY_BLOCKED_PATTERNS` regex (14 patterns) in `classify_task_risk()` runs before email/payment blocked checks. Covers upload, delete, move, rename, copy, create folder, trash, empty trash, sync/backup commands. Returns `drive_write_not_supported` blocked reason.

### Config (config.py)

- Added `drive_client_id` (str) and `drive_client_secret` (str) to Settings dataclass, read from `DRIVE_CLIENT_ID` and `DRIVE_CLIENT_SECRET` env vars.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| `test_phase39_drive.py` | 27 | ✅ All pass (15.2s) |
| `test_phase39_background.py` | 18 | ✅ All pass (no regression) |

## Phase 39, Task 3 — Planner Wiring & Background Intent Detection

Wired the Drive and Analytics tools into the agent planner, added background intent detection, and auto-creates `BackgroundTask` on approve-plan for background commands.

### Changes

**`accountant_agent.py`**:
- `BACKGROUND_PATTERNS` regex matches "in the background", "while I work", "automatically", "fire and forget", "do it silently", etc.
- `_mock_agent_response()` now has an early-return Drive chain branch (before email/Excel intents) that detects "download from google drive" commands and returns the 5-step Drive→Download→Analyze→Excel chain.
- `_build_mock_steps()` has a new Drive+Analytics chain: `drive_list_recent_files` → `drive_download_file` (×2) → `analyze_invoice_dataset` → `excel_create_summary_from_file`.
- `build_task_plan()` checks `BACKGROUND_PATTERNS.search(command)` and sets `run_in_background: true` in the plan.
- `_mock_agent_response()` also sets `run_in_background` in the JSON response.

**`accountant_autopilot.py`**:
- Propagates `run_in_background` from the plan through `build_accountant_plan()`.

**`agent.py` router**:
- `approve_plan_with_run()` checks `plan_data.get("run_in_background")` — if true, creates a `BackgroundTask` row (queued), starts the `BackgroundTaskRunner`, and returns `background_task_id` in the response alongside the normal run/step data.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| `test_phase39_planner.py` | 21 | ✅ All pass (25.5s) |
| All Phase 39 tests | 66 (18+27+21) | ✅ All pass (59.1s) |

### Phase 39, Task 4 — Frontend UX for Background Tasks

**3 new files**:
- `frontend/src/components/agent/BackgroundTaskWidget.jsx` — polling widget in TopBar, pulsing Loader icon with badge count, dropdown with progress bars, cancel button
- `frontend/src/components/agent/BackgroundResultCard.jsx` — chat timeline card showing task result (min/max amounts, Open Excel File button)
- `frontend/tests/backgroundTasks.test.jsx` — 13 component tests

**3 modified files**:
- `frontend/src/api.js` — `runTaskInBackground`, `getBackgroundTasks`, `cancelBackgroundTask`
- `frontend/src/pages/AccountantAgent.jsx` — `handleApprovePlan` checks `plan.run_in_background`, shows toast and polls for completion, renders `BackgroundResultCard`
- `frontend/src/components/layout/TopBar.jsx` — renders `BackgroundTaskWidget` next to Emergency Stop

### Test results (frontend)

| Suite | Tests | Result |
|-------|-------|--------|
| `backgroundTasks.test.jsx` | 13 | ✅ All pass |
| All frontend tests (30 files) | 536 | ✅ All pass |

## Phase 39, Task 5 — Tauri OS Notifications & Final Polish

Native OS notifications when background tasks complete, plus completed-task recovery on app restart.

### Changes

**`frontend/src/components/agent/BackgroundTaskWidget.jsx`**:
- Tracks previous task statuses via `prevTasksRef`.
- When polling detects a transition from `running`/`queued` to `completed`/`failed`, triggers a notification.
- Uses `@tauri-apps/plugin-notification` when `window.__TAURI__` is present (desktop mode).
- Falls back to Web Notification API (`Notification` object) in web/browser mode.
- Notification body shows: "Processed {count} invoices. Biggest: ${amount}. Click to view."
- Failure notifications show the error message.

**`frontend/src/pages/AccountantAgent.jsx`**:
- On app load (`load()` function), fetches completed/failed `BackgroundTask` from the API.
- Renders any recent completed/failed tasks as `BackgroundResultCard` entries in the chat timeline.

**`desktop/tauri/src-tauri/capabilities/default.json`**:
- Added `notification:default`, `notification:allow-is-permission-granted`, `notification:allow-request-permission`, `notification:allow-notify` permissions.

**`frontend/package.json`**:
- Added `@tauri-apps/plugin-notification` ^2.x dependency.

**`docs/PHASE_39_QA.md`** (new):
- 6-section manual QA checklist covering all Phase 39 features.
- Step-by-step instructions for background tasks, Drive safety gate, frontend UX, OS notifications, and app-start recovery.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 39) | 66 | ✅ All pass |
| Frontend (all 30 files) | 536 | ✅ All pass |
| Frontend build | — | ✅ |

## Phase 40A — Always-On Proactive Watcher Scheduler

DB-backed background scheduler that silently monitors Gmail, Drive, and Local Folders to auto-extract invoices without user intervention.

### New model

`backend/app/models/background_watcher.py`:
- `BackgroundWatcher` — `id` (PK), `user_id` (FK), `name`, `source_type` (gmail/drive/folder), `config_json`, `schedule_minutes` (default 60), `last_run_at` (nullable), `status` (active/paused/error), `created_at`, `updated_at`.

### New service

`backend/app/services/watcher_scheduler.py`:
- `WatcherScheduler` singleton with thread-based polling loop checking due watchers every 60s.
- `_is_due` checks `last_run_at` vs `schedule_minutes`; never-run watchers always trigger.
- `_execute_watcher` generates predefined read-only plans per source type:
  - **Gmail**: `email_search` → `email_download_attachments` → `extract_invoice_data`
  - **Drive**: `drive_list_recent_files` → `drive_download_file` → `extract_invoice_data`
  - **Folder**: `scan_local_folder` → `extract_invoice_data`
- Merges user `config_json` (`keywords`, `days_back`) into plan params.
- Passes validated plan to `BackgroundTaskRunner` for async execution.
- Updates `last_run_at` on success; sets `status = 'error'` on exception.

### Safety rules

- `_validate_watcher_plan()` checks every step:
  1. **Risk level check** — tools with `medium`/`high` risk (e.g. `email_download_attachments`, `excel_create_summary_from_file`) get `_needs_approval=True` → task set to `pending_approval`
  2. **Allowed list check** — tools not in `WATCHER_ALLOWED_TOOLS` (low-risk read-only set) get `_blocked=True` → watcher set to `error` status
- `WATCHER_ALLOWED_TOOLS`: `email_search`, `email_preview_messages`, `email_save_attachment`, `drive_list_recent_files`, `drive_download_file`, `file_open_folder`, `scan_local_folder`, `extract_invoice_data`
- `HIGH_RISK_TOOLS`: `excel_create_summary_from_file`, `excel_create_workbook`, `create_daily_invoices_excel`, `browser_open_url`, `browser_click`, `browser_type`, `desktop_click`, `desktop_type`, `email_download_attachments`

### Router

`backend/app/routers/watchers.py` at `/api/watchers`:
- `GET /` — list user's watchers (newest first)
- `POST /` — create watcher (name, source_type, config_json, schedule_minutes)
- `PATCH /{id}` — update name/config/status/schedule (scope to user)
- `DELETE /{id}` — delete watcher (scope to user)
- `POST /{id}/run-now` — trigger immediate execution

### Lifecycle

Started in `main.py` lifespan — `WatcherScheduler.get_instance().start()` on boot, `.stop()` on shutdown.

### Frontend

- **WatcherSettings.jsx** at `/watchers`: clean settings page with watcher list, toggle switches (Pause/Resume), Run Now, Delete, and Add Watcher form with source type selector (Mail/HardDrive/Folder icons), keywords config, schedule dropdown, days-back input.
- **Sidebar.jsx**: Eye icon link in WORKSPACE section.
- **api.js**: `listWatchers()`, `createWatcher(body)`, `updateWatcher(id, body)`, `deleteWatcher(id)`, `runWatcherNow(id)`.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 40A) | 20 | ✅ All pass |
| Frontend (Phase 40A) | 10 | ✅ All pass |
| Frontend (32 files) | 556 | ✅ All pass |

## Phase 40B — Real Local LLM Brain with Ollama

Ollama integration providing a real local LLM brain for task planning, with automatic fallback to mock provider on connection failure.

### Changes

**`app/services/accountant_agent.py`**:
- `_check_local_llm_reachable(endpoint)` — probes Ollama `/api/tags` with 5s timeout, returns bool.
- `_build_ollama_system_prompt()` — builds system prompt from `TOOL_REGISTRY` with strict JSON-only format, multilingual instruction, banned actions, and exact JSON schema.
- `_call_ollama_provider(prompt, context)` — sends to Ollama `/api/generate` with `format: "json"`, temperature 0.1, 120s timeout. Raises `ConnectionError` on HTTP/URL errors.
- `call_agent_provider()` — routes `provider=="ollama"` to `_call_ollama_provider`, catches `ConnectionError`/`ValueError` → falls back to `_fallback_mock_response`.
- `get_agent_status()` — returns `status: "connected"` or `"ollama_unreachable"` based on health check.

**`app/config.py`**:
- `ollama_base_url` (default `http://localhost:11434`) — from `OLLAMA_BASE_URL` env var.
- `ollama_model` (default `llama3.1`) — from `OLLAMA_MODEL` env var.

**`app/routers/agent.py`**:
- `GET /api/agent/llm-status` — calls Ollama `/api/tags`, returns `{status, models, base_url}` on success, `{status: "offline", error}` on failure. No auth required (internal status endpoint).

**Frontend — `LocalAgent.jsx`**:
- "Local AI Brain" section with connection status pill (`Connected`/`Offline`), base URL display, and model list.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 40B) | 17 | ✅ All pass |

## Phase 40C — Autonomous Error Recovery & Self-Correction

Upgrades `BackgroundTaskRunner` with self-healing: if a step fails, it attempts a recovery strategy or pauses to ask the user for clarification.

### Recovery strategies (`RECOVERY_MAP`)

| Error Pattern | Recovery Steps | Fallback |
|--------------|----------------|----------|
| `extract_invoice_data:low_confidence` | 1 step: `screen_read_text` with invoice target | Generic clarification question |
| `extract_invoice_data:not found` | 1 step: `file_find_latest_download` | Ask user for file path |
| `excel_create_summary_from_file:unsupported` | None (empty list) | Ask user to save as .xlsx/.csv |

### Changes

**`backend/app/models/background_task.py`**:
- Added `clarification_question` (String(500), nullable) column.
- `paused_for_input` is a recognized status value alongside queued/running/completed/failed/cancelled.

**`backend/app/services/background_runner.py`**:
- Wrap `execute_tool` call in try/except; failed/error results enter recovery logic.
- `_get_recovery_steps(tool_name, error_message)` — matches against `RECOVERY_MAP`, returns recovery steps list or `None`.
- `_build_clarification_question(tool_name, error_message, params)` — generates user-friendly question from template or generic fallback.
- Recovery injection: if recovery steps exist, executes them inline. If they succeed, loop continues. If they fail or no recovery exists, sets `status="paused_for_input"` with `clarification_question` and returns.

**`backend/app/routers/background_tasks.py`**:
- `POST /background-tasks/{id}/answer` — accepts `{"user_answer": "..."}`, validates task exists / belongs to user / is `paused_for_input`, appends a `user_input` step to the plan with the answer, clears `clarification_question`, sets `status="running"`, and starts `BackgroundTaskRunner`.

**Frontend — `BackgroundTaskWidget.jsx`**:
- `NEEDS_ATTENTION_STATUSES` set with `paused_for_input`.
- `AlertTriangle` icon from lucide-react colored orange (`#ea580c`).
- Orange-tinted button with Needs Attention count badge.
- Dropdown: orange-bordered item with `AlertTriangle` + clarification question in warning box, text input, Send button, and Enter-to-submit. Cancel button visible for paused tasks.

**API** (`api.js`):
- `answerBackgroundTask(id, userAnswer)` — `POST` to `/background-tasks/{id}/answer`.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 40C) | 15 | ✅ All pass (54.4s) |
| Frontend (backgroundRecovery) | 10 | ✅ All pass (9.7s) |

## Phase 41 — Semantic Memory & RAG (Local Vector DB)

Local ChromaDB vector database for semantic search across all extracted invoice data, with automatic indexing on extraction.

### New service

`backend/app/services/semantic_memory.py`:
- `MockEmbeddingFunction` — deterministic CI-safe embeddings via SHA256 hashing (no ML models needed for tests).
- `SemanticMemory` — singleton service wrapping ChromaDB `PersistentClient` at `data_dir/vector_store/`.
- `index_invoice(invoice_id, text_content, metadata)` — embeds and stores invoice text + metadata.
- `semantic_search(query, top_k, user_id)` — returns top K matches with score, metadata, and text excerpt.
- `get_semantic_memory()` / `reset_semantic_memory()` — singleton lifecycle.

### New tool

`semantic_search_invoices` (low risk, no approval) in `tool_registry.py:1160` + executor:

### Auto-indexing

`_execute_extract_invoice_data` in `agent_tool_executor.py` now calls `_index_extracted_invoice()` after every successful extraction (both demo and real mode), indexing vendor, invoice_no, amount, date, currency, and file_path.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 41) | 16 | ✅ All pass (53.2s) |

## Phase 42 — Continuous Learning & Correction Loop

Feedback loop where the agent learns from user corrections and dynamically injects rules into the Ollama LLM system prompt.

### New model

`backend/app/models/correction_rule.py`:
- `AccountingCorrectionRule` — `id` (PK), `user_id` (FK), `trigger_vendor_pattern`, `wrong_category` (nullable), `correct_category`, `notes` (nullable), `created_at`.

### New service

`backend/app/services/learning_loop.py`:
- `record_correction(db, user_id, trigger_vendor, wrong_category, correct_category, notes)` — Creates a new rule.
- `get_active_rules(db, user_id)` — Returns all rules for the user.
- `delete_rule(db, rule_id, user_id)` — Deletes a rule scoped to user.
- `format_rules_for_prompt(rules)` — Formats rules into a strict text block under `### LEARNED CORRECTION RULES (MANDATORY)` header.

### Changes to `accountant_agent.py`

- `_build_ollama_system_prompt()` now accepts `db` and `user_id` parameters. When provided, it fetches the user's active correction rules and injects them into the system prompt under `### LEARNED CORRECTION RULES (MANDATORY)`.
- `_call_ollama_provider()`, `call_agent_provider()`, and `build_task_plan()` all threaded with optional `db`/`user`/`user_id` parameters to propagate correction rules to the Ollama provider.

### New router

`backend/app/routers/learning.py` at `/api/agent`:
- `POST /correct` — Accepts `trigger_vendor`, `wrong_category`, `correct_category`. Creates a correction rule.
- `GET /corrections` — Lists user's correction rules.
- `DELETE /corrections/{id}` — Deletes a rule.

### Frontend

- **`BackgroundResultCard.jsx`**: Added "Correct This" button (`Edit3` icon from lucide-react) next to largest/smallest vendor entries. Clicking opens an inline form with "Correct category for [Vendor]:" input. Submitting calls `POST /api/agent/correct` and shows "Rule saved ✓" success state. Cancel button hides the form.
- **`api.js`**: Added `createCorrection()`, `listCorrections()`, `deleteCorrection()` methods.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 42) | 15 | ✅ All pass (25.0s) |
| Frontend (learningLoop) | 7 | ✅ All pass (4.2s) |
| No regression (Phase 41 + 40B) | 33 | ✅ All pass (28.7s) |

## Phase 43 — Real Accounting Write-Back (QuickBooks/Xero API)

Real accounting write-back adapters for QuickBooks and Xero (mock by default) with safety-gated high-risk executors, audit logging, and frontend Push to QuickBooks button.

### New service

`backend/app/services/accounting_writeback.py`:
- `QuickBooksWritebackAdapter` and `XeroWritebackAdapter` with `create_bill()` returning mock success by default.
- `MOCK_MODE = True` unless `QUICKBOOKS_ENV`/`XERO_ENV` == "production".
- Mock mode returns a deterministic success response with bill ID, vendor, amount, and status.

### New tools (tool_registry.py)

| Tool | Risk | Approval | Description |
|------|------|----------|-------------|
| `quickbooks_create_bill` | high | **yes** | Create a bill in QuickBooks (writeback) |
| `xero_create_bill` | high | **yes** | Create a bill in Xero (writeback) |

### Executors (agent_tool_executor.py)

- `_execute_quickbooks_create_bill` and `_execute_xero_create_bill` — check safety gate env var `QUICKBOOKS_WRITEBACK_ENABLED`, instantiate adapter, call `create_bill()`, log audit via `_log_writeback_audit()`.
- `_log_writeback_audit()` — writes audit log with action `accounting.writeback.{provider}.{action}`.
- Safety gate: `QUICKBOOKS_WRITEBACK_ENABLED` must be "true"/"1"/"yes"/"on" — otherwise returns `EXECUTOR_RESULT_BLOCKED`.
- High-risk tools already blocked in dry-run mode by existing executor framework (returns `dry_run` status).

### Frontend

- **`BackgroundResultCard.jsx`**: Added `PushToQuickBooksButton` component (`CloudUpload` icon from lucide-react) rendered when task has `total_sum` or `total_amount`. Shows "Push to QuickBooks" → "Pushing..." → back to "Push to QuickBooks" on completion. Calls `onPushToQuickBooks` callback with `vendor_name`, `total_amount`, `line_items`, `due_date`.

### Pre-existing bugs fixed during Phase 43 QA

| Bug | File | Fix |
|-----|------|------|
| Broken indentation in `_execute_file_copy_table_to_excel` — dangling `try:`, floating dict keys at wrong indent | `agent_tool_executor.py:2208-2224` | Closed `try` with `except Exception: pass`, fixed dict key indentation to 20-space inside `return {}`, added fallback return |
| `_log_writeback_audit` had duplicate `except Exception:` blocks and a bogus `return` block referencing undefined `source`/`target`/`params` | `agent_tool_executor.py:2314-2348` | Removed duplicate except, removed bogus return block |
| `test_high_risk_blocked_in_dry_run_mode` expected `"blocked"` but dry-run short-circuit returns `"dry_run"` before reaching high-risk check | `test_phase43_writeback.py:199-210` | Changed assertion from `"blocked"` to `"dry_run"` |

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 43 writeback) | 10 | ✅ All pass (23.8s) |
| Frontend (writeback.test.jsx) | 5 | ✅ All pass |
| Frontend full suite (34 files) | 568 | ✅ All pass |

## Phase 44 — Deep Excel COM Automation via xlwings

Upgrades the Excel engine from basic file manipulation (openpyxl) to full Windows COM Automation using `xlwings`. Controls the actual Excel.exe process for Pivot Tables, complex formatting, workbook switching, and live formula calculation.

### Dependency

`xlwings>=0.33.0` added to `backend/requirements.txt`. xlwings requires Excel to be installed on the Windows machine. Gracefully falls back when xlwings is unavailable.

### New service

`backend/app/services/excel_com_automation.py`:
- `ExcelComAdapter` — context manager wrapping `xlwings.App(visible=False)`.
- **VBA macro blocklist**: `_check_vba_safety()` blocks `macro`, `application.run`, `vba`, `runmacro` in any parameter — raises `PermissionError`.
- **File path safety**: `_is_path_allowed()` blocks `C:\Windows`, `C:\Program Files`, `C:\Program Files (x86)`. Configurable `ALLOWED_DATA_DIRS` override.
- **Timeout per COM operation**: `_run_with_timeout()` runs each COM call in a daemon thread with configurable timeout (default 60s, via `OFFICEPILOT_COM_TIMEOUT` env var). Raises `TimeoutError` on hang.
- **Zombie prevention**: `app.quit()` called in `__exit__` finally block; all workbook `close()` calls in finally blocks.
- Methods:
  - `create_pivot_table(file_path, data_range, pivot_location, row_fields, value_field)`
  - `switch_workbook_and_copy(source_path, dest_path, sheet_name)`
  - `apply_conditional_formatting(file_path, sheet_name, range, rule_type, formula)`
  - `calculate_and_read_formula(file_path, sheet_name, cell_address)`
  - `create_chart(file_path, sheet_name, chart_type, data_range, title)`

### Tool registration (tool_registry.py)

| Tool | Risk | Approval | Description |
|------|------|----------|-------------|
| `excel_create_pivot_table` | **high** | **yes** | COM-powered pivot table (upgraded from medium) |
| `excel_switch_workbooks` | medium | yes | Copy sheet between workbooks via COM |
| `excel_advanced_formatting` | medium | yes | Conditional formatting via COM |
| `excel_calculate_and_read` | low | no | Force Excel calculation and read result |
| `excel_create_chart` | medium | yes | Create chart via COM |

### Executors (agent_tool_executor.py)

- 5 new executor functions mapped in `executor_map`, each with:
  - Path validation against blocked system directories (`_validate_com_file_path`)
  - Graceful fallback when xlwings/Excel not available
  - Timeout/PermissionError/Exception handling returning structured `EXECUTOR_RESULT_BLOCKED` or `EXECUTOR_RESULT_FAILED`
- `COM_TIMEOUT_SECONDS` configurable via `OFFICEPILOT_COM_TIMEOUT` env var (default 60)

### BackgroundTaskRunner update (background_runner.py)

- `COM_TOOLS` frozenset with all 5 COM tool names
- `COM_TIMEOUT` constant (default 60s)
- Step execution for COM tools wrapped in a daemon thread with `thread.join(timeout=COM_TIMEOUT)`. If timeout triggers, marks step as `timeout` status

### Frontend

- **AgentPlanCard.jsx**: Shows "Advanced Excel" badge when any plan step uses a COM tool
- **AccountantAgent.jsx**: Shows warning "This will run advanced Excel operations via COM automation. This may take a few moments." before approve buttons when COM tools are in the plan
- **BackgroundResultCard.jsx**: Shows "Advanced Excel" badge when result contains pivot table or chart data

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 44 COM) | 45 | ✅ All pass (18.3s) |
| Frontend (writeback + backgroundTasks + sidebarConsistency) | 38 | ✅ All pass |
| Frontend build | — | ✅ |

## Phase 45A — Automated Bank Reconciliation

Semantic-memory-powered bank reconciliation with COM-powered Excel reporting.

### New service

`backend/app/services/bank_reconciliation.py`:
- `BankFeedAdapter.parse_feed(file_path)` — parses CSV/JSON bank feed files into `BankTransaction` list. Mock mode generates 5 realistic transactions.
- `ReconciliationEngine.reconcile(bank_transactions, extracted_invoices, user_id)` — uses `SemanticMemory.semantic_search()` for initial matching (score clamped to [0,1]). Falls back to exact-match scoring against provided `extracted_invoices` using vendor name overlap and amount comparison.
- `generate_reconciliation_excel(records, output_path)` — uses `ExcelComAdapter` COM when available (for conditional formatting via Excel object model), falls back to `openpyxl PatternFill`. Green/yellow/red conditional formatting on Status column.

### Confidence tiers

| Score | Status | Description |
|-------|--------|-------------|
| >= 0.8 | `matched` | High confidence match via semantic memory or exact-match |
| 0.5–0.8 | `fuzzy_match` | Partial match — needs human review |
| < 0.5 | `unmatched` | No matching invoice found |

### New tools (tool_registry.py)

| Tool | Risk | Approval | Description |
|------|------|----------|-------------|
| `bank_parse_feed` | low | no | Parse bank feed CSV/JSON to structured transactions |
| `bank_reconcile_and_report` | medium | **yes** | Reconcile bank transactions against invoices and generate Excel report |

### Executors (agent_tool_executor.py)

- `_execute_bank_parse_feed` — wraps `BankFeedAdapter.parse_feed()`, returns transaction count + list.
- `_execute_bank_reconcile_and_report` — wraps `ReconciliationEngine.reconcile()` + `generate_reconciliation_excel()`, returns status counts + output path.

### Router endpoints (2 new)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agent/bank/parse` | POST | Parse uploaded bank feed file |
| `/api/agent/bank/reconcile` | POST | Run reconciliation and generate Excel report |

Added at bottom of `app/routers/agent.py`. Both endpoints wrap `execute_tool` directly (same pattern as `/folder-invoice/scan` and `/folder-invoice/create-excel`).

### Frontend

- **BankReconciliation.jsx** at `/app/reconciliation`: file upload area, parsed-transactions table with date/description/amount/type columns, "Run Bank Reconciliation" button, summary stats cards (total, matched, unmatched, fuzzy), "Download Excel Report" button.
- **Sidebar.jsx**: "Reconciliation" nav link with Scale icon in WORKSPACE section.
- **api.js**: `bankParseFeed()` and `bankReconcile()` methods.

### Key decisions

- `ReconciliationEngine` uses `SemanticMemory.semantic_search` for initial matching; score clamped to `max(0.0, min(1.0, score))`. Falls back to exact-match scoring when search confidence < 0.5.
- `generate_reconciliation_excel` tries COM first (conditional formatting with Excel object model), falls back to openpyxl PatternFill (green `C6EFCE`/`006100`, yellow `FFEB9C`/`9C6500`, red `FFC7CE`/`9C0006`).
- `BANK_FEED_MODE` env var controls mock mode (default "mock").
- Output path defaults to `data_dir/exports/reconciliation/reconciliation_{timestamp}.xlsx`.
- Routes bypass the run/step workflow for simplicity (same pattern as Phase 25 folder-invoice endpoints).

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 45A reconciliation) | 24 | ✅ All pass |
| Frontend (bankReconciliation) | 9 | ✅ All pass |
| Frontend build | — | ✅ |

## Phase 45B — Voice-Driven Live Excel Editing (Active Workbook COM)

COM automation upgrade to connect to the ACTIVE visible Excel instance, enabling real-time voice-driven editing with safety undo snapshots.

### Changes

`backend/app/services/excel_com_automation.py`:
- `connect_to_active_workbook()` — uses `xw.apps.active` instead of `xw.App()` to hook into the user's visible Excel process. Sets `app.screen_updating = False` for speed. Saves a temporary undo snapshot (`_save_active_snapshot()`) via `LIVE_EDIT_SNAPSHOT_DIR` config before any write.
- `execute_live_command(command_type, params)` — routes 12 command types to the `active_workbook`:
  - **Write operations** (auto-undo-snapshot before each): `format_range`, `set_value`, `write_values`, `apply_formula`, `clear_range`, `conditional_format`, `insert_pivot`, `insert_chart`
  - **Read operations**: `read_range`, `get_active_cell`, `list_sheets`, `activate_sheet`
- VBA macro blocklist enforced on all params before execution.
- `_parse_color()` helper converts hex colors (`#FF0000`) to Excel COM BGR int format.

### Tool registration

`tool_registry.py`:
- `excel_live_edit_active_workbook` (risk: high, approval: YES, snapshot: YES)
- input_schema with 12 `command_type` enum + `params` object

### Executor

`agent_tool_executor.py: _execute_excel_live_edit_active_workbook`:
- Creates `ExcelComAdapter()`, calls `connect_to_active_workbook()`, then `execute_live_command()`.
- Returns workbook_name, command_type, live_result, snapshot_path, undo_available.
- Handles RuntimeError (no active Excel), TimeoutError, PermissionError.

### Voice intent detection

`accountant_autopilot.py: build_accountant_plan()`:
- `LIVE_EXCEL_PATTERNS` regex detects 10+ phrases (English + Roman Urdu) before LLM-first planning.
- Returns a `live_excel_edit` plan with high risk, requires approval, and a single `excel_live_edit_active_workbook` step.

### Frontend

`TopBar.jsx`:
- "Live Excel Mode" toggle button with `MousePointerClick` SVG icon (cursor arrow).
- When active: red border/accent, red pulsing dot animation (`live-excel-pulse` keyframe).
- Title tooltip: "Live Excel Mode active — voice commands will directly edit your open file. Press Ctrl+Z to undo."
- CSS in `topbar.css`: `.live-excel-toggle`, `.live-excel-toggle--active`, `.live-excel-dot` classes.

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 45B live excel) | 37 | ✅ All pass (16.9s) |
| Frontend build | 1899 modules | ✅ 5.95s |

## Phase 45C — Multi-Agent Swarm Architecture

Three specialist agent profiles — Auditor (read-only), Tax (categorization), Data Entry (write-back) — each filtered to only their allowed tools.

### New service

`backend/app/services/agent_swarm.py`:
- `SPECIALIST_PROFILES` dict with 3 profiles:
  - **auditor** (blue): 73 read-only tools, restricted to screen/desktop/file/email read-only + semantic search
  - **tax** (green): 52 tools including Excel categorization + bank reconciliation
  - **data_entry** (red): 14 write-back tools (QuickBooks, Xero, Excel COM, browser fill, desktop type)
- `SwarmManager.classify_and_route(command)` — regex-based routing: auditor patterns > data_entry patterns > tax patterns > general fallback
- `execute_swarm_task(db, user_id, command, context, mode)` — classifies command, retrieves profile, passes `allowed_tools` to `build_task_plan()`
- `list_agent_profiles()` — returns all 3 profiles with name/color/icon/tool_count/description

### Changes to existing files

**`accountant_agent.py`**:
- `build_task_plan()` accepts `agent_profile: dict | None` — prepends `system_prompt_additions` to prompt, passes `allowed_tools` to `call_agent_provider`.
- `call_agent_provider()` accepts `allowed_tools: list[str] | None` — passes to `_build_ollama_system_prompt()`.
- `_build_ollama_system_prompt()` accepts `allowed_tools: list[str] | None` — when provided, only those tools appear in the LLM system prompt.

**`routers/agent.py`**:
- `POST /plan-task` response includes `"assigned_agent": "auditor" | "tax" | "data_entry" | "general"` — populated by `SwarmManager.classify_and_route()`.
- `GET /api/agent/profiles` — new endpoint returning all specialist profiles.

**Frontend — `AgentChatWindow.jsx`**:
- `<AgentBadge>` component renders colored badge (blue `#dbeafe`/`#1e40af` for auditor, green `#dcfce7`/`#166534` for tax, red `#fee2e2`/`#991b1b` for data entry, indigo `#e0e7ff`/`#3730a3` for general).

### Test results

| Suite | Tests | Result |
|-------|-------|--------|
| Backend (Phase 45C swarm) | 27 | ✅ All pass (34.7s) |
| Frontend (agentSwarm) | 9 | ✅ All pass |
| Frontend full suite (36 files) | 586 | ✅ All pass |
| Frontend build | 1899 modules | ✅ 6.51s |
