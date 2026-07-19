"""End-to-end API tests driving the full pipeline over HTTP."""

from __future__ import annotations

from fastapi.testclient import TestClient

from advisor.api.app import create_app
from advisor.api.sessions import SessionStore
from advisor.config import Settings

from .conftest import FakeLLM


def _upload(client: TestClient, data: bytes) -> str:
    resp = client.post(
        "/api/upload", files={"file": ("stmt.xlsx", data, "application/vnd.ms-excel")}
    )
    assert resp.status_code == 201, resp.text
    session_id: str = resp.json()["session_id"]
    return session_id


def test_health(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_returns_summary(client: TestClient, sample_xlsx: bytes) -> None:
    resp = client.post(
        "/api/upload", files={"file": ("stmt.xlsx", sample_xlsx, "application/vnd.ms-excel")}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["summary"]["n_periods"] == 2
    assert body["summary"]["currency"] == "USD"


def test_upload_uses_configured_company_profile(sample_xlsx: bytes) -> None:
    settings = Settings(
        company_name="A1 Polymer Ltd.",
        group_name="Anwar Group of Industries",
        currency="BDT",
        fiscal_year_end_month=6,
    )
    app = create_app(settings=settings, session_store=SessionStore())
    with TestClient(app) as configured_client:
        resp = configured_client.post(
            "/api/upload", files={"file": ("stmt.xlsx", sample_xlsx, "application/vnd.ms-excel")}
        )
        assert resp.status_code == 201
        summary = resp.json()["summary"]
        assert summary["company_name"] == "A1 Polymer Ltd."
        assert summary["currency"] == "BDT"


def test_template_download_roundtrip(client: TestClient) -> None:
    resp = client.get("/api/template")
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"  # xlsx is a zip
    assert "income_statement_template.xlsx" in resp.headers["content-disposition"]


def test_upload_bad_file_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/upload", files={"file": ("x.xlsx", b"not a workbook", "application/x")}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "ingestion_failed"


def test_analyze_produces_facts_and_narrative(
    client: TestClient, sample_xlsx: bytes, fake_llm: FakeLLM
) -> None:
    sid = _upload(client, sample_xlsx)
    resp = client.post("/api/analyze", json={"session_id": sid, "include_narrative": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["facts"]["engine_version"]
    assert body["narrative"]["provider"] == "fake"
    assert "charts" in body["dashboard"]
    assert fake_llm.calls  # the injected LLM was used


def test_analyze_unknown_session_404(client: TestClient) -> None:
    resp = client.post("/api/analyze", json={"session_id": "nope", "include_narrative": False})
    assert resp.status_code == 404
    assert resp.json()["code"] == "session_not_found"


def test_scenario_reflows(client: TestClient, sample_xlsx: bytes) -> None:
    sid = _upload(client, sample_xlsx)
    client.post("/api/analyze", json={"session_id": sid, "include_narrative": False})
    resp = client.post(
        "/api/scenario",
        json={"session_id": sid, "assumptions": {"cogs_pct": "8"}},
    )
    assert resp.status_code == 200
    assert resp.json()["comparison"]["metric_deltas"]


def test_chat_requires_analysis(client: TestClient, sample_xlsx: bytes) -> None:
    sid = _upload(client, sample_xlsx)
    resp = client.post("/api/chat", json={"session_id": sid, "message": "How are margins?"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "not_analyzed"


def test_chat_after_analysis(client: TestClient, sample_xlsx: bytes) -> None:
    sid = _upload(client, sample_xlsx)
    client.post("/api/analyze", json={"session_id": sid, "include_narrative": False})
    resp = client.post("/api/chat", json={"session_id": sid, "message": "How are margins?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"]
    assert len(body["history"]) == 2


def test_exports(client: TestClient, sample_xlsx: bytes) -> None:
    sid = _upload(client, sample_xlsx)
    client.post("/api/analyze", json={"session_id": sid, "include_narrative": False})

    excel = client.get(f"/api/export/excel?session_id={sid}")
    assert excel.status_code == 200
    assert excel.content[:2] == b"PK"  # xlsx is a zip

    pdf = client.get(f"/api/export/pdf?session_id={sid}")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")

    dash = client.get(f"/api/export/dashboard?session_id={sid}")
    assert dash.status_code == 200
    assert "charts" in dash.json()


def test_delete_session(client: TestClient, sample_xlsx: bytes) -> None:
    sid = _upload(client, sample_xlsx)
    assert client.delete(f"/api/session/{sid}").status_code == 204
    assert client.post("/api/analyze", json={"session_id": sid}).status_code == 404
