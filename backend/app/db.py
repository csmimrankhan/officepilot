"""SQLAlchemy engine, session, and Base."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()

_connect_args: dict = {}
if _settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    _settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create tables. Imported lazily by main and tests."""
    from .models import (  # noqa: F401
        audit_log,
        browser_action_run,
        browser_action_step,
        browser_automation_policy,
        browser_page_snapshot,
        email_account,
        email_attachment,
        email_import,
        entity_version,
        file_snapshot,
        invoice,
        invoice_file,
        invoice_line_item,
        restore_log,
        setting,
        workflow_version,
        accounting_connection,
        accounting_field_mapping,
        accounting_vendor_mapping,
        accounting_category_mapping,
        accounting_sync_preview,
        accounting_sync_log,
        accounting_entry_validation,
        accounting_voice_command,
        workflow_recording_policy,
        recorded_workflow,
        workflow_recording_session,
        recorded_workflow_step,
        workflow_replay_run,
        workflow_replay_step_log,
        screen_control,
        safety_policy,
        role_permission,
        audit_export,
        user,
        automation_safety_state,
        onboarding_state,
        demo_walkthrough,
        pilot_feedback,
        bug_report,
        usage_event,
        pilot_readiness,
        pilot_waitlist,
        public_page_event,
        agent_task_plan, agent_workflow_memory, agent_workflow_run, agent_workflow_step_log,
        accounting_skill, accounting_skill_version,
        dictation_history,
        email_token,
        email_search_run,
        email_attachment_download,
        app_release,
        user_device,
        user_session,
        oauth_account,
        subscription,
        feature_entitlement,
        in_app_notification,
        browser_session,
        voice_command,
        workflow_recorded_event,
        workflow_skill_draft,
        quickbooks_sync_state,
    )

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a session and ensures close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
