# OfficePilot AI — Sidecar Packaging Guide (Phase 8)

This document explains how the FastAPI agent is bundled into a
single Windows executable with **PyInstaller** and shipped as
the **Tauri sidecar**.

> The Tauri shell spawns the sidecar and supervises it
> (state, health, restart, kill on exit). See
> `desktop/tauri/README.md` for the supervisor side. This
> document focuses on the **Python** build.

---

## 1. What is a sidecar?

A sidecar is a process that ships alongside the main app.
Tauri 2.0 spawns it via the shell plugin and (optionally)
includes it in the installer bundle.

For OfficePilot AI:

- The main app = `OfficePilot AI.exe` (Tauri / Rust).
- The sidecar = `officepilot-agent-x86_64-pc-windows-msvc.exe`
  (PyInstaller-bundled Python + FastAPI).

The Tauri shell places the sidecar at
`desktop/tauri/src-tauri/binaries/officepilot-agent-<target>.exe`
during build time, and bundles it next to `OfficePilot AI.exe`
in the installer.

---

## 2. Files involved

| File                                          | Role                                            |
| --------------------------------------------- | ----------------------------------------------- |
| `backend/officepilot_sidecar.py`              | Entry point PyInstaller bundles.                |
| `scripts/officepilot_sidecar.spec`            | PyInstaller spec (hidden imports, excludes).    |
| `scripts/build_sidecar_windows.ps1`           | PowerShell wrapper that runs PyInstaller.       |
| `desktop/tauri/src-tauri/tauri.conf.json`     | Declares `externalBin`.                         |
| `desktop/tauri/src-tauri/Cargo.toml`          | `tauri-plugin-shell` for the sidecar.           |
| `desktop/tauri/src-tauri/src/agent.rs`        | The supervisor.                                 |
| `desktop/tauri/src-tauri/capabilities/default.json` | `shell:allow-execute` allowlist.          |

---

## 3. The sidecar entry point

`backend/officepilot_sidecar.py` is intentionally tiny. It:

1. Sets `OFFICEPILOT_SIDECAR=1` so the agent can label itself
   in `/api/health -> sidecar.mode`.
2. Resolves the data dir (env var → `%LOCALAPPDATA%/OfficePilot AI/data` → exe dir).
3. Ensures the standard subdirs exist (`logs`, `cache`, `audit`,
   `recordings`, `tmp`).
4. Imports `uvicorn` and runs `app.main:app` exactly as
   `python -m uvicorn` would.

The Tauri supervisor passes `--port` and (optionally) the
bind host via env vars (`OFFICEPILOT_AGENT_HOST`,
`OFFICEPILOT_AGENT_PORT`). The entry point reads them.

The `__main__` block writes a crash log to
`$OFFICEPILOT_DATA_DIR/logs/sidecar_crash.log` if uvicorn
fails to start, so the user can find the cause from the
Privacy Dashboard.

---

## 4. The PyInstaller spec

`scripts/officepilot_sidecar.spec` configures:

- **Entry**: `backend/officepilot_sidecar.py`.
- **Hidden imports**: every `app.*` submodule (the dynamic
  imports in the router loader miss some, so we list them by
  hand) plus `uvicorn.*` internals, SQLAlchemy SQLite
  dialect, `PIL._tkinter_finder`, `pytesseract`, `fitz`
  (PyMuPDF), `openpyxl`, `pdfplumber`, `cryptography.fernet`,
  the Google API client stack, and `requests`.
- **Excludes**: `tkinter`, `test`, `unittest`, `pydoc`,
  `doctest`, `matplotlib`, `numpy.tests`. These shave
  ~30 MB off the binary on Windows.
- **Output name**: `officepilot-agent`.
- **Console**: `True` (so the supervisor can capture
  stdout/stderr).
- **UPX**: disabled — UPX-packed binaries are flagged by some
  AV engines as suspicious.

### 4.1 Adding a new hidden import

When you add a new router or service, append the dotted
module path to `HIDDEN_IMPORTS` in
`scripts/officepilot_sidecar.spec`. For example, the moment we
add a new `app.services.reporting` package we need:

```python
"app.services.reporting",
"app.services.reporting.pdf",
"app.services.reporting.excel",
```

If PyInstaller misses an import, the symptom is
`ModuleNotFoundError: No module named 'app.services.reporting'`
on the first call into the affected code path. Re-run
`scripts/build_sidecar_windows.ps1 -Clean` and look for
warnings at the end of the PyInstaller log.

### 4.2 Adding a new third-party dep

Add it to `backend/requirements.txt` **and** to
`HIDDEN_IMPORTS` in the spec. Then re-run the build script.

### 4.3 Adding a data file

PyInstaller's `datas=` list is empty by default. If you ever
ship something the agent reads at runtime (e.g. a Tesseract
tessdata folder, a default prompt), add it as a tuple:

```python
datas = [
    (str(BACKEND / "data" / "prompts"), "data/prompts"),
],
```

PyInstaller copies the source folder into the bundle and
exposes it under `sys._MEIPASS` at runtime. Use
`Path(sys._MEIPASS) / "data" / "prompts"` to resolve it from
Python.

---

## 5. The build script

`scripts/build_sidecar_windows.ps1` does six things:

1. Resolves paths and prints a banner.
2. Verifies Python 3.11+ is on PATH.
3. `pip install -r backend/requirements.txt` + PyInstaller
   (skippable with `-SkipInstall`).
4. Optionally wipes `backend/build/` and `backend/dist/`
   (with `-Clean`).
