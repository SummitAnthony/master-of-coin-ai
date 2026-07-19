"""Fixtures for API integration tests: a TestClient with an injected fake LLM."""

from __future__ import annotations

import io
from collections.abc import Iterator

import openpyxl
import pytest
from fastapi.testclient import TestClient

from advisor.api.app import create_app
from advisor.api.deps import get_optional_llm_client
from advisor.api.sessions import SessionStore


class FakeLLM:
    """Deterministic offline LLM stand-in injected via dependency override."""

    provider = "fake"
    model = "fake-1"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        self.calls.append(prompt)
        return "- point one\n- point two"


def _sample_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Income Statement"
    for row in (
        ["Particulars", "FY2022-23", "FY2023-24"],
        ["Revenue", 2000000000, 2480000000],
        ["Cost of Goods Sold", 1200000000, 1910000000],
        ["Administrative Expenses", 100000000, 138000000],
        ["Sales Volume (MT)", 16000, 18500],
    ):
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(fake_llm: FakeLLM) -> Iterator[TestClient]:
    app = create_app(session_store=SessionStore())
    app.dependency_overrides[get_optional_llm_client] = lambda: fake_llm
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_xlsx() -> bytes:
    return _sample_xlsx()
