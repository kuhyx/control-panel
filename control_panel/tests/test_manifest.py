from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from control_panel import _manifest
from control_panel._manifest import ManifestError
from control_panel._types import Category, Scope

if TYPE_CHECKING:
    from pathlib import Path


def write_manifest(base: Path, order: list[str], subsystems: dict[str, dict]) -> Path:
    (base / "subsystems").mkdir(parents=True)
    (base / "fleet.json").write_text(json.dumps({"order": order}))
    for name, body in subsystems.items():
        (base / "subsystems" / f"{name}.json").write_text(json.dumps(body))
    return base


def minimal(subsystem_id: str) -> dict:
    return {"id": subsystem_id, "title": subsystem_id, "category": "enforcement"}


def test_loads_and_orders(tmp_path: Path) -> None:
    base = write_manifest(
        tmp_path / "m", ["b", "a"], {"a": minimal("a"), "b": minimal("b")}
    )
    entries = _manifest.load_manifest(base)
    assert [entry.id for entry in entries] == ["b", "a"]


def test_unordered_subsystems_are_appended_not_dropped(tmp_path: Path) -> None:
    base = write_manifest(tmp_path / "m", ["a"], {"a": minimal("a"), "z": minimal("z")})
    assert [e.id for e in _manifest.load_manifest(base)] == ["a", "z"]


def test_full_entry_parses(tmp_path: Path) -> None:
    body = {
        **minimal("full"),
        "units": [
            {
                "name": "x.timer",
                "scope": "user",
                "kind": "timer",
                "why_it_matters": "because",
                "login_oneshot": True,
                "arming_lives_on": ["y.timer"],
                "retired": {
                    "since": "2026-01-01",
                    "superseded_by": "z.timer",
                    "note": "n",
                },
            }
        ],
        "probes": [{"kind": "tcp", "target": "127.0.0.1:1"}],
        "logs": [{"id": "l", "kind": "file", "path": "/var/log/x"}],
        "snapshot_dirs": ["~/snap-*"],
        "facts": {"k": "v"},
    }
    base = write_manifest(tmp_path / "m", ["full"], {"full": body})
    entry = _manifest.load_manifest(base)[0]
    assert entry.category is Category.ENFORCEMENT
    assert entry.units[0].scope is Scope.USER
    assert entry.units[0].retired is not None
    assert entry.units[0].retired.superseded_by == "z.timer"
    assert entry.units[0].arming_lives_on == ("y.timer",)
    assert entry.live.probes[0].target == "127.0.0.1:1"
    assert entry.logs[0].scope is Scope.SYSTEM
    assert entry.snapshot_dirs == ("~/snap-*",)
    assert entry.facts == {"k": "v"}


def test_missing_required_key_is_fatal(tmp_path: Path) -> None:
    base = write_manifest(tmp_path / "m", [], {"a": {"id": "a", "title": "a"}})
    with pytest.raises(ManifestError, match="category"):
        _manifest.load_manifest(base)


def test_missing_file_is_fatal(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="unreadable"):
        _manifest.load_manifest(tmp_path / "nothing-here")


def test_malformed_json_is_fatal(tmp_path: Path) -> None:
    base = tmp_path / "m"
    (base / "subsystems").mkdir(parents=True)
    (base / "fleet.json").write_text("{{{")
    with pytest.raises(ManifestError, match="unreadable"):
        _manifest.load_manifest(base)


def test_non_object_manifest_is_fatal(tmp_path: Path) -> None:
    base = tmp_path / "m"
    (base / "subsystems").mkdir(parents=True)
    (base / "fleet.json").write_text("[]")
    with pytest.raises(ManifestError, match="must be a JSON object"):
        _manifest.load_manifest(base)


def test_empty_subsystem_dir_is_fatal(tmp_path: Path) -> None:
    base = write_manifest(tmp_path / "m", [], {})
    with pytest.raises(ManifestError, match="no subsystem manifests"):
        _manifest.load_manifest(base)


def test_duplicate_ids_are_fatal(tmp_path: Path) -> None:
    base = write_manifest(
        tmp_path / "m", [], {"a": minimal("dup"), "b": minimal("dup")}
    )
    with pytest.raises(ManifestError, match="duplicate subsystem id"):
        _manifest.load_manifest(base)


def test_non_object_unit_is_fatal(tmp_path: Path) -> None:
    base = write_manifest(
        tmp_path / "m", [], {"a": {**minimal("a"), "units": ["oops"]}}
    )
    with pytest.raises(ManifestError, match="each unit must be an object"):
        _manifest.load_manifest(base)


def test_non_object_retired_is_fatal(tmp_path: Path) -> None:
    body = {
        **minimal("a"),
        "units": [{"name": "x", "scope": "user", "kind": "timer", "retired": "yes"}],
    }
    base = write_manifest(tmp_path / "m", [], {"a": body})
    with pytest.raises(ManifestError, match="'retired' must be an object"):
        _manifest.load_manifest(base)


def test_the_real_shipped_manifest_loads() -> None:
    # The manifest is data, and data rots. This is the gate that catches a
    # typo in it before the dashboard silently under-reports a subsystem.
    entries = _manifest.load_manifest()
    ids = [entry.id for entry in entries]
    assert "phone-focus-mode" in ids
    assert "kuhytrack" in ids
    assert len(entries) >= 13


def test_rationale_sources_parse(tmp_path: Path) -> None:
    body = {
        **minimal("a"),
        "docs": [{"path": "/etc/policy.md", "label": "policy"}],
        "audits": [{"path": "/etc/audit.log", "label": "audit"}],
    }
    base = write_manifest(tmp_path / "m", [], {"a": body})
    entry = _manifest.load_manifest(base)[0]
    assert entry.docs[0].label == "policy"
    assert entry.audits[0].path == "/etc/audit.log"


def test_a_non_array_rationale_source_is_fatal(tmp_path: Path) -> None:
    base = write_manifest(
        tmp_path / "m", [], {"a": {**minimal("a"), "docs": {"path": "x"}}}
    )
    with pytest.raises(ManifestError, match="must be an array"):
        _manifest.load_manifest(base)
