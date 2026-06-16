# Desktop Update & Billing (Phase 35)

## Manual Update Flow

1. The frontend polls `POST /api/app/check-update` on app startup and every hour.
2. If an update is available, `UpdateBanner` appears at the top of the page.
3. The user clicks "Download" which opens `download_url` in the browser.
4. The user downloads and runs the installer manually.

### Critical Updates

If `is_critical: true`, the response includes `"blocked": true` and a message:
```json
{
  "latest_version": "0.36.0",
  "update_available": true,
  "critical": true,
  "blocked": true,
  "message": "A required security update is available.",
  "download_url": "https://releases.officepilot.ai/download/0.36.0/OfficePilot-0.36.0.exe",
  "release_notes": "Security fix for ..."
}
```

The `UpdateBanner` shows a warning icon and "Update Now" button instead.

## Future Tauri Updater Flow

When Tauri's built-in auto-updater is enabled (`tauri-plugin-updater`):

1. The Rust supervisor calls `POST /api/app/check-update` on startup.
2. The API returns JSON with `download_url` and `updater_url`.
3. Tauri compares the `latest_version` with the current app version.
4. If newer, Tauri downloads the update in the background.
5. Tauri shows a native update dialog.
6. On user confirmation, Tauri installs the update and restarts.

### Required Tauri Config

In `tauri.conf.json`:
```json
{
  "plugins": {
    "updater": {
      "endpoints": ["https://api.officepilot.ai/api/app/check-update"],
      "pubkey": "..."
    }
  }
}
```

### Release JSON Format (for Tauri updater)

The update endpoint returns:
```json
{
  "latest_version": "0.36.0",
  "update_available": true,
  "critical": false,
  "download_url": "https://releases.officepilot.ai/download/0.36.0/OfficePilot-0.36.0-x86_64.msi",
  "release_notes": "## What's new\n- Excel automation improvements\n- Bug fixes",
  "minimum_required_version": "0.33.0"
}
```

Tauri updater expects a JSON response with:
- `version` — semver string
- `notes` — release notes (markdown)
- `pub_date` — ISO 8601 date
- `platforms` — object with platform-specific download URLs and signatures

For now, the backend returns the simpler format. Adapt the endpoint if/when Tauri updater is wired.

### Code Signing Requirement

- Windows installers must be Authenticode-signed.
- The signing certificate must be from a trusted CA (DigiCert, Sectigo, etc).
- Signing is done by `scripts/sign_installers.ps1` using `signtool.exe`.
- The PowerShell script reads `OFFICEPILOT_CERT_THUMBPRINT` env var.
- The script is a no-op if the env var is not set (safe for dev machines).

### Release Process

1. Build new version (bump `OFFICEPILOT_APP_VERSION` in `.env`).
2. Run all tests: `cd backend && python -m pytest -q` and `cd frontend && npm test -- --run`.
3. Build frontend: `cd frontend && npm run build`.
4. Build sidecar: `cd backend && pyinstaller scripts/officepilot_sidecar.spec --noconfirm`.
5. Build Tauri: `cd desktop/tauri && cargo tauri build`.
6. Sign installers: `scripts/sign_installers.ps1`.
7. Upload installers to release server.
8. Insert a row into `app_releases` via the API or direct DB insert:

```sql
INSERT INTO app_releases (version, platform, channel, download_url, release_notes, minimum_required_version, is_critical)
VALUES ('0.36.0', 'windows', 'stable', 'https://releases.officepilot.ai/download/0.36.0/OfficePilot-0.36.0-x86_64.msi', 'Bug fixes and improvements', '0.33.0', false);
```

## Billing & Licensing

### Current Implementation

- **Mock/manual provider only** — no real Stripe/Paddle integration.
- No card collection inside Tauri.
- Local dev bypass: `ALLOW_BILLING_BYPASS=true` (default in dev).
- Billing is purely informational (status, plan, feature listing).

### Models

- `subscriptions` — user_id, provider, plan, status, trial_ends_at, current_period_end
- `feature_entitlements` — plan, feature_key, enabled, limit_value

### Plans

| Plan | Price | Key Features |
|------|-------|-------------|
| Free | $0 | Excel automation, Gmail read-only, 5 skills, 50 runs/mo |
| Trial | $0 (14 days) | All features, 100 runs/mo, 20 skills |
| Pro | $29/mo | All features, 1000 runs/mo, 50 skills |

### Feature Gates

The `require_feature(db, user_id, feature_key)` helper determines if a user can use a given feature:

- Gated features: `browser_export`, `gmail_readonly`, `workflow_recorder`, `advanced_skills`, `voice_shortcuts`
- Not gated: login/register, local Excel demo, basic invoice upload

In dev mode (`ALLOW_BILLING_BYPASS=true`), all features are unlocked.

### Future Billing Checkout Flow

1. User clicks "Upgrade to Pro" on `/app/billing`.
2. Frontend calls `POST /api/billing/start-checkout` with `{ plan: "pro" }`.
3. Backend creates a Stripe Checkout Session (or Paddle link).
4. Backend returns `checkout_url`.
5. User completes payment in Stripe/Paddle hosted page.
6. Stripe sends webhook to `POST /api/billing/webhook`.
7. Backend updates subscription status.
8. Frontend polls or listens for license update.

### Future Webhook Flow

1. Stripe webhook hits `POST /api/billing/webhook`.
2. Backend verifies webhook signature.
3. Updates `subscriptions` table (status, plan, period end).
4. Creates `in_app_notification` for the user.
5. Returns 200 OK.

### Future License Check Flow

1. Frontend polls `GET /api/billing/license` on page load and every 5 min.
2. Backend checks subscription status and period end.
3. Returns plan, features, and upgrade_required flag if expired.
4. Frontend uses `require_feature` for feature-gated actions.

### API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/billing/license` | GET | JWT | Current license status + features |
| `/api/billing/plans` | GET | JWT | Available plans with pricing |
| `/api/billing/start-checkout` | POST | JWT | Start checkout (placeholder) |
| `/api/billing/manage` | POST | JWT | Billing portal (placeholder) |
| `/api/app/check-update` | POST | JWT | Check for app updates |
| `/api/app/releases/latest` | GET | JWT | Latest release details |
| `/api/app/register-device` | POST | JWT | Register/update device |
| `/api/app/notifications` | GET | JWT | List in-app notifications |
| `/api/app/notifications/{id}/seen` | POST | JWT | Mark notification as seen |
