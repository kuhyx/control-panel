from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_detail as fd
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    path = fx.build(sysroot / "home/tester" / _db.STORE)
    calls = [
        fd.call(carry_usd=1.0, create_usd=0.5),
        fd.call(family="git log", target="git log", carry_usd=0.2),
        fd.call(
            name="mcp__chrome__shot",
            family="mcp:chrome",
            target="shot",
            images=1,
            result_tokens=2600,
            carry_usd=0.7,
        ),
        fd.call(name="Skill", family="skill", target="dataviz", carry_usd=0.3),
        fd.call(name="Read", family="Read:rules", target="/h/.claude/rules/a.md"),
        fd.call(name="Read", family="Read:file", target="/r/a.py", carry_usd=0.05),
        fd.call(name="Read", family="Read:file", target="/r/a.py", carry_usd=0.05),
        fd.call(name="WebFetch", family="WebFetch", target="docs.example.com"),
        fd.call(name="Grep", family="Grep", target="x"),
        fd.call(key="s1/agent-a", model="claude-sonnet-5-5", carry_usd=9.0),
        fd.call(ts=fx.T0 + fx.DAY, day="2026-09-29", cwd="/home/tester", carry_usd=4.0),
    ]
    marks = [
        fd.mark(kind="hook_context", tokens=50, carry_usd=0.4),
        fd.mark(
            kind="hook_run",
            name="SessionStart:startup",
            detail="start.sh",
            tokens=100,
            carry_usd=0.6,
        ),
        fd.mark(
            kind="attach", name="skill_listing", detail="", tokens=900, carry_usd=0.8
        ),
        fd.mark(kind="image", name="user", detail="", tokens=2600, carry_usd=0.1),
    ]
    fd.insert(path, calls=calls, marks=marks)
    return path


def _carry(query: str = "") -> dict[str, Any]:
    _, payload = _api.route(["panel", "carry"], query)
    return payload


def _labels(rows: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [(r["label"], r["detail"]) for r in rows]


def test_families_rank_by_creation_plus_carry(store: Path) -> None:
    payload = _carry("from=2026-09-28&to=2026-09-29")
    first = payload["families"][0]
    assert (first["label"], first["count"]) == ("git status", 3)
    assert first["total_usd"] == pytest.approx(1.5 + 9.01 + 4.01)
    assert first["carried_calls"] == 5.0
    assert "creation" in payload["caption"]


def test_buckets_by_tool_hook_attachment_and_path(store: Path) -> None:
    payload = _carry()
    assert _labels(payload["mcp"]) == [("mcp:chrome", "shot")]
    assert _labels(payload["skills"]) == [("skill", "dataviz")]
    assert _labels(payload["context_reads"]) == [
        ("Read:rules", "/h/.claude/rules/a.md")
    ]
    assert _labels(payload["web"]) == [("WebFetch", "docs.example.com")]
    assert payload["images"][0]["count"] == 1
    assert _labels(payload["rereads"]) == [("Read:file", "/r/a.py")]
    assert payload["rereads"][0]["count"] == 2
    hooks = _labels(payload["hooks"])
    assert hooks == [
        ("SessionStart:startup (run)", "start.sh"),
        ("PreToolUse:Bash (context)", "time_cap.sh"),
    ]
    assert _labels(payload["attachments"]) == [("skill_listing", "")]
    assert _labels(payload["pasted_images"]) == [("user", "")]


def test_daily_and_totals_split_results_from_other_context(store: Path) -> None:
    payload = _carry()
    first, second = payload["daily"]
    assert first["day"] == "2026-09-28"
    assert first["context_usd"] == pytest.approx(0.4 + 0.6 + 0.8 + 0.1)
    assert second["results_usd"] == pytest.approx(4.01)
    totals = payload["totals"]
    assert totals["spend_usd"] == pytest.approx(10.0)
    assert totals["carry_total_usd"] == pytest.approx(
        sum(d["results_usd"] + d["context_usd"] for d in payload["daily"])
    )


@pytest.mark.parametrize(
    ("query", "count"),
    [
        ("cwd=/home/tester/src", 10),
        ("model=claude-sonnet-5-5", 1),
        ("scope=main", 10),
        ("scope=sub", 1),
    ],
)
def test_every_filter_applies(store: Path, query: str, count: int) -> None:
    payload = _carry(query)
    assert sum(r["count"] for r in payload["families"]) == count


def test_tables_take_the_shared_params(store: Path) -> None:
    payload = _carry("t.families.limit=1&t.families.sort=label")
    assert [r["label"] for r in payload["families"]] == ["git log"]
    assert payload["_tables"]["families"]["total"] > 1


def test_an_empty_range_has_no_rows(store: Path) -> None:
    payload = _carry("from=2020-01-01&to=2020-01-02")
    assert payload["families"] == []
    assert payload["mcp"] == []
    assert payload["totals"] == {"carry_total_usd": 0, "spend_usd": 0}
