"""Phase 35: Desktop Update + License Foundation tests."""
from __future__ import annotations

import os

os.environ["AGENT_PROVIDER"] = "mock"
os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase35.db"
os.environ["ALLOW_BILLING_BYPASS"] = "false"

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models.app_release import AppRelease
from app.models.subscription import Subscription
from app.models.feature_entitlement import FeatureEntitlement
from app.models.in_app_notification import InAppNotification
from app.services.app_update import require_feature


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///./test_phase35.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    try:
        Base.metadata.drop_all(bind=e)
    except Exception:
        pass
    e.dispose()
    import gc
    gc.collect()
    import time
    for _ in range(10):
        try:
            os.remove("test_phase35.db")
            break
        except PermissionError:
            time.sleep(0.5)


@pytest.fixture
def db_session(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def user_token(client):
    resp = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "Password123!",
        "full_name": "Test User",
        "confirm_password": "Password123!",
    })
    if resp.status_code == 200:
        data = resp.json()
        tok = data.get("access_token") or data.get("token")
        if tok:
            return tok
    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "Password123!",
    })
    data = resp.json()
    return data.get("access_token") or data.get("token")


# ── Device Registration ──────────────────────────────────────────────


def test_register_device(client, user_token):
    resp = client.post(
        "/api/app/register-device",
        json={
            "device_id": "test-device-001",
            "device_name": "Test Windows PC",
            "platform": "windows",
            "app_version": "0.35.0",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["device_id"] == "test-device-001"


# ── Update Checking ──────────────────────────────────────────────────


def test_check_update_no_update_available(client, user_token, db_session):
    from app.models.app_release import AppRelease
    db_session.query(AppRelease).delete()
    db_session.commit()
    resp = client.post(
        "/api/app/check-update",
        json={"app_version": "0.35.0", "platform": "windows", "channel": "stable"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["update_available"] is False


def test_check_update_available(client, user_token, db_session):
    release = AppRelease(
        version="0.36.0",
        platform="windows",
        channel="stable",
        download_url="https://example.com/officepilot-0.36.0.exe",
        release_notes="Bug fixes",
        minimum_required_version="0.35.0",
        is_critical=False,
    )
    db_session.add(release)
    db_session.commit()

    resp = client.post(
        "/api/app/check-update",
        json={"app_version": "0.35.0", "platform": "windows", "channel": "stable"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["update_available"] is True
    assert data["latest_version"] == "0.36.0"
    assert data["critical"] is False


def test_check_critical_update_blocks(client, user_token, db_session):
    release = AppRelease(
        version="0.37.0",
        platform="windows",
        channel="stable",
        download_url="https://example.com/officepilot-0.37.0.exe",
        release_notes="Security fix",
        minimum_required_version="0.35.0",
        is_critical=True,
    )
    db_session.add(release)
    db_session.commit()

    resp = client.post(
        "/api/app/check-update",
        json={"app_version": "0.35.0", "platform": "windows", "channel": "stable"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["update_available"] is True
    assert data["critical"] is True
    assert data.get("blocked") is True
    assert "security update" in data.get("message", "")


# ── License and Feature Gates ────────────────────────────────────────


def test_license_trial_active(client, user_token, db_session):
    from app.models.subscription import Subscription
    from app.models.user import User
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    if user:
        sub = db_session.query(Subscription).filter(Subscription.user_id == user.id).first()
        if sub:
            sub.status = "active"
            sub.current_period_end = datetime.utcnow() + timedelta(days=30)
            db_session.commit()
    resp = client.get(
        "/api/billing/license",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "trial"
    assert data["status"] == "active"
    assert "features" in data
    assert data["features"]["excel_automation"] is True
    assert data["features"]["browser_export"] is True
    assert data["features"]["gmail_readonly"] is True


def test_license_expired_gates_features(client, user_token, db_session):
    from app.models.user import User
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    sub = db_session.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub:
        sub = Subscription(
            user_id=user.id,
            provider="manual",
            plan="trial",
            status="expired",
            trial_ends_at=datetime.utcnow() - timedelta(days=1),
            current_period_end=datetime.utcnow() - timedelta(days=1),
        )
        db_session.add(sub)
    else:
        sub.status = "expired"
        sub.current_period_end = datetime.utcnow() - timedelta(days=1)
    db_session.commit()

    resp = client.get(
        "/api/billing/license",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "expired"
    assert data.get("upgrade_required") is True
    assert data["features"]["excel_automation"] is True
    assert data["features"]["browser_export"] is False
    assert data["features"]["gmail_readonly"] is False


def test_feature_gate_allows_enabled_feature(client, user_token, db_session):
    from app.models.user import User
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    sub = db_session.query(Subscription).filter(Subscription.user_id == user.id).first()
    if sub:
        sub.status = "active"
        sub.current_period_end = datetime.utcnow() + timedelta(days=30)
        db_session.commit()
    allowed = require_feature(db_session, user.id, "excel_automation")
    assert allowed is True


def test_feature_gate_disabled_for_expired(client, user_token, db_session):
    from app.models.user import User
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    sub = db_session.query(Subscription).filter(Subscription.user_id == user.id).first()
    if sub:
        sub.status = "expired"
        sub.current_period_end = datetime.utcnow() - timedelta(days=1)
        db_session.commit()

    allowed = require_feature(db_session, user.id, "browser_export")
    assert allowed is False


def test_plans_endpoint(client, user_token):
    resp = client.get(
        "/api/billing/plans",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "plans" in data
    plans = data["plans"]
    assert len(plans) >= 1
    plan_ids = [p["id"] for p in plans]
    assert "trial" in plan_ids or "free" in plan_ids


# ── Notifications ────────────────────────────────────────────────────


def test_notifications_list(client, user_token, db_session):
    from app.models.user import User
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    n = InAppNotification(
        user_id=user.id,
        title="Test Notification",
        message="This is a test",
        type="info",
    )
    db_session.add(n)
    db_session.commit()

    resp = client.get(
        "/api/app/notifications",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["notifications"]) >= 1
    assert data["notifications"][0]["title"] == "Test Notification"


def test_mark_notification_seen(client, user_token, db_session):
    from app.models.user import User
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    n = InAppNotification(
        user_id=user.id,
        title="Seen Test",
        message="Mark as seen",
        type="info",
    )
    db_session.add(n)
    db_session.commit()

    resp = client.post(
        f"/api/app/notifications/{n.id}/seen",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


# ── Tauri Updater Endpoint ──────────────────────────────────────────────


def test_updater_no_release_returns_empty(client, user_token, db_session):
    """No release in DB returns empty platforms."""
    db_session.query(AppRelease).delete()
    db_session.commit()
    resp = client.get(
        "/api/app/updater/windows/stable",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "0.0.0"
    assert data["platforms"] == {}


def test_updater_with_release_returns_valid_json(client, user_token, db_session):
    """Seeded release returns Tauri-compatible updater JSON."""
    from app.models.app_release import AppRelease
    release = AppRelease(
        version="1.0.0",
        platform="windows",
        channel="stable",
        target="windows-x86_64",
        artifact_type="msi",
        download_url="http://example.com/update.msi",
        updater_artifact_url="http://example.com/update.msi",
        updater_signature="dW50cnVzdGVkIHNpZ25hdHVyZQo=",
        pub_date="2026-06-12T00:00:00Z",
        release_notes="Test release",
        minimum_required_version="0.36.0",
        is_critical=False,
    )
    db_session.add(release)
    db_session.commit()

    resp = client.get(
        "/api/app/updater/windows/stable",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert data["notes"] == "Test release"
    assert "windows-x86_64" in data["platforms"]
    assert data["platforms"]["windows-x86_64"]["signature"] == "dW50cnVzdGVkIHNpZ25hdHVyZQo="
    assert data["platforms"]["windows-x86_64"]["url"] == "http://example.com/update.msi"


def test_updater_latest_stable_selected(client, user_token, db_session):
    """Latest stable release is selected."""
    from datetime import timedelta
    from app.models.app_release import AppRelease
    from app.db import Base
    # Clear releases from previous tests
    db_session.query(AppRelease).delete()
    db_session.commit()
    now = datetime.utcnow()
    r1 = AppRelease(
        version="0.35.0", platform="windows", channel="stable",
        target="windows-x86_64", download_url="http://old.com",
        updater_signature="old_sig", pub_date="2026-05-01T00:00:00Z",
        release_notes="Old release",
        created_at=now - timedelta(days=30),
    )
    r2 = AppRelease(
        version="1.0.0", platform="windows", channel="stable",
        target="windows-x86_64", download_url="http://new.com",
        updater_signature="new_sig", pub_date="2026-06-12T00:00:00Z",
        release_notes="New release",
        created_at=now,
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    resp = client.get(
        "/api/app/updater/windows/stable",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert data["notes"] == "New release"


def test_updater_wrong_platform_returns_empty(client, user_token, db_session):
    """Wrong platform should return no update."""
    from app.models.app_release import AppRelease
    db_session.query(AppRelease).delete()
    db_session.commit()
    db_session.add(AppRelease(
        version="1.0.0", platform="macos", channel="stable",
        target="darwin-x86_64", download_url="http://mac.com",
        updater_signature="sig", pub_date="2026-06-12T00:00:00Z",
    ))
    db_session.commit()

    resp = client.get(
        "/api/app/updater/windows/stable",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "0.0.0"
    assert data["platforms"] == {}


def test_updater_endpoint_is_public(client):
    """Updater endpoint is intentionally public (Tauri auto-updater cannot pass Bearer tokens)."""
    resp = client.get("/api/app/updater/windows/stable")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "platforms" in data
