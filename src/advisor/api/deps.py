"""FastAPI dependency providers."""

from __future__ import annotations

from fastapi import Depends, Request

from advisor.config import Settings
from advisor.narrative.client import SupportsGenerate
from advisor.narrative.errors import MissingAPIKeyError
from advisor.narrative.factory import get_llm_client as build_llm_client

from .sessions import SessionStore


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_session_store(request: Request) -> SessionStore:
    store: SessionStore = request.app.state.session_store
    return store


def get_optional_llm_client(
    settings: Settings = Depends(get_settings),
) -> SupportsGenerate | None:
    """Return a configured client, or None when no credential is set (offline)."""
    try:
        return build_llm_client(settings)
    except MissingAPIKeyError:
        return None
