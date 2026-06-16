# OfficePilot AI — Desktop Build Guide (Phase 8)

This document walks through everything you need to install Rust,
build the bundled Python sidecar, and produce a Windows
installer for the OfficePilot AI desktop shell.

> **Scope.** This guide is for the **Tauri 2.0** shell
> (`desktop/tauri/`) and the **PyInstaller** sidecar
> (`backend/officepilot_sidecar.py`). The web stack (backend +
> frontend) has its own READMEs.

---

## 1. Install Rust

The desktop shell is a Tauri 2.0 app, so you need the Rust
toolchain that targets `x86_64-pc-windows-msvc`.

```powershell
# 1. rustup (the official installer)
winget install Rustlang.Rustup

# 2. Set the default toolchain to the MSVC target Tauri expects
rustup default stable-x86_64-pc-windows-msvc

# 3. Make sure the target is installed
rustup target add x86_64-pc-windows-msvc

# 4. Verify
rustc --version     # rustc 1.77+
cargo --version     # cargo 1.77+
```

### 1.1 Visual Studio Build Tools

`rustc` on Windows ships with `rustup` but **not** with the
MSVC linker. Install the **Build Tools for Visual Studio**
with the *Desktop development with C++* workload
(<https://visualstudio.microsoft.com/visual-cpp-build-tools/>).
The setup wizard offers the workload under the *Individual
components* tab if you do not want the full IDE.

After installation, confirm `link.exe` is on PATH:

```powershell
where.exe link.exe
```

### 1.2 WebView2

Tauri 2.0 uses the system WebView2 runtime. It is preinstalled
on Windows 11; on Windows 10 install the Evergreen Bootstrapper
from
<https://developer.microsoft.com/microsoft-edge/webview2/>.

---

## 2. Install Node.js 18+

Already required for the frontend. Use `winget`, `nvm`, or the
official installer:

```powershell
winget install OpenJS.NodeJS.LTS
node --version   # v18+
npm  --version
```

---

## 3. Install Python 3.11+ (build-time only)

End users of the **bundled** installer do **not** need Python
on their machine. You only need Python locally to build the
PyInstaller sidecar.

```powershell
winget install Python.Python.3.11
# or use pyenv-win / the official installer with "Add to PATH"
python --version
```

`backend/requirements.txt` already lists the runtime deps
(fastapi, uvicorn, sqlalchemy, pymupdf, pdfplumber,
pytesseract, Pillow, openpyxl, cryptography, google-*,
requests, etc.). The sidecar build script installs them in a
vEnv-friendly way.

---

## 4. Build the bundled Python sidecar

```powershell
cd C:\path\to\Officecopilot
.\scripts\build_sidecar_windows.ps1
```

What the script does:

1. `pip install -r backend/requirements.txt` + PyInstaller.
2. `pyinstaller --noconfirm --clean scripts/officepilot_sidecar.spec`.
3. Copies the produced `officepilot-agent.exe` from
   `backend/dist/` to
   `desktop/tauri/src-tauri/binaries/officepilot-agent-x86_64-pc-windows-msvc.exe`.

Useful flags:

```powershell
.\scripts\build_sidecar_windows.ps1 -Clean         # wipe build/ + dist/ first
.\scripts\build_sidecar_windows.ps1 -SkipInstall   # skip the pip step
```

Expected artefacts:

- `backend/dist/officepilot-agent.exe` (~80-110 MB, frozen
  Python 3.11 + every parser / OCR / Excel dep).
- `desktop/tauri/src-tauri/binaries/officepilot-agent-x86_64-pc-windows-msvc.exe`.

---

## 5. Run the desktop shell in dev

### 5.1 System Python mode (recommended for FastAPI work)

```powershell
cd desktop\tauri
$env:USE_SYSTEM_PYTHON_AGENT = "true"
cargo tauri dev
```

The supervisor spawns `python -m uvicorn app.main:app` from
your local interpreter. Hot-reload the Python side by
restarting the desktop shell (Ctrl-C in the cargo tauri
terminal, then `cargo tauri dev` again).

### 5.2 Bundled sidecar mode (recommended for release testing)

```powershell
cd desktop\tauri
# Confirm the sidecar binary is in place
ls src-tauri\binaries\officepilot-agent-x86_64-pc-windows-msvc.exe
cargo tauri dev
```

The supervisor launches the bundled `.exe` and reads the
`OFFICEPILOT_SIDECAR=1` env var the sidecar sets itself.

### 5.3 Verifying the supervisor state

Open the **Local Agent** page in the UI. The four pills are:

| State     | Pill colour  | Trigger                                            |
| --------- | ------------ | -------------------------------------------------- |
| `starting`| amber        | The sidecar was just spawned.                      |
| `online`  | green        | `GET /api/health` returned 2xx.                    |
| `offline` | red          | The sidecar is not running or probes are failing.  |
| `failed`  | red (bold)   | Auto-respawn cap reached; press **Retry** to reset.|

When `state == failed` a `Retry` button appears under the
status summary. `Retry` calls `request_agent_retry`, which
resets the restart cap and re-spawns the child.

### 5.4 Supervisor / probe architecture (Phase 9)

The supervisor was split into two cooperating tasks in Phase
9 so the network probe never blocks the spawn/reap loop:

- **Supervisor thread** (`std::thread`): spawn / reap child
  process, refresh uptime, emit status events. Ticks every
  1 s.
- **Health-probe task** (`tauri::async_runtime::spawn`):
  performs `GET /api/health` against the sidecar every
  `HEALTH_INTERVAL_OK = 15s` when healthy and
  `HEALTH_INTERVAL_DOWN = 3s` when not. The blocking `ureq`
  call is wrapped in `spawn_blocking` so it does not stall
  the runtime.

The probe task also owns the "is the agent healthy?"
transitions (`online` / `offline`) and resets the consecutive
failure counter when it sees a healthy response. The
supervisor thread only flips `starting` / `failed`.

---

## 6. Build the Windows installer

```powershell
cd desktop\tauri
cargo tauri build
```

Outputs land in `desktop\tauri\src-tauri\target\release\bundle\`:

- `msi/OfficePilot AI_0.8.0_x64_en-US.msi`
- `nsis/OfficePilot AI_0.8.0_x64-setup.exe`

The bundle includes:

- `OfficePilot AI.exe` — the Tauri shell.
- `binaries/officepilot-agent-x86_64-pc-windows-msvc.exe` —
  the bundled sidecar.
- The React UI in `_up_/...` (the `frontendDist` is
  `../../frontend/dist`).
- WebView2 bootstrapper (so Windows 10 users get WebView2
  automatically).

### 6.1 Unsigned-installer warning

The MSI / NSIS produced by this build is **unsigned**. The
first install triggers a Windows SmartScreen warning. The user
can click *More info → Run anyway*. This is acceptable for an
internal / pilot build but **not** for production distribution.

### 6.2 Code signing (Phase 9 — wired but gated by env var)

`tauri.conf.json -> bundle.windows` carries the SHA1
`certificateThumbprint` placeholder, the timestamp URL, the
digest algorithm, and a `signCommand` that delegates to
`scripts/sign_installers.ps1`. Tauri invokes that command
*after* each `.exe` / `.msi` is built, so no manual
post-step is needed. The script silently **skips signing**
when the env var is absent so dev / CI builds still work.

**Setup on the release machine:**

1. Acquire a code-signing certificate (DigiCert, Sectigo,
   GlobalSign, or Azure Trusted Signing).
2. Import the cert into `Cert:\CurrentUser\My` (PowerShell
   `Import-PfxCertificate`).
3. Set the env var before invoking `cargo tauri build`:

   ```powershell
   $env:OFFICEPILOT_CERT_THUMBPRINT = "AABBCCDDEEFF00112233445566778899AABBCCDD"
   $env:OFFICEPILOT_TIMESTAMP_URL    = "http://timestamp.sectigo.com"   # optional
   $env:OFFICEPILOT_SIGN_DESCRIPTION = "OfficePilot AI"                 # optional
   cd desktop\tauri
   cargo tauri build
   ```

4. Verify the signature:

   ```powershell
   Get-AuthenticodeSignature `
     "src-tauri\target\release\bundle\nsis\OfficePilot AI_0.8.0_x64-setup.exe" `
     | Select-Object Status, SignerCertificate, TimeStamperCertificate
   ```

   A valid signature reads `Valid`; with a self-signed dev
   cert you'll see `UnknownError` ("chain terminated in a
   root certificate which is not trusted by the trust
   provider") which is expected.

`scripts/sign_installers.ps1` can also be run by hand
against any subset of files:

```powershell
..\scripts\sign_installers.ps1 `
    "src-tauri\target\release\bundle\msi\OfficePilot AI_0.8.0_x64_en-US.msi"
```

The script auto-discovers the latest `*.exe` / `*.msi` under
`target/release/bundle/{msi,nsis}/` when called with no
arguments.

### 6.3 Auto-update (Phase 9 — plugin enabled, endpoint still TODO)

`tauri-plugin-updater` is a dependency in
`desktop/tauri/src-tauri/Cargo.toml` and is **initialised** in
`src/lib.rs` via `tauri_plugin_updater::Builder::new().build()`.
The plugin itself only registers the JS-side `check()` /
`install()` commands — it does not poll on its own. The
manifest is scaffolded in `tauri.conf.json -> plugins.updater`
with a placeholder URL and pubkey.

To turn on real auto-update in a later release:

1. Stand up an HTTPS endpoint that serves a `*.json` manifest:
   ```json
   {
     "version": "0.9.0",
     "notes": "...",
     "pub_date": "2026-07-01T00:00:00Z",
     "platforms": {
       "windows-x86_64": {
         "signature": "...",
         "url": "https://updates.officepilot.example/.../OfficePilot_0.9.0_x64-setup.exe"
       }
     }
   }
   ```
2. Generate a keypair with `tauri signer generate -w
   ~/.tauri/officepilot.key` and paste the **public** key
   into `tauri.conf.json -> plugins.updater.pubkey`.
3. Sign each release artefact with `tauri signer sign -k
   ~/.tauri/officepilot.key
   target/release/bundle/nsis/OfficePilot_*.exe`.
4. Replace the placeholder URL in `plugins.updater.endpoints`.
5. Have the React layer invoke
   `import { check } from "@tauri-apps/plugin-updater"; await check();`
   on a "Check for updates" button — *not* on every launch.

---

## 7. Troubleshooting

### 7.1 `cargo tauri dev` fails with `link.exe not found`

You need the Visual Studio Build Tools *Desktop development
with C++* workload. See §1.1.

### 7.2 Sidecar spawns but `/api/health` never returns

1. Open the **Local Agent** page; the pill will be
   `starting` → `offline`.
2. Check `data/logs/sidecar.log` (or
   `%LOCALAPPDATA%\OfficePilot AI\data\logs\sidecar.log` on a
   bundled install) for the sidecar's stderr output.
3. If you see `ImportError: No module named 'app.main'`, the
   PyInstaller spec is missing a hidden import. Re-run
   `scripts/build_sidecar_windows.ps1 -Clean` and look for
   warnings at the end of the PyInstaller log.
4. If you see `PermissionError: [Errno 13]`, another process
   is bound to port 8000. Either stop the other process or
   set `OFFICEPILOT_AGENT_PORT=8123` before launching.

### 7.3 Sidecar build is huge (>200 MB)

The default PyInstaller output includes some heavy optional
deps. The `excludes=` list in `scripts/officepilot_sidecar.spec`
already trims `tkinter`, `test`, `unittest`, `pydoc`,
`doctest`, `matplotlib`, `numpy.tests`. If you do not use
PaddleOCR, also exclude `paddleocr` / `paddle` from the spec.

### 7.4 SmartScreen blocks the installer

Expected — the installer is unsigned. Click *More info →
Run anyway*. See §6.1 / §6.2 for the code-signing recipe.

### 7.5 WebView2 install hangs on Windows 10

The NSIS bundle has `webviewInstallMode.type =
"downloadBootstrapper"`, which downloads the WebView2 runtime
on first launch. If the host is offline, switch to
`"embedBootstrapper"` in `tauri.conf.json -> bundle.windows`
or preinstall the Evergreen Runtime.

### 7.6 Vite dev server cannot bind 5173

Another process is using the port. Either free the port or
override `devUrl` in `tauri.conf.json -> build.devUrl`. The
frontend `.env` (`VITE_API_BASE`) and the Tauri shell's
`OFFICEPILOT_AGENT_HOST` / `OFFICEPILOT_AGENT_PORT` are
independent — they do not need to agree on a port.

---

## 8. Verification checklist

Before tagging a release, run through this list on a clean
Windows 10 / 11 VM.

- [ ] Rust toolchain installs cleanly (`rustc --version`).
- [ ] `.\scripts\build_sidecar_windows.ps1` produces a
      `officepilot-agent-x86_64-pc-windows-msvc.exe` in
      `src-tauri/binaries/`.
- [ ] `cargo tauri dev` opens a 1280x800 window.
- [ ] The **Local Agent** page shows `Agent Online`.
- [ ] `GET /api/health` returns 200 with `"ok": true` and
      `"sidecar.mode": "bundled"`.
- [ ] Tray menu opens the main window and exits cleanly.
- [ ] Uploading a PDF / running the parser benchmark still
      works (no regressions).
- [ ] `cargo tauri build` produces
      `bundle/msi/OfficePilot AI_0.8.0_x64_en-US.msi` and
      `bundle/nsis/OfficePilot AI_0.8.0_x64-setup.exe`.
- [ ] Installing the MSI on a clean VM launches the app and
      connects to the bundled agent (no Python on the VM).
- [ ] `data/logs/sidecar.log` records startup.
- [ ] `cargo tauri dev` with
      `USE_SYSTEM_PYTHON_AGENT=true` uses system Python (the
      agent's `/api/health -> sidecar.mode` reads
      `system-python`).

---

## 9. See also

- `desktop/tauri/README.md` — the *Tauri* layer overview.
- `docs/SIDECAR_PACKAGING.md` — the *PyInstaller* layer
  details (hidden imports, excludes, data files, troubleshooting).
- `backend/README.md` — the FastAPI agent.
- `frontend/README.md` — the React UI.
