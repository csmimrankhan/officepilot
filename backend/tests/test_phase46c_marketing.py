"""Phase 46C — Marketing Blitz & Waitlist Activation tests."""

from __future__ import annotations

import os

os.environ["OFFICEPILOT_APP_VERSION"] = "1.0.0"

from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()
client = TestClient(app)


def _admin_headers():
    from app.services.auth import create_access_token
    from app.db import SessionLocal, init_db
    from app.models.user import User

    init_db()
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == "admin@test.com").first()
        if not u:
            from app.services.auth import hash_password

            u = User(
                email="admin@test.com",
                password_hash=hash_password("testpass"),
                role="admin",
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        token = create_access_token(u.id, u.email, u.role)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


def test_launch_email_returns_html():
    headers = _admin_headers()
    resp = client.get("/api/admin/waitlist/launch-email", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/html; charset=utf-8"
    body = resp.text
    assert "OfficePilot v1.0.0" in body
    assert "Download" in body
    assert "Multi-Agent Swarm" in body
    assert "Semantic Bank Reconciliation" in body
    assert "Live Voice-Driven Excel Editing" in body
    assert "Autonomous Background Watchers" in body
    assert "Ollama Local LLM Brain" in body


def test_launch_email_injects_name():
    headers = _admin_headers()
    resp = client.get("/api/admin/waitlist/launch-email?name=Alice", headers=headers)
    assert resp.status_code == 200
    assert "Hello Alice" in resp.text


def test_launch_email_default_name():
    headers = _admin_headers()
    resp = client.get("/api/admin/waitlist/launch-email", headers=headers)
    assert resp.status_code == 200
    assert "Hello there" in resp.text


def test_launch_email_requires_admin():
    resp = client.get("/api/admin/waitlist/launch-email")
    assert resp.status_code == 401
