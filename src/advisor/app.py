"""Desktop launcher: serve the FastAPI app and open it in a pywebview window.

Run with ``master-of-coin`` (console script) or ``python -m advisor.app``.
This module is excluded from coverage; it is the GUI shell, exercised manually
and by the packaged-binary smoke test (M8).
"""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from pathlib import Path

import uvicorn

from advisor import PRODUCT_NAME
from advisor.api.app import create_app


def _free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _serve(app: object, host: str, port: int) -> None:
    uvicorn.run(app, host=host, port=port, log_level="warning")  # type: ignore[arg-type]


def _selfcheck_sentinel() -> Path:
    import tempfile

    return Path(tempfile.gettempdir()) / "master_of_coin_selfcheck.txt"


def _report_selfcheck(message: str) -> None:
    """Emit the selfcheck result to stdout (console builds) and a sentinel file.

    Windowed (console=False) builds have no stdout, so the sentinel file is the
    reliable channel the packaged-binary smoke test reads.
    """
    print(message)
    with contextlib.suppress(OSError):
        _selfcheck_sentinel().write_text(message, encoding="utf-8")


def selfcheck() -> int:
    """Headless verification used by the packaged-binary smoke test (no GUI)."""
    from fastapi.testclient import TestClient

    from advisor._resources import resource_path

    app = create_app()
    with TestClient(app) as test_client:
        if test_client.get("/api/health").status_code != 200:
            _report_selfcheck("SELFCHECK FAILED: /api/health")
            return 1
        if test_client.get("/").status_code != 200:
            _report_selfcheck("SELFCHECK FAILED: dashboard not served")
            return 1
    if not resource_path("config/thresholds.yaml").exists():
        _report_selfcheck("SELFCHECK FAILED: thresholds asset missing")
        return 1
    _report_selfcheck("SELFCHECK OK")
    return 0


def main(*, host: str = "127.0.0.1", port: int | None = None) -> None:
    """Start the API server in a background thread and open the desktop window."""
    import webview  # imported lazily so non-GUI environments can import this module

    app = create_app()
    resolved_port = port or _free_port(host)
    thread = threading.Thread(target=_serve, args=(app, host, resolved_port), daemon=True)
    thread.start()
    time.sleep(0.8)  # give uvicorn a moment to bind before the window loads
    webview.create_window(
        PRODUCT_NAME,
        f"http://{host}:{resolved_port}/",
        width=1280,
        height=860,
    )
    webview.start()


if __name__ == "__main__":
    import sys

    if "--selfcheck" in sys.argv:
        raise SystemExit(selfcheck())
    main()
