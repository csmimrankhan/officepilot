"""Phase 41 — Semantic Memory & RAG (Local Vector DB) tests."""

from __future__ import annotations

import json
import os
import tempfile

os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["AGENT_PROVIDER"] = "mock"
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
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(User).delete()
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
        email="semantic_test@example.com",
        password_hash=hash_password("testpass"),
        role="admin",
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
def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def vector_dir():
    d = tempfile.mkdtemp(prefix="op_vector_")
    yield d
    import time
    import shutil
    time.sleep(0.1)
    for _ in range(3):
        try:
            shutil.rmtree(d, ignore_errors=False)
            break
        except PermissionError:
            time.sleep(0.2)


@pytest.fixture
def sm(vector_dir):
    from app.services.semantic_memory import SemanticMemory
    memory = SemanticMemory(persist_dir=vector_dir)
    yield memory
    try:
        memory.reset()
    except Exception:
        pass
    if memory._client is not None:
        try:
            memory._client.clear_system_cache()
        except Exception:
            pass


# ── Pure SemanticMemory service tests ──


class TestSemanticMemory:
    def test_index_and_search_exact_match(self, sm):
        sm.index_invoice(
            invoice_id="INV-001",
            text_content="Acme Corp invoice for $1500.00 dated 2025-01-15",
            metadata={"vendor": "Acme Corp", "amount": 1500.0, "date": "2025-01-15", "file_path": "/invoices/acme.pdf"},
        )
        results = sm.semantic_search("Acme Corp", top_k=5)
        assert len(results) >= 1
        assert results[0]["metadata"]["vendor"] == "Acme Corp"

    def test_search_returns_top_k(self, sm):
        for i in range(10):
            sm.index_invoice(
                invoice_id=f"INV-{i:03d}",
                text_content=f"Invoice from Vendor {i} for ${i * 100}.00",
                metadata={"vendor": f"Vendor {i}", "amount": i * 100},
            )
        results = sm.semantic_search("Vendor", top_k=3)
        assert len(results) <= 3

    def test_search_with_no_results(self, sm):
        sm.index_invoice(
            invoice_id="INV-001",
            text_content="Acme Corp invoice for $1500.00",
            metadata={"vendor": "Acme Corp", "amount": 1500.0},
        )
        results = sm.semantic_search("zzz_nonexistent_zzz", top_k=5)
        assert isinstance(results, list)

    def test_index_multiple_and_count(self, sm):
        for i in range(5):
            sm.index_invoice(
                invoice_id=f"INV-{i:03d}",
                text_content=f"Invoice {i} data",
                metadata={"vendor": f"Vendor {i}"},
            )
        assert sm.count() == 5

    def test_reset_clears_collection(self, sm):
        sm.index_invoice(
            invoice_id="INV-001",
            text_content="test data",
            metadata={"vendor": "Test"},
        )
        assert sm.count() == 1
        sm.reset()
        sm.initialize(sm._persist_dir)
        assert sm.count() == 0

    def test_mock_embedding_deterministic(self):
        from app.services.semantic_memory import MockEmbeddingFunction
        ef = MockEmbeddingFunction()
        v1 = ef(["hello world"])
        v2 = ef(["hello world"])
        v3 = ef(["different text"])
        assert v1 == v2
        assert v1 != v3
        assert all(isinstance(x, float) for x in v1[0])

    def test_index_with_user_id_filter(self, sm):
        sm.index_invoice(
            invoice_id="INV-001",
            text_content="Acme Corp invoice",
            metadata={"vendor": "Acme Corp", "user_id": 1},
        )
        sm.index_invoice(
            invoice_id="INV-002",
            text_content="Beta Corp invoice",
            metadata={"vendor": "Beta Corp", "user_id": 2},
        )
        results = sm.semantic_search("invoice", top_k=10, user_id=1)
        for r in results:
            assert r["metadata"]["user_id"] == 1


# ── Tool executor tests ──


