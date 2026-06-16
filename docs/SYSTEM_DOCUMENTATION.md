# OfficePilot AI — System Documentation

> **Version:** 0.36.1  
> **Codename:** Phase 38.5  
> **Platform:** Windows (primary), Web (development)  
> **Stack:** Python FastAPI + React SPA + Tauri 2 Desktop Shell  
> **Updated:** 2026-06-15

---

## 1. System Overview

OfficePilot AI is a **Universal Voice Accountant Agent** — a Windows desktop application that automates accounting work across Excel, browser apps, and accounting platforms via voice/text commands. It provides step-by-step planning, human-in-the-loop approval, safe execution, and workflow memory.

The system runs as three layers:

```
┌─────────────────────────────────────────────────────┐
│              Tauri 2 Desktop Shell (Rust)            │
│  System tray · Global shortcuts · Sidecar lifecycle  │
│  Auto-updater · Window management                    │
├─────────────────────────────────────────────────────┤
│              React SPA Frontend (Vite)               │
│  Chat-based Agent UI · Dashboard · Settings · Admin  │
│  Workflow recording · Browser cards · Voice UI       │
├─────────────────────────────────────────────────────┤
│            Python FastAPI Backend (Agent)            │
│  REST API · SQLAlchemy ORM · Services · Executors    │
│  Workflow engine · Agent provider · Voice layer      │
└─────────────────────────────────────────────────────┘
```

---

## 2. System Architecture

### 2.1 Overall Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER (Voice / Text)                              │
└────────────┬────────────────────────────────────┬───────────────────────┘
             │ Voice (Mic)                         │ Text (Typed)
             ▼                                     ▼
     ┌───────────────┐                   ┌───────────────────┐
     │  whisper.cpp  │                   │  React SPA (Vite) │
     │  (local STT)  │                   │  Port 5173        │
     └───────┬───────┘                   └────────┬──────────┘
             │ Transcribed text                   │ HTTP/REST
             ▼                                    ▼
     ┌──────────────────────────────────────────────────┐
     │          FastAPI Backend (Port 8000/8766)         │
     │                                                    │
     │  ┌──────────────────────────────────────────────┐  │
     │  │            Agent Planner                      │  │
 │  │  build_accountant_plan() — LLM-first planning  │  │
│  │  · Safety gate → Navigation → LLM (mock /     │  │
│  │    cloud / local Ollama) — understands ANY     │  │
│  │    natural language directly                   │  │
     │  └──────────────────────────────────────────────┘  │
     │                      │                              │
     │                      ▼                              │
     │  ┌──────────────────────────────────────────────┐  │
     │  │            Execution Engine                    │  │
     │  │  agent_tool_executor.py — 60+ tool executors  │  │
     │  │  · Browser (Playwright) · Desktop (pyautogui) │  │
     │  │  · Excel (openpyxl) · File IO · Email (Gmail) │  │
     │  │  · Screen/OCR (tesseract) · Workflow record   │  │
     │  └──────────────────────────────────────────────┘  │
     │                      │                              │
     │                      ▼                              │
     │  ┌──────────────────────────────────────────────┐  │
     │  │            Services Layer                     │  │
     │  │  Validation · Audit · Snapshots · Versions    │  │
     │  │  Safety/Policy · Permissions · Backup/Restore │  │
     │  │  Usage tracking · Demo/Onboarding · Feedback  │  │
     │  └──────────────────────────────────────────────┘  │
     │                                                    │
     │  Database: SQLite via SQLAlchemy ORM               │
     │  Storage: Local filesystem (invoices, exports,     │
     │           snapshots, audit logs, recordings)       │
     └──────────────────────────────────────────────────┘
                          │
                          ▼
     ┌──────────────────────────────────────────────────┐
     │  External Integrations                            │
     │  · Gmail API (read-only) · QuickBooks (sync)     │
     │  · Xero (sync) · Browser (Playwright Chromium)   │
     │  · Local file system (Downloads, folders)        │
     └──────────────────────────────────────────────────┘
