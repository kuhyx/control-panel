"""Shared fixtures.

The autouse ``sysroot`` fixture is the safety net: ``_sysroot`` reads
``CONTROL_PANEL_ROOT`` with no default, so a test that somehow escapes this
fixture raises ``KeyError`` instead of reading the real ``/etc``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from control_panel import _probe, _sysroot
from control_panel._live_types import ProbeRecord

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def sysroot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every filesystem read at a disposable tree."""
    monkeypatch.setenv(_sysroot.ROOT_ENV, str(tmp_path))
    monkeypatch.setenv("HOME", "/home/tester")
    (tmp_path / "home/tester").mkdir(parents=True)
    (tmp_path / "etc/logrotate.d").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def fake_probes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Record probe targets and answer every one as up, never touching a socket."""
    seen: list[tuple[str, str]] = []

    def run_all(targets: list[tuple[str, str]]) -> dict[tuple[str, str], ProbeRecord]:
        seen.extend(targets)
        return {
            t: ProbeRecord(kind=t[0], target=t[1], up=True, status=200) for t in targets
        }

    monkeypatch.setattr(_probe, "run_all", run_all)
    return seen
