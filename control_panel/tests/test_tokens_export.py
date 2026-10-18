from __future__ import annotations

from typing import TYPE_CHECKING

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
    fd.insert(
        path,
        calls=[fd.call(), fd.call(key="s1/agent-a", ts=fx.T0 + 60)],
        marks=[fd.mark(kind="compaction", tokens=9)],
        turns=[fd.turn_detail(latency_s=7.5)],
    )
    return path


def test_raw_rows_newest_first_with_detail_joined(store: Path) -> None:
    _, payload = _api.route(["panel", "export"], "")
    assert [t["key"] for t in payload["turns"]] == ["s2", "s1", "s1/agent-a", "s1"]
    assert payload["turns"][-1]["latency_s"] == 7.5
    assert [c["key"] for c in payload["calls"]] == ["s1/agent-a", "s1"]
    assert payload["marks"][0]["kind"] == "compaction"
    assert "limit=0" in payload["caption"]


def test_filters_and_default_limit_apply(store: Path) -> None:
    _, payload = _api.route(["panel", "export"], "scope=sub&t.turns.limit=1")
    assert [c["key"] for c in payload["calls"]] == ["s1/agent-a"]
    assert len(payload["turns"]) == 1
    assert payload["_tables"]["turns"]["matched"] == 1
    _, everything = _api.route(["panel", "export"], "")
    assert everything["_tables"]["calls"]["shown"] == 2
