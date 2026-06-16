"""Phase 13 — QuickBooks/Xero accounting sync tests.

Covers:
* status endpoint
* OAuth connect/callback (mock mode)
* connection list + disconnect
* field mappings CRUD
* vendor search + mapping
* category search + mapping
* preview sync (requires approved invoice + connection + vendor mapping)
* approve / reject preview
* execute sync (mock)
* validate sync result
* sync logs + failed syncs
* voice intent preview (allowed + blocked intents)
* audit log rows for every action
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.db import SessionLocal


PDF_TINY = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
)


def _upload(client: TestClient) -> dict:
    return client.post(
        "/api/invoices/upload",
        files={"file": ("test.pdf", io.BytesIO(PDF_TINY), "application/pdf")},
    ).json()


def _approve(client: TestClient, inv_id: int) -> dict:
    r = client.post(f"/api/invoices/{inv_id}/approve?actor=tester")
    assert r.status_code == 200
    return r.json()


def _create_connection(client: TestClient, provider: str = "quickbooks") -> dict:
    """Call the OAuth connect + callback to create an active connection row."""
    r = client.get(f"/api/accounting/{provider}/connect")
    assert r.status_code == 200
    r = client.get(
        f"/api/accounting/{provider}/callback",
        params={"code": "mock_code", "state": "mock_state", "realm_id": "mock_realm"},
        follow_redirects=False,
    )
    assert r.status_code in (200, 302, 307), f"Callback failed: {r.status_code} {r.text[:200]}"
    conns = client.get("/api/accounting/connections").json()
    matching = [c for c in conns if c["provider"] == provider and c["status"] == "active"]
    assert len(matching) >= 1, f"No active {provider} connection created"
    return matching[0]


def _create_vendor_mapping(client: TestClient, provider: str = "quickbooks") -> dict:
    r = client.post(
        "/api/accounting/vendors/map",
        json={
            "provider": provider,
            "local_vendor_name": "ACME Office Supplies",
            "external_contact_id": f"{provider}-vendor-001",
            "external_contact_name": "ACME (QB)",
        },
    )
    assert r.status_code == 200
    return r.json()


def _create_category_mapping(client: TestClient, provider: str = "quickbooks") -> dict:
    r = client.post(
        "/api/accounting/categories/map",
        json={
            "provider": provider,
            "local_category": "Office Supplies",
            "external_account_id": f"{provider}-cat-office",
            "external_account_name": "Office Supplies",
        },
    )
    assert r.status_code == 200
    return r.json()


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def test_accounting_status(client: TestClient):
    r = client.get("/api/accounting/status")
    assert r.status_code == 200
    data = r.json()
    assert "quickbooks_configured" in data
    assert "quickbooks_env" in data
    assert "xero_env" in data
    assert data["quickbooks_env"] == "mock"
    assert data["xero_env"] == "mock"
    assert "draft_only" in data
    assert "block_duplicates" in data


# ---------------------------------------------------------------------------
# OAuth connect
# ---------------------------------------------------------------------------


def test_quickbooks_connect_mock(client: TestClient):
    r = client.get("/api/accounting/quickbooks/connect")
    assert r.status_code == 200
    data = r.json()
    assert data["authorization_url"].startswith("https://appcenter.intuit.com/")


def test_xero_connect_mock(client: TestClient):
    r = client.get("/api/accounting/xero/connect")
    assert r.status_code == 200
    data = r.json()
    assert data["authorization_url"].startswith("https://login.xero.com/")


# ---------------------------------------------------------------------------
# OAuth callback + connection lifecycle
# ---------------------------------------------------------------------------


def test_quickbooks_callback_and_connection(client: TestClient):
    _create_connection(client, "quickbooks")
    conns = client.get("/api/accounting/connections").json()
    assert len(conns) >= 1
    conn = conns[0]
    assert conn["provider"] == "quickbooks"
    assert conn["status"] == "active"


def test_xero_callback_and_connection(client: TestClient):
    _create_connection(client, "xero")
    conns = client.get("/api/accounting/connections").json()
    assert len(conns) >= 1
    conn = conns[0]
    assert conn["provider"] == "xero"
    assert conn["status"] == "active"


def test_connections_list_empty_initial(client: TestClient):
    r = client.get("/api/accounting/connections")
    assert r.status_code == 200
    assert r.json() == []


def test_disconnect_unknown(client: TestClient):
    r = client.post("/api/accounting/connections/999/disconnect")
    assert r.status_code == 404


def test_connect_and_disconnect(client: TestClient):
    conn = _create_connection(client, "quickbooks")
    r = client.post(f"/api/accounting/connections/{conn['id']}/disconnect")
    assert r.status_code == 200
    data = r.json()
    assert data["disconnected"] is True
    assert data["provider"] == "quickbooks"

    conns = client.get("/api/accounting/connections").json()
    active = [c for c in conns if c["status"] == "active"]
    assert len(active) == 0


# ---------------------------------------------------------------------------
# Field mappings
# ---------------------------------------------------------------------------


def test_field_mappings_empty_initially(client: TestClient):
    r = client.get("/api/accounting/mappings")
    assert r.status_code == 200
    assert r.json() == []


def test_field_mappings_filter(client: TestClient):
    r = client.get("/api/accounting/mappings?provider=xero")
    assert r.status_code == 200
    assert r.json() == []


def test_create_and_list_field_mappings(client: TestClient):
    r = client.patch(
        "/api/accounting/mappings",
        json={
            "mappings": [
                {
                    "provider": "quickbooks",
                    "local_field": "vendor_name",
                    "external_field": "CustomerRef.name",
                    "enabled": True,
                },
                {
                    "provider": "xero",
                    "local_field": "total_amount",
                    "external_field": "Total",
                    "enabled": True,
                },
            ]
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2

    r = client.get("/api/accounting/mappings")
    assert len(r.json()) == 2

    r = client.get("/api/accounting/mappings?provider=quickbooks")
    qb = r.json()
    assert len(qb) == 1
    assert qb[0]["provider"] == "quickbooks"
    assert qb[0]["local_field"] == "vendor_name"


# ---------------------------------------------------------------------------
# Vendor search + mapping
# ---------------------------------------------------------------------------


def test_vendor_search_needs_connection(client: TestClient):
    r = client.get("/api/accounting/vendors/search?provider=quickbooks&query=ACME")
    assert r.status_code == 409


def test_vendor_search_mock(client: TestClient):
    _create_connection(client, "quickbooks")
    r = client.get("/api/accounting/vendors/search?provider=quickbooks&query=ACME")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0


def test_vendor_map_create(client: TestClient):
    mapping = _create_vendor_mapping(client, "quickbooks")
    assert mapping["local_vendor_name"] == "ACME Office Supplies"
    assert mapping["external_contact_id"] == "quickbooks-vendor-001"

    r = client.get("/api/accounting/vendor-mappings?provider=quickbooks")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_vendor_map_update(client: TestClient):
    _create_vendor_mapping(client, "quickbooks")
    r = client.post(
        "/api/accounting/vendors/map",
        json={
            "provider": "quickbooks",
            "local_vendor_name": "ACME Office Supplies",
            "external_contact_id": "qb-vendor-002",
            "external_contact_name": "ACME Updated",
        },
    )
    assert r.status_code == 200
    assert r.json()["external_contact_id"] == "qb-vendor-002"


# ---------------------------------------------------------------------------
# Category search + mapping
# ---------------------------------------------------------------------------


def test_category_search_needs_connection(client: TestClient):
    r = client.get("/api/accounting/categories?provider=quickbooks&query=office")
    assert r.status_code == 409


def test_category_search_mock(client: TestClient):
    _create_connection(client, "quickbooks")
    r = client.get("/api/accounting/categories?provider=quickbooks&query=office")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0


def test_category_map_create(client: TestClient):
    mapping = _create_category_mapping(client, "xero")
    assert mapping["local_category"] == "Office Supplies"
    assert mapping["external_account_id"] == "xero-cat-office"

    r = client.get("/api/accounting/category-mappings?provider=xero")
    assert r.status_code == 200
    assert len(r.json()) == 1


# ---------------------------------------------------------------------------
# Preview + approval pipeline
# ---------------------------------------------------------------------------


def test_preview_sync_not_approved(client: TestClient):
    inv = _upload(client)
    _create_connection(client, "quickbooks")
    _create_vendor_mapping(client, "quickbooks")
    _create_category_mapping(client, "quickbooks")
    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=quickbooks"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["eligible"] is False


def test_preview_sync_no_vendor_mapping(client: TestClient):
    inv = _upload(client)
    _approve(client, inv["id"])
    _create_connection(client, "quickbooks")
    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=quickbooks"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["eligible"] is False


def test_full_sync_pipeline_quickbooks(client: TestClient):
    inv = _upload(client)
    _approve(client, inv["id"])
    _create_connection(client, "quickbooks")
    _create_vendor_mapping(client, "quickbooks")
    _create_category_mapping(client, "quickbooks")

    # 1. Preview
    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=quickbooks"
    )
    assert r.status_code == 200
    preview = r.json()
    assert preview["provider"] == "quickbooks"
    assert preview["invoice_id"] == inv["id"]
    assert "preview" in preview
    assert "warnings" in preview
    assert "blockers" in preview
    preview_id = preview["preview_id"]

    # 2. Get preview
    r = client.get(f"/api/accounting/previews/{preview_id}")
    assert r.status_code == 200
    assert r.json()["id"] == preview_id

    # 3. Approve preview
    r = client.post(
        f"/api/accounting/previews/{preview_id}/approve",
        json={"actor": "tester", "reason": "Looks good"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "approved"

    # 4. Sync
    r = client.post(f"/api/accounting/previews/{preview_id}/sync?actor=tester")
    assert r.status_code == 200
    sync_result = r.json()
    assert sync_result["status"] == "success"
    assert sync_result["provider"] == "quickbooks"
    assert "external_record_id" in sync_result
    assert "sync_log_id" in sync_result
    sync_log_id = sync_result["sync_log_id"]

    # 5. Validate
    r = client.post(f"/api/accounting/sync-logs/{sync_log_id}/validate")
    assert r.status_code == 200
    validation = r.json()
    assert validation["validation_status"] in ("validated", "valid", "matched")

    # 6. Get validations
    r = client.get(f"/api/accounting/validations/{inv['id']}")
    assert r.status_code == 200
    vlist = r.json()
    assert len(vlist) >= 1


def test_preview_reject(client: TestClient):
    inv = _upload(client)
    _approve(client, inv["id"])
    _create_connection(client, "quickbooks")
    _create_vendor_mapping(client, "quickbooks")
    _create_category_mapping(client, "quickbooks")

    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=quickbooks"
    )
    assert r.status_code == 200
    preview_id = r.json()["preview_id"]

    r = client.post(
        f"/api/accounting/previews/{preview_id}/reject",
        json={"actor": "tester", "reason": "Wrong amounts"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_sync_rejected_preview_fails(client: TestClient):
    inv = _upload(client)
    _approve(client, inv["id"])
    _create_connection(client, "quickbooks")
    _create_vendor_mapping(client, "quickbooks")
    _create_category_mapping(client, "quickbooks")

    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=quickbooks"
    )
    assert r.status_code == 200
    preview_id = r.json()["preview_id"]

    client.post(
        f"/api/accounting/previews/{preview_id}/reject",
        json={"actor": "tester", "reason": "No"},
    )

    r = client.post(f"/api/accounting/previews/{preview_id}/sync?actor=tester")
    assert r.status_code == 409
    assert "rejected" in r.json()["detail"].lower()


def test_preview_double_approve(client: TestClient):
    inv = _upload(client)
    _approve(client, inv["id"])
    _create_connection(client, "quickbooks")
    _create_vendor_mapping(client, "quickbooks")
    _create_category_mapping(client, "quickbooks")

    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=quickbooks"
    )
    preview_id = r.json()["preview_id"]

    client.post(
        f"/api/accounting/previews/{preview_id}/approve",
        json={"actor": "tester", "reason": "ok"},
    )
    r = client.post(
        f"/api/accounting/previews/{preview_id}/approve",
        json={"actor": "tester", "reason": "again"},
    )
    assert r.status_code == 409


def test_preview_double_reject(client: TestClient):
    inv = _upload(client)
    _approve(client, inv["id"])
    _create_connection(client, "quickbooks")
    _create_vendor_mapping(client, "quickbooks")
    _create_category_mapping(client, "quickbooks")

    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=quickbooks"
    )
    preview_id = r.json()["preview_id"]

    client.post(
        f"/api/accounting/previews/{preview_id}/reject",
        json={"actor": "tester", "reason": "No"},
    )
    r = client.post(
        f"/api/accounting/previews/{preview_id}/reject",
        json={"actor": "tester", "reason": "Still no"},
    )
    assert r.status_code == 409


def test_xero_sync_pipeline(client: TestClient):
    inv = _upload(client)
    _approve(client, inv["id"])
    _create_connection(client, "xero")
    _create_vendor_mapping(client, "xero")
    _create_category_mapping(client, "xero")

    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=xero"
    )
    assert r.status_code == 200
    preview_id = r.json()["preview_id"]

    r = client.post(
        f"/api/accounting/previews/{preview_id}/approve",
        json={"actor": "tester", "reason": "Good"},
    )
    assert r.status_code == 200

    r = client.post(f"/api/accounting/previews/{preview_id}/sync?actor=tester")
    assert r.status_code == 200
    sync_result = r.json()
    assert sync_result["status"] == "success"
    assert sync_result["provider"] == "xero"

    r = client.post(f"/api/accounting/sync-logs/{sync_result['sync_log_id']}/validate")
    assert r.status_code == 200
    assert r.json()["validation_status"] in ("validated", "valid", "matched")


# ---------------------------------------------------------------------------
# Sync logs + failed syncs
# ---------------------------------------------------------------------------


def test_sync_logs_list(client: TestClient):
    r = client.get("/api/accounting/sync-logs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_failed_syncs_empty(client: TestClient):
    r = client.get("/api/accounting/failed-syncs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_sync_logs_filtered(client: TestClient):
    inv = _upload(client)
    _approve(client, inv["id"])
    _create_connection(client, "quickbooks")
    _create_vendor_mapping(client, "quickbooks")
    _create_category_mapping(client, "quickbooks")

    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=quickbooks"
    )
    preview_id = r.json()["preview_id"]
    client.post(
        f"/api/accounting/previews/{preview_id}/approve",
        json={"actor": "tester", "reason": "ok"},
    )
    client.post(f"/api/accounting/previews/{preview_id}/sync?actor=tester")

    r = client.get(f"/api/accounting/sync-logs?invoice_id={inv['id']}")
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ---------------------------------------------------------------------------
# Voice intents
# ---------------------------------------------------------------------------


def test_voice_preview_known_intent(client: TestClient):
    r = client.post(
        "/api/accounting/voice/preview",
        json={
            "provider": "quickbooks",
            "intent": "export_this_invoice_to_quickbooks",
            "invoice_id": None,
            "actor": "tester",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["blocked"] is False
    assert data["intent"] == "export_this_invoice_to_quickbooks"


def test_voice_preview_unknown_intent(client: TestClient):
    r = client.post(
        "/api/accounting/voice/preview",
        json={
            "provider": "quickbooks",
            "intent": "create_quickbooks_entry",
            "invoice_id": None,
            "actor": "tester",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["blocked"] is True


def test_voice_preview_with_invoice(client: TestClient):
    inv = _upload(client)
    r = client.post(
        "/api/accounting/voice/preview",
        json={
            "provider": "quickbooks",
            "intent": "export_this_invoice_to_quickbooks",
            "invoice_id": inv["id"],
            "actor": "tester",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["blocked"] is False
    assert data["intent"] == "export_this_invoice_to_quickbooks"


# ---------------------------------------------------------------------------
# Audit log entries
# ---------------------------------------------------------------------------


def _audit_logs(client: TestClient) -> list[dict]:
    r = client.get("/api/audit-logs")
    assert r.status_code == 200
    return r.json()


def test_audit_log_connect(client: TestClient):
    client.get("/api/accounting/quickbooks/connect")
    logs = _audit_logs(client)
    actions = [log["action"] for log in logs]
    assert any("oauth.start" in a for a in actions)


def test_audit_log_disconnect(client: TestClient):
    conn = _create_connection(client, "quickbooks")
    client.post(f"/api/accounting/connections/{conn['id']}/disconnect")
    logs = _audit_logs(client)
    actions = [log["action"] for log in logs]
    assert any("disconnected" in a for a in actions)


def test_audit_log_preview_and_sync(client: TestClient):
    inv = _upload(client)
    _approve(client, inv["id"])
    _create_connection(client, "quickbooks")
    _create_vendor_mapping(client, "quickbooks")
    _create_category_mapping(client, "quickbooks")

    r = client.post(
        f"/api/accounting/invoices/{inv['id']}/preview-sync?provider=quickbooks"
    )
    preview_id = r.json()["preview_id"]

    client.post(
        f"/api/accounting/previews/{preview_id}/approve",
        json={"actor": "tester", "reason": "ok"},
    )
    client.post(f"/api/accounting/previews/{preview_id}/sync?actor=tester")

    logs = _audit_logs(client)
    actions = [log["action"] for log in logs]
    assert any("preview" in a for a in actions)
    assert any("preview.approve" in a for a in actions)
    assert any(".sync" in a for a in actions)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_preview_unknown_invoice(client: TestClient):
    r = client.post(
        "/api/accounting/invoices/99999/preview-sync?provider=quickbooks"
    )
    assert r.status_code == 404


def test_vendor_search_bad_provider(client: TestClient):
    r = client.get("/api/accounting/vendors/search?provider=unknown&query=test")
    assert r.status_code == 409
