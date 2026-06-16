"""Tests for Phase 38.6 Task 1 — First-Run Onboarding Wizard."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import init_db, SessionLocal
from app.main import create_app
from app.models.user import User


@pytest.fixture(autouse=True)
def _clean_db():
    """Drop and recreate tables before each test."""
    from app.db import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


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
def test_user(db):
    from app.services.auth import hash_password
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
        full_name="Test User",
        role="user",
        onboarding_completed=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(client, test_user):
    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_user_model_has_onboarding_completed(test_user):
    assert hasattr(test_user, "onboarding_completed")
    assert test_user.onboarding_completed is False


def test_check_setup_returns_all_fields(client, auth_token):
    resp = client.get("/api/onboarding/check-setup", headers={
        "Authorization": f"Bearer {auth_token}"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "whisper_model_ready" in data
    assert "local_llm_reachable" in data
    assert "demo_data_seeded" in data
    assert "onboarding_completed" in data
    assert data["onboarding_completed"] is False
    assert data["local_llm_reachable"] is False  # No local LLM
    assert data["agent_provider"] == "mock"


@patch("app.services.windows_voice_layer.detect_whisper_status")
def test_check_setup_with_mocked_whisper(mock_detect, client, auth_token):
    mock_detect.return_value = {"model_found": True, "cli_found": True}
    resp = client.get("/api/onboarding/check-setup", headers={
        "Authorization": f"Bearer {auth_token}"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["whisper_model_ready"] is True


def test_check_setup_requires_auth(client):
    resp = client.get("/api/onboarding/check-setup")
    assert resp.status_code == 401


def test_complete_onboarding_sets_flag(client, auth_token, db):
    resp = client.post("/api/onboarding/complete", json={
        "demo_data": False,
    }, headers={
        "Authorization": f"Bearer {auth_token}"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["onboarding_completed"] is True

    db.expire_all()
    user = db.query(User).filter(User.email == "test@example.com").first()
    assert user.onboarding_completed is True


def test_complete_onboarding_with_demo_data(client, auth_token):
    resp = client.post("/api/onboarding/complete", json={
        "demo_data": True,
    }, headers={
        "Authorization": f"Bearer {auth_token}"
    })
    assert resp.status_code == 200


def test_complete_onboarding_requires_auth(client):
    resp = client.post("/api/onboarding/complete", json={"demo_data": False})
    assert resp.status_code == 401


def test_login_returns_onboarding_completed(client, test_user):
    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "onboarding_completed" in data["user"]
    assert data["user"]["onboarding_completed"] is False

    # After completing onboarding
    test_user.onboarding_completed = True
    from app.db import SessionLocal
    db = SessionLocal()
    db.merge(test_user)
    db.commit()
    db.close()

    resp2 = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp2.status_code == 200
    assert resp2.json()["user"]["onboarding_completed"] is True


def test_me_returns_onboarding_completed(client, auth_token, test_user):
    resp = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {auth_token}"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "onboarding_completed" in data["user"]
    assert data["user"]["onboarding_completed"] is False
