# Tauri Auto-Updater

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Tauri App   │────▶│ Backend          │────▶│ app_releases DB  │
│ (Rust)      │     │ /api/app/updater │     │ table            │
│             │     │ /windows/stable  │     │                  │
│ updater     │     │                  │     │ version          │
│ plugin      │◀────│ returns Tauri-   │◀────│ updater_sig      │
│ checks      │     │ compatible JSON  │     │ artifact_url     │
│ every hour  │     │                  │     │ pub_date         │
└─────────────┘     └──────────────────┘     └──────────────────┘
```

### Components

1. **tauri-plugin-updater (Rust)** — installed in `Cargo.toml`, registered in `lib.rs`.
2. **@tauri-apps/plugin-updater (JS)** — frontend API for check/download/install.
3. **`tauri.conf.json`** — `plugins.updater` block with endpoints, pubkey, install mode.
4. **Backend `/api/app/updater/windows/stable`** — returns Tauri v2 updater JSON.
5. **`app_releases` DB table** — stores version, signature, artifact URL, pub_date.
6. **Admin `/api/admin/releases`** — POST to create, GET to list, DELETE to remove.

## Signing Key Generation

```powershell
cd desktop/tauri
npx tauri signer generate `
  --password "your-key-password" `
  --write-keys .updater-private-key.pem
```

This creates two files:

- `.updater-private-key.pem` — **SECRET** private key. Never commit.
- `.updater-private-key.pem.pub` — Public key. Add to `tauri.conf.json`.

### Public Key Location

The public key is stored in:

```
desktop/tauri/src-tauri/tauri.conf.json → plugins.updater.pubkey
```

### Private Key Storage

**Development:**
- File: `desktop/tauri/.updater-private-key.pem`
- Env: `TAURI_SIGNING_PRIVATE_KEY_PATH` or `TAURI_SIGNING_PRIVATE_KEY`
- Env: `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`

**Production (CI/CD):**
- Store as GitHub Actions secret or secure vault variable.
- Never check the private key into version control.
- Use `TAURI_SIGNING_PRIVATE_KEY` environment variable in CI.

### How to Rotate Key

1. Generate a new key pair:
   ```powershell
   npx tauri signer generate --password "new-password" --write-keys .updater-new-key.pem
   ```
2. Extract the new public key:
   ```powershell
   Get-Content .updater-new-key.pem.pub
   ```
3. Update `tauri.conf.json` → `plugins.updater.pubkey` with the new public key.
4. Update signing env vars to use the new private key.
5. Sign the next release with the new key.
6. Delete the old private key.
7. Update `.env.updater.example` with the new key path/password.

### What Happens if Key is Lost

- **Cannot sign new updates.** Users will not receive updates.
- **Cannot re-sign old releases.** The new key produces different signatures.
- **Cannot validate existing signatures.** Each release's signature is tied to the key.
- **Mitigation:** Store the private key in multiple secure locations:
  - Local encrypted file
  - Password manager
  - CI/CD secrets (GitHub Actions, etc.)

If the key is permanently lost, a new key must be generated and users must do a full reinstall of the latest version signed with the new key.

## Local Update Test

### Prerequisites

1. Build 0.36.0 installer (baseline).
2. Build 0.36.1 signed artifact.
3. Seed 0.36.1 release in the database.
4. Backend running on port 8765.

### Steps

```powershell
# 1. Generate signing key (one-time)
cd desktop/tauri
npx tauri signer generate --password "test" --write-keys .updater-private-key.pem

# 2. Build 0.36.0 (baseline)
# Edit version in Cargo.toml, tauri.conf.json, package.json to 0.36.0
npx tauri build

# 3. Install 0.36.0 MSI/NSIS

# 4. Bump version to 0.36.1 across all sources

# 5. Build 0.36.1 with signing
$env:TAURI_SIGNING_PRIVATE_KEY_PATH=".updater-private-key.pem"
$env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD="test"
npx tauri build

# 6. Sign the artifact
npx tauri signer sign `
  --private-key-path ".updater-private-key.pem" `
  --password "test" `
  "src-tauri/target/release/bundle/msi/OfficePilot AI_0.36.1_x64_en-US.msi"

# 7. Copy artifact + signature to releases folder
mkdir ../../releases/0.36.1 -Force
Copy-Item "src-tauri/target/release/bundle/msi/OfficePilot AI_0.36.1_x64_en-US.msi" "../../releases/0.36.1/"
Copy-Item "src-tauri/target/release/bundle/msi/OfficePilot AI_0.36.1_x64_en-US.msi.sig" "../../releases/0.36.1/"

# 8. Seed release in DB
# Use admin API or direct DB insert

# 9. Start backend
cd backend
python -m uvicorn app.main:app --port 8765

# 10. Open the 0.36.0 app
# The UpdateBanner should show 0.36.1 available.
# Click "Download & Install" — app downloads, verifies signature, installs, restarts.
```

### Expected Result

1. App checks updater endpoint → receives 0.36.1 JSON with signature.
2. UpdateBanner shows "Update available: v0.36.1".
3. User clicks update.
4. App downloads signed MSI.
5. Signature verifies against the public key in `tauri.conf.json`.
6. App installs silently (passive mode).
7. App restarts.
8. App version becomes 0.36.1.

## Production Updater Endpoint

**Endpoints:**