```

### 2.2 Component Breakdown

#### 2.2.1 Tauri Desktop Shell (`desktop/tauri/src-tauri/`)

| Component | File | Purpose |
|-----------|------|---------|
| Main | `src/main.rs` | Entry point, launches the Tauri app |
| Library | `src/lib.rs` | Plugin registration (shell, dialog, global-shortcut, updater), system tray, agent supervisor, window management |
| Agent supervisor | `src/agent.rs` | Spawns/monitors the Python sidecar binary, health probes, auto-restart |
| System tray | `src/tray.rs` | Tray icon with menu (Show, Exit), close-to-tray behavior |
| Config | `tauri.conf.json` | Window size, bundle targets (MSI/NSIS), updater config, external binaries |
| Capabilities | `capabilities/default.json` | Permission grants for Tauri plugins |

**Build outputs:**
- `OfficePilot AI_0.36.1_x64_en-US.msi` (MSI installer)
- `OfficePilot AI_0.36.1_x64-setup.exe` (NSIS installer)
- `.sig` signature file for code-signing

#### 2.2.2 Python FastAPI Backend (`backend/app/`)

**Entry point:** `main.py` — mounts 40+ routers, runs startup hooks, configures CORS.

**Routers** (`routers/` — 40 files):

| Category | Routers |
|----------|---------|
| Auth | `auth.py` — register, login, logout, JWT tokens (HMAC-SHA256) |
| Core | `invoices.py`, `settings.py`, `audit.py`, `local.py` |
| Agent | `agent.py` — plan-task, approve, execute-step, workflows CRUD |
| Workflow | `workflows.py`, `workflow_recorder.py`, `workflow_recording.py` |
| Browser | `browser.py` — browser automation policies, actions, preview |
| Screen | `screen_control.py` — screen capture, OCR, click/type |
| Gmail | `integrations_gmail.py`, `email_automation.py` |
| Accounting | `accounting.py`, `accounting_skills.py` |
| Phase 19 | `demo_walkthrough.py`, `feedback.py`, `bug_reports.py`, `usage.py`, `pilot_readiness.py` |
| Phase 20 | `public_waitlist.py` |
| Admin | `admin.py`, `system.py`, `backup.py`, `audit_exports.py` |
| Voice | `voice.py`, `voice_layer.py` |
| Other | `app_updates.py`, `billing.py`, `diagnostics.py`, `about.py` |

**Services** (`services/` — 62 files):

| Service | Purpose |
|---------|---------|
| `accountant_autopilot.py` | Command intent cascade, Roman Urdu NLP, plan building |
| `accountant_agent.py` | Agent provider abstraction (mock/OpenAI-compatible/DeepSeek), task planning, risk classification |
| `agent_tool_executor.py` | 60+ tool executors: browser, desktop, Excel, file, email, workflow, safety, screen/OCR |
| `tool_registry.py` | 7-category tool definitions with risk levels, approval requirements |
| `agent_memory.py` | Workflow memory CRUD, run/step lifecycle |
| `agent_context.py` | Runtime context builder (active app, user role, kill switch, feature flags) |
| `auth.py` | Password hashing (PBKDF2-HMAC-SHA256), JWT creation/verification |
| `email_service.py` / `gmail_readonly_service.py` | Gmail OAuth, search, preview, download |
| `excel_tools.py` | Full Excel automation (summary creation, formatting, formula validation) |
| `browser_automation.py` | Playwright adapter with domain policy, risk classifier, redaction |
| `screen_control.py` | Screen capture, OCR, click/type executors, blocklist/allowlist |
| `versioning.py` / `snapshots.py` | Entity/file version capture, history, restore with audit |
| `safety.py` | Kill switch, safety policy, role-based access |
| `storage_manager.py` | Storage path management, cache cleaning |
| `windows_voice_layer.py` | Microphone recording, whisper.cpp transcription (multilingual model) |
| `multilingual_command.py` | Roman Urdu / English language detection and translation |
| `language_utils.py` | Lightweight multi-language detection (French, Spanish, German, Roman Urdu) |
| `demo.py` | Demo data seeding and reset |
| Various others | Feedback, bug reports, usage tracking, pilot readiness, backup, etc. |

**Database models** (`models/` — 73 tables):

| Group | Models |
|-------|--------|
| Core | Invoice, InvoiceFile, InvoiceLineItem, Setting, AuditLog |
| Auth | User, UserSession, RolePermission |
| Agent | AgentTaskPlan, AgentWorkflowMemory, AgentWorkflowRun, AgentWorkflowStepLog |
| Workflow | WorkflowRun, WorkflowApproval, WorkflowLog, WorkflowVersion |
| Browser | BrowserAutomationPolicy, BrowserActionRun, BrowserActionStep, BrowserPageSnapshot |
| Screen | ScreenControlPolicy, ScreenControlSession, ScreenControlAction, ScreenControlStepLog |
| Gmail | EmailAccount, EmailSearchRun, EmailAttachmentDownload, EmailToken |
| Accounting | AccountingConnection, AccountingSyncLog, AccountingSkill, AccountingSkillVersion |
| Recording | WorkflowRecordingSession, WorkflowRecordedEvent, WorkflowSkillDraft |
| Versioning | EntityVersion, FileSnapshot, RestoreLog |
| Pilot | PilotFeedback, BugReport, UsageEvent, PilotReadiness, PilotWaitlist |
| Marketing | PublicPageEvent |
| Voice | VoiceCommand, DictationHistory |
| Safety | SafetyPolicy, AutomationSafetyState, AuditExport |
| Billing | Subscription, FeatureEntitlement, InAppNotification, AppRelease, UserDevice |

#### 2.2.3 React SPA Frontend (`frontend/src/`)

**Entry:** `main.jsx` → `App.jsx` (React Router with auth guards, layout shell)

**Key libraries:**
- React 18 + React Router 6 (client-side routing)
- lucide-react (SVG icons)
- Vitest + Testing Library (unit tests)
- Vite (bundler)
- @tauri-apps/plugin-updater (Tauri integration)

**Pages** (`pages/` — 83 files):

| Category | Pages |
|----------|-------|
| Auth | Login, Register, ForgotPassword, ResetPassword, VerifyEmail, GoogleCallback |
| Dashboard | Dashboard (agent-first layout with quick actions) |
| Agent | AccountantAgent (chat-first UI with plan preview, execution timeline, save workflow) |
| Workflow | WorkflowEditor, WorkflowRuns, WorkflowRunDetail, WorkflowVersions, RecordWorkflow, RecordedWorkflowsList, ReplayRunner, ReplayLogs |
| Browser | BrowserSettings, BrowserLogs, BrowserTestForm |
| Screen | ScreenSettings, ScreenAssistant, ScreenLogs |
| Gmail | EmailIntegrations, ImportedEmails, ImportedEmailDetail |
| Accounting | AccountingIntegrations, AccountingMappings, AccountingSkills, AccountingSyncLogs, AccountingSyncPreviewModal |
| Voice | VoiceCommandCenter, VoiceIntents, DictationHistory, VoiceLayerSettings |
| Admin | AdminDashboard, AdminUsers, AdminUserDetail, AdminWaitlist, AdminSystemHealth, AdminAIStatus, AdminAuditLogs |
| Safety | SafetyPolicyCenter, EmergencySafety, PermissionsManager, AuditLogs, AuditExport |
| Pilot | PilotReadiness, PilotUsageReview, FeedbackInbox, BugReports |
| Other | VersionHistory, FileSnapshots, RestoreActivity, StorageSettings, PrivacyDashboard, LocalAgent, CleanupPage, ReleaseReadiness, StartupMetrics, DemoSettings, etc. |

**Components** (`components/`):

| Component | Purpose |
|-----------|---------|
| `layout/` | AppShell, Sidebar, TopBar, NavIcon |
| `agent/` | TrayFloatingAgent, AgentChatWindow, AgentPlanCard, AgentApprovalCard, AgentProgressTimeline, AgentResultCard, AgentModeSwitcher, WorkflowMemoryQuickList, FilePickerCard, FileSelectionCard |
| `billing/` | UpdateBanner |
| `voice/` | VoiceCommandModal, FloatingVoiceAssistant |
| `admin/` | Admin layout components |
| `auth/` | Auth guards |
| `ui/` | UI primitives |

---

## 3. System Flow

### 3.1 Command Processing Pipeline (LLM-First)

This is the central decision flow in `build_accountant_plan()`. All language-specific
regex cascades (Roman Urdu, PDF, Recording, Skills, Workflow Replay, Folder Invoice,
P&L, Excel commands) have been removed. The LLM is the primary intent engine.

```
User Command (Voice/Text — ANY natural language)
        │
        ▼
