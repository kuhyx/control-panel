from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest

from control_panel.tests import _fixture_tokens as fx
from control_panel.tokens import _api, _db, _tables

if TYPE_CHECKING:
    from pathlib import Path

ROWS: list[dict[str, Any]] = [
    {"name": "Bash", "usd": 3.0, "kind": "tool", "tags": ["a"], "note": None},
    {"name": "Read", "usd": 1.0, "kind": "tool", "tags": [], "note": "big file"},
    {"name": "hook", "usd": None, "kind": "mark", "tags": [], "note": "x"},
    {"name": "Grep", "usd": 2.0, "kind": "tool", "tags": [], "note": "x"},
]


def _apply(query: str, **extra: object) -> dict[str, Any]:
    return _tables.apply({"rows": ROWS, "scalar": 1, **extra}, query)


def _names(out: dict[str, Any]) -> list[str]:
    return [r["name"] for r in out["rows"]]


@pytest.mark.parametrize(
    ("query", "names"),
    [
        ("", ["Bash", "Read", "hook", "Grep"]),
        ("t.rows.q=BIG", ["Read"]),
        ("t.rows.f.note=~X", ["hook", "Grep"]),
        ("t.rows.f.usd=1.5..", ["Bash", "Grep"]),
        ("t.rows.f.usd=..2", ["Read", "Grep"]),
        ("t.rows.f.usd=x..", ["Bash", "Read", "Grep"]),
        ("t.rows.f.kind==MARK|nope", ["hook"]),
        ("t.rows.sort=-usd", ["Bash", "Grep", "Read", "hook"]),
        ("t.rows.sort=usd", ["Read", "Grep", "Bash", "hook"]),
        ("t.rows.sort=kind,-name", ["hook", "Read", "Grep", "Bash"]),
        ("t.rows.sort=-usd&t.rows.limit=2", ["Bash", "Grep"]),
        (
            "t.rows.limit=0&t.rows.limit=x&t.rows.f.note=",
            ["Bash", "Read", "hook", "Grep"],
        ),
        ("t.other.q=zzz&cwd=/x&t.rows.bogus=1", ["Bash", "Read", "hook", "Grep"]),
    ],
)
def test_search_filter_sort_limit(query: str, names: list[str]) -> None:
    assert _names(_apply(query)) == names


def test_meta_counts_and_column_kinds() -> None:
    out = _apply("t.rows.q=r&t.rows.limit=1")
    meta = out["_tables"]["rows"]
    assert (meta["total"], meta["matched"], meta["shown"]) == (4, 3, 1)
    cols = meta["columns"]
    assert cols["usd"] == {"kind": "number"}
    assert cols["kind"] == {"kind": "enum", "values": ["mark", "tool"]}
    assert cols["name"] == {"kind": "text"}
    assert cols["tags"] == {"kind": "object"}
    assert out["scalar"] == 1


def test_nested_tables_and_dicts_have_dotted_ids() -> None:
    payload = {
        "prompts": [{"idx": 0, "tools": ROWS}, {"idx": 1, "tools": ROWS[:1]}],
        "arms": {"a": {"cases": [{"n": 1}, {"n": True}]}},
        "_tables": {"stale": 1},
    }
    out = _tables.apply(payload, "t.prompts.tools.sort=-usd&t.prompts.tools.limit=1")
    assert [p["tools"][0]["name"] for p in out["prompts"]] == ["Bash", "Bash"]
    meta = out["_tables"]
    assert meta["prompts.tools"]["total"] == 5
    assert meta["prompts.tools"]["shown"] == 2
    assert meta["arms.a.cases"]["columns"]["n"] == {"kind": "text"}
    assert "stale" not in meta


def test_defaults_apply_unless_overridden() -> None:
    defaults = {"rows": {"limit": "1", "sort": "-usd"}}
    assert _names(_tables.apply({"rows": ROWS}, "", defaults)) == ["Bash"]
    assert _names(_tables.apply({"rows": ROWS}, "t.rows.limit=0", defaults)) == [
        "Bash",
        "Grep",
        "Read",
        "hook",
    ]


@pytest.fixture
def store(sysroot: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_api, "_now", lambda: fx.T0 + 2 * fx.DAY)
    return fx.build(sysroot / "home/tester" / _db.STORE)


def test_every_endpoint_takes_table_params(store: Path) -> None:
    status, payload = _api.route(["panel", "sessions"], "t.sessions.f.final_tag==DONE")
    assert status == HTTPStatus.OK
    assert [s["key"] for s in payload["sessions"]] == ["s1"]
    assert payload["_tables"]["sessions"]["total"] == 2
    _, detail = _api.route(["session", "s1"], "t.prompts.limit=1")
    assert len(detail["prompts"]) == 1
    status, _ = _api.route(["session", "nope"], "t.prompts.limit=1")
    assert status == HTTPStatus.NOT_FOUND


def test_sessions_honour_scope(store: Path) -> None:
    _, sub = _api.route(["panel", "sessions"], "scope=sub")
    assert [(s["key"], s["usd_scope"]) for s in sub["sessions"]] == [("s1", 3.0)]
    _, main = _api.route(["panel", "sessions"], "scope=main")
    assert [s["key"] for s in main["sessions"]] == ["s2", "s1"]


def test_schema_describes_endpoints_params_and_panel_tables(store: Path) -> None:
    status, schema = _api.route(["schema"], "")
    assert status == HTTPStatus.OK
    assert "t.<table>.sort" in schema["table_params"]
    sessions = schema["panels"]["sessions"]
    assert sessions["default_table_params"] == {"sessions": {"limit": "200"}}
    assert sessions["tables"]["sessions"]["usd"] == "number"
    assert "_tables" not in schema


def test_long_repeated_values_filter_as_text_not_enum() -> None:
    rows = [{"lever": "x" * 50}, {"lever": "x" * 50}]
    meta = _tables.apply({"rows": rows}, "")["_tables"]["rows"]
    assert meta["columns"]["lever"] == {"kind": "text"}