class TestSemanticSearchExecutor:
    def test_executor_returns_results(self, sm, monkeypatch):
        sm.index_invoice(
            invoice_id="INV-001",
            text_content="Acme Corp $1500.00 invoice",
            metadata={"vendor": "Acme Corp", "amount": 1500.0, "date": "2025-01-15", "file_path": "/invoices/acme.pdf"},
        )
        monkeypatch.setattr("app.services.semantic_memory.get_semantic_memory", lambda: sm)

        from app.services.agent_tool_executor import _execute_semantic_search_invoices
        result = _execute_semantic_search_invoices({"query": "Acme", "top_k": 5}, db=None, user=None)
        assert result["status"] == "success"
        output = result["output"]
        assert output["total_found"] >= 1
        assert output["results"][0]["vendor"] == "Acme Corp"

    def test_executor_empty_query_fails(self):
        from app.services.agent_tool_executor import _execute_semantic_search_invoices
        result = _execute_semantic_search_invoices({"query": ""}, db=None, user=None)
        assert result["status"] == "failed"

    def test_executor_no_params_fails(self):
        from app.services.agent_tool_executor import _execute_semantic_search_invoices
        result = _execute_semantic_search_invoices({}, db=None, user=None)
        assert result["status"] == "failed"

    def test_executor_returns_found_invoices_in_correct_format(self, sm, monkeypatch):
        sm.index_invoice(
            invoice_id="INV-001",
            text_content="Acme Corp $1500.00 invoice 2025-01-15",
            metadata={
                "vendor": "Acme Corp", "amount": 1500.0, "date": "2025-01-15",
                "file_path": "/invoices/acme.pdf", "invoice_no": "INV-001", "currency": "USD",
            },
        )
        monkeypatch.setattr("app.services.semantic_memory.get_semantic_memory", lambda: sm)

        from app.services.agent_tool_executor import _execute_semantic_search_invoices
        result = _execute_semantic_search_invoices({"query": "Acme", "top_k": 5}, db=None, user=None)
        inv = result["output"]["results"][0]
        assert "vendor" in inv
        assert "amount" in inv
        assert "date" in inv
        assert "file_path" in inv
        assert "score" in inv


# ── Integration tests via execute_tool and HTTP ──


class TestSemanticSearchIntegration:
    def test_execute_tool_dispatches_correctly(self, sm, monkeypatch):
        sm.index_invoice(
            invoice_id="INV-001",
            text_content="Acme Corp $1500.00",
            metadata={"vendor": "Acme Corp", "amount": 1500.0},
        )
        monkeypatch.setattr("app.services.semantic_memory.get_semantic_memory", lambda: sm)

        from app.services.agent_tool_executor import execute_tool
        result = execute_tool("semantic_search_invoices", {"query": "Acme", "top_k": 5}, mode="live", db=None, user=None)
        assert result["status"] == "success"
        assert result["output"]["total_found"] >= 1

    def test_tool_registered_in_registry(self):
        from app.services.tool_registry import get_tool
        tool = get_tool("semantic_search_invoices")
        assert tool is not None
        assert tool.risk_level == "low"
        assert tool.approval_required is False

    def test_tool_def_in_input_schema_requires_query(self):
        from app.services.tool_registry import get_tool
        tool = get_tool("semantic_search_invoices")
        props = tool.input_schema.get("properties", {})
        assert "query" in props
        assert "top_k" in props

    def test_extract_invoice_data_indexes_in_semantic_memory(self, monkeypatch):
        indexed = []

        class FakeSM:
            def index_invoice(self, invoice_id, text_content, metadata=None):
                indexed.append({"invoice_id": invoice_id, "text_content": text_content, "metadata": metadata})

        monkeypatch.setattr("app.services.semantic_memory.get_semantic_memory", lambda: FakeSM())

        from app.services.agent_tool_executor import _execute_extract_invoice_data
        result = _execute_extract_invoice_data(
            {"filepath": ""},
            db=None, user=None,
        )
        assert result["status"] == "success"
        assert len(indexed) >= 1
        assert indexed[0]["metadata"]["vendor"] in ("Demo Corp", "Sample Ltd")

    def test_semantic_search_via_http_endpoint(self, client, headers, sm, monkeypatch):
        sm.index_invoice(
            invoice_id="INV-001",
            text_content="Acme Corp $1500.00 invoice data for testing",
            metadata={"vendor": "Acme Corp", "amount": 1500.0, "date": "2025-01-15"},
        )
        monkeypatch.setattr("app.services.semantic_memory.get_semantic_memory", lambda: sm)
        monkeypatch.setattr("app.services.semantic_memory.get_semantic_memory", lambda: sm)

        plan = {"steps": [{
            "tool": "semantic_search_invoices",
            "params": {"query": "Acme", "top_k": 5},
            "description": "Search for Acme invoices",
        }]}
        resp = client.post(
            "/api/agent/run-background",
            json={"command": "search Acme invoices", "plan_json": plan},
            headers=headers,
        )
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]

        import time
        time.sleep(2)

        resp = client.get(f"/api/agent/background-tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed", f"Expected completed, got {data['status']}: {data}"
        result_summary = data.get("result_summary", {})
        step_results = result_summary.get("step_results", [])
        assert len(step_results) >= 1
        assert step_results[0]["status"] == "success"
