# OfficePilot AI — Admin Guide

**Version:** 0.36.1 | **Phase:** 37 | **Build:** Stability Freeze

---

## Admin Dashboard

Admin pages are available to users with `owner` or `admin` role. Navigate via:

- **User Management** (`/admin/users`) — Create, edit, deactivate users
- **Audit Logs** (`/admin/audit-logs`) — Browse all audit log entries
- **Waitlist** (`/admin/waitlist`) — Manage pilot waitlist entries
- **System Health** (`/admin/system-health`) — View all component statuses
- **AI Status** (`/admin/ai-status`) — View AI/LLM configuration

---

## System Health (`/admin/system-health`)

Shows live status of all system components:

| Component | Status Source |
|-----------|---------------|
| Backend | Process health check |
| Database | SQLite `SELECT 1` |
| Sidecar | Bundled binary detection |
| Updater | Auto-updater endpoint active |
| Gmail Read-Only | OAuth configuration status |
| Excel Automation | Always enabled (openpyxl bundled) |
| Workflow Recorder | Env var `WORKFLOW_RECORDING_ENABLED` |
| Browser Automation | Env var `BROWSER_AUTOMATION_ENABLED` |
| Local Whisper | CLI + model file detection |
| LLM Provider | `AGENT_PROVIDER` + `AGENT_ALLOW_CLOUD` |

---

## AI Status (`/admin/ai-status`)

Read-only view of all AI/LLM configuration. **Never exposes raw API keys.**

Shows three sections:

### Accountant Agent (Planner)
| Field | Source |
|-------|--------|
| Provider | `AGENT_PROVIDER` (default: `mock`) |
| Model | `AGENT_MODEL` |
| API Key Configured | Boolean (not the key value) |
| Cloud AI Allowed | `AGENT_ALLOW_CLOUD` (default: `false`) |

### AI Mode (Dictation Polish)
| Field | Source |
|-------|--------|
| Provider | `AI_MODE_PROVIDER` |
| Model | `AI_MODE_MODEL` |
| API Key Configured | Boolean |
| Cloud AI Allowed | `AI_MODE_ALLOW_CLOUD` (default: `false`) |

### Voice STT (Speech-to-Text)
| Field | Source |
|-------|--------|
| Provider | `VOICE_PROVIDER` (default: `mock`) |
| Cloud STT Allowed | `VOICE_ALLOW_CLOUD_STT` (default: `false`) |
| OpenAI Key Configured | Boolean |

---

## Zero-Cloud-by-Default

OfficePilot v0.36.1 runs **fully without LLM** in its default configuration:

- `AGENT_PROVIDER=mock` — rule-based plan generation, no API calls
- `AGENT_ALLOW_CLOUD=false` — cloud provider calls blocked
- `AI_MODE_ALLOW_CLOUD=false` — dictation polish blocked
- `VOICE_PROVIDER=mock` — no cloud STT
- `VOICE_ALLOW_CLOUD_STT=false` — cloud STT blocked
- `OPENAI_API_KEY` — empty

To enable cloud AI, set the following environment variables **before starting the app**:

```bash
# Enable LLM-powered agent planning
AGENT_PROVIDER=deepseek
AGENT_API_KEY=sk-...
AGENT_ALLOW_CLOUD=true

# Enable AI dictation polish
AI_MODE_API_KEY=sk-...
AI_MODE_ALLOW_CLOUD=true

# Enable OpenAI Whisper STT
VOICE_PROVIDER=openai
OPENAI_API_KEY=sk-...
VOICE_ALLOW_CLOUD_STT=true
```

---

## API Endpoints

### `GET /api/admin/system-health`
Requires `admin` or `owner` role. Returns JSON with all component statuses.

### `GET /api/admin/ai-status`  
Requires `admin` or `owner` role. Returns JSON with AI configuration. API key fields are boolean `*_configured` flags, never raw values.

---

## Pre-existing Test Status

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 35 update/billing | 16 | ✅ All pass (fixed: updater endpoint test, order-dependent cleanup) |
| Phase 37 zero-cloud | 25 | ✅ All pass (new) |
| Frontend Phase 35 | 7 | ✅ All pass (fixed: fake timers for UpdateBanner) |
| Pydantic v2 warnings | 11 | ⚠️ Non-breaking deprecation warnings (class-based `Config`) |