┌───────────────────────────────────┐
│ 1. Safety Gate                    │ → Blocked → Return blocked response
│    (DANGEROUS_KEYWORDS +           │          (payment, delete, tax,
│     BLOCKED_EMAIL_PATTERNS +       │           banking blocked by policy)
│     BLOCKED_PAYMENT_PATTERNS)      │
└───────────────────────────────────┘
        │ (passed)
        ▼
┌───────────────────────────────────┐
│ 2. Navigation Patterns            │ → Match → Return navigation plan
│    (voice, settings, workflow      │          (no execution, just route)
│     memory)                        │
└───────────────────────────────────┘
        │ (passed)
        ▼
┌───────────────────────────────────┐
│ 3. LLM-First Planning             │ → Provider produces JSON plan
│    (Mock / Cloud / Local Ollama)  │
│                                   │
│    Mock provider:                 │
│     · English + French + Spanish  │
│       + German keyword detection  │
│       for Excel downloads         │
│     · Falls back to clarification │
│       for unknown commands        │
│                                   │
│    Cloud provider (OpenAI/Deep-   │
│     Seek): system prompt rule 10  │
│     instructs: "The user's        │
│     command may be in ANY natural │
│     language. Understand it,      │
│     translate conceptually to     │
│     English, produce JSON plan."  │
│                                   │
│    Local provider (Ollama/        │
│     Llama.cpp): same system       │
│     prompt as cloud; endpoint     │
│     configurable via              │
│     LOCAL_LLM_ENDPOINT            │
└───────────────────────────────────┘
        │
        ▼
  Plan returned: task_title,
  task_type, risk_level, steps[],
  clarification_needed, etc.
