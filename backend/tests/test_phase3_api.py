"""Phase 3 API tests: mark-duplicate, organize-file, review-queue, audit, folder-rules."""

from __future__ import annotations

import io

import fitz
from fastapi.testclient import TestClient


def _make_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    text = (
        "ACME Office Supplies\n"
        "INVOICE\n"
        "Invoice Number: INV-2026-0042\n"
        "Invoice Date: 2026-05-12\n"
        "Total: $460.64\n"
    )
    page.insert_text((50, 60), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def _upload(client: TestClient, *, name: str = "a.pdf", actor: str = "user") -> int:
    pdf = _make_pdf_bytes()
    r = client.post(
        "/api/invoices/upload",
        params={"actor": actor},
        files={"file": (name, io.BytesIO(pdf), "application/pdf")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------- mark-duplicate


def test_mark_duplicate_links_invoice_and_records_audit(client: TestClient):
    original = _upload(client, name="orig.pdf")
    dup = _upload(client, name="copy.pdf", actor="alice")

    r = client.post(
        f"/api/invoices/{dup}/mark-duplicate",
        params={"duplicate_of": original, "actor": "alice"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "duplicate"
    assert body["duplicate_of_invoice_id"] == original

    logs = client.get("/api/audit-logs", params={"entity_id": dup, "entity_type": "invoice"}).json()
    actions = [l["action"] for l in logs]
    assert "mark_duplicate" in actions
    md_log = next(l for l in logs if l["action"] == "mark_duplicate")
    assert md_log["before_data_json"]["status"] != "duplicate"
    assert md_log["after_data_json"]["status"] == "duplicate"
    assert md_log["after_data_json"]["duplicate_of_invoice_id"] == original


def test_cannot_approve_marked_duplicate(client: TestClient):
    original = _upload(client, name="orig.pdf")
    dup = _upload(client, name="copy.pdf")
    client.post(f"/api/invoices/{dup}/mark-duplicate", params={"duplicate_of": original})

    r = client.post(f"/api/invoices/{dup}/approve")
    assert r.status_code == 409
    assert "duplicate" in r.json()["detail"].lower()


def test_cannot_mark_self_as_duplicate(client: TestClient):
    inv = _upload(client)
    r = client.post(f"/api/invoices/{inv}/mark-duplicate", params={"duplicate_of": inv})
    assert r.status_code == 400


def test_cannot_mark_against_another_duplicate(client: TestClient):
    a = _upload(client, name="a.pdf")
    b = _upload(client, name="b.pdf")
    c = _upload(client, name="c.pdf")
    client.post(f"/api/invoices/{b}/mark-duplicate", params={"duplicate_of": a})
    r = client.post(f"/api/invoices/{c}/mark-duplicate", params={"duplicate_of": b})
    assert r.status_code == 400


# ---------------------------------------------------------------- organize-file


def test_organize_file_endpoint_moves_to_target(client: TestClient):
    inv = _upload(client)
    r = client.post(f"/api/invoices/{inv}/organize-file", params={"actor": "user"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["file"]["organized_path"], "organized_path should be set"
    # Both paths should now point to the moved file
    assert body["file"]["current_path"] == body["file"]["organized_path"]
    import os
    assert os.path.exists(body["file"]["organized_path"])


def test_organize_file_disabled_returns_conflict(client: TestClient):
    inv = _upload(client)
    # Disable folder rules via the settings endpoint
    client.patch("/api/settings/folder-rules", json={"enabled": False})

    r = client.post(f"/api/invoices/{inv}/organize-file")
    assert r.status_code == 409


def test_organize_file_records_audit_with_diff(client: TestClient):
    inv = _upload(client, actor="alice")
    r = client.post(f"/api/invoices/{inv}/organize-file", params={"actor": "alice"})
    assert r.status_code == 200
    logs = client.get("/api/audit-logs", params={"entity_id": inv, "entity_type": "invoice"}).json()
    actions = [l["action"] for l in logs]
    assert "organize_file" in actions
    org_log = next(l for l in logs if l["action"] == "organize_file")
    assert org_log["actor"] == "alice"
    assert "from" in org_log["before_data_json"]["current_path"] or org_log["before_data_json"]["current_path"]
    assert org_log["after_data_json"]["organized_path"]


# ---------------------------------------------------------------- review queue


def test_review_queue_groups_by_status(client: TestClient):
    a = _upload(client, name="a.pdf")
    b = _upload(client, name="b.pdf")
    c = _upload(client, name="c.pdf")

    # Approve a
    client.patch(
        f"/api/invoices/{a}",
        json={
            "vendor_name": "ACME",
            "invoice_number": "X",
            "invoice_date": "2026-01-01",
            "currency": "USD",
            "total_amount": 1.0,
        },
    )
    client.post(f"/api/invoices/{a}/approve")

    # Reject b
    client.patch(
        f"/api/invoices/{b}",
        json={
            "vendor_name": "ACME",
            "invoice_number": "Y",
            "invoice_date": "2026-01-01",
            "currency": "USD",
            "total_amount": 1.0,
        },
    )
    client.post(f"/api/invoices/{b}/reject", params={"reason": "test"})

    r = client.get("/api/invoices/review-queue")
    assert r.status_code == 200
    body = r.json()

    # Counts reflect actual statuses
    assert body["counts"]["approved"] >= 1
    assert body["counts"]["rejected"] >= 1

    # Lists contain the relevant invoices
    approved_ids = {i["id"] for i in body["by_status"]["approved"]}
    rejected_ids = {i["id"] for i in body["by_status"]["rejected"]}
    assert a in approved_ids
    assert b in rejected_ids
    # c is still ready_for_approval (or needs_review) – it shouldn't be in approved/rejected
    assert c not in approved_ids
    assert c not in rejected_ids

    # Each item carries the trust-layer metadata
    for item in body["by_status"]["rejected"]:
        if item["id"] == b:
            assert item["rejected_reason"] == "test"


def test_review_queue_duplicate_items_carry_duplicate_of_id(client: TestClient):
    a = _upload(client, name="a.pdf")
    b = _upload(client, name="b.pdf")
    client.post(f"/api/invoices/{b}/mark-duplicate", params={"duplicate_of": a})

    r = client.get("/api/invoices/review-queue").json()
    dup_items = r["by_status"]["duplicate"]
    target = next(i for i in dup_items if i["id"] == b)
    assert target["duplicate_of_invoice_id"] == a


# ---------------------------------------------------------------- audit timeline


def test_invoice_audit_timeline_returns_actions_newest_first(client: TestClient):
    inv = _upload(client, actor="alice")
    client.patch(
        f"/api/invoices/{inv}",
        json={"vendor_name": "Edited", "actor": "alice"},
    )
    client.post(f"/api/invoices/{inv}/organize-file", params={"actor": "alice"})

    r = client.get(f"/api/invoices/{inv}/audit")
    assert r.status_code == 200
    body = r.json()
    actions = [entry["action"] for entry in body]
    # Newest first means the most recent action is at index 0
    assert actions[0] in ("organize_file", "edit", "extraction", "upload")
    # Must include all of upload, extraction, edit, organize_file
    assert "upload" in actions
    assert "extraction" in actions
    assert "edit" in actions
    assert "organize_file" in actions
    # Newest first: timestamps should be non-increasing
    timestamps = [entry["timestamp"] for entry in body]
    assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------- folder rules


def test_get_folder_rules_returns_defaults(client: TestClient):
    r = client.get("/api/settings/folder-rules")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["conflict_strategy"] in ("suffix", "skip", "overwrite")
    assert body["move_on_approve"] is True
    assert "{vendor}" in body["pattern"]


def test_patch_folder_rules_updates_and_audits(client: TestClient):
    r = client.patch(
        "/api/settings/folder-rules",
        params={"actor": "alice"},
        json={"pattern": "Bills/{year}/{vendor}.{ext}", "conflict_strategy": "skip"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pattern"] == "Bills/{year}/{vendor}.{ext}"
    assert body["conflict_strategy"] == "skip"

    r2 = client.get("/api/settings/folder-rules")
    assert r2.json() == body

    # Audit log contains the change
    r3 = client.get("/api/settings/folder-rules/audit")
    assert r3.status_code == 200
    rows = r3.json()
    assert rows
    latest = rows[0]
    assert latest["actor"] == "alice"
    assert latest["after"]["pattern"] == "Bills/{year}/{vendor}.{ext}"
    assert latest["before"]["pattern"] != latest["after"]["pattern"]


def test_patch_folder_rules_partial_update_preserves_other_fields(client: TestClient):
    r = client.patch("/api/settings/folder-rules", json={"move_on_approve": False})
    assert r.status_code == 200
    body = r.json()
    assert body["move_on_approve"] is False
    # Other fields preserved
    assert body["enabled"] is True
    assert body["conflict_strategy"] in ("suffix", "skip", "overwrite")


def test_patch_folder_rules_invalid_strategy_rejected(client: TestClient):
    r = client.patch("/api/settings/folder-rules", json={"conflict_strategy": "nope"})
    assert r.status_code == 422


# ---------------------------------------------------------------- approve/reject contract


def test_approve_records_approved_by_and_audits_with_diff(client: TestClient):
    inv = _upload(client)
    client.patch(
        f"/api/invoices/{inv}",
        json={
            "vendor_name": "ACME",
            "invoice_number": "X",
            "invoice_date": "2026-01-01",
            "currency": "USD",
            "total_amount": 1.0,
        },
    )

    r = client.post(f"/api/invoices/{inv}/approve", params={"actor": "manager"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "approved"
    assert body["approved_by"] == "manager"
    assert body["approved_at"]

    logs = client.get("/api/audit-logs", params={"entity_id": inv, "entity_type": "invoice"}).json()
    approve = next(l for l in logs if l["action"] == "approve")
    assert approve["actor"] == "manager"
    assert approve["after_data_json"]["status"] == "approved"
    assert approve["before_data_json"]["status"] == "ready_for_approval"


def test_reject_requires_reason(client: TestClient):
    inv = _upload(client)
    client.patch(
        f"/api/invoices/{inv}",
        json={"vendor_name": "ACME", "invoice_number": "X", "invoice_date": "2026-01-01",
              "currency": "USD", "total_amount": 1.0},
    )
    r = client.post(f"/api/invoices/{inv}/reject")
    assert r.status_code == 400
    assert "reason" in r.json()["detail"].lower()


def test_reject_stores_reason_on_invoice_and_audit(client: TestClient):
    inv = _upload(client)
    client.patch(
        f"/api/invoices/{inv}",
        json={"vendor_name": "ACME", "invoice_number": "X", "invoice_date": "2026-01-01",
              "currency": "USD", "total_amount": 1.0},
    )
    r = client.post(f"/api/invoices/{inv}/reject", params={"reason": "duplicate vendor", "actor": "bob"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "rejected"
    assert body["rejected_reason"] == "duplicate vendor"

    logs = client.get("/api/audit-logs", params={"entity_id": inv, "entity_type": "invoice"}).json()
    reject = next(l for l in logs if l["action"] == "reject")
    assert reject["actor"] == "bob"
    assert reject["after_data_json"]["rejected_reason"] == "duplicate vendor"


# ---------------------------------------------------------------- file preview endpoint


def test_file_preview_inline_disposition(client: TestClient):
    inv = _upload(client)
    r = client.get(f"/api/invoices/{inv}/file", params={"inline": True})
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith("inline")


def test_file_preview_attachment_disposition(client: TestClient):
    inv = _upload(client)
    r = client.get(f"/api/invoices/{inv}/file", params={"inline": False})
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith("attachment")
