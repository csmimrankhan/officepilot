# OfficePilot AI — Backend (Phases 1 + 2 + 3 + 5)

FastAPI service for invoice upload, text/OCR extraction, review, approval,
Excel export, Gmail invoice email automation (Phase 2), the **trust layer
(Phase 3: approval/audit/duplicate/folder-organizer)**, and the **parser
engine adapter (Phase 5)**. SQLite by default.

## Install

```powershell
cd C:\Users\dsmim\Desktop\Officecopilot\backend
pip install -r requirements.txt
```

Python 3.11+ is required. Tesseract OCR is optional — if not installed, image
uploads will land in `needs_review` with a clear warning.

## Environment variables

All variables are optional (defaults shown). Copy `backend/.env.example` to
`backend/.env` or the repo-root `.env` to override.

| Variable                          | Default                                                       | Purpose                                            |
| --------------------------------- | ------------------------------------------------------------- | -------------------------------------------------- |
| `OFFICEPILOT_ENV`                 | `development`                                                 | Free-form label, surfaces in health check.         |
| `OFFICEPILOT_DB_URL`              | `sqlite:///./officepilot.db`                                  | SQLAlchemy URL.                                    |
| `OFFICEPILOT_STORAGE_ROOT`        | `./storage`                                                   | Where invoice originals and Excel exports land.    |
| `OFFICEPILOT_OCR_ENABLED`         | `true`                                                        | Master switch for OCR fallback.                    |
| `OFFICEPILOT_TESSERACT_CMD`       | (empty)                                                       | Absolute path to the `tesseract` binary.           |
| `OFFICEPILOT_MAX_UPLOAD_MB`       | `20`                                                          | Upload size cap in MB.                             |
| `OFFICEPILOT_CONFIDENCE_THRESHOLD`| `0.6`                                                         | Below this the invoice goes to `needs_review`.     |
| `OFFICEPILOT_CORS_ORIGINS`        | `http://localhost:5173,http://127.0.0.1:5173`                 | Comma-separated CORS origins.                      |
| `OFFICEPILOT_GMAIL_CLIENT_ID`     | *(empty)*                                                     | Google OAuth client ID (Web application).          |
| `OFFICEPILOT_GMAIL_CLIENT_SECRET` | *(empty)*                                                     | Google OAuth client secret.                        |
| `OFFICEPILOT_GMAIL_REDIRECT_URI`  | `http://127.0.0.1:8000/api/integrations/gmail/callback`       | Must match the Google Cloud console exactly.       |
| `OFFICEPILOT_GMAIL_TOKEN_KEY`     | *(empty)*                                                     | 44-char url-safe base64 Fernet key.                |
| `OFFICEPILOT_GMAIL_STATE_DIR`     | `./storage/gmail`                                             | Where OAuth state and Fernet key are persisted.    |
| `OFFICEPILOT_GMAIL_MIN_SCORE`     | `0.4`                                                         | Min score for an email to be considered.           |
| `OFFICEPILOT_GMAIL_MAX_RESULTS`   | `50`                                                          | Max emails per sync.                               |
| `OFFICEPILOT_GMAIL_SEARCH_DAYS`   | `30`                                                          | Look-back window in days.                          |
| `OFFICEPILOT_GMAIL_ALLOW_REAL`    | `true`                                                        | When `false`, the fake client is used (CI/dev).    |
| `OFFICEPILOT_PARSER_ENGINE`       | `existing`                                                    | Parser engine: `existing` / `docling` / `ocr` / `hybrid`. |

### Generating a Fernet key for production

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the output into `OFFICEPILOT_GMAIL_TOKEN_KEY`. The same key must be
used across restarts; rotating it invalidates existing stored tokens and
forces the user to reconnect Gmail.

## Database / migrations

Phases 1 + 2 use SQLAlchemy `create_all` on startup. Eight tables are
created in `officepilot.db`:

| Table                 | New in | Purpose                                                    |
| --------------------- | ------ | ---------------------------------------------------------- |
| `invoice_files`       | Phase 1| (Phase 2 added `source`, `email_import_id`, `email_attachment_id`) |
| `invoices`            | Phase 1| Invoice rows.                                              |
| `invoice_line_items`  | Phase 1| Line items per invoice.                                    |
| `audit_logs`          | Phase 1| Append-only audit trail.                                   |
| `email_accounts`      | Phase 2| Connected Gmail account + encrypted tokens.                |
| `email_imports`       | Phase 2| One row per processed email.                               |
| `email_attachments`   | Phase 2| One row per attachment, with FK to `invoices`.             |

Existing Phase 1 databases gain the new columns via `create_all` (SQLite
handles `ALTER TABLE ADD COLUMN` for nullable columns automatically). No
manual migration step is required.

To switch to Alembic in a later phase, see the Phase 1 README.

## Run locally

