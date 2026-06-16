# System Flow and Architecture

## 1. Core Logic Flow
OfficePilot follows a strict safety-first lifecycle for every action:

**Input** → **Parse** → **Validate** → **Review** → **Approve** → **Snapshot** → **Act** → **Validate** → **Audit** → **Restore**

---

## 2. High-Level Architecture
The system is built as a **Local Agent** architecture, ensuring privacy and control.

```
       [ User Interface ]
              ↕ (REST API / JWT)
    ┌──────────────────────────┐
    │    FastAPI Local Agent   │ <─── [ Auth / Roles ]
    └─────────────┬────────────┘
                  │
    ┌─────────────┴────────────┐
    │   Database (SQLite)      │
    │   Local File Storage     │
    └─────────────┬────────────┘
                  │
    ┌─────────────┴───────────────────────────────────────────┐
    │                     Engines Layer                       │
    ├──────────────┬──────────────┬──────────────┬────────────┤
    │    Parser    │  Validation  │   Workflow   │  Audit     │
    ├──────────────┼──────────────┼──────────────┼────────────┤
    │    Excel     │  Accounting  │   Browser    │  Screen    │
    ├──────────────┼──────────────┼──────────────┼────────────┤
    │    Voice     │   Safety     │   Email      │  Restore   │
    └──────────────┴──────────────┴──────────────┴────────────┘
```

---

## 3. Component Details

### Frontend (React / Vite)
- **State Management**: React Hooks + Context.
- **API Client**: Centralized `api.js` for all backend communication.
- **UI Components**: Modular components for Invoice Review, Voice Assistant, and Safety Center.
- **Security**: JWT tokens stored securely; session-based role enforcement.

### Backend (FastAPI / Python)
- **Routers**: Domain-specific endpoints (e.g., `/api/invoices`, `/api/voice`).
- **Services**: Business logic decoupled from API routing.
- **Models**: SQLAlchemy ORM for SQLite.
- **Schemas**: Pydantic for strict data contract enforcement.

### Desktop Shell (Tauri)
- **Native Host**: Windows webview container.
- **Sidecar**: Bundles the Python FastAPI server as a standalone executable.
- **Process Management**: Monitors sidecar health and port availability (8767).

---

## 4. Key Data Flows

### A. Manual Invoice Processing
1. User uploads file via Frontend.
2. Backend saves file and triggers `TextExtractionService` (OCR).
3. `ParserService` identifies fields (Vendor, Date, Amount).
4. `ValidatorService` checks for duplicates and logic errors (e.g., Tax + Subtotal != Total).
5. Result appears in **Review Queue**.
6. User clicks **Approve**.

### B. Accounting Sync (QuickBooks/Xero)
1. Approved invoice is selected for sync.
2. `AccountingService` fetches mappings (Chart of Accounts).
3. Backend generates a **Sync Preview**.
4. User Approves Sync.
5. `AccountingService` pushes a **Draft** entry via OAuth API.
6. Backend reads back the entry from the provider to **Validate** it was created correctly.

### C. Voice Command Execution
1. Frontend captures audio via `MediaRecorder`.
2. `VoiceSTTService` transcribes audio (Mock/OpenAI/Local).
3. `VoiceIntentParser` identifies the command (e.g., "show pending").
4. Backend returns a **Command Preview**.
5. User clicks **Approve** (if risky).
6. `ActionExecutor` triggers the corresponding route/service.

---

## 5. Safety Architecture
- **Snapshots**: Before any file modification (like Excel), a bit-perfect copy is saved.
- **Audit Logs**: Immutable record of who did what and when.
- **Kill Switch**: Global state that blocks all `ActionExecutor` calls if toggled.
- **Allowlists**: Browser automation only functions on pre-approved domains.
- **Role Permissions**: "Accountant" cannot change "Safety Policies"; only "Owner" can.

---

## 6. External Integrations
| Service | Integration Type | Purpose |
| :--- | :--- | :--- |
| **Gmail/Outlook** | OAuth2 / Graph API | Invoice discovery and import. |
| **QuickBooks/Xero** | OAuth2 / REST API | Syncing invoice data to accounting. |
| **OpenAI** | REST API (Optional) | High-accuracy transcription (Whisper). |
| **Playwright** | Browser Automation | Safe, automated form filling. |

---

## 7. Known Technical Limitations
- **Backup**: Currently manual local backup only; no cloud-sync backup.
- **Concurrency**: SQLite handles local multi-threading, but not designed for 100+ concurrent web users.
- **Rate Limiting**: Local-first assumes single-user safety; global rate limiting is minimal.
- **Screen Control**: Accuracy depends on OS-level permissions and display scaling.
