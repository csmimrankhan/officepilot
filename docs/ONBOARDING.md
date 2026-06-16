# Onboarding

After first login, a setup checklist appears in the sidebar to guide new users.

## Checklist Steps

| # | Step | Optional | Description |
|---|------|----------|-------------|
| 1 | `create_owner` | No | Create the first owner account |
| 2 | `confirm_agent` | No | Confirm the local agent is online |
| 3 | `load_demo_data` | No | Load sample data via Demo Mode |
| 4 | `upload_invoice` | No | Upload your first invoice |
| 5 | `review_invoice` | No | Review an extracted invoice |
| 6 | `approve_invoice` | No | Approve an invoice |
| 7 | `export_excel` | No | Export to Excel |
| 8 | `view_audit_log` | No | View the audit log |
| 9 | `run_backup` | No | Run a local backup |
| 10 | `check_readiness` | No | Check the readiness dashboard |
| 11 | `connect_gmail` | Yes | Connect Gmail (optional) |
| 12 | `connect_accounting` | Yes | Connect QuickBooks/Xero sandbox (optional) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/onboarding/status` | Get checklist + completed steps + progress % |
| POST | `/api/onboarding/complete-step` | Mark a step as complete (`{"step": "step_name"}`) |
| POST | `/api/onboarding/dismiss` | Dismiss the entire checklist |

## Database

A single `onboarding_state` table stores per-user state:

- `user_id` — Foreign key to `users`
- `checklist_json` — The full checklist definition
- `completed_steps_json` — Array of completed step names
- `dismissed` — Boolean, whether the user dismissed the checklist
- `created_at` / `updated_at` — Timestamps