```

### 3.2 Plan-to-Execution Flow

```
User sends command
        │
        ▼
Agent creates Plan (task_type, risk_level, steps[])
        │
        ▼
┌─────────────────┐     ┌───────────────────┐
│ Requires        │ Yes  │ Plan Preview      │
│ Approval?       │─────→│ (steps, risk,     │
│                 │      │  summary_for_user)│
└─────────────────┘      └────────┬──────────┘
        │ No                      │
        ▼                         ▼
┌─────────────────┐     ┌───────────────────┐
│ Approve &       │     │ User Approves     │
│ Execute         │     │ (Dry-Run / Live)  │
└────────┬────────┘     └────────┬──────────┘
         │                       │
         ▼                       ▼
┌────────────────────────────────────────┐
│          Execution Engine              │
│                                        │
│  For each step in steps[]:             │
│  1. Resolve template variables         │
│     ({file_path}, {selected_file_path})│
│  2. Execute tool via agent_tool_       │
│     executor.py                        │
│  3. Store result in step_log           │
│  4. Audit-log every action             │
│                                        │
│  Modes: dry_run (preview only)         │
│         live (real execution)          │
└────────────────────────────────────────┘
        │
        ▼
┌─────────────────┐
│ Run Complete    │
│                 │
│ If live +       │
│ successful:     │
│ → Show save CTA │
│ → Save workflow │
│   option        │
└─────────────────┘
```

### 3.3 Universal Language Handling

All language-specific regex cascades have been removed. The system now handles
commands in any natural language through the LLM provider:

```
User: "crée un résumé du fichier excel dans téléchargements"  (French)
User: "crear un resumen del archivo de excel en descargas"     (Spanish)
User: "erstellen sie eine zusammenfassung der excel-datei"      (German)
User: "download folder mein parcel lab ki excel file ki summary banao" (Roman Urdu)
User: "create a summary of the parcel lab excel in downloads"  (English)
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Safety Gate (blocked words checked — language-agnostic)   │
│ 2. Navigation Patterns (language-agnostic)                    │
│ 3. LLM provider receives the ORIGINAL text in any language    │
│    · Mock provider: multi-language keyword detection          │
│    · Cloud provider: system prompt rule 10 — understand any  │
│      language, translate conceptually to English internally   │
│    · Local provider (Ollama): same prompt as cloud            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
  Plan: excel_summary_from_downloads
  Steps: file_find_in_downloads → excel_create_summary_from_file
  (same regardless of input language)
