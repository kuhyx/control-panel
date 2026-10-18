from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

from control_panel import _routes
from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _context, _db

if TYPE_CHECKING:
    from pathlib import Path

NOW = fx.T0 + 2 * fx.DAY


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: NOW)
    return fx.build(sysroot / "home/tester" / _db.STORE)


def _get(path: str) -> tuple[HTTPStatus, dict[str, Any]]:
    router = _routes.Router.__new__(_routes.Router)
    resolved = router.resolve(path)
    assert resolved is not None
    return resolved


def test_missing_store_is_service_unavailable() -> None:
    status, payload = _get("/api/tokens")
    assert status == HTTPStatus.SERVICE_UNAVAILABLE
    assert "ingest" in payload["error"]


def test_index_lists_panels_options_and_coverage(store: Path) -> None:
    status, payload = _get("/api/tokens")
    assert status == HTTPStatus.OK
    assert [p["name"] for p in payload["panels"]] == [
        "overview",
        "sessions",
        "efficiency",
        "ab",
        "levers",
        "context",
    ]
    assert payload["options"]["models"] == ["claude-opus-5-5", "claude-sonnet-5-5"]
    coverage = payload["coverage"]
    assert coverage["any_from"] == "2026-03-11"
    assert coverage["aggregate_from"] == "2026-07-01"
    assert coverage["snapshots"] == ["2026-09-20", "2026-09-30"]
    assert payload["snapshot_metrics"]["2026-09-30"]["usd_per_day"] == 10.0


def test_overview_window_uses_the_record_span(store: Path) -> None:
    status, payload = _get("/api/tokens/panel/overview?window=2026-09-30")
    assert status == HTTPStatus.OK
    tiles = payload["tiles"]
    assert tiles["usd"] == pytest.approx(10.0)
    assert tiles["calls"] == 4
    # Records span exactly one day, so USD/day equals the total.
    assert tiles["usd_per_day"] == pytest.approx(10.0)
    days = {d["day"]: d for d in payload["daily"]}
    assert days["2026-09-28"]["sub_share"] == pytest.approx(0.5)
    assert days["2026-09-28"]["over_share"] == pytest.approx(1 / 6)


@pytest.mark.parametrize(
    ("query", "usd"),
    [
        ("cwd=/home/tester/src/a", 6.0),
        ("model=claude-sonnet-5-5", 3.0),
        ("scope=main", 7.0),
        ("scope=sub", 3.0),
        ("from=2026-09-29&to=2026-09-29", 4.0),
    ],
)
def test_overview_filters(store: Path, query: str, usd: float) -> None:
    _, payload = _get(f"/api/tokens/panel/overview?{query}")
    assert payload["tiles"]["usd"] == pytest.approx(usd)


def test_overview_marks_aggregate_only_history(store: Path) -> None:
    _, payload = _get("/api/tokens/panel/overview?from=2026-06-01")
    (row,) = payload["aggregate"]
    assert row == {"day": "2026-07-01", "sessions": 1, "usd_est": 2.5}
    assert payload["prompts"] == []


def test_sessions_sorted_by_cost_and_filtered(store: Path) -> None:
    _, payload = _get("/api/tokens/panel/sessions")
    assert [s["key"] for s in payload["sessions"]] == ["s1", "s2"]
    assert payload["sessions"][0]["active_s"] == 900
    _, payload = _get("/api/tokens/panel/sessions?cwd=/home/tester/src/a")
    assert [s["key"] for s in payload["sessions"]] == ["s1"]


def test_session_detail_has_prompts_subagents_tools(store: Path) -> None:
    status, payload = _get("/api/tokens/session/s1")
    assert status == HTTPStatus.OK
    first = payload["prompts"][0]
    assert first["text"] == "fix a"
    assert first["usd"] == pytest.approx(5.0)
    assert first["subagents"][0]["description"] == "Find x"
    assert [t["name"] for t in first["tools"]] == ["Bash", "Agent"]
    assert payload["unattributed"] == []
    assert _get("/api/tokens/session/nope")[0] == HTTPStatus.NOT_FOUND


