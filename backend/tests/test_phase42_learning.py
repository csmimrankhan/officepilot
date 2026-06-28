"""Phase 42 — Continuous Learning & Correction Loop tests."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["AGENT_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase42.db"
os.environ["OFFICEPILOT_APP_VERSION"] = "1.0.0"

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
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(User).delete()
        from app.models.correction_rule import AccountingCorrectionRule
        db.query(AccountingCorrectionRule).delete()
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
        email="learn@test.com",
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


class TestLearningService:
    def test_record_correction_creates_rule(self, db):
        from app.services.learning_loop import record_correction

        rule = record_correction(db=db, user_id=1, trigger_vendor="Adobe", wrong_category="Office Supplies", correct_category="Software")
        assert rule.id is not None
        assert rule.trigger_vendor_pattern == "Adobe"
        assert rule.wrong_category == "Office Supplies"
        assert rule.correct_category == "Software"
        assert rule.user_id == 1

    def test_get_active_rules_returns_user_rules(self, db):
        from app.services.learning_loop import get_active_rules, record_correction

        r1 = record_correction(db=db, user_id=42, trigger_vendor="Adobe", correct_category="Software")
        r2 = record_correction(db=db, user_id=42, trigger_vendor="Starbucks", correct_category="Meals & Entertainment")
        record_correction(db=db, user_id=99, trigger_vendor="Other", correct_category="Misc")

        rules = get_active_rules(db=db, user_id=42)
        assert len(rules) == 2
        assert rules[0].trigger_vendor_pattern == "Starbucks"
        assert rules[1].trigger_vendor_pattern == "Adobe"

    def test_delete_rule_removes_rule(self, db):
        from app.services.learning_loop import delete_rule, get_active_rules, record_correction

        rule = record_correction(db=db, user_id=1, trigger_vendor="Adobe", correct_category="Software")
        assert len(get_active_rules(db=db, user_id=1)) == 1

        deleted = delete_rule(db=db, rule_id=rule.id, user_id=1)
        assert deleted is True
        assert len(get_active_rules(db=db, user_id=1)) == 0

    def test_delete_rule_wrong_user_returns_false(self, db):
        from app.services.learning_loop import delete_rule, record_correction

        rule = record_correction(db=db, user_id=1, trigger_vendor="Adobe", correct_category="Software")
        deleted = delete_rule(db=db, rule_id=rule.id, user_id=99)
        assert deleted is False

    def test_format_rules_for_prompt_empty(self):
        from app.services.learning_loop import format_rules_for_prompt

        result = format_rules_for_prompt([])
        assert result == ""

    def test_format_rules_with_wrong_category(self, db):
        from app.services.learning_loop import format_rules_for_prompt, record_correction

        rule = record_correction(db=db, user_id=1, trigger_vendor="Adobe", wrong_category="Office Supplies", correct_category="Software")
        result = format_rules_for_prompt([rule])
        assert "### LEARNED CORRECTION RULES (MANDATORY)" in result
        assert "If vendor contains 'Adobe'" in result
        assert "Never use 'Office Supplies'" in result
        assert "ALWAYS" in result

    def test_format_rules_without_wrong_category(self, db):
        from app.services.learning_loop import format_rules_for_prompt, record_correction

        rule = record_correction(db=db, user_id=1, trigger_vendor="Netflix", correct_category="Subscriptions")
        result = format_rules_for_prompt([rule])
        assert "If vendor contains 'Netflix'" in result
        assert "Never use" not in result


class TestLearningRouter:
    def test_create_correction_endpoint(self, client, auth_headers):
        resp = client.post(
            "/api/agent/correct",
            json={"trigger_vendor": "Adobe", "wrong_category": "Office Supplies", "correct_category": "Software"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "rule_id" in data

    def test_create_correction_requires_auth(self, client):
        resp = client.post(
            "/api/agent/correct",
            json={"trigger_vendor": "Adobe", "correct_category": "Software"},
        )
        assert resp.status_code == 401

    def test_list_corrections_endpoint(self, client, auth_headers):
        client.post(
            "/api/agent/correct",
            json={"trigger_vendor": "Adobe", "correct_category": "Software"},
            headers=auth_headers,
        )
        client.post(
            "/api/agent/correct",
            json={"trigger_vendor": "Starbucks", "correct_category": "Meals & Entertainment"},
            headers=auth_headers,
        )
        resp = client.get("/api/agent/corrections", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["trigger_vendor_pattern"] == "Starbucks"

    def test_delete_correction_endpoint(self, client, auth_headers):
        create_resp = client.post(
            "/api/agent/correct",
            json={"trigger_vendor": "Adobe", "correct_category": "Software"},
            headers=auth_headers,
        )
        rule_id = create_resp.json()["rule_id"]

        resp = client.delete(f"/api/agent/corrections/{rule_id}", headers=auth_headers)
        assert resp.status_code == 200

        list_resp = client.get("/api/agent/corrections", headers=auth_headers)
        assert len(list_resp.json()) == 0

    def test_delete_wrong_user_returns_404(self, client, auth_headers, db):
        from app.services.learning_loop import record_correction

        rule = record_correction(db=db, user_id=999, trigger_vendor="Adobe", correct_category="Software")

        resp = client.delete(f"/api/agent/corrections/{rule.id}", headers=auth_headers)
        assert resp.status_code == 404


class TestSystemPromptInjection:
    def test_build_ollama_system_prompt_no_rules(self):
        from app.services.accountant_agent import _build_ollama_system_prompt

        prompt = _build_ollama_system_prompt(db=None, user_id=None)
        assert "LEARNED CORRECTION RULES" not in prompt
        assert "You are OfficePilot AI" in prompt

    def test_build_ollama_system_prompt_with_rules(self, db, user):
        from app.services.accountant_agent import _build_ollama_system_prompt
        from app.services.learning_loop import record_correction

        record_correction(db=db, user_id=user.id, trigger_vendor="Adobe", correct_category="Software")
        record_correction(db=db, user_id=user.id, trigger_vendor="Starbucks", wrong_category="Office Supplies", correct_category="Meals & Entertainment")

        prompt = _build_ollama_system_prompt(db=db, user_id=user.id)
        assert "LEARNED CORRECTION RULES (MANDATORY)" in prompt
        assert "Adobe" in prompt
        assert "Starbucks" in prompt
        assert "Office Supplies" in prompt
        assert "Software" in prompt
        assert "Meals & Entertainment" in prompt

    def test_build_ollama_system_prompt_no_other_users_rules(self, db, user):
        from app.services.accountant_agent import _build_ollama_system_prompt
        from app.services.learning_loop import record_correction

        record_correction(db=db, user_id=999, trigger_vendor="Secret", correct_category="Hidden")

        prompt = _build_ollama_system_prompt(db=db, user_id=user.id)
        assert "Secret" not in prompt
        assert "Hidden" not in prompt