```

**Key differences from the old regex-based system:**
- No Roman Urdu-specific patterns — the LLM understands any language
- No English-specific regex (EXCEL_PATTERNS, FOLDER_INVOICE_PATTERNS, etc.)
- The mock provider still uses keyword patterns for offline demos, but now supports
  French, Spanish, German, and English (English remains for Roman Urdu speakers)
- The cloud and local LLM providers understand any natural language via the system prompt
- `detect_language()` preserves the original language in the response for voice replies
- `_build_excel_downloads_summary_plan()` and `_extract_file_query()` remain for the
  Excel-from-downloads workflow (used by all providers via `build_accountant_plan`)

### 3.3A Excel Downloads Flow (Language-Agnostic)

```
User command (any language) matched by LLM provider
        │
        ▼
build_accountant_plan() → LLM determines "excel_summary_from_downloads"
        │
        ├─ Mock provider: multi-language keyword detection
        │   (English, French, Spanish, German keywords)
        │
        ├─ Cloud/Local provider: LLM interprets intent
        │   from the natural language command
        │
        ▼
1. _extract_file_query() → "parcel lab"
   (filler phrases + stop words removed — handles Roman Urdu)
        │
        ▼
2. _build_excel_downloads_summary_plan("parcel lab")
        │
        ├─ Step 1: file_find_in_downloads
        │   query="parcel lab", extensions=[".xlsx", ".xls", ".csv"]
        │
        └─ Step 2: excel_create_summary_from_file
            path="{selected_file_path}"
        │
        ▼
3. User approves → Execution:
        │
        ├─ Step 1: _execute_file_find_in_downloads()
        │   → Searches real Downloads folder
        │   → Returns selected_file_path
        │
        └─ Step 2: excel_create_summary_from_file
            → Creates summary with auto-detected columns and totals
```

### 3.4 Dry-Run vs Live Flow

```
          Approve & Dry-Run              Approve & Execute
                │                               │
                ▼                               ▼
     Run created with mode='dry_run'    Run created with mode='live'
                │                               │
                ▼                               │
     All steps executed in dry-run              │
     (no side effects, no file IO)              │
                │                               │
                ▼                               │
     Results shown as preview                   │
                │                               │
     "Switch to Live" button ───────────────────┘
                │
                ▼
     Steps re-executed with real IO
                │
                ▼
     Run completed → Save Workflow CTA
     is shown (only after live success)