5. Runs `python -m PyInstaller --noconfirm --clean
   scripts/officepilot_sidecar.spec`.
6. Copies `backend/dist/officepilot-agent.exe` to
   `desktop/tauri/src-tauri/binaries/officepilot-agent-x86_64-pc-windows-msvc.exe`.

The target triple defaults to
`x86_64-pc-windows-msvc` to match the Rust target Tauri
uses. Override with `-TargetTriple` only if you are
cross-compiling.

---

## 6. Tauri integration

### 6.1 `tauri.conf.json -> bundle.externalBin`

```json
"externalBin": [
  "binaries/officepilot-agent"
]
```

Tauri resolves this to
`binaries/officepilot-agent-<target-triple><.exe>`. If the
file is missing, `cargo tauri build` fails with a clear
error.

### 6.2 `tauri.conf.json -> plugins.updater`

Scaffolded but inactive (see `docs/DESKTOP_BUILD.md` §6.3).

### 6.3 `Cargo.toml` dependencies

- `tauri-plugin-shell = "2.0"` — provides the
  `Shell::sidecar()` API used by `agent.rs`.
- `tauri-plugin-updater = "2.0"` — declared but **not**
  initialised in `lib.rs` (TODO).
- `ureq = { version = "2", default-features = false,
  features = ["tls", "json"] }` — the HTTP health probe.

### 6.4 `capabilities/default.json`

The sidecar process is launched via
`shell:allow-execute`, scoped to a single binary. Without
this allowlist Tauri 2.0 refuses the call.

### 6.5 `agent.rs` spawn flow

```rust
let shell = app.shell();
let cmd = shell.sidecar("officepilot-agent")?;
let (mut rx, child) = cmd
    .args(["--port", &DEFAULT_AGENT_PORT.to_string()])
    .spawn()?;
tauri::async_runtime::spawn(async move {
    while let Some(event) = rx.recv().await { /* log it */ }
});
Ok(ChildHandle::Bundled(child))
```

A worker thread streams the sidecar's stdout/stderr into
`$OFFICEPILOT_DATA_DIR/logs/sidecar.log` so the user can
debug from the Privacy Dashboard.

### 6.6 Dev vs prod mode

- `cargo tauri dev` + `USE_SYSTEM_PYTHON_AGENT=true` →
  supervisor spawns `python -m uvicorn app.main:app`.
- `cargo tauri dev` (no env var) → supervisor spawns the
  bundled sidecar from `src-tauri/binaries/`.
- `cargo tauri build` → MSI/NSIS ships the bundled sidecar.

The default is bundled in both dev and prod so the
"what dev does" path is a strict subset of the "what prod
does" path.

---

## 7. End-to-end smoke test

After running `scripts/build_sidecar_windows.ps1` and
`cargo tauri build`:

1. Install the MSI on a **clean** Windows 10/11 VM (no Python
   installed).
2. Launch *OfficePilot AI* from the Start menu.
3. Open the **Local Agent** page. The state pill should be
   `Agent Online` within ~5 s.
4. Hit `http://127.0.0.1:8000/api/health` from the VM's
   browser. The response should include
   `"sidecar": {"bundled": true, "frozen": true, "mode": "bundled"}`.
5. Upload a PDF in the UI. The parser should return a normal
   invoice result.
6. Use the tray → Exit. Confirm no orphan
   `officepilot-agent.exe` shows up in Task Manager.
7. Open `%LOCALAPPDATA%\OfficePilot AI\data\logs\sidecar.log`
   and confirm the startup banner is there.

---

## 8. Troubleshooting

### 8.1 `PyInstaller` cannot find a module

- The dotted import is missing from `HIDDEN_IMPORTS` in
  `scripts/officepilot_sidecar.spec`. Add it and re-run
  with `-Clean`.

### 8.2 The bundled `.exe` is enormous

- Look at the `excludes=` list in the spec. Common wins:
  `numpy.tests`, `pandas.tests`, `scipy`, `matplotlib`.
- Use `pyinstaller --log-level=DEBUG` once to see the largest
  modules; the PyInstaller `TOC` log in `build/` shows the
  per-module size.

### 8.3 Antivirus flags the binary

- Disable UPX (already disabled in our spec).
- Sign the binary with a code-signing certificate
  (see `docs/DESKTOP_BUILD.md` §6.2).
- Submit the binary to your AV vendor's false-positive
  portal.

### 8.4 `ModuleNotFoundError: No module named 'app.main'`

The spec is missing the backend package's data. Check that
`pathex=[str(BACKEND)]` is set in the spec — we already do
this in `scripts/officepilot_sidecar.spec`.

### 8.5 The sidecar starts but exits with code 1 immediately

- Open `%LOCALAPPDATA%\OfficePilot AI\data\logs\sidecar_crash.log`
  (or `data/logs/sidecar_crash.log` in a dev install). The
  `__main__` block writes a full traceback there.
- The most common cause is a port conflict: another process
  is bound to 8000. Stop it or set
  `OFFICEPILOT_AGENT_PORT=8123` before launching.

---

## 9. What this guide does **not** cover

- Code signing — see `docs/DESKTOP_BUILD.md` §6.2.
- Auto-update — see `docs/DESKTOP_BUILD.md` §6.3.
- macOS / Linux bundles — Tauri 2.0 supports them, but the
  sidecar target triple differs and PyInstaller cross-builds
  are out of scope for Phase 8.
- Multiple Python interpreters — the sidecar freezes
  whatever Python 3.11 the build host uses. To support
  multiple versions, build per-version and ship the
  matching sidecar.