| Environment | URL |
|-------------|-----|
| Development | `http://localhost:8765/api/app/updater/windows/stable` |
| Production | `https://officepilot.ai/api/app/updater/windows/stable` |

Update `tauri.conf.json` → `plugins.updater.endpoints` for production:

```json
{
  "plugins": {
    "updater": {
      "active": true,
      "endpoints": [
        "https://officepilot.ai/api/app/updater/windows/stable"
      ],
      "pubkey": "<public-key>",
      "windows": { "installMode": "passive" }
    }
  }
}
```

**Response format** (Tauri v2 compatible):

```json
{
  "version": "0.36.1",
  "notes": "Bug fixes and performance improvements.",
  "pub_date": "2026-06-12T00:00:00Z",
  "platforms": {
    "windows-x86_64": {
      "signature": "dW50cnVzdGVk...",
      "url": "https://officepilot.ai/static/releases/0.36.1/OfficePilot%20AI_0.36.1_x64_en-US.msi"
    }
  }
}
```

## Release Artifact Upload

After building, artifacts are stored in:

```
releases/<version>/
  OfficePilot AI_<version>_x64_en-US.msi
  OfficePilot AI_<version>_x64_en-US.msi.sig
```

For production, upload to your static hosting (e.g., CDN, S3, or the backend's `static/releases/` mount).

The backend automatically serves the `releases/` directory at `/static/releases/`.

To seed a release via admin API:

```bash
curl -X POST http://localhost:8765/api/admin/releases \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "0.36.1",
    "platform": "windows",
    "channel": "stable",
    "target": "windows-x86_64",
    "artifact_type": "msi",
    "download_url": "http://localhost:8765/static/releases/0.36.1/OfficePilot%20AI_0.36.1_x64_en-US.msi",
    "updater_artifact_url": "http://localhost:8765/static/releases/0.36.1/OfficePilot%20AI_0.36.1_x64_en-US.msi",
    "updater_signature": "<base64-signature>",
    "pub_date": "2026-06-12T00:00:00Z",
    "release_notes": "Updater test release.",
    "minimum_required_version": "0.36.0",
    "is_critical": false
  }'
```

### Admin Release Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/releases` | GET | List all releases |
| `/api/admin/releases` | POST | Create new release (admin only) |
| `/api/admin/releases/{id}` | DELETE | Remove release (admin only) |

### Other Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/app/register-device` | POST | Register device for update tracking |
| `/api/app/check-update` | POST | Backend-side update check |
| `/api/app/releases/latest` | GET | Get latest release metadata |
| `/api/app/updater/windows/stable` | GET | Tauri updater manifest |

## Rollback Strategy

If an update fails or causes issues:

1. **User-initiated rollback:** Users can reinstall the previous MSI manually.
2. **Critical update override:** Set `is_critical=true` to force users to update.
3. **Minimum version enforcement:** Set `minimum_required_version` — the app can block usage if below the minimum.
4. **DB-persisted releases:** Old releases remain in the database; can be re-seeded as the "latest" if needed.

## Critical Update Flow

When `is_critical=true` is set:

1. The `check-update` endpoint returns `{ critical: true, blocked: true }`
2. The `UpdateBanner` shows a red banner with "Critical update required"
3. The Tauri updater plugin shows a mandatory update prompt
4. The user must update to continue using the app

## Full Module Regression Checklist

After each update:

### Authentication
- [ ] Login works
- [ ] Logout works
- [ ] Token refresh works

### Infrastructure
- [ ] Device registration updates app_version
- [ ] License endpoint returns valid status
- [ ] Billing page renders correctly
- [ ] Update check returns correct version
- [ ] Sidecar health reports "Ready"/"online"

### Excel Automation
- [ ] Create Excel summary works
- [ ] File picker works
- [ ] Output file generated
- [ ] Original file unchanged

### Browser Automation
- [ ] Export monthly P&L works
- [ ] Browser cards render
- [ ] Manual login card shows
- [ ] Guided download card shows

### Gmail Read-Only
- [ ] Download invoice attachments works
- [ ] Gmail cards render
- [ ] Mock download works
- [ ] Create Excel summary from attachment works
- [ ] Send/forward/delete/move/mark-read blocked

### Workflow Recorder
- [ ] Record workflow works
- [ ] Overlay visible during recording
- [ ] Stop recording works
- [ ] Preview events works
- [ ] Convert to skill draft works
- [ ] Save skill works

### Skills
- [ ] Saved skill matches on command
- [ ] Dry-run required before live execution
- [ ] Live execution blocked without approval

### Voice
- [ ] Voice command center loads
- [ ] Stop phrase does not duplicate transcript

### Safety
- [ ] "transfer money from bank" blocked
- [ ] "delete all emails" blocked
- [ ] "send email to vendor" blocked
- [ ] "forward invoice emails" blocked
- [ ] "bypass security" blocked
- [ ] "delete accounting records" blocked
- [ ] "enter password" blocked

### Emergency
- [ ] Emergency stop works
- [ ] No active run returns clean response

## Release QA Script

Run the full QA script before shipping:

```powershell
.\scripts\release_qa_windows.ps1
```

For a quick smoke check against a running backend:

```powershell
.\scripts\release_qa_windows.ps1 -SkipBuild -SkipTauri -ApiBaseUrl "http://localhost:8765"
```
