"""End-to-end smoke test: the demo flow over HTTP + static dashboard serving.

The pywebview window itself is not launched (no display in CI); we exercise the
served app and the launcher's pure helpers.
"""

from __future__ import annotations

import io
import re

import openpyxl
import pytest
from fastapi.testclient import TestClient

from advisor.api.app import create_app
from advisor.api.deps import get_optional_llm_client

pytestmark = pytest.mark.e2e


class _FakeLLM:
    provider = "fake"
    model = "fake-1"

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        return "- watch margins\n- review finance cost"


def _xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Income Statement"
    for row in (
        ["Particulars", "FY2022-23", "FY2023-24"],
        ["Revenue", 2000000000, 2480000000],
        ["Cost of Goods Sold", 1200000000, 1910000000],
        ["Sales Volume (MT)", 16000, 18500],
    ):
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_optional_llm_client] = lambda: _FakeLLM()
    return TestClient(app)


def test_static_dashboard_is_served(client: TestClient) -> None:
    index = client.get("/")
    assert index.status_code == 200
    assert "Master of Coin AI" in index.text
    assert "minimal-lab-shell" in index.text
    assert "command-dock" in index.text
    assert "executive-brief" in index.text
    assert "theme-toggle" in index.text
    assert "command-palette" in index.text
    assert "dropzone" in index.text
    assert "board-pack" in index.text
    assert "Executive Committee" in index.text
    assert "committee-view" in index.text
    assert "committee-preview" in index.text
    assert "advisor-marketplace" in index.text
    assert "advisor-modal" in index.text
    assert "Run Committee Analysis" in index.text
    assert "Consensus Confidence" in index.text
    assert "Built-in Advisor" in index.text
    assert "data-remove-advisor" in index.text
    assert "advisor-remove-icon" in index.text
    assert "committee-active-count" in index.text
    assert "settings-view" in index.text
    assert "data-chart-range" in index.text
    assert "data-committee-preset" in index.text
    assert "data-advisor-mode" in index.text
    assert "data-configure-advisor" in index.text
    assert "AI Advisor" not in index.text
    assert "ambient-one" not in index.text
    assert "ambient-two" not in index.text
    assert client.get("/app.js").status_code == 200
    script = client.get("/app.js")
    assert "toggleTheme" in script.text
    assert "openCommandPalette" in script.text
    assert "animateNumber" in script.text
    assert "setProductView" in script.text
    assert "openAdvisorModal" in script.text
    assert "runCommitteeAnalysis" in script.text
    assert "installMarketplaceAdvisor" in script.text
    assert "addAdvisorToCommittee" in script.text
    assert "removeCommitteeAdvisor" in script.text
    assert "updateCommitteeSummary" in script.text
    assert "activateNavigation" in script.text
    assert "scrollToTarget" in script.text
    assert "exportReport" in script.text
    assert "setChartRange" in script.text
    assert "setCommitteePreset" in script.text
    assert "setAdvisorMode" in script.text
    assert "openConfigureAdvisor" in script.text
    assert "editCommittee" in script.text
    styles = client.get("/styles.css")
    assert styles.status_code == 200
    assert "backdrop-filter" in styles.text
    assert "#0B0D12" in styles.text
    assert "#6D5EF7" in styles.text
    assert "--type-display" in styles.text
    assert "--type-body" in styles.text
    assert "--density-page" in styles.text
    assert "--clarity-surface" in styles.text
    assert "font-feature-settings" in styles.text
    assert re.search(r"\.advisor-remove-icon\s*\{[^}]*opacity:\s*1;", styles.text, re.S)
    assert ".advisor-remove-icon::before" in styles.text
    assert "@media (max-width: 1320px)" in styles.text


def test_sidebar_navigation_targets_exist(client: TestClient) -> None:
    index = client.get("/").text
    nav_targets = re.findall(r'<a[^>]+href="#([^"]+)"[^>]+data-view=', index)
    assert nav_targets
    for target in nav_targets:
        assert f'id="{target}"' in index


def test_full_demo_flow(client: TestClient) -> None:
    up = client.post("/api/upload", files={"file": ("s.xlsx", _xlsx(), "application/vnd.ms-excel")})
    sid = up.json()["session_id"]

    analysis = client.post("/api/analyze", json={"session_id": sid, "include_narrative": True})
    assert analysis.status_code == 200
    assert analysis.json()["dashboard"]["scorecard"]

    scenario = client.post(
        "/api/scenario", json={"session_id": sid, "assumptions": {"cogs_pct": "8"}}
    )
    assert scenario.status_code == 200

    chat = client.post("/api/chat", json={"session_id": sid, "message": "How are margins?"})
    assert chat.status_code == 200 and chat.json()["reply"]

    pdf = client.get(f"/api/export/pdf?session_id={sid}")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")


def test_launcher_helpers_import() -> None:
    from advisor import app as launcher

    port = launcher._free_port("127.0.0.1")
    assert isinstance(port, int) and port > 0
