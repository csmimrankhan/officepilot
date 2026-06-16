# OfficePilot AI — Tauri Desktop Shell

Phases 7 and 8 of the OfficePilot AI build introduce a **Windows
desktop shell** that hosts the existing React UI + FastAPI agent
in a single Tauri window with a system tray.

| Folder          | What it is                                           |
| --------------- | ---------------------------------------------------- |
| `../../backend` | FastAPI agent (Python) — the local AI runtime        |
| `../../frontend`| React + Vite UI — the page tree the user sees        |
| `./src-tauri`   | This Tauri (Rust) desktop shell                       |
| `../../scripts` | PyInstaller build script for the bundled sidecar     |

## What Phase 8 ships (on top of Phase 7)

- A **bundled PyInstaller sidecar** that ships the Python agent
  inside the installer. End users no longer need a Python
  install on their machine.
- A supervisor that can launch the agent in two modes:
  - **Bundled sidecar** — the production default.
  - **System Python** — opt-in for development, toggled by
    setting the `USE_SYSTEM_PYTHON_AGENT=true` environment
    variable before `cargo tauri dev`.
- A new `AgentState` enum (`starting` / `online` / `offline` /
  `failed`) surfaced to the UI as four coloured pills on the
  **Local Agent** page, plus a `Retry` button.
- `GET /api/health` is a real HTTP probe (using `ureq`).
- MSI + NSIS installers are configured; the unsigned-installer
  warning and code-signing TODOs are documented in
  `../../docs/DESKTOP_BUILD.md`.
- `tauri-plugin-updater` is wired into `Cargo.toml` and a TODO
  in `src/lib.rs` explains why the plugin is *not* enabled by
  default (no public manifest / signing key yet).

## What Phase 9 ships (on top of Phase 8)

- **End-to-end `cargo tauri build`** — Rust 1.96.0 + MSVC
  14.44.35207 + Windows 11 SDK 10.0.26100.0. Both the MSI
  (`OfficePilot AI_0.8.0_x64_en-US.msi`) and the NSIS
  installer (`OfficePilot AI_0.8.0_x64-setup.exe`) were
  produced successfully and live under
  `target/release/bundle/{msi,nsis}/`.
- **Code signing wired in** — `tauri.conf.json ->
  bundle.windows` exposes
  `certificateThumbprint` / `timestampUrl` /
  `digestAlgorithm` / `signCommand` (the last delegates
  to `scripts/sign_installers.ps1`). The script reads
  `OFFICEPILOT_CERT_THUMBPRINT` from the env and signs
  every produced `.exe` / `.msi` with `signtool.exe` plus
  a Sectigo timestamp. With the env var absent the script
  is a no-op so dev builds still work.
- **Auto-update plugin enabled** — `lib.rs` now calls
  `tauri_plugin_updater::Builder::new().build()` so the
  JS-side `check()` / `install()` commands are
  available. The plugin does not auto-poll; the React
  layer is expected to call `check()` on a "Check for
  updates" button. The manifest URL and pubkey are still
  placeholders.
- **Async health probe** — the supervisor was split into
  a `std::thread` (spawn / reap, 1 s tick) and an async
  `spawn_probe_task` that runs `ureq` inside
  `spawn_blocking` and uses `tokio::time::sleep` for the
  15 s (healthy) / 3 s (down) cadence. The supervisor
  thread is no longer blocked on network I/O.
- **Spec path bug fixed** —
  `scripts/officepilot_sidecar.spec` had a
  `Path(SPECPATH).resolve().parent` off-by-one that
  resolved `backend/` to `Desktop/backend/` instead of
  `Officecopilot/backend/`. The sidecar build now
  resolves correctly on every invocation.

## What Phase 7 + 8 + 9 explicitly do **not** include

- Full desktop automation (mouse / keyboard hooks).
- Screen capture, OCR of the user's screen.
- Workflow recording.
- macOS / Linux sidecar builds (Windows-only).
- Browser-Use / Playwright automation. No outbound browser
  control from the desktop shell.

> Phase 9 *does* sign the MSI / NSIS bundles when
> `OFFICEPILOT_CERT_THUMBPRINT` is set, and *does* enable
> the auto-update plugin. The manifest URL + signing pubkey
> are still placeholders, so live updates remain a
> follow-up.

## Prerequisites

