from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from control_panel import _cli, _collect, _doctor, _manifest, _sysroot, _web_server
from control_panel._types import Arming, Scope, UnitRecord
from control_panel.tests import _fixture_fleet as fleet

if TYPE_CHECKING:
    from control_panel._manifest import ManifestEntry


@pytest.fixture
def stub_collection(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[UnitRecord]]:
    """Replace the real fleet read with a controllable one."""
    holder: dict[str, list[UnitRecord]] = {"units": []}
    monkeypatch.setattr(_manifest, "load_manifest", lambda: (fleet.entry(),))
    monkeypatch.setattr(_collect, "read_systemd", lambda _runner: fleet.view())
    monkeypatch.setattr(
        _collect,
        "collect_units",
        lambda _r, _e, _v: {"s": tuple(holder["units"])},
    )
    return holder


def test_doctor_exits_zero_when_everything_is_armed(
    stub_collection: dict[str, list[UnitRecord]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    stub_collection["units"] = [
        UnitRecord(name="a.timer", scope=Scope.USER, arming=Arming.ARMED)
    ]
    assert _cli.main(["doctor"]) == 0
    assert "ARMED=1" in capsys.readouterr().out


def test_doctor_exits_one_and_counts_problems(
    stub_collection: dict[str, list[UnitRecord]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    stub_collection["units"] = [
        UnitRecord(name="a.timer", scope=Scope.USER, arming=Arming.UNARMED)
    ]
    assert _cli.main(["doctor"]) == 1
    assert "1 unit(s) need attention" in capsys.readouterr().out


def test_serve_dispatches_with_the_chosen_port(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []

    def record(port: int) -> int:
        seen.append(port)
        return 0

    monkeypatch.setattr(_web_server, "serve", record)
    assert _cli.main(["serve", "--port", "9999"]) == 0
    assert seen == [9999]


def test_serve_defaults_to_the_reserved_port(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []

    def record(port: int) -> int:
        seen.append(port)
        return 0

    monkeypatch.setattr(_web_server, "serve", record)
    _cli.main(["serve"])
    assert seen == [_web_server.DEFAULT_PORT]
    assert _web_server.DEFAULT_PORT == 8760


def test_the_cli_defaults_the_sysroot_to_the_real_filesystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Only the CLI may supply this default; the library must keep refusing to
    # guess, so a test that forgets the fixture fails loudly.
    monkeypatch.delenv(_sysroot.ROOT_ENV)
    monkeypatch.setattr(_web_server, "serve", lambda port: 0)
    _cli.main(["serve"])
    assert _sysroot.sysroot() == ""


def test_no_command_is_rejected() -> None:
    with pytest.raises(SystemExit):
        _cli.main([])


def test_doctor_renders_without_colour_when_piped(
    stub_collection: dict[str, list[UnitRecord]], monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[bool] = []
    real = _doctor.render

    def spy(
        entries: tuple[ManifestEntry, ...],
        units: dict[str, tuple[UnitRecord, ...]],
        *,
        colour: bool,
    ) -> str:
        captured.append(colour)
        return real(entries, units, colour=colour)

    monkeypatch.setattr(_doctor, "render", spy)
    _cli.main(["doctor"])
    assert captured == [False]


def test_dashboards_dispatches_to_the_checker(monkeypatch: pytest.MonkeyPatch) -> None:
    from control_panel import _dashboards

    monkeypatch.setattr(_dashboards, "run", lambda _runner, _out: 7)
    assert _cli.main(["dashboards"]) == 7