```

---

## 4. Key Design Decisions

### 4.1 Safety-First Architecture

| Layer | Mechanism |
|-------|-----------|
| **Plan** | Blocked keywords (payment, bank transfer, delete records, password entry, security settings, tax filing, payroll) |
| **Domain** | Browser domain blocklist wins over allowlist; banking, payment, crypto domains blocked by default |
| **Risk** | Risk classifier: low=read, medium=write, high=delete/submit. High-risk always requires approval |
| **Exec** | Defense-in-depth: even unregistered tools are blocked at executor level with `gmail_readonly_policy` |
| **Kill** | Global kill switch persists in DB, synced to in-memory cache, checked before every plan/approve/execute |
| **Audit** | Every plan, approve, execute, stop action writes an audit_log row |
| **Redact** | Sensitive values (password, token, OTP, CVV, SSN, PIN) redacted in all logs and previews |

### 4.2 Universal Language Strategy

- **LLM-first intent parsing** — all language-specific regex cascades removed; the LLM provider (mock, cloud, or local) is the primary intent engine
- **Mock provider multi-language support** — keyword detection for English, French, Spanish, German Excel-downloads commands (offline fallback)
- **Cloud/local provider** — system prompt rule 10: "The user's command may be in ANY natural language. Understand it, translate conceptually to English, produce JSON plan."
- **Whisper multilingual model** — `ggml-small.bin` (~500 MB) supports 100+ languages; auto-detects language from audio
- **Query extraction (Excel downloads)** — `_extract_file_query()` uses stop-word removal for file name extraction (handles Roman Urdu phrases like "ki file", "wala file", "ka naam")
- **Bilingual replies** — `detect_language()` preserves original language in response; `voice_reply_text` generated in the detected language
- **No external NLP library** — pure keyword heuristics for mock provider; LLM handles true language understanding

### 4.3 Local-First Privacy

- All processing runs locally — no cloud dependency for core functionality
- Gmail is read-only (OAuth `gmail.readonly` scope only)
- Bug report packages are local-only with sensitive data redaction
- Usage tracking is local-only, gated by `USAGE_TRACKING_ENABLED`
- Database is SQLite in the local filesystem
- All invoice, export, snapshot, and audit data stays on the user's machine

---

## 5. Limitations

### 5.1 Technical Limitations

| Area | Limitation | Status |
|------|------------|--------|
| **Platform** | Windows-only (Tauri 2, whisper.cpp, pyautogui). No macOS/Linux support | Will not change |
| **Offline LLM** | Local LLM (Ollama/Llama.cpp) requires a separately installed and running service. The agent connects to it via OpenAI-compatible API. No built-in model downloading or management for the LLM | Separate tool |
| **Multilingual** | Mock provider supports English/French/Spanish/German only for Excel-downloads keyword detection. Cloud/local LLM required for full multilingual understanding of all command types. Roman Urdu handled via English keyword overlap in mock mode | Acceptable |
| **Database** | SQLite only — no PostgreSQL/MySQL support. Concurrent write contention at high scale | Acceptable for single-user |
| **OCR** | English-only. Tesseract must be installed separately for real OCR. Fallback to basic image parsing | Known limitation |
| **Browser** | Playwright Chromium required for real browser automation. Falls back to deterministic dry-run without it | Documented |
| **Voice** | whisper.cpp multilingual model (`ggml-small.bin`) ~500 MB. Download as separate step (not bundled in installer). CPU-only transcription latency (~2-10s for 500MB model). English-only model (`ggml-base.en.bin`, ~150 MB) available as fallback | One-time setup |
| **Excel** | openpyxl only — no .xls (legacy) format support. Large files (>50MB) may cause memory issues | Known |
| **Gmail** | Read-only only — no send/delete/move/archive | Intentional safety |
| **Agent LLM** | Mock provider by default (supports English + French + Spanish + German Excel keywords). Cloud LLM requires `AGENT_ALLOW_CLOUD=true` + API key. Local LLM (Ollama/Llama.cpp) requires running service at `LOCAL_LLM_ENDPOINT`. No built-in API key management | Intentional privacy |
| **Installer** | Code signing requires external certificate (`OFFICEPILOT_CERT_THUMBPRINT`). MSI ~150MB | Installer is large |
| **Updates** | Auto-updater points to localhost by default (development). Production endpoint requires deployment setup | Scaffolded |
| **Python** | Bundled sidecar is Python 3.11 (~150MB). No custom Python path support | Acceptable |

### 5.2 Functional Limitations

| Area | Limitation |
|------|------------|
| **QuickBooks/Xero** | Sync is mock/sandbox-only. Real OAuth credentials not configured in current build |
| **Banking** | No banking site automation. Blocked by domain policy |
| **Password manager** | No password auto-fill. Domain blocked by default |
| **PDF debit/credit** | Not supported — returns clarification message |
| **Tax filing** | Blocked at agent planner level |
| **Payroll** | Blocked at agent planner level |
| **Multi-user** | Single-user desktop app. Auth system exists but organization/team features not implemented |
| **Invoice parsing** | Basic extraction only. Complex multi-page layouts may have lower accuracy |
| **Workflow recording** | MVP stage — event-to-skill draft conversion is heuristic |

---

## 6. Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OFFICEPILOT_DB_URL` | `sqlite:///./officepilot.db` | Database connection string |
| `OFFICEPILOT_STORAGE_ROOT` | `./storage` | Local storage root directory |
| `OFFICEPILOT_OCR_ENABLED` | `true` | Enable OCR engine |
| `OFFICEPILOT_TESSERACT_CMD` | `` | Path to tesseract executable |
| `OFFICEPILOT_CORS_ORIGINS` | multi-origin | Allowed CORS origins |
| `AGENT_PROVIDER` | `mock` | Agent LLM provider (`mock`, `local`, `openai_compatible`, `deepseek`) |
| `AGENT_ALLOW_CLOUD` | `false` | Allow cloud LLM calls |
| `AGENT_API_KEY` | `` | API key for cloud provider |
| `AGENT_MODEL` | `` | Model name for cloud/local provider |
| `LOCAL_LLM_ENDPOINT` | `http://localhost:11434/v1` | Endpoint URL for local LLM (Ollama/Llama.cpp). Must expose `/chat/completions` |
| `WHISPER_MODEL_PATH` | `` | Path to whisper.cpp model file. Overrides auto-detection. Set to `C:\path\to\ggml-small.bin` |
| `BROWSER_AUTOMATION_ENABLED` | `false` | Enable real browser automation |
| `BROWSER_HEADLESS` | `false` | Browser headless mode |
| `DEMO_MODE` | (not set) | Enable demo mode with sample data |
| `USAGE_TRACKING_ENABLED` | `true` | Enable local usage tracking |
| `VOICE_APPROVAL_ENABLED` | `false` | Enable voice approval |
| `ALLOW_BILLING_BYPASS` | `true` | Bypass feature entitlement checks |
| `OFFICEPILOT_AGENT_PORT` | `8766` | Agent backend port |