def test_levers_rows_and_metric_series(store: Path) -> None:
    _, payload = _get("/api/tokens/panel/levers")
    assert [r["status"] for r in payload["rows"]] == ["applied", "proposed"]
    series = payload["series"]["subagent_usd_share"]
    assert [p["date"] for p in series["snapshots"]] == ["2026-09-20", "2026-09-30"]
    assert series["daily"][0]["value"] == pytest.approx(0.5)


def test_efficiency_and_unknown_panel(store: Path) -> None:
    status, payload = _get("/api/tokens/panel/efficiency")
    assert status == HTTPStatus.OK
    assert set(payload["captions"]) == {"done", "commits", "estimate"}
    assert _get("/api/tokens/panel/nope")[0] == HTTPStatus.NOT_FOUND
    assert _get("/api/tokens/bogus")[0] == HTTPStatus.NOT_FOUND


def test_ab_banner_everywhere_and_for_the_tray(store: Path) -> None:
    _, index = _get("/api/tokens")
    assert index["ab_banner"]["level"] == "grey"
    status, payload = _get("/api/tokens/ab")
    assert status == HTTPStatus.OK
    assert payload["banner"]["text"].endswith("(n=2)")
    _, panel = _get("/api/tokens/panel/ab")
    assert panel["arms"]["sonnet"]["n"] == 3


def test_context_files_live_size_cost_and_limit(store: Path) -> None:
    _, payload = _get("/api/tokens/panel/context")
    rows = {
        r["path"].rsplit("/", 2)[-2] + "/" + r["path"].rsplit("/", 1)[-1]: r
        for r in payload["files"]
    }
    claude = rows[".claude/CLAUDE.md"]
    assert claude["bytes"] == 4000
    assert claude["tokens"] == 1000
    # 1,000 tokens x 4 calls/day (4 calls over the 7-day window... 4/7) x $0.2/M
    assert claude["usd_per_day"] == pytest.approx(1000 * (4 / 7) * 0.2 / 1e6)
    assert claude["history"] == [{"ts": fx.T0 - fx.DAY, "bytes": 4000, "source": "git"}]
    assert rows["memory/MEMORY.md"]["status"] == "ok"
    assert rows["memory/MEMORY.md"]["warning"] is None
    assert payload["measure_command"].startswith("wc -lc")
    assert rows["a/CLAUDE.md"]["usd_per_day"] == pytest.approx(
        100 * (3 / 7) * 0.2 / 1e6
    )
    assert rows["tester/gone.md"]["bytes"] is None


def test_context_file_content_only_for_listed_paths(store: Path, sysroot: Path) -> None:
    listed = str(sysroot / "home/tester/.claude/CLAUDE.md")
    status, payload = _get(f"/api/tokens/context-file?path={listed}")
    assert status == HTTPStatus.OK
    assert payload["content"] == "x" * 4000
    assert "git_log" in payload
    status, _ = _get("/api/tokens/context-file?path=/etc/passwd")
    assert status == HTTPStatus.NOT_FOUND


def test_now_is_wall_clock() -> None:
    assert _api._now() > fx.T0


def test_skill_and_agent_files_count_only_their_description() -> None:
    text = "---\nname: x\ndescription: abcd\n---\nlong body " * 3
    assert _context._standing_bytes(text, "description") == len(" abcd")
    assert _context._standing_bytes("no front matter", "description") == 0
    assert _context._standing_bytes("abc", "always") == 3


def test_context_file_without_git_has_an_empty_log(
    store: Path, sysroot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_context, "GIT", str(sysroot / "no-such-git"))
    listed = str(sysroot / "home/tester/.claude/CLAUDE.md")
    _, payload = _get(f"/api/tokens/context-file?path={listed}")
    assert payload["git_log"] == []
