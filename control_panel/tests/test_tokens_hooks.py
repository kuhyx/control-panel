from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path

DAY2 = {"ts": fx.T0 + fx.DAY, "day": "2026-09-29", "cwd": "/home/tester"}


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    marks = [
        fd.mark(count=3, duration_ms=60),
        fd.mark(kind="hook_context", tokens=200, create_usd=0.1, carry_usd=0.5),
        fd.mark(kind="hook_error", count=2, duration_ms=0),
        fd.mark(kind="hook_msg", count=4, duration_ms=0),
        fd.mark(
            name="SessionStart:startup",
            detail="start.sh",
            tokens=100,
            duration_ms=500,
            create_usd=0.05,
            carry_usd=0.25,
        ),
        fd.mark(
            kind="hook_block",
            name="Stop",
            detail="status_tag_stop.py",
            count=2,
            retry_usd=1.5,
        ),
        fd.mark(
            kind="hook_block",
            name="SubagentStop",
            detail="evidence_stop.py",
            retry_usd=0.25,
        ),
        fd.mark(kind="hook_block", name="PreToolUse:Bash", detail="git_guard.sh"),
        fd.mark(kind="hook_error", name="UserPromptSubmit", detail="", duration_ms=0),
        fd.mark(key="s1/agent-a", model="claude-sonnet-5-5", count=5),
        fd.mark(**DAY2, kind="hook_context", tokens=50, carry_usd=2.0),
    ]
    fd.insert(path, marks=marks)
    return path


def _hooks(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "hooks"], query)
    return payload


def _row(payload: dict[str, Any], hook: str, script: str) -> dict[str, Any]:
    return next(
        r for r in payload["hooks"] if (r["hook"], r["script"]) == (hook, script)
    )


def test_per_hook_fires_runtime_tokens_cost_blocks_errors(store: Path) -> None:
    payload = _hooks("from=2026-09-28&to=2026-09-28")
    bash = _row(payload, "PreToolUse:Bash", "time_cap.sh")
    assert bash["fires"] == 3 + 5
    assert bash["runtime_s"] == pytest.approx(0.07)
    assert bash["mean_ms"] == pytest.approx(70 / 8)
    assert bash["tokens"] == 200
    assert bash["create_usd"] == pytest.approx(0.1)
    assert bash["carry_usd"] == pytest.approx(0.5)
    assert (bash["errors"], bash["messages"], bash["blocks"]) == (2, 4, 0)
    stop = _row(payload, "Stop", "status_tag_stop.py")
    assert (stop["fires"], stop["mean_ms"], stop["blocks"]) == (0, None, 2)
    assert stop["retry_usd"] == pytest.approx(1.5)
    assert stop["total_usd"] == pytest.approx(1.5)
    assert payload["hooks"][0]["hook"] == "Stop"
    assert _row(payload, "UserPromptSubmit", "")["errors"] == 1
    assert "duration" in payload["caption"]


def test_stop_bounces_per_script(store: Path) -> None:
    rows = _hooks()["stop_bounces"]
    assert [(r["hook"], r["script"], r["count"]) for r in rows] == [
        ("Stop", "status_tag_stop.py", 2),
        ("SubagentStop", "evidence_stop.py", 1),
    ]
    assert rows[0]["retry_usd"] == pytest.approx(1.5)


def test_daily_cost_and_totals(store: Path) -> None:
    payload = _hooks()
    first, second = payload["daily"]
    assert first["day"] == "2026-09-28"
    assert first["injected_usd"] == pytest.approx(0.6 + 0.3)
    assert first["retry_usd"] == pytest.approx(1.75)
    assert second["injected_usd"] == pytest.approx(2.0)
    totals = payload["totals"]
    assert totals["fires"] == 3 + 1 + 5
    assert totals["blocks"] == 4
    assert totals["errors"] == 3
    assert totals["tokens"] == 350
    assert totals["injected_usd"] == pytest.approx(2.9)
    assert totals["retry_usd"] == pytest.approx(1.75)
    assert totals["spend_usd"] == pytest.approx(10.0)


@pytest.mark.parametrize(
    ("query", "fires", "tokens"),
    [
        ("cwd=/home/tester/src", 9, 300),
        ("cwd=/home/tester", 9, 350),
        ("model=claude-sonnet-5-5", 5, 0),
        ("scope=main", 4, 350),
        ("scope=sub", 5, 0),
        ("from=2026-09-29&to=2026-09-29", 0, 50),
    ],
)
def test_every_filter_applies(store: Path, query: str, fires: int, tokens: int) -> None:
    totals = _hooks(query)["totals"]
    assert (totals["fires"], totals["tokens"]) == (fires, tokens)


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _hooks("from=2020-01-01&to=2020-01-02")
    assert payload["hooks"] == []
    assert payload["stop_bounces"] == []
    assert payload["daily"] == []
    assert payload["totals"]["fires"] == 0


BUDGET = """    time  budget  event / command
------------------------------------------------------------------------------
   1.20s    1.0s  OVER  UserPromptSubmit  bash /home/kuhy/.claude/hooks/task_size_u...
   0.06s    1.5s  ok    Stop              python3 /home/kuhy/.claude/hooks/evidence...
   0.01s    2.0s  ok    PostToolUseFailure bash /home/kuhy/.claude/hooks/time_cap_po...
garbage line
------------------------------------------------------------------------------
   1.27s  total across 3 hook(s)

All hooks within budget.
"""


def test_budget_gate_table_is_read_live_from_disk(store: Path, sysroot: Path) -> None:
    path = sysroot / "home/tester/.claude/state/hook_budget_result.txt"
    path.parent.mkdir(parents=True)
    path.write_text(BUDGET, encoding="utf-8")
    payload = _hooks()
    rows = payload["budget"]
    assert [(r["event"], r["status"]) for r in rows] == [
        ("UserPromptSubmit", "OVER"),
        ("Stop", "ok"),
        ("PostToolUseFailure", "ok"),
    ]
    assert rows[0]["time_s"] == pytest.approx(1.2)
    assert rows[0]["budget_s"] == pytest.approx(1.0)
    assert rows[0]["over_s"] == pytest.approx(0.2)
    assert rows[1]["over_s"] == 0
    assert rows[2]["command"].startswith("bash /home/kuhy/.claude/hooks/time_cap")
    info = payload["budget_file"]
    assert info["found"] is True
    assert info["path"].endswith(".claude/state/hook_budget_result.txt")
    assert info["mtime"] > 0
    assert info["over"] == 1


def test_budget_gate_missing_file(store: Path) -> None:
    payload = _hooks()
    assert payload["budget"] == []
    assert payload["budget_file"]["found"] is False
    assert payload["budget_file"]["mtime"] is None
