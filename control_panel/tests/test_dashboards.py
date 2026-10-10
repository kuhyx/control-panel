from __future__ import annotations

from dataclasses import replace
import io

import pytest

from control_panel import _dashboards, _live, _manifest
from control_panel._live_types import DashboardRecord, ProbeRecord
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner


def _dash(
    *, up: bool | None, status: int | None = None, detail: str | None = None
) -> DashboardRecord:
    probe = ProbeRecord(kind="http", target="u", up=up, status=status, detail=detail)
    return DashboardRecord(label="UI", url="http://127.0.0.1:1/", probe=probe)


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (_dash(up=None, detail="not probed: public"), "skipped"),
        (_dash(up=True, status=401), "login"),
        (_dash(up=True, status=200), "ok"),
        (_dash(up=True, status=302), "ok"),
        (_dash(up=True, status=404), "FAIL"),
        (_dash(up=False, detail="refused"), "FAIL"),
        (_dash(up=True, status=None), "FAIL"),
        # Anki's 404 answers mangatl's port: a clash fails whatever the probe.
        (replace(_dash(up=True, status=200), clash="port 1 held by a"), "FAIL"),
        (replace(_dash(up=None), clash="port 1 held by a"), "FAIL"),
    ],
)
def test_verdict(record: DashboardRecord, expected: str) -> None:
    assert _dashboards.verdict(record) == expected


def _patch(
    monkeypatch: pytest.MonkeyPatch, records: tuple[DashboardRecord, ...]
) -> None:
    monkeypatch.setattr(_manifest, "load_manifest", lambda: (fleet.entry(),))
    monkeypatch.setattr(
        _live,
        "collect",
        lambda _runner, _entries: {"s": _live.LiveView(dashboards=records)},
    )


def test_run_reports_failures_with_exit_1(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, (_dash(up=True, status=200), _dash(up=False, detail="refused")))
    out = io.StringIO()
    assert _dashboards.run(FakeRunner({}), out) == 1
    text = out.getvalue()
    assert "ok" in text
    assert "refused" in text
    assert "1 dashboard(s) failed." in text


def test_run_passes_when_all_usable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, (_dash(up=True, status=200),))
    out = io.StringIO()
    assert _dashboards.run(FakeRunner({}), out) == 0
    assert "all dashboards usable." in out.getvalue()
