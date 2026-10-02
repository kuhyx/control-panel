from __future__ import annotations

from control_panel import _journal
from control_panel._manifest_live import ManifestContainer
from control_panel._runner import CommandResult
from control_panel._types import Scope
from control_panel.tests import _fixture_fleet as fleet
from control_panel.tests._fixture_runner import FakeRunner, ok

ENTRIES = (
    fleet.live_entry(
        units=(fleet.service("bot.service"), fleet.service("d.service", Scope.SYSTEM)),
        containers=(ManifestContainer(name="gitea"),),
    ),
)


def test_clamp_bounds() -> None:
    assert _journal.clamp(0) == 1
    assert _journal.clamp(5) == 5
    assert _journal.clamp(10**6) == _journal.MAX_LINES


def test_only_declared_sources_are_readable() -> None:
    assert _journal.is_declared(ENTRIES, "user", "bot.service")
    assert _journal.is_declared(ENTRIES, "system", "d.service")
    assert _journal.is_declared(ENTRIES, "docker", "gitea")
    assert not _journal.is_declared(ENTRIES, "system", "bot.service")
    assert not _journal.is_declared(ENTRIES, "docker", "bot.service")
    assert _journal.read(FakeRunner({}), ENTRIES, "system", "sshd.service", 5) is None


def test_argv_per_source() -> None:
    assert _journal.argv_for("user", "a", 3)[:2] == ("journalctl", "--user")
    assert "--user" not in _journal.argv_for("system", "a", 3)
    assert _journal.argv_for("docker", "g", 3) == (
        "docker",
        "logs",
        "--timestamps",
        "--tail",
        "3",
        "g",
    )


def test_user_journal_tail() -> None:
    argv = _journal.argv_for("user", "bot.service", 2)
    runner = FakeRunner({argv: ok(argv, "one\ntwo\nthree\n")})
    read = _journal.read(runner, ENTRIES, "user", "bot.service", 2)
    assert read == {
        "source": "user",
        "name": "bot.service",
        "lines": ["two", "three"],
        "ok": True,
        "error": "",
    }


def test_docker_merges_both_streams_in_time_order() -> None:
    argv = _journal.argv_for("docker", "gitea", 100)
    result = CommandResult(
        argv=argv,
        returncode=0,
        stdout="2026-01-01T00:00:01Z out\n2026-01-01T00:00:03Z out2\n",
        stderr="2026-01-01T00:00:02Z err\n",
    )
    read = _journal.read(FakeRunner({argv: result}), ENTRIES, "docker", "gitea", 100)
    assert read is not None
    assert [line.split()[1] for line in read["lines"]] == ["out", "err", "out2"]


def test_failure_is_reported() -> None:
    read = _journal.read(FakeRunner({}), ENTRIES, "system", "d.service", 5)
    assert read is not None
    assert read["ok"] is False
    assert read["error"] == "no fixture"
