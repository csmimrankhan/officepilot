# PyInstaller spec for the OfficePilot AI sidecar.
#
# This file is consumed by ``scripts/build_sidecar_windows.ps1``.
# It is *not* invoked directly; running PyInstaller as a module
# is more portable across PyInstaller versions.
#
# The output binary is named ``officepilot-agent`` and copied to
# ``desktop/tauri/src-tauri/binaries/officepilot-agent-<target>.exe``
# by the build script (Tauri 2.0 sidecar naming convention).

# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Path to backend/ relative to this spec file.
# SPECPATH points to the directory holding this .spec file (scripts/).
# Its parent is the project root, where the backend/ package lives.
ROOT = Path(SPECPATH).resolve().parent
BACKEND = (ROOT / "backend").resolve()

block_cipher = None


# Hidden imports that PyInstaller's static analyser misses because
# they are loaded via importlib / dynamic lookup. The local agent
# has a few of these (Gmail sync, parser engines, storage manager,
# audit, workflow runner).
HIDDEN_IMPORTS = [
    "app",
    "app.main",
    "app.config",
    "app.db",
    "app.routers.local",
    "app.routers.invoices",
    "app.routers.audit",
    "app.routers.parser",
    "app.routers.settings",
    "app.routers.workflows",
    "app.routers.email_imports",
    "app.routers.integrations_gmail",
    "app.routers.browser",
    "app.routers.versions",
    "app.services.agent_status",
    "app.services.audit",
    "app.services.benchmark",
    "app.services.browser_automation",
    "app.services.excel_export",
    "app.services.extraction",
    "app.services.organizer",
    "app.services.parser",
    "app.services.settings",
    "app.services.snapshots",
    "app.services.storage",
    "app.services.storage_manager",
    "app.services.text_extraction",
    "app.services.validator",
    "app.services.versioning",
    "app.services.email",
    "app.services.email.crypto",
    "app.services.email.gmail_client",
    "app.services.email.oauth",
    "app.services.email.scoring",
    "app.services.email.sync",
    "app.services.engines",
    "app.services.engines.existing_engine",
    "app.services.engines.docling_engine",
    "app.services.engines.ocr_engine",
    "app.services.engines.hybrid_engine",
    "app.services.engines.registry",
    "app.services.workflows",
    "app.services.workflows.registry",
    "app.services.workflows.runner",
    "app.services.workflows.invoice_upload",
    "app.services.workflows.email_import",
    "app.services.workflows.excel_export",
    "app.services.workflows.browser_automation",
    "app.models",
    "app.models.browser_action_run",
    "app.models.browser_action_step",
    "app.models.browser_automation_policy",
    "app.models.browser_page_snapshot",
    "app.models.entity_version",
    "app.models.file_snapshot",
    "app.models.restore_log",
    "app.models.workflow_version",
    "app.utils",
    "app.utils.hashing",
    "app.schemas",
    # Optional / third-party
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.server",
    "uvicorn.config",
    "sqlalchemy.dialects.sqlite",
    "PIL._tkinter_finder",
    "pytesseract",
    "fitz",  # PyMuPDF
    "openpyxl",
    "pdfplumber",
    "cryptography",
    "cryptography.fernet",
    "googleapiclient",
    "googleapiclient.discovery",
    "google.oauth2.credentials",
    "google_auth_oauthlib.flow",
    "requests",
]


# Data files the agent might need at runtime. We keep this empty
# for now; the agent only reads/writes to the data dir which is
# configured at runtime.
DATAS = []


a = Analysis(
    [str(BACKEND / "officepilot_sidecar.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim a few heavy modules we never import. Removing these
        # shrinks the binary by ~30 MB on Windows.
        "tkinter",
        "test",
        "unittest",
        "pydoc",
        "doctest",
        "matplotlib",
        "numpy.tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="officepilot-agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX makes AV engines flag the binary
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # console=True so the Tauri supervisor sees stderr
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
