from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_subagents as fs
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path

SONNET = "claude-sonnet-5-5"
AB_LOG = "home/tester/.claude/logs/agent-ab.jsonl"


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    fs.insert(
        path,
        turns=[
            fs.turn(
                "s1/agent-a", fx.T0 + 61, 0.5, model=SONNET, tokens=(100, 50, 800, 50)
            ),
            fs.turn("s1/agent-b", fx.T0 + 71, 1.0, tokens=(100, 100, 200, 100)),
            fs.turn("s1/agent-b", fx.T0 + 72, 1.0, tokens=(100, 100, 200, 100)),
            fs.turn(
                "s2/agent-c", fx.T0 + fx.DAY, 2.0, cwd="/home/tester", day="2026-09-29"
            ),
        ],
        links=[
            fs.link("s1/agent-b", description="Build y", wall_s=100.0, active_s=80.0),
        ],
        agent_calls=[
            fs.agent_call("s1", "a", fx.T0 + 59, agent_type="Explore"),
            fs.agent_call("s1", "b", fx.T0 + 70),
        ],
    )
    fd.insert(
        path,
        calls=[
            fd.call(
                ts=fx.T0 + 59,
                name="Agent",
                family="Agent",
                target="Explore",
                result_tokens=200,
            ),
            fd.call(
                ts=fx.T0 + 70,
                name="Agent",
                family="Agent",
                target="general-purpose [worktree]",
                result_tokens=100,
            ),
        ],
        marks=[
            fd.mark(
                kind="hook_run",
                name="PreToolUse:Agent",
                detail="agent_model_pretool.sh",
                count=2,
            ),
            fd.mark(
                kind="hook_context",
                name="PreToolUse:Agent",
                detail="agent_model_pretool.sh",
                count=1,
                tokens=30,
            ),
        ],
    )
    return path


def _subagents(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "subagents"], query)
    return payload


def _by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {r[key]: r for r in rows}


def test_totals_and_leverage(store: Path) -> None:
    totals = _subagents()["totals"]
    assert totals["agents"] == 3
    assert totals["usd"] == pytest.approx(3.5 + 2.0 + 2.0)
    assert totals["calls"] == 5
    assert totals["returned_tokens"] == 300
    assert totals["spent_tokens"] == 2000
    assert totals["leverage"] == pytest.approx(0.15)
    assert totals["worktree_agents"] == 1


def test_grouped_by_type_model_and_description(store: Path) -> None:
    payload = _subagents()
    by_type = _by(payload["by_type"], "label")
    explore = by_type["Explore"]
    assert (explore["agents"], explore["calls"], explore["wall_s"]) == (1, 2, 60)
    assert explore["leverage"] == pytest.approx(0.2)
    assert by_type["(unlinked)"]["leverage"] is None
    assert payload["by_type"][0]["label"] == "Explore"
    by_model = _by(payload["by_model"], "label")
    assert by_model["claude-opus-5-5"]["agents"] == 2
    desc = _by(payload["by_description"], "label")["Build y"]
    assert (desc["active_s"], desc["returned_tokens"]) == (80, 100)
    assert "returned" in payload["caption"]


def test_worktree_agents_link_to_their_cost(store: Path) -> None:
    (row,) = _subagents()["worktree"]
    assert (row["key"], row["sub_key"], row["usd"]) == ("s1", "s1/agent-b", 2.0)
    assert row["target"] == "general-purpose [worktree]"


def test_routing_marks_and_missing_ab_log(store: Path) -> None:
    routing = _subagents()["routing"]
    assert (routing["hook_runs"], routing["rewrites"]) == (2, 1)
    assert routing["ab"] == []
    assert "agent-ab.jsonl" in routing["gap"]


def test_routing_reads_the_ab_log_in_range(store: Path, sysroot: Path) -> None:
    log = sysroot / AB_LOG
    log.parent.mkdir(parents=True)
    inside = "2026-09-28T12:00:00Z"
    lines = [
        {
            "ts": inside,
            "arm": "sonnet",
            "class": "judgment",
            "subagent_type": "general-purpose",
        },
        {
            "ts": inside,
            "arm": "sonnet",
            "class": "judgment",
            "subagent_type": "general-purpose",
        },
        {
            "ts": inside,
            "arm": "opus",
            "class": "judgment",
            "subagent_type": "general-purpose",
        },
        {
            "ts": "2020-01-01T00:00:00Z",
            "arm": "opus",
            "class": "x",
            "subagent_type": "general-purpose",
        },
    ]
    text = "\n".join(json.dumps(line) for line in lines)
    log.write_text(text + '\nnot json\n{"ts": 5}\n{"ts": "later"}\n', encoding="utf-8")
    routing = _subagents()["routing"]
    assert routing["gap"] == ""
    assert [(r["arm"], r["count"]) for r in routing["ab"]] == [
        ("sonnet", 2),
        ("opus", 1),
    ]


@pytest.mark.parametrize(
    ("query", "keys", "returned"),
    [
        ("cwd=/home/tester/src", 2, 300),
        (f"model={SONNET}", 1, 200),
        ("scope=main", 0, 0),
        ("scope=sub", 3, 300),
        ("from=2026-09-29&to=2026-09-29", 1, 0),
    ],
)
def test_every_filter_applies(
    store: Path, query: str, keys: int, returned: int
) -> None:
    totals = _subagents(query)["totals"]
    assert totals["agents"] == keys
    assert totals["returned_tokens"] == returned


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _subagents("from=2020-01-01&to=2020-01-02")
    assert payload["by_type"] == []
    assert payload["worktree"] == []
    assert payload["totals"]["leverage"] is None
