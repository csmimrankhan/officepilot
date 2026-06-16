# OfficePilot AI — Frontend (Phases 1 + 2)

React + Vite single-page UI for OfficePilot AI Phase 1 (manual invoice
upload, review, Excel export) and Phase 2 (Gmail invoice automation).

## Install

```powershell
cd C:\Users\dsmim\Desktop\Officecopilot\frontend
npm install
```

## Environment variables

All variables are optional. Copy `frontend/.env.example` to `frontend/.env`.

| Variable          | Default                 | Purpose                                |
| ----------------- | ----------------------- | -------------------------------------- |
| `VITE_API_BASE`   | `http://127.0.0.1:8000` | Base URL of the FastAPI backend.       |

## Run locally

```powershell
cd C:\Users\dsmim\Desktop\Officecopilot\frontend
npm run dev
```

Open <http://127.0.0.1:5173>. Start the backend on port 8000 first.

## Build

```powershell
npm run build
npm run preview
```

## Tests

```powershell
npm test
```

Vitest + Testing Library cover the API client, shared components, the
Upload / Review pages, and the Phase 2 email pages (Integrations,
Imported Emails, Imported Email Detail, Source badge).

## Pages

| Page                  | Route                       | Purpose                                          |
| --------------------- | --------------------------- | ------------------------------------------------ |
| Upload Invoice        | `/upload`                   | Manual PDF / image upload + extraction.          |
| Review Queue          | `/review`                   | All invoices; filter by status; source badge.    |
| Invoice Detail        | `/invoices/:id`             | Edit fields, approve, reject, link to email.     |
| Approved Invoices     | `/approved`                 | List of approved invoices.                       |
| Export Excel          | `/export`                   | Generate approved-only `.xlsx`.                  |
| Email Integrations    | `/integrations`             | Connect / Sync / Disconnect Gmail.               |
| Imported Emails       | `/imported-emails`          | All email imports + scores.                      |
| Imported Email Detail | `/imported-emails/:id`      | Per-email breakdown and attachment results.      |
| Audit Logs            | `/audit`                    | All audit log entries.                           |