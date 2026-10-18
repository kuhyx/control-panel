"""The tools end to end against the fake API, plus the schema budget."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from control_panel_mcp import _client, _mcp, _smoke
from control_panel_mcp.tests.conftest import (
    AB,
    CARRY,
    CONTEXT,
    DETAIL,
    EFFICIENCY,
    LEVERS,
    OVERVIEW,
    SESSIONS,
)

if TYPE_CHECKING:
    import pytest

    from control_panel_mcp.tests.conftest import Fake

P = "/api/tokens/panel/"
TOOLS = {
    "overview",
    "sessions",
    "session_detail",
    "carry_costs",
    "context_files",
    "optimization_prompt",
    "levers",
    "efficiency",
    "ab_status",
    "hooks",
    "anomalies",
}
SCHEMA_BUDGET_CHARS = 5600  # ~1.4k tokens for all eleven tools


def test_tool_list_and_schema_budget() -> None:
    tools = asyncio.run(_mcp.mcp.list_tools())
    assert {t.name for t in tools} == TOOLS
    size = len(json.dumps([t.model_dump(exclude_none=True) for t in tools]))
    assert size < SCHEMA_BUDGET_CHARS
    assert all(t.output_schema is None for t in tools)


def test_overview_window_and_json(fake: Fake) -> None:
    fake.routes[P + "overview"] = (200, OVERVIEW)
    assert "$1,234 total" in _mcp.overview("2026-10-01..2026-10-07")
    assert fake.last()[1] == {"from": "2026-10-01", "to": "2026-10-07"}
    assert json.loads(_mcp.overview(as_json=True)) == OVERVIEW


def test_sessions_sends_table_grammar(fake: Fake) -> None:
    fake.routes[P + "sessions"] = (200, {**SESSIONS, "_tables": {}})
    out = _mcp.sessions("fix", "cwd=/x&final_tag==DONE", "-calls", 5)
    assert "| abc |" in out
    assert fake.last()[1] == {
        "cwd": "/x",
        "t.sessions.f.final_tag": "=DONE",
        "t.sessions.q": "fix",
        "t.sessions.sort": "-calls",
        "t.sessions.limit": "5",
    }


def test_sessions_local_fallback(fake: Fake) -> None:
    fake.routes[P + "sessions"] = (200, SESSIONS)
    out = _mcp.sessions(limit=1)
    assert "(1 rows)" in out


def test_session_detail(fake: Fake) -> None:
    fake.routes["/api/tokens/session/abc"] = (200, DETAIL)
    assert "**fix / it**" in _mcp.session_detail("abc")
    assert "HTTP 404: nope" in _mcp.session_detail("zzz")


def test_down_message(down: None) -> None:
    assert _mcp.overview().startswith(_client.DOWN)


def test_carry_costs(fake: Fake) -> None:
    assert _mcp.carry_costs() == "carry panel not built yet (TODO group D)"
    fake.routes[P + "carry"] = (200, CARRY)
    assert "| git | $4.00 |" in _mcp.carry_costs("families", "7d", 3)
    assert fake.last()[1]["t.families.limit"] == "3"


def test_context_and_prompt(fake: Fake) -> None:
    fake.routes[P + "context"] = (200, CONTEXT)
    assert "(1;" in _mcp.context_files(over_limit_only=True)
    assert _mcp.optimization_prompt().startswith("Shrink these 1 Claude")
    assert "| /r/a.md | 10 |" in _mcp.optimization_prompt(["a.md"])


def test_levers_efficiency_ab(fake: Fake) -> None:
    fake.routes[P + "levers"] = (200, LEVERS)
    fake.routes[P + "efficiency"] = (200, EFFICIENCY)
    fake.routes[P + "ab"] = (200, AB)
    assert "(1 rows)" in _mcp.levers("proposed")
    assert "per DONE" in _mcp.efficiency("7d")
    assert "collecting" in _mcp.ab_status()


def test_hooks_prefers_own_panel(fake: Fake) -> None:
    fake.routes[P + "hooks"] = (200, {"fires": [{"hook": "h", "count": 3}]})
    assert "**fires**" in _mcp.hooks()


def test_hooks_falls_back_to_carry(fake: Fake) -> None:
    assert _mcp.hooks() == "hooks panel not built yet (TODO groups D/F)"
    fake.routes[P + "carry"] = (200, CARRY)
    assert "| spec_gate | $1.00 |" in _mcp.hooks()


def test_hooks_reports_other_errors(fake: Fake) -> None:
    fake.routes[P + "hooks"] = (503, {"error": "no token store"})
    assert _mcp.hooks() == "HTTP 503: no token store"


def test_anomalies(fake: Fake) -> None:
    assert _mcp.anomalies() == "anomalies panel not built yet (TODO group N)"
    fake.routes[P + "anomalies"] = (200, {"spikes": [{"day": "d", "usd": 9.0}]})
    assert "| d | $9.00 |" in _mcp.anomalies("7d")


def test_main_runs_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(_mcp.mcp, "run", lambda: calls.append(True))
    _mcp.main()
    assert calls == [True]


def test_smoke_over_real_stdio(fake: Fake, capsys: pytest.CaptureFixture[str]) -> None:
    """The server as Claude Code runs it: a subprocess speaking JSON-RPC."""
    fake.routes[P + "overview"] = (200, OVERVIEW)
    _smoke.asyncio.run(_smoke.run([("overview", {"window": "7d"})]))
    out = capsys.readouterr().out
    assert "ALL" in out
    assert "$1,234 total" in out


def test_smoke_main(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []
    monkeypatch.setattr(_smoke, "run", lambda calls: calls)
    monkeypatch.setattr(_smoke.asyncio, "run", seen.append)
    _smoke.main()
    assert seen == [_smoke.CALLS]
