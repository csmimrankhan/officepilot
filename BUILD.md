# BUILD.md

How to take a clean checkout of OfficePilot AI all the way to a
signed, installable Windows desktop bundle. The phases are
ordered; do not skip ahead.

## 0. Prerequisites

- **Python 3.11+** (3.12 works).
- **Node 20+** with `npm`.
- **Rust toolchain** (`rustup`, `cargo`, MSVC build tools) on
  Windows. *Not required for backend / frontend tests or for
  rebuilding the Python sidecar binary; only needed for the
  Tauri MSI / NSIS bundle step at the bottom.*
- **PyInstaller 6.x** for the sidecar rebuild.
- (Optional) **Playwright 1.44+** for the Phase 12 browser
  automation "live" mode. Without Playwright the sidecar still
  boots and the UI still works; the adapter just stays in
  dry-run mode.

## 1. Backend dev environment

```
cd backend
pip install -r requirements.txt
python -m pytest -q         # 224 tests should pass
python -m uvicorn app.main:app --reload
```

The backend listens on `http://127.0.0.1:8000` by default. If
port 8000 is busy (e.g. Docker), override with
`OFFICEPILOT_AGENT_PORT=8765 python -m uvicorn app.main:app`.

## 2. Frontend dev environment

```
cd frontend
npm install
npm test -- --run           # 94 tests should pass
npm run dev                 # http://localhost:5173
```

The dev server expects the backend at `VITE_API_BASE` (default
`http://127.0.0.1:8000`).

## 3. Phase 12 browser automation — installing Playwright

The app boots without Playwright. To enable the real Chromium
backend (instead of the dry-run fallback):

```
pip install playwright
playwright install chromium
```

The first `playwright install` pulls ~150 MB of Chromium into
the user's `AppData/Local/ms-playwright` folder. Subsequent
runs use the cached binary.

Set `BROWSER_AUTOMATION_ENABLED=true` (or toggle the master
switch in the **Browser Settings** page) to actually run
Playwright. Set `BROWSER_HEADLESS=true` to suppress the
visible browser window during local drills.

## 4. Rebundling the Python sidecar

The Tauri supervisor spawns a single `officepilot-agent.exe`
binary. After a backend code change you must rebuild and
copy it into the Tauri binary directory:

```
cd backend
pyinstaller scripts/officepilot_sidecar.spec --noconfirm --clean
copy dist\officepilot-agent.exe ..\desktop\tauri\src-tauri\binaries\officepilot-agent-x86_64-pc-windows-msvc.exe
```

Cold boot (first run after `git clean` / OS restart) takes
~15-20 s on this dev machine because Windows Defender scans
the new ~110 MB binary. Warm restarts are 3-5 s.

The Tauri `externalBin` config and the spec file path must
stay in sync. The filename in `binaries/` is hard-coded in
`desktop/tauri/src-tauri/tauri.conf.json` under `bundle.externalBin`.

## 5. Tauri desktop build (requires Rust)

```
cd desktop/tauri/src-tauri
cargo tauri dev          # local dev with the live sidecar
cargo tauri build        # MSI + NSIS bundle
```

Artifacts land in `desktop/tauri/src-tauri/target/release/bundle/`.
The MSI and NSIS bundle folders are picked up by the signing
wrapper.

## 6. Code signing

`scripts/sign_installers.ps1` is the env-gated wrapper:

```
$env:OFFICEPILOT_CERT_THUMBPRINT = '77C7F1A2AD879B2A55EDD1C9D726F9A9C66E46CA'
pwsh scripts/sign_installers.ps1
```

Without the thumbprint the script no-ops so it is safe to run
in CI. The dev cert (`CN=OfficePilot Dev Code Sign`) is a
30-day self-signed cert and is only present on the build box.

## 7. Smoke tests after a fresh build

- [ ] `cd backend && python -m pytest -q` → 224 passed.
- [ ] `cd frontend && npm test -- --run` → 94 passed.
- [ ] `python -m uvicorn app.main:app` and `curl http://127.0.0.1:8000/api/health` returns `phase: 12, version: 0.12.0`.
- [ ] `cd frontend && npm run dev` opens the SPA and shows "Phase 12 · Browser Automation" in the sidebar.
- [ ] `Browser Settings` page loads; toggling the master switch persists across page refreshes.
- [ ] `Browser Test Form` page renders the local form iframe.
- [ ] `Voice Intents` page lists `open_google_sheet` and `create_quickbooks_entry`; the latter's Preview button is disabled with a "Blocked" reason.
- [ ] (Optional) `playwright install chromium`, then `BROWSER_AUTOMATION_ENABLED=true` and `/api/browser/status` returns `adapter_mode: "playwright", live: true`.

## Known blockers (carried from AGENTS.md)

- Docker hogs port 8000 on the dev machine. Workaround: set `OFFICEPILOT_AGENT_PORT`.
- Rust toolchain is not installed on the current dev machine. The Tauri MSI / NSIS bundles are last-built Phase 9 (0.8.0); rebuild on a Rust-capable box.
- PyInstaller rebuilds of the 110 MB sidecar take ~25-30 min the first time (Windows Defender first-run scan). Subsequent warm starts are 3-5 s.
