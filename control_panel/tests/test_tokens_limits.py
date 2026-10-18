from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _context, _db, _limits

if TYPE_CHECKING:
    from pathlib import Path

CONFIG = _limits.load()


BASE = _limits.Size(
    name="x.md",
    kind="rules (loaded recursively)",
    standing="always",
    lines=10,
    bytes=400,
    standing_bytes=400,
    tokens=100,
)


def _size(**kw: str | int) -> _limits.Size:
    return replace(BASE, **kw)


def test_memory_index_over_its_read_limit_is_a_hard_breach() -> None:
    found = _limits.status(
        CONFIG,
        _size(name="MEMORY.md", kind="auto-memory index", lines=210, bytes=30000),
    )
    assert found["status"] == _limits.OVER_HARD
    hard = [b for b in found["breaches"] if b["hard"]]
    assert {b["measure"] for b in hard} == {"lines", "bytes"}
    assert "25,000 bytes" in found["hard_limits"]
    assert "12,500 bytes" in found["budgets"]


def test_soft_budgets_only_make_it_over_budget() -> None:
    found = _limits.status(CONFIG, _size(lines=300, tokens=2500))
    assert found["status"] == _limits.OVER_BUDGET
    assert {b["measure"] for b in found["breaches"]} == {"lines", "tokens"}
    assert not any(b["hard"] for b in found["breaches"])


def test_selectors_and_ok() -> None:
    skill = _size(kind="skill", standing="description", standing_bytes=2000)
    assert _limits.status(CONFIG, skill)["status"] == _limits.OVER_HARD
    # The 2,000-token budget is for always-loaded files only.
    repo = _size(kind="repo CLAUDE.md", standing="in repo", tokens=5000)
    assert _limits.status(CONFIG, repo)["status"] == _limits.OK


def test_line_count_matches_wc_plus_a_trailing_line() -> None:
    assert _context.checked_lines("a\nb\n") == 2
    assert _context.checked_lines("a\nb") == 2
    assert _context.checked_lines("") == 0


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    return fx.build(sysroot / "home/tester" / _db.STORE)


def test_context_panel_reports_status_and_hard_warning(store: Path) -> None:
    memory = store.parents[2] / ".claude/memory/MEMORY.md"
    memory.write_text("line\n" * 300, encoding="utf-8")
    _, payload = _api.route(["panel", "context"], "")
    row = next(r for r in payload["files"] if r["path"] == str(memory))
    assert row["lines"] == 300
    assert row["status"] == _limits.OVER_HARD
    assert row["warning"].startswith("over 200 lines")
    claude = store.parents[2] / ".claude/CLAUDE.md"
    claude.write_text("rule\n" * 300, encoding="utf-8")
    _, payload = _api.route(["panel", "context"], "")
    row = next(r for r in payload["files"] if r["path"] == str(claude))
    assert (row["status"], row["warning"]) == (_limits.OVER_BUDGET, None)
