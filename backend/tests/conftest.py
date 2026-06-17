"""Shared test fixtures."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure a clean, isolated env before importing the app.
_TMP = Path(tempfile.mkdtemp(prefix="officepilot-tests-"))
os.environ["OFFICEPILOT_DB_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["OFFICEPILOT_STORAGE_ROOT"] = str(_TMP / "storage")
os.environ["OFFICEPILOT_DATA_DIR"] = str(_TMP / "data")
os.environ["OFFICEPILOT_OCR_ENABLED"] = "false"  # don't depend on tesseract binary
os.environ["OFFICEPILOT_CONFIDENCE_THRESHOLD"] = "0.6"
# Phase 2: never hit the real Gmail API in tests; use the built-in fake client.
os.environ["OFFICEPILOT_GMAIL_ALLOW_REAL"] = "false"
os.environ["OFFICEPILOT_GMAIL_CLIENT_ID"] = ""
os.environ["OFFICEPILOT_GMAIL_CLIENT_SECRET"] = ""
os.environ["OFFICEPILOT_GMAIL_STATE_DIR"] = str(_TMP / "gmail")
# Phase 17: allow open registration in tests
os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["ALLOW_FIRST_OWNER_BOOTSTRAP"] = "true"
# Phase 18: demo mode in tests
os.environ["DEMO_MODE"] = "true"
os.environ["DEMO_SEED_ON_FIRST_RUN"] = "false"
# Phase 19: usage tracking
os.environ["USAGE_TRACKING_ENABLED"] = "true"
os.environ["EXTERNAL_ANALYTICS_ENABLED"] = "false"
# Phase 20: public landing page
os.environ["PUBLIC_ANALYTICS_ENABLED"] = "true"
# Phase 21: performance/cleanup defaults
os.environ["LOG_RETENTION_DAYS"] = "90"
os.environ["DEMO_DATA_RETENTION_DAYS"] = "30"
os.environ["MAX_AUDIT_EXPORTS"] = "50"
os.environ["MAX_BUG_REPORT_PACKAGES"] = "50"
# Phase 23B: Accountant AutoPilot test defaults
os.environ["MULTILINGUAL_ENABLED"] = "true"
os.environ["PILOT_TOOLS_ENABLED"] = "false"
os.environ["ADVANCED_TOOLS_ENABLED"] = "true"
os.environ["DEV_TOOLS_ENABLED"] = "false"
os.environ["TTS_ENABLED"] = "false"
os.environ["ACCOUNT_PLATFORM_MODE"] = "universal"

from app.db import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import audit_log, invoice, invoice_file, invoice_line_item, setting  # noqa: E402,F401
from app.models import (  # noqa: E402,F401
    workflow_recording_policy, recorded_workflow, workflow_recording_session,
    recorded_workflow_step, workflow_replay_run, workflow_replay_step_log,
)
from app.models import (  # noqa: E402,F401
    screen_control_policy, screen_control_session, screen_control_action,
    screen_control_step_log,
)
from app.models import (  # noqa: E402,F401
    safety_policy, role_permission, audit_export,
)
from app.models import (  # noqa: E402,F401
    user, automation_safety_state,
)
from app.models import (  # noqa: E402,F401
    onboarding_state,
)
from app.models import (  # noqa: E402,F401
    demo_walkthrough, pilot_feedback, bug_report, usage_event, pilot_readiness,
)
from app.models import (  # noqa: E402,F401
    pilot_waitlist, public_page_event,
)
from app.models import (  # noqa: E402,F401
    agent_task_plan, agent_workflow_memory, agent_workflow_run, agent_workflow_step_log,
)
from app.models import DictationHistory  # noqa: E402,F401
from app.models import accounting_skill  # noqa: E402,F401


@pytest.fixture(scope="session", autouse=True)
def _build_schema():
    from app.db import engine, init_db
    init_db()
    engine.connect().close()
    yield
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(autouse=True)
def _reset_settings_cache_and_fake_client():
    """Force a fresh settings read per-test, and clear any global fake client."""
    from app.config import _settings_singleton
    from app.services.email import gmail_client as gc
    from app.services.email.crypto import _fernet
    import app.services.windows_voice_layer as _voice_mod

    _settings_singleton.cache_clear()
    if isinstance(_voice_mod._voice_settings_cache, dict):
        _voice_mod._voice_settings_cache.clear()
    _voice_mod._voice_settings_cached_at = 0
    _voice_mod._recording_state["active"] = False
    _voice_mod._recording_state["started_at"] = None
    _voice_mod._recording_state["mode"] = None
    _voice_mod._recording_state["temp_audio"] = None
    _fernet.cache_clear()
    gc._FAKE_HANDLE.clear()
    _truncate_all_tables()
    yield
    gc._FAKE_HANDLE.clear()


def _truncate_all_tables() -> None:
    """Clear all data between tests so each test starts from a clean slate.

    Uses the existing engine and respects FK order.
    """
    from app.db import engine
    from sqlalchemy import text

    tables = [
        # Phase 34 — Email search/attachment downloads (children of users, email_accounts)
        "email_attachment_downloads",
        "email_search_runs",
        # Phase 22.5 — Voice commands
        "voice_commands",
        # Phase 34 — Email verification/password reset tokens (children of users)
        "password_reset_tokens",
        "email_verification_tokens",
        # Phase 35 — in-app notifications (children of users)
        "in_app_notifications",
        # Phase 32 — Browser sessions
        "browser_sessions",
        # Phase 33 — Workflow recorded events & skill drafts (children of users + recording_sessions)
        "workflow_recorded_events",
        "workflow_skill_drafts",
        # Phase 35 — user devices & subscriptions (children of users)
        "user_devices",
        "subscriptions",
        # Phase 35 — feature entitlements
        "feature_entitlements",
        # Phase 35 — app releases
        "app_releases",
        # Phase 34 — Email tokens (children of users)
        # (password_reset_tokens, email_verification_tokens already listed above)
        # Audit logs (children of everything)
        "audit_logs",
        "browser_action_steps",
        "browser_page_snapshots",
        "browser_action_runs",
        "browser_automation_policies",
        "email_attachments",
        "email_imports",
        "email_accounts",
        "invoice_line_items",
        "invoices",
        "invoice_files",
        "settings",
        "workflow_logs",
        "workflow_approvals",
        "workflow_runs",
        # Phase 10 — version history + restore tables
        "workflow_versions",
        "file_snapshots",
        "entity_versions",
        "restore_logs",
        # Phase 13 — accounting sync tables
        "accounting_voice_commands",
        "accounting_entry_validations",
        "accounting_sync_logs",
        "accounting_sync_previews",
        "accounting_category_mappings",
        "accounting_vendor_mappings",
        "accounting_field_mappings",
        "accounting_connections",
        # Phase 14 — workflow recording tables
        "workflow_replay_step_logs",
        "workflow_replay_runs",
        "recorded_workflow_steps",
        "workflow_recording_sessions",
        "recorded_workflows",
        "workflow_recording_policies",
        # Phase 15 — screen control tables
        "screen_control_step_logs",
        "screen_control_actions",
        "screen_control_sessions",
        "screen_control_policies",
        # Phase 16B — safety + permissions + audit export tables
        "safety_policies",
        "role_permissions",
        "audit_exports",
        # Phase 17 — auth + persistent kill switch tables
        "user_sessions",
        "oauth_accounts",
        "users",
        "automation_safety_state",
        # Phase 18 — onboarding
        "onboarding_state",
        # Phase 19 — pilot readiness
        "demo_walkthroughs",
        "pilot_feedback",
        "bug_reports",
        "usage_events",
        "pilot_readiness",
        # Phase 20 — public landing page & waitlist
        "pilot_waitlist",
        "public_page_events",
        # Phase 23 — Accountant Agent tables
        "agent_workflow_step_logs",
        "agent_workflow_runs",
        "agent_workflow_memory",
        "agent_task_plans",
        # Phase 27 — Windows Voice Layer
        "dictation_history",
        # Phase 29 — Accounting Skills (Hermes-style skill memory)
        "accounting_skill_versions",
        "accounting_skill_runs",
        "accounting_skills",
    ]
    with engine.begin() as conn:
        for tbl in tables:
            try:
                conn.execute(text(f"DELETE FROM {tbl}"))
            except Exception:  # table may not exist on first run
                pass


@pytest.fixture()
def db_session():
    """Return a scoped DB session bound to the same engine as the app.

    Uses ``app.db.SessionLocal`` instead of a second engine so that
    data written by the request handlers (TestClient → SessionLocal)
    is visible in test assertions.  A separate engine can hide committed
    rows when SQLite's connection pool interferes in a large suite run.
    """
    from app.db import SessionLocal
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client():
    from app.db import SessionLocal
    from app.main import app

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ----------------------------- sample text invoices ----------------------------


SAMPLE_TEXT_INVOICE = """\
ACME Office Supplies
123 Industrial Way
Springfield, IL 62704

INVOICE

Invoice Number: INV-2026-0042
Invoice Date: 2026-05-12
Due Date: 2026-06-11

Bill To:
Globex Manufacturing
5000 Client Plaza
Shelbyville, TN

Description                  Qty    Unit Price    Line Total
Printer Paper A4            10     4.50          45.00
Toner Cartridge HP 26X      4      89.00         356.00
Stapler Heavy Duty          2      14.75         29.50

Subtotal: 430.50
Tax (7%): 30.14
Total: $460.64

Payment Terms: Net 30
"""


SAMPLE_NO_TOTAL = """\
Beta Logistics
INVOICE
Invoice Number: BL-001
Invoice Date: 2026-01-01

Subtotal: 100.00
Tax: 8.00
"""


@pytest.fixture()
def sample_text_path():
    p = _TMP / "sample_invoice.txt"
    p.write_text(SAMPLE_TEXT_INVOICE, encoding="utf-8")
    return p


@pytest.fixture()
def sample_no_total_path():
    p = _TMP / "sample_no_total.txt"
    p.write_text(SAMPLE_NO_TOTAL, encoding="utf-8")
    return p
