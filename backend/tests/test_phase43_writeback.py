"""Phase 43 — Real Accounting Write-Back (QuickBooks/Xero API) tests."""

import json
import os

os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["AGENT_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase43.db"
os.environ["OFFICEPILOT_APP_VERSION"] = "1.0.0"
os.environ["QUICKBOOKS_WRITEBACK_ENABLED"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, get_db, init_db
from app.main import create_app
from app.models.user import User
from app.services.auth import hash_password, create_access_token


@pytest.fixture(autouse=True)
def _clean_db():
    init_db()
    db = SessionLocal()
    try:
        db.query(User).delete()
        from app.models.correction_rule import AccountingCorrectionRule
        db.query(AccountingCorrectionRule).delete()
        from app.models.audit_log import AuditLog
        db.query(AuditLog).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(User).delete()
        from app.models.correction_rule import AccountingCorrectionRule
        db.query(AccountingCorrectionRule).delete()
        from app.models.audit_log import AuditLog
        db.query(AuditLog).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def user(db):
    u = User(
        email="writeback@test.com",
        password_hash=hash_password("testpass"),
        role="user",
        onboarding_completed=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def token(user):
    return create_access_token(user.id, user.email, user.role)


@pytest.fixture
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestAccountingWritebackAdapter:
    def test_mock_adapter_returns_correct_json_structure(self):
        from app.services.accounting_writeback import QuickBooksWritebackAdapter

        adapter = QuickBooksWritebackAdapter()
        result = adapter.create_bill(
            vendor_name="Acme Corp",
            line_items=[{"description": "Consulting", "amount": 5000.00}],
            total_amount=5000.00,
            due_date="2026-07-28",
        )
        assert result["status"] == "success"
        assert result["bill_id"].startswith("mock-quickbooks-")
        assert "Acme Corp" in result["vendor_name"]
        assert result["total_amount"] == 5000.00
        assert "url" in result

    def test_mock_xero_adapter_returns_correct_json_structure(self):
        from app.services.accounting_writeback import XeroWritebackAdapter

        adapter = XeroWritebackAdapter()
        result = adapter.create_bill(
            vendor_name="OfficeMart Ltd",
            line_items=[{"description": "Supplies", "amount": 1200.00}],
            total_amount=1200.00,
            due_date="2026-07-28",
        )
        assert result["status"] == "success"
        assert result["bill_id"].startswith("mock-xero-")
        assert result["total_amount"] == 1200.00

    def test_mock_adapter_default_due_date(self):
        from app.services.accounting_writeback import QuickBooksWritebackAdapter

        adapter = QuickBooksWritebackAdapter()
        result = adapter.create_bill(
            vendor_name="Test Vendor",
            total_amount=100.00,
        )
        assert result["status"] == "success"
        assert result["total_amount"] == 100.00
        assert result["vendor_name"] == "Test Vendor"

    def test_adapter_real_mode_payload_shape(self):
        from app.services.accounting_writeback import QuickBooksWritebackAdapter

        adapter = QuickBooksWritebackAdapter()
        adapter.MOCK_MODE = False
        result = adapter.create_bill(
            vendor_name="Real Vendor",
            line_items=[{"description": "Service", "amount": 2500.00, "account": "Office Supplies"}],
            total_amount=2500.00,
            due_date="2026-07-28",
        )
        assert result["status"] == "real_mode_payload"
        assert "payload" in result
        payload = result["payload"]
        assert "Bill" in payload
        assert payload["Bill"]["VendorRef"]["name"] == "Real Vendor"
        assert payload["Bill"]["TotalAmt"] == 2500.00


class TestWritebackExecutors:
    def test_quickbooks_create_bill_executor(self, db, user):
        from app.services.agent_tool_executor import execute_tool

        result = execute_tool(
            "quickbooks_create_bill",
            {"vendor_name": "Acme Corp", "total_amount": 5000.00, "due_date": "2026-07-28"},
            "live",
            db,
            user,
        )
        assert result["status"] == "success"
        output = result["output"]
        assert output["bill_id"].startswith("mock-quickbooks-")
        assert output["vendor_name"] == "Acme Corp"
        assert output["total_amount"] == 5000.00

    def test_xero_create_bill_executor(self, db, user):
        from app.services.agent_tool_executor import execute_tool

        result = execute_tool(
            "xero_create_bill",
            {"vendor_name": "OfficeMart", "total_amount": 1200.00, "line_items": []},
            "live",
            db,
            user,
        )
        assert result["status"] == "success"
        output = result["output"]
        assert output["bill_id"].startswith("mock-xero-")
        assert output["vendor_name"] == "OfficeMart"

    def test_tool_registry_has_high_risk_tools(self):
        from app.services.tool_registry import get_tool

        qb_tool = get_tool("quickbooks_create_bill")
        assert qb_tool is not None
        assert qb_tool.risk_level == "high"
        assert qb_tool.approval_required is True
        assert qb_tool.audit_required is True

        xero_tool = get_tool("xero_create_bill")
        assert xero_tool is not None
        assert xero_tool.risk_level == "high"
        assert xero_tool.approval_required is True
        assert xero_tool.audit_required is True

    def test_high_risk_blocked_in_dry_run_mode(self, db, user):
        from app.services.agent_tool_executor import execute_tool

        result = execute_tool(
            "quickbooks_create_bill",
            {"vendor_name": "Acme Corp", "total_amount": 1000.00},
            "dry_run",
            db,
            user,
        )
        assert result["status"] == "dry_run"
        assert "dry-run" in result["message"].lower()

    def test_safety_gate_blocks_without_env_var(self, db, user):
        old_val = os.environ.pop("QUICKBOOKS_WRITEBACK_ENABLED", None)
        try:
            from app.services.agent_tool_executor import execute_tool

            result = execute_tool(
                "quickbooks_create_bill",
                {"vendor_name": "Acme Corp", "total_amount": 1000.00},
                "live",
                db,
                user,
            )
            assert result["status"] == "blocked"
            assert "blocked" in result["message"].lower()
        finally:
            if old_val is not None:
                os.environ["QUICKBOOKS_WRITEBACK_ENABLED"] = old_val

    def test_audit_log_recorded(self, db, user):
        from app.models.audit_log import AuditLog
        from app.services.agent_tool_executor import execute_tool

        execute_tool(
            "quickbooks_create_bill",
            {"vendor_name": "AuditTest", "total_amount": 777.00},
            "live",
            db,
            user,
        )

        audit_entry = (
            db.query(AuditLog)
            .filter(AuditLog.action.like("accounting.writeback.%"))
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert audit_entry is not None
        assert audit_entry.action == "accounting.writeback.quickbooks.create_bill"
        assert "AuditTest" in (audit_entry.details or "")
        assert "777" in (audit_entry.details or "")
