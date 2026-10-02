from __future__ import annotations

from typing import Any

import pytest

from control_panel import _tray_model


def _sub(
    sid: str, state: str, *, important: bool = True, **extra: object
) -> dict[str, Any]:
    return {
        "id": sid,
        "title": sid.upper(),
        "state": state,
        "important": important,
        **extra,
    }


@pytest.mark.parametrize(
    ("state", "level"),
    [
        ("ARMED", "ok"),
        ("RETIRED", "ok"),
        ("BAD", "red"),
        ("NOT_INSTALLED", "red"),
        ("UNARMED", "red"),
        ("DEGRADED", "amber"),
        ("UNKNOWN", "amber"),
    ],
)
def test_level_of(state: str, level: str) -> None:
    assert _tray_model.level_of(_sub("a", state)) == level


def test_red_needs_an_important_subsystem() -> None:
    assert _tray_model.overall([_sub("a", "BAD", important=False)]) == "amber"
    assert _tray_model.overall([_sub("a", "BAD"), _sub("b", "ARMED")]) == "red"
    assert _tray_model.overall([_sub("a", "DEGRADED")]) == "amber"
    assert _tray_model.overall([_sub("a", "ARMED")]) == "ok"
    assert _tray_model.overall([{"id": "x", "title": "X", "state": "BAD"}]) == "red"


def test_build_projects_items_and_tooltip() -> None:
    status = {
        "subsystems": [
            _sub(
                "ok",
                "ARMED",
                dashboards=[{"label": "UI", "url": "http://u/", "probe": {}}],
            ),
            _sub("amb", "DEGRADED"),
            _sub("bad", "BAD"),
        ]
    }
    view = _tray_model.build(status, "http://127.0.0.1:8760/")
    assert view["level"] == "red"
    assert view["tooltip"].splitlines() == [
        "2 of 3 need attention",
        "BAD: BAD",
        "AMB: DEGRADED",
    ]
    first = view["items"][0]
    assert first["panel_url"] == "http://127.0.0.1:8760/#/s/ok"
    assert first["dashboards"] == [{"label": "UI", "url": "http://u/"}]
    assert view["items"][1]["dashboards"] == []


def test_tooltip_all_healthy_and_capped() -> None:
    healthy = _tray_model.build({"subsystems": [_sub("a", "ARMED")]}, "p")
    assert healthy["tooltip"] == "All 1 subsystems healthy"
    many = [_sub(f"s{i}", "UNKNOWN") for i in range(10)]
    tip = _tray_model.build({"subsystems": many}, "p")["tooltip"].splitlines()
    assert tip[-1] == "... and 2 more"
    assert len(tip) == 10
