"""FastAPI application: upload, analyse, scenario, chat, and export endpoints."""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