```powershell
cd C:\Users\dsmim\Desktop\Officecopilot\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000/api/health> and <http://127.0.0.1:8000/docs>.

### First-time Gmail setup

1. Create a Google Cloud project and an **OAuth 2.0 Client (Web application)**.
2. Add `http://127.0.0.1:8000/api/integrations/gmail/callback` to
   **Authorized redirect URIs**.
3. Enable the **Gmail API** for the project.
4. Copy the client ID and client secret into your `.env`:
   ```
   OFFICEPILOT_GMAIL_CLIENT_ID=…
   OFFICEPILOT_GMAIL_CLIENT_SECRET=…
   ```
5. Restart the backend.
6. Open <http://127.0.0.1:5173/integrations> and click **Connect Gmail**.

## Tests

```powershell
cd C:\Users\dsmim\Desktop\Officecopilot\backend
python -m pytest -q
```

Tests cover storage, parser, validator, end-to-end API flows, duplicate
detection, audit logging, Excel export, **Gmail scoring, encrypted token
storage, sync orchestration (with a fake Gmail client), and Gmail
endpoints**. OCR is disabled inside the test harness, and the real Gmail
API is disabled (`OFFICEPILOT_GMAIL_ALLOW_REAL=false`).

## API surface

### Phase 1
| Method | Path                                | Purpose                          |
| ------ | ----------------------------------- | -------------------------------- |
| POST   | `/api/invoices/upload`              | Upload + extract one invoice.    |
| GET    | `/api/invoices`                     | List invoices (filter by `status`). |
| GET    | `/api/invoices/{id}`                | Invoice detail.                  |
| GET    | `/api/invoices/{id}/file`           | Stream the original file.        |
| PATCH  | `/api/invoices/{id}`                | Edit fields / line items.        |
| POST   | `/api/invoices/{id}/approve`        | Mark as approved.                |
| POST   | `/api/invoices/{id}/reject`         | Mark as rejected (with reason).  |
| GET    | `/api/invoices/export/excel`        | Download approved-only `.xlsx`.  |
| GET    | `/api/audit-logs`                   | Filterable audit log.            |
| GET    | `/api/health`                       | Liveness probe.                  |

### Phase 2
| Method | Path                                                | Purpose                                  |
| ------ | --------------------------------------------------- | ---------------------------------------- |
| GET    | `/api/integrations/gmail/status`                    | OAuth + connection status.               |
| GET    | `/api/integrations/gmail/connect`                   | Returns a Google consent URL.            |
| GET    | `/api/integrations/gmail/callback`                  | OAuth callback.                          |
| POST   | `/api/integrations/gmail/sync-invoices`             | Run a sync pass.                         |
| POST   | `/api/integrations/gmail/disconnect`                | Disconnect and purge tokens.             |
| GET    | `/api/email-imports`                                | List email imports (filter by status).   |
| GET    | `/api/email-imports/{id}`                           | One email import with attachments.       |

### Phase 5 (parser engine)
| Method | Path                                | Purpose                                                    |
| ------ | ----------------------------------- | ---------------------------------------------------------- |
| GET    | `/api/parser/engines`               | List registered parser engines.                            |
| GET    | `/api/parser/benchmark`             | Run a benchmark on the golden invoices (JSON or CSV).      |

## Security & safety (Phase 2)

- Scope is strictly `gmail.readonly`. We never ask for write/modify scopes.
- We never send, delete, modify, mark-as-read, archive, or label emails.
- OAuth tokens are encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256).
- `disconnect` purges the encrypted tokens immediately.
- The sync orchestrator writes a dedicated audit log entry for every
  candidate, skip, duplicate, error, and import — all of which are
  visible in the **Audit Logs** page and via `GET /api/audit-logs`.

## Phase 5 — Parser engine

The parser layer is pluggable. Set `OFFICEPILOT_PARSER_ENGINE` to one
of:

- `existing` (default) — Phase 1-3 PyMuPDF + pdfplumber + regex pipeline.
- `docling` — Docling layout-aware parser. Gracefully falls back to
  `existing` when Docling is not installed.
- `ocr` — OCR-first engine using PaddleOCR if available, else
  Tesseract. Always rasterises the document, even for digital PDFs.
- `hybrid` — runs `existing` + `docling` + `ocr` in parallel and
  reconciles the result by per-field confidence.

Switching the setting is non-destructive: existing invoices keep the
engine name they were parsed with (visible in the audit log), and
flipping back to `existing` reproduces the Phase 1-3 behaviour
exactly. Two new endpoints expose the engines:

- `GET /api/parser/engines` — list registered engines.
- `GET /api/parser/benchmark?engines=existing,docling&format=json|csv`
  — run all (or selected) engines on the three synthetic golden
  invoices in `backend/tests/golden_invoices/` and return per-field
  accuracy, runtime, and warnings. Use this to A/B test before
  changing the production setting.

The golden invoices are synthetic (no real client data); the
rendered PDFs are gitignored.
