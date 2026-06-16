# Place the PyInstaller-bundled sidecar here as
# ``officepilot-agent-x86_64-pc-windows-msvc.exe`` before running
# ``cargo tauri build``. The Tauri 2.0 sidecar naming convention
# is ``<binary-name>-<target-triple><.exe>``.
#
# The recommended workflow is:
#
#   .\scripts\build_sidecar_windows.ps1
#
# which builds the sidecar from ``backend/officepilot_sidecar.py``
# and copies it to this directory automatically.
#
# In dev mode, set ``USE_SYSTEM_PYTHON_AGENT=true`` to launch the
# agent via your local ``python -m uvicorn app.main:app`` instead
# of this bundled binary. The bundled binary is the production
# default.
#
# ── Phase 28: Voice Layer ────────────────────────────────────────────────
#
# whisper-cli.exe and models/ggml-base.en.bin (or ggml-tiny.en.bin)
# go here for automatic bundling into the installer. The voice layer
# auto-detects them from this directory at startup.
#
# Download:
#   .\scripts\download_whisper_cpp.ps1         # → whisper-cli.exe
#   .\scripts\download_whisper_models.ps1      # → models/ggml-base.en.bin
#
# On first run without a model, the app can download it from HuggingFace
# via Settings → Voice Layer → "Download ggml-base.en.bin".