1. **Rust** (MSVC toolchain). Install via [rustup](https://rustup.rs):

       winget install Rustlang.Rustup
       rustup default stable-x86_64-pc-windows-msvc
       rustup target add x86_64-pc-windows-msvc

   Verify with `rustc --version` and `cargo --version`.

2. **Microsoft Visual Studio Build Tools** with the *Desktop
   development with C++* workload. rustup-msvc will need the
   MSVC linker (`link.exe`).

3. **WebView2 Runtime** (preinstalled on Windows 11; on Windows
   10 install it from
   <https://developer.microsoft.com/microsoft-edge/webview2/>).

4. **Node.js 18+** (already required for the frontend).

5. **Python 3.11+** — only required when you want to **build
   the sidecar** (`scripts/build_sidecar_windows.ps1`) or run
   the agent in `USE_SYSTEM_PYTHON_AGENT` mode. End users of
   the bundled installer do **not** need Python on their
   machine.

6. **PyInstaller 6+** — installed automatically by the build
   script.

## First-time setup

From the repo root:

```powershell
# 1. Install JS deps for the frontend
cd ..\..\frontend
npm install

# 2. Build the React UI once so the Tauri release config
#    has a dist/ to point at
npm run build

# 3. (Production) Build the bundled Python sidecar
cd ..\..
.\scripts\build_sidecar_windows.ps1
```

The sidecar build places
`officepilot-agent-x86_64-pc-windows-msvc.exe` into
`desktop/tauri/src-tauri/binaries/`. Tauri picks it up
automatically via `tauri.conf.json -> bundle.externalBin`.

## Development run (system Python)

For day-to-day Python development — when you want to iterate
on the FastAPI code without rebuilding the sidecar binary —
launch `cargo tauri dev` with the system-Python flag:

```powershell
cd desktop\tauri
$env:USE_SYSTEM_PYTHON_AGENT = "true"
cargo tauri dev
```

This will:

1. Run `npm --prefix ../../frontend run dev` (Vite on
   `http://localhost:5173`).
2. Compile the Rust binary.
3. Open a 1280x800 window pointed at the Vite dev server.
4. Spawn `python -m uvicorn app.main:app --host 127.0.0.1
   --port 8000` as a child process.
5. Poll `http://127.0.0.1:8000/api/health` every 15 s
   (3 s while unhealthy) and restart on failure.
6. Show a green "Agent Online" pill in the **Local Agent** page.

## Development run (bundled sidecar)

If you want to test the bundled binary in dev (recommended
before tagging a release):

```powershell
cd desktop\tauri
# Make sure the sidecar is in place
.\..\..\scripts\build_sidecar_windows.ps1
cargo tauri dev
```

The supervisor will launch
`binaries/officepilot-agent-x86_64-pc-windows-msvc.exe` instead
of system Python. The agent's `/api/health` response will
include `"sidecar": {"bundled": true, "frozen": true,
"mode": "bundled"}`.

## Production build (Windows MSI + NSIS)

```powershell
cd desktop\tauri
cargo tauri build
```

Outputs go to `desktop\tauri\src-tauri\target\release\bundle\`:

- `msi/OfficePilot AI_0.8.0_x64_en-US.msi`
- `nsis/OfficePilot AI_0.8.0_x64-setup.exe`

Both bundles are **unsigned**. Windows SmartScreen will warn
on first install. See `../../docs/DESKTOP_BUILD.md` for the
code-signing recipe and the auto-update TODO.

## Agent state model

The supervisor in `src/agent.rs` exposes a four-state
machine to the UI:

| State     | Pill colour  | Meaning                                                     |
| --------- | ------------ | ----------------------------------------------------------- |
| `starting`| amber        | The sidecar was just spawned; first probe in flight.        |
| `online`  | green        | `GET /api/health` answered 2xx in the last probe.           |
| `offline` | red          | No child is running, or the last probe failed.              |
| `failed`  | red (bold)   | Auto-respawn cap reached; the user must press **Retry**.    |

The state is broadcast to the React UI as a Tauri event
`agent://status` carrying the latest `AgentStatus` snapshot.
The UI also calls `get_agent_status` on mount and every 5
seconds, so a missed event still recovers.

## Tray menu

| Entry              | Behaviour                                            |
| ------------------ | ---------------------------------------------------- |
| Open InvoicePilot  | Show + focus main window                              |
| Sync invoices      | Show window + emit `tray://sync` (UI hits `/api/email-imports/sync`) |
| Pending approvals  | Show window + emit `tray://approvals` (UI navigates to `/workflows/approvals`) |
| Settings           | Show window + emit `tray://settings` (UI navigates to `/local/storage`) |
| Exit               | Kill the sidecar and quit the app                     |

Left-click on the tray icon also shows + focuses the main
window. The **Exit** entry is the only way to fully quit the
app; closing the main window just hides it (Phase 7
behaviour).

## File map

    desktop/tauri/
    |- README.md                       (this file)
    +- src-tauri/
       |- Cargo.toml                   Rust crate manifest (tauri + plugins + ureq + tokio)
       |- tauri.conf.json              Tauri build + window + bundle + externalBin + code-signing config
       |- build.rs                     tauri_build::build()
       |- capabilities/
       |  `- default.json              Tauri 2 capability allowlist (shell:allow-execute for the sidecar)
       |- binaries/
       |  |- README.md                 Sidecar placement instructions
       |  `- officepilot-agent-*.exe   (built by scripts/build_sidecar_windows.ps1)
       |- icons/                       Placeholder PNG/ICO (see icons/README.md)
       +- src/
          |- main.rs                   Windows-subsystem entry point
          |- lib.rs                    Wires tray + agent supervisor + updater + RunEvent exit hook
          |- agent.rs                  Sidecar spawn (bundled | system) + async health probe + state machine
          `- tray.rs                   System tray menu + click handlers

    scripts/
    |- build_sidecar_windows.ps1       PyInstaller wrapper
    |- officepilot_sidecar.spec        PyInstaller spec for the sidecar
    `- sign_installers.ps1             Phase 9: signtool wrapper (env-var gated)

    backend/
    `- officepilot_sidecar.py           Sidecar entry point (frozen-aware)

## Known limitations (Phase 8) — Phase 9 status

- **Installer is unsigned** — *resolved in Phase 9.*
  `tauri.conf.json -> bundle.windows` carries the SHA1
  `certificateThumbprint`, timestamp URL, and a
  `signCommand` that calls
  `scripts/sign_installers.ps1`. The script reads
  `OFFICEPILOT_CERT_THUMBPRINT` from the env and signs
  every produced `.exe` / `.msi` with `signtool.exe` +
  Sectigo timestamp. With the env var absent the script
  is a no-op so dev builds still work.
- **Auto-update is scaffolded but not enabled** — *resolved
  in Phase 9.* `lib.rs` now calls
  `tauri_plugin_updater::Builder::new().build()` so the
  plugin's JS commands (`check()`, `install()`) are
  available. The manifest URL and pubkey are still
  placeholders; a real `tauri signer generate` keypair +
  HTTPS manifest endpoint are needed for live updates.
- **No full desktop control** — out of scope, unchanged.
- **No workflow recording** — out of scope, unchanged.
- **No browser automation** — out of scope, unchanged.
- **Sync `ureq` health probe** — *resolved in Phase 9.*
  The probe was moved into a `tauri::async_runtime::spawn`
  task with `tokio::time::sleep` and a `spawn_blocking`
  wrapper around `ureq`. The supervisor thread only handles
  spawn / reap and is no longer blocked on network I/O.
- **`cargo tauri build` not exercised on the build host** —
  *resolved in Phase 9.* Both the MSI and the NSIS bundle
  were produced successfully against Rust 1.96.0 +
  MSVC 14.44.35207 + Windows 11 SDK 10.0.26100.0.

## Phase 9 changes (recap)

- `src-tauri/Cargo.toml` — added `tokio = { version = "1",
  features = ["time", "rt"] }` for the async probe.
- `src-tauri/src/agent.rs` — split the supervisor into
  a `std::thread` (spawn / reap) and an async
  `spawn_probe_task` (health probe + state transitions).
  `attempts` counter moved into `AgentStateInner` so the
  probe can reset it.
- `src-tauri/src/lib.rs` — `tauri_plugin_updater::Builder::new()
  .build()` initialised unconditionally; the JS layer is
  expected to call `check()` on demand, not on every
  launch.
- `src-tauri/tauri.conf.json` — `bundle.windows` now
  exposes `certificateThumbprint`, `timestampUrl`,
  `digestAlgorithm`, and `signCommand` (delegates to
  `scripts/sign_installers.ps1`).
- `scripts/sign_installers.ps1` — *new* signtool wrapper
  that auto-discovers MSI/NSIS bundles.
- `scripts/officepilot_sidecar.spec` — fixed a
  `Path(SPECPATH).resolve().parent` off-by-one that
  resolved `backend/` to `Desktop/backend/` instead of
  `Officecopilot/backend/`.

## Acceptance checklist (Phase 8) — Phase 9 deltas

- [x] PyInstaller sidecar builds via
      `scripts/build_sidecar_windows.ps1` and lands in
      `src-tauri/binaries/officepilot-agent-x86_64-pc-windows-msvc.exe`.
- [x] Tauri launches the bundled sidecar by default and falls
      back to system Python when
      `USE_SYSTEM_PYTHON_AGENT=true`.
- [x] The Tauri shell kills the sidecar on app exit.
- [x] The supervisor detects a crashed sidecar and surfaces
      a "Failed" pill with a **Retry** button.
- [x] `GET /api/health` is probed with a real HTTP request
      (`ureq`); status < 500 is treated as alive.
- [x] MSI + NSIS bundles are produced by `cargo tauri build`.
- [x] The unsigned-installer limitation is documented.
      **Phase 9:** `scripts/sign_installers.ps1` signs
      every produced artefact when
      `OFFICEPILOT_CERT_THUMBPRINT` is set.
- [x] The auto-update TODO is documented.
      **Phase 9:** `tauri-plugin-updater` is now wired
      in `lib.rs`; the React layer can call `check()` on
      demand.
- [x] **Phase 9:** Health probe is async — the supervisor
      thread never blocks on network I/O.
- [x] **Phase 9:** `cargo tauri build` runs end-to-end on
      the build host (Rust 1.96.0 + MSVC + Win 11 SDK).
- [x] No new DB tables were added; the existing schema is
      unchanged.
- [x] All existing invoice / export / workflow features still
      work through the desktop shell.
