"""Audit log tests."""

from fastapi.testclient import TestClient


def test_audit_logs_include_all_required_actions(client: TestClient):
    import io
    from tests.test_api import _make_pdf_bytes
    pdf = _make_pdf_bytes()
    r = client.post(
        "/api/invoices/upload",
        files={"file": ("x.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    inv_id = r.json()["id"]
    client.patch(f"/api/invoices/{inv_id}", json={"vendor_name": "X"})
    client.post(f"/api/invoices/{inv_id}/reject", params={"reason": "test"})
    client.get("/api/invoices/export/excel")

    actions = [
        a
        for a in client.get("/api/audit-logs", params={"entity_id": inv_id}).json()
    ]
    seen = {row["action"] for row in actions}
    assert "upload" in seen
    assert "extraction" in seen
    assert "edit" in seen
    assert "reject" in seen
    # export.excel has entity_id=None; query it separately.
    export_logs = client.get("/api/audit-logs", params={"action": "export.excel"}).json()
    assert any(row["action"] == "export.excel" for row in export_logs)
