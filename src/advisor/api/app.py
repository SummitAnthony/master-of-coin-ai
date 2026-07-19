"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import advisor
from advisor._resources import resource_path
from advisor.config import Settings, load_settings

from .errors import register_exception_handlers
from .routes import router
from .sessions import SessionStore

_WEB_DIR = resource_path("web")


def create_app(
    *, settings: Settings | None = None, session_store: SessionStore | None = None
) -> FastAPI:
    """Build the API app, wiring settings, session store, routes, and handlers."""
    app = FastAPI(title=advisor.PRODUCT_NAME, version=advisor.__version__)
    app.state.settings = settings or load_settings()
    app.state.session_store = session_store or SessionStore()
    register_exception_handlers(app)
    app.include_router(router)
    if _WEB_DIR.is_dir():  # mounted only when the dashboard assets exist (M7)
        app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
    return app
