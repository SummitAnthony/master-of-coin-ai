"""API routes: upload, analyze, scenario, chat, export, health, session delete."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

import advisor
from advisor.config import Settings, load_thresholds
from advisor.engine.facts import build_facts
from advisor.engine.scenario import run_scenario
from advisor.ingestion import extract_income_statement
from advisor.ingestion.extractor import ExtractOptions
from advisor.narrative.advisor import Advisory
from advisor.narrative.advisor import advisor as run_advisor
from advisor.narrative.chat import answer_question
from advisor.narrative.client import SupportsGenerate
from advisor.reports.dashboard import build_dashboard_payload
from advisor.reports.excel import build_workbook
from advisor.reports.pdf import build_pdf_bytes
from advisor.reports.template import build_input_template
from advisor.reports.word import build_document

from .deps import get_optional_llm_client, get_session_store, get_settings
from .errors import ApiError
from .models import (
    AnalysisResponse,
    AnalyzeRequest,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ExportFormat,
    HealthResponse,
    ScenarioRequest,
    ScenarioResponse,
    UploadResponse,
    to_scenario_model,
    to_statement_summary,
)
from .sessions import Session, SessionStore

router = APIRouter(prefix="/api")

_EXPORT_MEDIA = {
    ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ExportFormat.PDF: "application/pdf",
    ExportFormat.WORD: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_EXPORT_EXT = {ExportFormat.EXCEL: "xlsx", ExportFormat.PDF: "pdf", ExportFormat.WORD: "docx"}


def _require_session(store: SessionStore, session_id: str) -> Session:
    try:
        return store.get(session_id)
    except KeyError as exc:
        raise ApiError(404, "session_not_found", f"No session {session_id!r}") from exc


def _require_analyzed(session: Session) -> Session:
    if session.facts is None:
        raise ApiError(409, "not_analyzed", "Call /api/analyze before this operation")
    return session


def _dash_narrative(session: Session) -> Advisory:
    return session.narrative or Advisory(
        executive_summary="",
        risk_commentary="",
        recommendations=[],
        provider="none",
        model="none",
        degraded=True,
    )


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok", version=advisor.__version__, provider=settings.llm_provider.value
    )


@router.get("/template")
def template(settings: Settings = Depends(get_settings)) -> StreamingResponse:
    """Download a blank input template pre-labelled for the configured profile."""
    buffer = BytesIO()
    build_input_template(entity=settings.entity_meta()).save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type=_EXPORT_MEDIA[ExportFormat.EXCEL],
        headers={"Content-Disposition": 'attachment; filename="income_statement_template.xlsx"'},
    )


@router.post("/upload", status_code=201)
def upload(
    file: UploadFile = File(...),
    store: SessionStore = Depends(get_session_store),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    content = file.file.read()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        statement = extract_income_statement(
            tmp_path, ExtractOptions(entity=settings.entity_meta())
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    session = store.create(statement, load_thresholds())
    return UploadResponse(session_id=session.id, summary=to_statement_summary(statement))


@router.post("/analyze")
def analyze(
    req: AnalyzeRequest,
    store: SessionStore = Depends(get_session_store),
    settings: Settings = Depends(get_settings),
    llm: SupportsGenerate | None = Depends(get_optional_llm_client),
) -> AnalysisResponse:
    session = _require_session(store, req.session_id)
    session.facts = build_facts(session.statement, thresholds=session.thresholds)
    if req.include_narrative:
        session.narrative = run_advisor(
            session.facts, client=llm, settings=settings, fail_soft=True
        )
    dashboard = build_dashboard_payload(
        session.facts, _dash_narrative(session), generated_at=datetime.now(UTC)
    )
    return AnalysisResponse(
        session_id=session.id, facts=session.facts, narrative=session.narrative, dashboard=dashboard
    )


@router.post("/scenario")
def scenario(
    req: ScenarioRequest,
    store: SessionStore = Depends(get_session_store),
    settings: Settings = Depends(get_settings),
    llm: SupportsGenerate | None = Depends(get_optional_llm_client),
) -> ScenarioResponse:
    session = _require_session(store, req.session_id)
    model = to_scenario_model(req.name, req.assumptions)
    result = run_scenario(session.statement, model, thresholds=session.thresholds)
    session.scenario_facts = result.scenario_facts
    narrative = _dash_narrative(session)
    if req.include_narrative:
        narrative = run_advisor(
            result.scenario_facts, client=llm, settings=settings, fail_soft=True
        )
    dashboard = build_dashboard_payload(
        result.scenario_facts, narrative, generated_at=datetime.now(UTC)
    )
    return ScenarioResponse(
        session_id=session.id,
        scenario_facts=result.scenario_facts,
        comparison=result.comparison,
        dashboard=dashboard,
    )


@router.post("/chat")
def chat(
    req: ChatRequest,
    store: SessionStore = Depends(get_session_store),
    settings: Settings = Depends(get_settings),
    llm: SupportsGenerate | None = Depends(get_optional_llm_client),
) -> ChatResponse:
    session = _require_analyzed(_require_session(store, req.session_id))
    assert session.facts is not None  # narrowed by _require_analyzed
    reply = answer_question(
        session.facts,
        session.chat_history,
        req.message,
        client=llm,
        settings=settings,
        fail_soft=True,
    )
    session.chat_history.append(("user", req.message))
    session.chat_history.append(("assistant", reply))
    history = [ChatMessage(role=role, content=content) for role, content in session.chat_history]  # type: ignore[arg-type]
    return ChatResponse(session_id=session.id, reply=reply, history=history)


@router.get("/export/{fmt}")
def export(
    fmt: ExportFormat,
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> Response:
    session = _require_analyzed(_require_session(store, session_id))
    assert session.facts is not None
    narrative = _dash_narrative(session)
    generated_at = datetime.now(UTC)

    if fmt is ExportFormat.DASHBOARD:
        return JSONResponse(
            build_dashboard_payload(session.facts, narrative, generated_at=generated_at)
        )

    buffer = BytesIO()
    if fmt is ExportFormat.EXCEL:
        build_workbook(session.facts, narrative, generated_at=generated_at).save(buffer)
    elif fmt is ExportFormat.WORD:
        build_document(session.facts, narrative, generated_at=generated_at).save(buffer)
    else:  # PDF
        buffer.write(build_pdf_bytes(session.facts, narrative, generated_at=generated_at))
    buffer.seek(0)
    filename = f"advisory.{_EXPORT_EXT[fmt]}"
    return StreamingResponse(
        buffer,
        media_type=_EXPORT_MEDIA[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/session/{session_id}", status_code=204)
def delete_session(session_id: str, store: SessionStore = Depends(get_session_store)) -> Response:
    store.delete(session_id)
    return Response(status_code=204)
