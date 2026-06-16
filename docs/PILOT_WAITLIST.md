# Pilot Waitlist

## Purpose

Collect signups from users interested in the OfficePilot AI pilot program.
Store and manage waitlist entries with status tracking.

## Database Table: `pilot_waitlist`

| Column | Type | Notes |
|--------|------|-------|
| id | Integer | Primary key, auto-increment |
| name | String(255) | Required |
| email | String(255) | Unique, case-insensitive, indexed |
| company | String(255) | Optional |
| role | String(128) | Optional |
| invoice_volume | String(64) | Optional |
| current_workflow | Text | Optional |
| interested_features_json | Text | Optional |
| country | String(128) | Optional |
| notes | Text | Optional |
| status | String(32) | One of: new, contacted, demo_scheduled, accepted, rejected |
| created_at | DateTime | Auto-set |
| updated_at | DateTime | Auto-set on update |

## Status Values

| Status | Meaning |
|--------|---------|
| `new` | Fresh signup, not yet reviewed |
| `contacted` | Admin has reached out |
| `demo_scheduled` | A demo has been scheduled |
| `accepted` | Approved for pilot access |
| `rejected` | Not accepted at this time |

## Service Functions (`services/public_pilot_waitlist.py`)

- `submit_waitlist()` — Create entry or return existing for duplicate email
- `list_waitlist()` — Admin list with status/search/pagination
- `update_waitlist_status()` — Change entry status (validated)
- `get_waitlist_summary()` — Aggregated stats (total, by role, by volume, by status)
- `export_waitlist_csv()` — Full CSV export for download

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/public/waitlist` | None | Submit signup |
| GET | `/api/admin/waitlist` | owner/admin | List entries (with filters) |
| PATCH | `/api/admin/waitlist/{id}` | owner/admin | Update entry status |
| GET | `/api/admin/waitlist/summary` | owner/admin | Get summary stats |
| GET | `/api/admin/waitlist/export.csv` | owner/admin | Download CSV |

## Admin Dashboard (`/admin/waitlist`)

Features:
- Summary cards (total, by role, by volume, by status)
- Searchable/filterable table with status tags
- Inline status update via dropdown
- CSV export button
- Color-coded status badges

## Privacy

- Email uniqueness enforced (case-insensitive)
- No data transmitted to external services
- Admin-only access to entries
- CSV export available for admin download
