"""Tests for the Phase 5 parser endpoints."""

from __future__ import annotations


def test_list_engines_endpoint(client):
    r = client.get("/api/parser/engines")
    assert r.status_code == 200
    body = r.json()
    names = {e["name"] for e in body["engines"]}
    assert names == {"existing", "docling", "ocr", "hybrid"}


def test_benchmark_endpoint_returns_json(client):
    r = client.get("/api/parser/benchmark?engines=existing")
    assert r.status_code == 200
    body = r.json()
    assert body["engines"] == ["existing"]
    assert "summary" in body
    assert "runs" in body
    assert len(body["runs"]) == 3


def test_benchmark_endpoint_returns_csv(client):
    r = client.get("/api/parser/benchmark?engines=existing&format=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    text = r.text
    # Header should include all field columns.
    assert "engine,fixture,file" in text
    # And the summary section should appear.
    assert "Per-engine summary" in text


def test_benchmark_endpoint_all_engines_default(client):
    r = client.get("/api/parser/benchmark")
    assert r.status_code == 200
    body = r.json()
    # All 4 engines are available.
    assert set(body["summary"].keys()) == {"existing", "docling", "ocr", "hybrid"}


def test_benchmark_endpoint_invalid_format_422(client):
    r = client.get("/api/parser/benchmark?format=xml")
    assert r.status_code == 422
