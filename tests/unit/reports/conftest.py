"""Fixtures for report unit tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from advisor.narrative.advisor import Advisory
from advisor.schema import Facts
from tests._reportdata import GEN_AT, make_advisory, make_facts


@pytest.fixture
def facts() -> Facts:
    return make_facts()


@pytest.fixture
def advisory() -> Advisory:
    return make_advisory()


@pytest.fixture
def gen_at() -> datetime:
    return GEN_AT
