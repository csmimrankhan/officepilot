"""FastAPI entry point for the OfficePilot AI backend (Phases 1 + 2 + 3 + 5 + 6 + 7)."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import SessionLocal, init_db
from .services.startup_metrics import get_metrics, mark_startup
from .routers import audit as audit_router
from .routers import browser as browser_router
from .routers import email_imports as email_imports_router
from .routers import integrations_gmail as gmail_router
from .routers import invoices as invoices_router
from .routers import local as local_router
from .routers import parser as parser_router
from .routers import settings as settings_router
from .routers import versions as versions_router
from .routers import workflows as workflows_router
from .routers import accounting as accounting_router
from .routers import workflow_recording as recording_router
from .routers import screen_control as screen_router
from .routers import safety as safety_router
from .routers import permissions as permissions_router
from .routers import audit_exports as audit_exports_router
from .routers import system as system_router
from .routers import backup as backup_router
from .routers import auth as auth_router
from .routers import demo as demo_router
from .routers import onboarding as onboarding_router
from .routers import about as about_router
from .routers import diagnostics as diagnostics_router
from .routers import demo_walkthrough as demo_walkthrough_router
from .routers import feedback as feedback_router
from .routers import bug_reports as bug_reports_router
from .routers import usage as usage_router
from .routers import pilot_readiness as pilot_readiness_router
from .routers import public_waitlist as public_waitlist_router
from .routers import voice as voice_router
from .routers import voice_layer as voice_layer_router
from .routers import agent as agent_router
from .routers import accounting_skills as accounting_skills_router
from .routers import workflow_recorder as workflow_recorder_router
from .routers import admin as admin_router
from .routers import email_automation as email_automation_router
from .routers import app_updates as app_updates_router
from .routers import billing as billing_router
from .routers import integrations_quickbooks as quickbooks_router
from .routers import background_tasks as background_tasks_router
from .routers import watchers as watchers_router
from .routers import learning as learning_router
from .routers import release_notes as release_notes_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
)
logger = logging.getLogger("officepilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    mark_startup("lifespan_started")
    settings = get_settings()
    settings.invoices_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    settings.gmail_state_dir.mkdir(parents=True, exist_ok=True)
    # Phase 7: also create the data subdirs the local shell relies on.
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.audit_dir.mkdir(parents=True, exist_ok=True)
    settings.recordings_dir.mkdir(parents=True, exist_ok=True)
    # Phase 10: file snapshots for the Undo Automation feature.
    settings.snapshots_dir.mkdir(parents=True, exist_ok=True)
    # Phase 12: browser automation screenshots.
    settings.browser_snapshots_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    # Phase 12: seed the singleton policy row and prune old runs.
    try:
        from .services import browser_automation as _ba
        from .routers.browser import prune_old_runs

        with SessionLocal() as _db:
            _ba.get_or_create_policy(_db)
            _db.commit()
            prune_old_runs(_db)
    except Exception:  # pragma: no cover - non-fatal
        logger.exception("Phase 12 startup hook failed (non-fatal)")
    # Phase 13: create accounting data dirs.
    try:
        _acct_dir = settings.data_dir / "accounting"
        _acct_dir.mkdir(parents=True, exist_ok=True)
    except Exception:  # pragma: no cover - non-fatal
        logger.exception("Phase 13 startup hook failed (non-fatal)")
    # Phase 15: create screen control snapshot dir.
    try:
        settings.screen_snapshots_dir.mkdir(parents=True, exist_ok=True)
    except Exception:  # pragma: no cover - non-fatal
        logger.exception("Phase 15 startup hook failed (non-fatal)")
    # Phase 16B: safety policy + permissions seeding.
    try:
        from .services.safety import get_or_create_safety_policy
        from .services.permissions import seed_default_permissions

        with SessionLocal() as _db:
            get_or_create_safety_policy(_db)
            seed_default_permissions(_db)
            _db.commit()
    except Exception:  # pragma: no cover - non-fatal
        logger.exception("Phase 16B startup hook failed (non-fatal)")
    # Phase 16B: create audit exports dir.
    try:
        (settings.data_dir / "audit_exports").mkdir(parents=True, exist_ok=True)
    except Exception:  # pragma: no cover - non-fatal
        logger.exception("Phase 16B dir creation failed (non-fatal)")
    # Phase 17: init persistent kill switch from DB.
    try:
        from .services.safety import init_kill_switch

        with SessionLocal() as _db:
            init_kill_switch(_db)
    except Exception:  # pragma: no cover - non-fatal
        logger.exception("Phase 17 kill switch init failed (non-fatal)")
    # Phase 18: demo seed on first run
    try:
        settings = get_settings()
        if settings.demo_seed_on_first_run:
            from .services.demo import seed_demo_data, is_demo_mode
            if is_demo_mode():
                with SessionLocal() as _db:
                    seed_demo_data(_db)
    except Exception:
        logger.exception("Phase 18 demo seed failed (non-fatal)")
    # Phase 19: bug reports dir + logs dir for diagnostics capture.
    try:
        (settings.data_dir / "bug_reports").mkdir(parents=True, exist_ok=True)
        (settings.data_dir / "logs").mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("Phase 19 dir creation failed (non-fatal)")
    # Phase 20: marketing assets dir for public landing page screenshots.
    try:
        settings.project_root.joinpath("marketing").mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("Phase 20 marketing dir creation failed (non-fatal)")
    # Phase 23: Agent provider init check.
    try:
        from .services.accountant_agent import get_agent_status
        _status = get_agent_status()
        logger.info("Phase 23 agent provider: %s (status=%s)", _status.get("provider"), _status.get("status"))
    except Exception:
        logger.exception("Phase 23 agent status check failed (non-fatal)")
    # Phase 28: voice layer init — temp audio cleanup, whisper model dir, auto-detect status.
    try:
        from .services import windows_voice_layer as _wvl
        _cleaned = _wvl.cleanup_temp_audio()
        if _cleaned:
            logger.info("Phase 28: cleaned %d stale temp audio files", _cleaned)
        _ws = _wvl.detect_whisper_status()
        logger.info("Phase 28: whisper status: cli=%s model=%s configured=%s",
                     _ws["whisper_cli_found"], _ws["whisper_model_found"], _ws["whisper_configured"])
    except Exception:
        logger.exception("Phase 28 voice layer init failed (non-fatal)")
    # Phase 35: seed default feature entitlements.
    try:
        from .models.feature_entitlement import FeatureEntitlement

        with SessionLocal() as _db:
            existing = _db.query(FeatureEntitlement).first()
            if not existing:
                seed_features = [
                    FeatureEntitlement(plan="free", feature_key="excel_automation", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="free", feature_key="browser_export", enabled=False, limit_value=None),
                    FeatureEntitlement(plan="free", feature_key="gmail_readonly", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="free", feature_key="workflow_recorder", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="free", feature_key="advanced_skills", enabled=False, limit_value=5),
                    FeatureEntitlement(plan="free", feature_key="voice_shortcuts", enabled=False, limit_value=None),
                    FeatureEntitlement(plan="free", feature_key="monthly_runs_limit", enabled=True, limit_value=50),
                    FeatureEntitlement(plan="free", feature_key="skills_limit", enabled=True, limit_value=5),
                    FeatureEntitlement(plan="pro", feature_key="excel_automation", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="pro", feature_key="browser_export", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="pro", feature_key="gmail_readonly", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="pro", feature_key="workflow_recorder", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="pro", feature_key="advanced_skills", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="pro", feature_key="voice_shortcuts", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="pro", feature_key="monthly_runs_limit", enabled=True, limit_value=1000),
                    FeatureEntitlement(plan="pro", feature_key="skills_limit", enabled=True, limit_value=50),
                    FeatureEntitlement(plan="trial", feature_key="excel_automation", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="trial", feature_key="browser_export", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="trial", feature_key="gmail_readonly", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="trial", feature_key="workflow_recorder", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="trial", feature_key="advanced_skills", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="trial", feature_key="voice_shortcuts", enabled=True, limit_value=None),
                    FeatureEntitlement(plan="trial", feature_key="monthly_runs_limit", enabled=True, limit_value=100),
                    FeatureEntitlement(plan="trial", feature_key="skills_limit", enabled=True, limit_value=20),
                ]
                _db.add_all(seed_features)
                _db.commit()
    except Exception:
        logger.exception("Phase 35 feature entitlement seed failed (non-fatal)")
    # Phase 40A: start background watcher scheduler.
    try:
        from .services.watcher_scheduler import WatcherScheduler

        _ws = WatcherScheduler.get_instance()
        _ws.start()
        logger.info("Phase 40A: watcher scheduler started")
    except Exception:
        logger.exception("Phase 40A watcher scheduler start failed (non-fatal)")
    mark_startup("backend_ready")
    logger.info(
        "OfficePilot AI backend ready (env=%s, db=%s, phase=23, data=%s, startup=%.2fs)",
        settings.app_env,
        settings.database_url,
        settings.data_dir,
        get_metrics().total_seconds() or 0,
    )
    yield
    # Phase 40A: stop background watcher scheduler on shutdown.
    try:
        from .services.watcher_scheduler import WatcherScheduler

        WatcherScheduler.get_instance().stop()
    except Exception:
        pass


def create_app() -> FastAPI:
    mark_startup("process_start")
    settings = get_settings()
    app = FastAPI(
        title="OfficePilot AI — Universal Voice Accountant Agent",
        description=(
            "Windows desktop app that automates accounting work across Excel, browser apps, "
            "and any accounting platform via voice/text commands, with step-by-step planning, "
            "approval, safe execution, and workflow memory."
        ),
        version="1.0.0",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "auth", "description": "User registration, login, JWT tokens, session management"},
            {"name": "agent", "description": "Accountant agent — plan, approve, execute, repeat workflows"},
            {"name": "invoices", "description": "Invoice upload, review, approve, reject, export"},
            {"name": "browser", "description": "Browser automation with allowlist, preview, approval, audit"},
            {"name": "email", "description": "Gmail read-only integration — search, preview, download attachments"},
            {"name": "accounting", "description": "QuickBooks/Xero sync with preview, approval, and audit"},
            {"name": "accounting-skills", "description": "Saved automation skills with trigger phrases and steps"},
            {"name": "screen", "description": "Screen control, OCR, click/type with preview and approval"},
            {"name": "voice", "description": "Voice command dispatch and transcription"},
            {"name": "voice-layer", "description": "Windows voice layer — microphone recording, whisper.cpp"},
            {"name": "workflows", "description": "LangGraph workflow engine — create, start, approve, retry"},
            {"name": "versions", "description": "Version history, file snapshots, entity restore"},
            {"name": "settings", "description": "App and folder rule settings"},
            {"name": "admin", "description": "Admin dashboard — users, releases, audit logs, waitlist"},
            {"name": "system", "description": "System health, cleanup, storage metrics"},
            {"name": "demo", "description": "Demo mode — sample data, guided walkthrough"},
            {"name": "onboarding", "description": "First-run onboarding wizard"},
            {"name": "local", "description": "Desktop shell — storage, audit export, privacy dashboard"},
            {"name": "app", "description": "App updates, device registration, notifications"},
            {"name": "billing", "description": "Subscription plans, license management"},
            {"name": "safety", "description": "Safety policies, kill switch, permissions"},
            {"name": "audit", "description": "Audit logs and exports"},
            {"name": "parser", "description": "Document parser engine (deprecated — use skills)"},
            {"name": "meta", "description": "Health check and metadata endpoints"},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    def health():
        # Phase 8: report whether this process is a bundled sidecar
        # or system Python. The Tauri supervisor reads this so it
        # can label the status pill in the UI correctly.
        import sys as _sys
        is_frozen = bool(getattr(_sys, "frozen", False))
        sidecar_env = os.environ.get("OFFICEPILOT_SIDECAR", "")
        is_sidecar = is_frozen or sidecar_env.lower() in ("1", "true", "yes", "on")
        metrics = get_metrics()
        return {
            "ok": True,
            "app": "officepilot-ai",
            "version": "1.0.0",
            "phase": 23,
            "startup_seconds": metrics.total_seconds(),
            "demo_mode": settings.demo_mode,
            "state": "online",
            "ocr_enabled": settings.ocr_enabled,
            "gmail_configured": settings.gmail_configured,
            "gmail_allow_real": settings.gmail_allow_real,
            "parser_engine": settings.parser_engine,
            "data_dir": str(settings.data_dir),
            "agent_url": f"http://{settings.agent_host}:{settings.agent_port}",
            "browser_automation_enabled": settings.browser_enabled,
            "accounting_sync_enabled": settings.accounting_sync_enabled,
            "quickbooks_configured": bool(settings.quickbooks_client_id),
            "xero_configured": bool(settings.xero_client_id),
            "screen_control_enabled": settings.screen_control_enabled,
            "sidecar": {
                "bundled": is_sidecar,
                "frozen": is_frozen,
                "mode": "bundled" if is_sidecar else "system-python",
            },
        }

    # ── Core business ───────────────────────────────────────────────
    app.include_router(invoices_router.router)
    app.include_router(settings_router.router)
    app.include_router(parser_router.router)

    # ── Auth & users ────────────────────────────────────────────────
    app.include_router(auth_router.router)
    app.include_router(permissions_router.router)

    # ── Workflow engine ────────────────────────────────────────────
    app.include_router(workflows_router.router)
    app.include_router(recording_router.router)
    app.include_router(workflow_recorder_router.router)

    # ── Email & Gmail ─────────────────────────────────────────────
    app.include_router(gmail_router.router)
    app.include_router(email_imports_router.router)
    app.include_router(email_automation_router.router)

    # ── Browser automation ─────────────────────────────────────────
    app.include_router(browser_router.router)

    # ── Screen control ────────────────────────────────────────────
    app.include_router(screen_router.router)

    # ── Accounting & sync ─────────────────────────────────────────
    app.include_router(accounting_router.router)
    app.include_router(accounting_skills_router.router)
    app.include_router(quickbooks_router.router)

    # ── Agent & AI ─────────────────────────────────────────────────
    app.include_router(agent_router.router)
    app.include_router(voice_router.router)
    app.include_router(voice_layer_router.router)

    # ── Safety & audit ─────────────────────────────────────────────
    app.include_router(safety_router.router)
    app.include_router(audit_router.router)
    app.include_router(audit_exports_router.router)

    # ── Version history ────────────────────────────────────────────
    app.include_router(versions_router.router)

    # ── Desktop / local ────────────────────────────────────────────
    app.include_router(local_router.router)
    app.include_router(backup_router.router)
    app.include_router(app_updates_router.router)

    # ── System & health ────────────────────────────────────────────
    app.include_router(system_router.router)
    app.include_router(about_router.router)
    app.include_router(diagnostics_router.router)

    # ── Demo & onboarding ─────────────────────────────────────────
    app.include_router(demo_router.router)
    app.include_router(onboarding_router.router)
    app.include_router(demo_walkthrough_router.router)

    # ── Feedback & bug reports ─────────────────────────────────────
    app.include_router(feedback_router.router)
    app.include_router(bug_reports_router.router)

    # ── Usage & pilot ──────────────────────────────────────────────
    app.include_router(usage_router.router)
    app.include_router(pilot_readiness_router.router)
    app.include_router(public_waitlist_router.router)

    # ── Background tasks ──────────────────────────────────────────
    app.include_router(background_tasks_router.router)

    # ── Watchers (Phase 40A) ──────────────────────────────────────
    app.include_router(watchers_router.router)

    # ── Learning & Corrections (Phase 42) ─────────────────────────
    app.include_router(learning_router.router)

    # ── Release Notes (Phase 46A) ──────────────────────────────────
    app.include_router(release_notes_router.router)

    # ── Billing & licensing ────────────────────────────────────────
    app.include_router(billing_router.router)

    # ── Admin (must be last — wildcard /* catches all) ─────────────
    app.include_router(admin_router.router)
    # Phase 36 — Static releases for updater
    _releases_dir = settings.project_root / "releases"
    _releases_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/releases", StaticFiles(directory=str(_releases_dir)), name="releases")
    return app


app = create_app()


# Phase 8: ``__main__`` entry point so the PyInstaller-bundled
# sidecar (``officepilot-agent.exe``) can launch uvicorn directly.
# The Tauri supervisor passes the host/port via env vars, which
# we read from :func:`get_settings`.
if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.agent_host,
        port=s.agent_port,
        log_level=os.environ.get("OFFICEPILOT_LOG_LEVEL", "info"),
        access_log=False,
    )
