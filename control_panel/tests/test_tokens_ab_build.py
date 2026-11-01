"""The build-class A/B is reported apart from the closed judgment one."""

from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path

BUILD_LOG = "home/tester/.claude/logs/agent-ab-build.jsonl"
BUILD = {
    "arms": {"sonnet": {"n": 4}, "opus": {"n": 3}},
    "diffs": {},
    "unjoined": 1,
    "banner": {"level": "grey", "text": "A/B build agents: collecting (n=3)"},
}


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    return fx.build(sysroot / "home/tester" / _db.STORE)


def _panel(name: str) -> dict[str, Any]:
    _, payload = _api.route(["panel", name], "")
    return payload


def test_ab_panel_carries_the_build_experiment(store: Path) -> None:
    with closing(sqlite3.connect(store)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta VALUES ('ab_build', ?)", (json.dumps(BUILD),)
        )
        conn.commit()
    build = _panel("ab")["build"]
    assert build["arms"]["sonnet"]["n"] == 4
    assert build["banner"]["text"].startswith("A/B build agents")
    assert build["metrics"]


def test_ab_panel_build_collecting_when_absent(store: Path) -> None:
    build = _panel("ab")["build"]
    assert build["arms"] == {}
    assert build["banner"]["text"] == "A/B build agents: collecting (n=0)"


def test_routing_counts_build_log_separately(store: Path, sysroot: Path) -> None:
    log = sysroot / BUILD_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": "2026-09-28T12:00:00Z",
        "arm": "sonnet",
        "class": "build",
        "subagent_type": "general-purpose",
    }
    log.write_text(json.dumps(row) + "\n", encoding="utf-8")
    routing = _panel("subagents")["routing"]
    assert routing["ab"] == []
    assert "agent-ab.jsonl" in routing["gap"]
    assert routing["ab_build"] == [
        {
            "arm": "sonnet",
            "class": "build",
            "subagent_type": "general-purpose",
            "count": 1,
        }
    ]
    assert routing["gap_build"] == ""


def test_routing_names_missing_build_log(store: Path) -> None:
    routing = _panel("subagents")["routing"]
    assert routing["ab_build"] == []
    assert "agent-ab-build.jsonl" in routing["gap_build"]