### 6.1 Multilingual Voice Setup

To enable multilingual voice commands end-to-end:

1. **Download multilingual Whisper model** (one-time):
   ```
   # Via the app UI: Open Voice Settings → Download Model → select "ggml-small.bin (multilingual)"
   # Or manually:
   cd backend && python -c "
   from app.services.windows_voice_layer import download_model
   result = download_model('ggml-small.bin')
   print(result)
   "
   ```

2. **Set the model path** (optional — auto-detected if placed in `data/whisper/`):
   ```
   set WHISPER_MODEL_PATH=C:\path\to\ggml-small.bin
   ```

3. **Choose an LLM provider for multilingual understanding**:
   - **Mock provider** (default, offline, no setup): supports English, French, Spanish, German
     keyword detection for Excel-downloads commands. Roman Urdu commands with English
     keywords work via overlap.
   - **Local LLM** (fully offline, best multilingual support):
     - Install [Ollama](https://ollama.ai) or [Llama.cpp](https://github.com/ggerganov/llama.cpp)
     - Pull a multilingual model: `ollama pull llama3.1` (supports English, French, German,
       Spanish, Hindi, Arabic, and many more)
     - Set environment:
       ```
       set AGENT_PROVIDER=local
       set AGENT_MODEL=llama3.1
       ```
   - **Cloud LLM** (requires internet):
     ```
     set AGENT_PROVIDER=openai_compatible
     set AGENT_ALLOW_CLOUD=true
     set AGENT_API_KEY=sk-...
     ```

4. **Verify the setup**:
   - Backend: `GET /api/agent/status` should show `"status": "connected"` or `"status": "mock"`
   - Voice: `GET /api/voice-layer/whisper-detect` should show `"whisper_configured": true`

---

## 7. Development & Testing

### 7.1 Common Commands

```bash
# Backend
cd backend && python -m uvicorn app.main:app --reload         # Dev server
cd backend && python -m pytest -q                              # All backend tests
cd backend && python -m pytest tests/test_phase23c.py -v      # Specific tests

# Frontend
cd frontend && npm run dev                                      # Dev server
cd frontend && npm test -- --run                                # All frontend tests
cd frontend && npm run build                                    # Production build

# Desktop (requires Rust)
cd desktop/tauri && cargo tauri dev                             # Dev mode
cd desktop/tauri && cargo tauri build                           # Production build

# Sidecar
cd backend && pyinstaller scripts/officepilot_sidecar.spec --noconfirm
```

### 7.2 Test Counts

| Suite | Tests |
|-------|-------|
| Backend unit tests | 104 pass |
| Frontend tests (27 files) | 498 pass |
| Backend full regression | ~1100 (some pre-existing failures) |

### 7.3 Build Outputs

| Artifact | Location |
|----------|----------|
| Backend | `backend/` (Python source, runs via uvicorn) |
| Frontend | `frontend/dist/` (Vite build) |
| Sidecar binary | `desktop/tauri/src-tauri/binaries/officepilot-agent-x86_64-pc-windows-msvc.exe` |
| MSI installer | `releases/0.36.1/OfficePilot AI_0.36.1_x64_en-US.msi` |
| NSIS installer | `releases/0.36.1/OfficePilot AI_0.36.1_x64-setup.exe` |
| Update signature | `releases/0.36.1/*.sig` |

---

## 8. Directory Structure Reference

```
Officecopilot/
├── backend/app/           # FastAPI backend
│   ├── main.py            # Entry point + router mounts
│   ├── config.py          # Environment variable loading
│   ├── db.py              # SQLAlchemy engine + session
│   ├── models/            # 73 SQLAlchemy ORM models
│   ├── routers/           # 40 API route files
│   ├── services/          # 62 service modules
│   ├── schemas/           # Pydantic request/response schemas
│   └── utils/             # Shared utilities
├── frontend/src/          # React SPA
│   ├── main.jsx           # Entry point
│   ├── App.jsx            # Router + layout shell
│   ├── api.js             # API client abstraction
│   ├── pages/             # 83 page components
│   ├── components/        # Shared UI components
│   ├── hooks/             # React hooks (useRecording etc.)
│   ├── utils/             # Utility functions
│   └── styles.css         # Global styles
├── desktop/tauri/         # Tauri 2 desktop shell
│   └── src-tauri/         # Rust source
│       ├── src/            # Rust modules (lib.rs, agent.rs, tray.rs, main.rs)
│       ├── tauri.conf.json # Tauri configuration
│       ├── Cargo.toml      # Rust dependencies
│       └── binaries/       # Sidecar + whisper models
├── docs/                  # Documentation
├── scripts/               # Build/deploy scripts
├── releases/              # Release artifacts
├── data/                  # Runtime data directory
├── samples/               # Sample data files
└── marketing/             # Marketing assets
```

---

## 9. API Endpoint Summary

| Prefix | Router | Endpoints |
|--------|--------|-----------|
| `/api/auth` | auth | register, login, logout, me, refresh |
| `/api/invoices` | invoices | upload, list, get, approve, reject, mark-duplicate, organize |
| `/api/settings` | settings | get, update, folder-rules |
| `/api/audit` | audit | list, export |
| `/api/versions` | versions | entity/file/workflow versions, diff, restore, timeline |
| `/api/browser` | browser | policies, preview, approve, reject, execute, status, logs |
| `/api/screen-control` | screen_control | policies, sessions, actions, execute, status |
| `/api/agent` | agent | status, context, plan-task, approve-plan, execute-step, workflows CRUD, runs |
| `/api/email` | email_automation | connect-gmail, search, preview, download, disconnect |
| `/api/workflow-recorder` | workflow_recorder | start/stop/cancel session, record event, convert to skill |
| `/api/accounting` | accounting | connect, sync, mappings, skills |
| `/api/admin` | admin | users, waitlist, system-health, releases |
| `/api/demo` | demo | seed, reset, status |
| `/api/feedback` | feedback | submit, list, update |
| `/api/bug-reports` | bug_reports | create, list, download |
| `/api/usage` | usage | record, summary |
| `/api/voice` | voice | commands, parse, intents |
| `/api/app` | app_updates, billing | check-update, register-device, license |
| `/api/local` | local | export-logs, storage |
| `/api/public` | public_waitlist | waitlist submit, page-event |
| `/api/safety` | safety | policy, kill-switch |
| `/api/permissions` | permissions | roles, permissions |
