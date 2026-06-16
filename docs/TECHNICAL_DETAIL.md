# Technical Detail Document

## 1. Technology Stack
- **Language**: Python 3.11+
- **Backend Framework**: FastAPI
- **Frontend Framework**: React 18 (Vite, Tailwind CSS)
- **Desktop Shell**: Tauri (Rust-based)
- **Database**: SQLite (SQLAlchemy 2.0 ORM)
- **Automation**: Playwright (Browser), PyAutoGUI (Screen fallback)
- **Workflow**: LangGraph (Custom state machine)
- **OCR/Parser**: Tesseract OCR / Custom Rule-based & LLM adapters
- **Packaging**: PyInstaller (Sidecar)

---

## 2. Database Schema Overview
Major tables and their roles:
- **`users`**: Auth, hashed passwords, roles.
- **`invoices`**: Core metadata, extraction results, status.
- **`invoice_files`**: Binary storage pointers and file metadata.
- **`audit_logs`**: Immutable history of all actions.
- **`snapshots`**: Bit-perfect copies of files before modification.
- **`accounting_sync_logs`**: History of QuickBooks/Xero draft creations.
- **`browser_action_runs`**: Logs of Playwright automation steps.
- **`voice_commands`**: Transcripts, parsed intents, and approval status.
- **`safety_policies`**: Global flags for automation and AI usage.

---

## 3. API Domain Map
| Prefix | Responsibility |
| :--- | :--- |
| `/api/auth` | Login, Register, Role verification. |
| `/api/invoices` | Upload, Extract, Review, Approve. |
| `/api/email` | OAuth, Import, Attachment processing. |
| `/api/accounting` | QuickBooks/Xero connection and sync. |
| `/api/voice` | STT, Intent parsing, Command execution. |
| `/api/safety` | Kill switch, Policy management. |
| `/api/backup` | Database and file system backups. |

---

## 4. Safety & Implementation Detail
### Risk-Level Enforcement
Every voice or automated action is assigned a risk level:
- **Low**: Navigation, Search (Execute immediately).
- **Medium**: Reading screen, Copying data (Preview required).
- **High**: Writing to Excel, Creating Accounting Draft (Approval + Snapshot required).
- **Blocked**: Sending emails, payments, deleting data (Forbidden).

### The "Sidecar" Architecture
The Python backend is packaged as a "Sidecar" using PyInstaller. 
1. Tauri starts the Sidecar on boot.
2. Sidecar binds to `127.0.0.1:8767`.
3. Frontend communicates via the Tauri proxy or direct local fetch.
4. If the Sidecar crashes, Tauri attempts a restart and notifies the user.

---

## 5. Voice Engine Internals
1. **Frontend**: `navigator.mediaDevices.getUserMedia` captures audio.
2. **STT Service**: 
   - `Mock`: Returns hardcoded strings for testing.
   - `OpenAI`: Sends audio blob to Whisper API (if enabled).
   - `Local`: Invokes a local Whisper executable (e.g., whisper.cpp).
3. **Intent Parser**: Uses regex-based pattern matching (Phase 22.7) to identify `domain` and `intent`.
4. **Execution**: Routed through the `ActionExecutor` which checks `SafetyPolicy` before calling the relevant service.

---

## 6. Accounting Sync Mechanism
1. **OAuth2**: Handles token exchange and refresh.
2. **Preview**: Generates a JSON payload of what will be sent to the API.
3. **Sync**: Pushes to `/Invoice` endpoint of the provider.
4. **Verification**: After sync, the system performs a `GET` on the newly created ID and compares every field (Amount, Tax, Date) to ensure no silent errors occurred during transmission.

---

## 7. Known Technical Debt
- **Rate Limiting**: Not currently enforced at the API level (assumes single-user local usage).
- **CI/CD**: Build scripts are manual PowerShell; needs migration to GitHub Actions.
- **DB Migrations**: Currently using `Base.metadata.create_all`; needs Alembic for production schema changes.
- **Screen OCR**: Performance on high-DPI 4K screens can be inconsistent; needs scaling calibration.
