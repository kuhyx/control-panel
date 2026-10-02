from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from control_panel import _manifest
from control_panel._manifest_live import (
    ManifestError,
    check_restartable,
    parse_containers,
    parse_dashboards,
    parse_ignored,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write(
    base: Path, entry: dict[str, Any], fleet: dict[str, Any] | None = None
) -> None:
    (base / "subsystems").mkdir(parents=True, exist_ok=True)
    (base / "fleet.json").write_text(json.dumps(fleet or {"order": []}))
    (base / "subsystems" / f"{entry['id']}.json").write_text(json.dumps(entry))


def test_dashboards_parse_with_on_demand_default() -> None:
    parsed = parse_dashboards(
        [
            {"label": "A", "url": "http://x/"},
            {"label": "B", "url": "u", "on_demand": True},
        ],
        "w",
    )
    assert parsed[0].on_demand is False
    assert parsed[1].on_demand is True


def test_absent_arrays_parse_empty() -> None:
    assert parse_dashboards(None, "w") == ()
    assert parse_containers(None, "w") == ()
    assert parse_ignored(None, "w") == ()


def test_non_array_is_refused() -> None:
    with pytest.raises(ManifestError, match="'containers' must be an array"):
        parse_containers({"name": "x"}, "w")
    with pytest.raises(ManifestError, match="array of objects"):
        parse_dashboards(["not an object"], "w")


def test_missing_required_key_names_the_file() -> None:
    with pytest.raises(ManifestError, match="w: missing required key 'url'"):
        parse_dashboards([{"label": "A"}], "w")


def test_ignored_listeners_parse() -> None:
    parsed = parse_ignored([{"port": 22, "why": "sshd"}], "w")
    assert parsed[0].port == 22
    assert parsed[0].why == "sshd"


def test_restartable_user_unit_in_server_is_accepted() -> None:
    check_restartable("server", (("a.service", "user", True),), (), "w")


def test_restartable_in_enforcement_is_a_load_error() -> None:
    with pytest.raises(ManifestError, match="only 'server' subsystems"):
        check_restartable("enforcement", (("guard.service", "user", True),), (), "w")


def test_restartable_container_outside_server_is_refused() -> None:
    containers = parse_containers([{"name": "c", "restartable": True}], "w")
    with pytest.raises(ManifestError, match="c marked restartable"):
        check_restartable("maintenance", (), containers, "w")


def test_restartable_system_unit_is_refused() -> None:
    with pytest.raises(ManifestError, match="needs root"):
        check_restartable("server", (("dufs.service", "system", True),), (), "w")


def test_loader_applies_the_restart_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "m"
    _write(
        base,
        {
            "id": "g",
            "title": "G",
            "category": "enforcement",
            "units": [
                {
                    "name": "g.service",
                    "scope": "user",
                    "kind": "service",
                    "restartable": True,
                }
            ],
        },
    )
    monkeypatch.setattr(_manifest, "MANIFEST_DIR", base)
    with pytest.raises(ManifestError, match="only 'server'"):
        _manifest.load_manifest()


def test_loader_reads_live_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "m"
    _write(
        base,
        {
            "id": "s",
            "title": "S",
            "category": "server",
            "important": False,
            "units": [
                {
                    "name": "s.service",
                    "scope": "user",
                    "kind": "service",
                    "restartable": True,
                }
            ],
            "containers": [{"name": "c", "restartable": True}],
            "dashboards": [{"label": "UI", "url": "http://127.0.0.1:1/"}],
        },
        {"order": ["s"], "ignored_listeners": [{"port": 22, "why": "sshd"}]},
    )
    monkeypatch.setattr(_manifest, "MANIFEST_DIR", base)
    (entry,) = _manifest.load_manifest()
    assert entry.live.important is False
    assert entry.units[0].restartable is True
    assert entry.live.containers[0].name == "c"
    assert entry.live.dashboards[0].label == "UI"
    assert _manifest.load_ignored_listeners()[0].port == 22


def test_real_manifest_loads_and_only_servers_restart() -> None:
    entries = _manifest.load_manifest()
    for entry in entries:
        flagged = [u for u in entry.units if u.restartable]
        flagged += [c for c in entry.live.containers if c.restartable]
        if flagged:
            assert entry.category == "server", entry.id
    assert _manifest.load_ignored_listeners()
