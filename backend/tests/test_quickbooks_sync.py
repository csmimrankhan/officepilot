"""Tests for Phase 38.6 Task 2 — Real QuickBooks Sync."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine, SessionLocal
from app.main import create_app
from app.models.accounting_connection import AccountingConnection
from app.services.accounting import encrypt_token


@pytest.fixture(autouse=True)
def _clean_db():
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
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def auth_token(client):
    from app.services.auth import hash_password, create_access_token
    from app.models.user import User
    db = SessionLocal()
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
        full_name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    token = create_access_token(user.id, user.email, user.role)
    return token


@pytest.fixture
def qb_connection(db):
    conn = AccountingConnection(
        provider="quickbooks",
        display_name="QuickBooks",
        company_name="Test Company",
        realm_id="mock_realm_abc123",
        access_token_encrypted=encrypt_token("mock_access_token"),
        refresh_token_encrypted=encrypt_token("mock_refresh_token"),
        scopes_json="[]",
        status="active",
        environment="mock",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def test_sync_status_no_connection(client, auth_token):
    resp = client.get("/api/quickbooks/status", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False


def test_sync_status_with_connection(client, auth_token, qb_connection):
    resp = client.get("/api/quickbooks/status", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["synced"] is False
    assert data["accounts_count"] == 0
    assert data["status"] == "never"


def test_sync_returns_mock_data(client, auth_token, qb_connection):
    resp = client.post("/api/quickbooks/sync", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["accounts_count"] == 10
    assert data["customers_count"] == 5
    assert data["invoices_count"] == 8
    assert data["last_sync_at"] is not None


def test_sync_persists_state(client, auth_token, qb_connection):
    client.post("/api/quickbooks/sync", headers={"Authorization": f"Bearer {auth_token}"})
    resp = client.get("/api/quickbooks/status", headers={"Authorization": f"Bearer {auth_token}"})
    data = resp.json()
    assert data["synced"] is True
    assert data["accounts_count"] == 10
    assert data["customers_count"] == 5
    assert data["invoices_count"] == 8
    assert data["status"] == "success"


def test_sync_twice_updates_counts(client, auth_token, qb_connection):
    client.post("/api/quickbooks/sync", headers={"Authorization": f"Bearer {auth_token}"})
    resp1 = client.get("/api/quickbooks/status", headers={"Authorization": f"Bearer {auth_token}"})
    first_sync = resp1.json()["last_sync_at"]

    client.post("/api/quickbooks/sync", headers={"Authorization": f"Bearer {auth_token}"})
    resp2 = client.get("/api/quickbooks/status", headers={"Authorization": f"Bearer {auth_token}"})
    second_sync = resp2.json()["last_sync_at"]

    assert second_sync >= first_sync


def test_sync_fails_if_not_connected(client, auth_token):
    resp = client.post("/api/quickbooks/sync", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 409


def test_sync_requires_auth(client):
    resp = client.post("/api/quickbooks/sync")
    assert resp.status_code == 401


def test_status_requires_auth(client):
    resp = client.get("/api/quickbooks/status")
    assert resp.status_code == 401
