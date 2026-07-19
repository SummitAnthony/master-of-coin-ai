"""Uniform, secret-safe error envelope and exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from advisor.ingestion.errors import IngestionError
from advisor.narrative.errors import LLMError, MissingAPIKeyError


class ApiError(HTTPException):
    """An HTTP error carrying a stable machine code plus a safe message."""

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


def _envelope(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return _envelope(exc.status_code, exc.code, str(exc.detail))

    @app.exception_handler(IngestionError)
    async def _handle_ingestion(_request: Request, exc: IngestionError) -> JSONResponse:
        return _envelope(422, "ingestion_failed", str(exc))

    @app.exception_handler(MissingAPIKeyError)
    async def _handle_missing_key(_request: Request, exc: MissingAPIKeyError) -> JSONResponse:
        return _envelope(503, "llm_unavailable", str(exc))

    @app.exception_handler(LLMError)
    async def _handle_llm(_request: Request, exc: LLMError) -> JSONResponse:
        return _envelope(502, "llm_failed", str(exc))
