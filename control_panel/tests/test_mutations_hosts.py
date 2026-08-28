from __future__ import annotations

from pathlib import Path
import re

import pytest

from control_panel._runner import CommandResult
from control_panel.mutations import _hosts_add
from control_panel.tests._fixture_runner import FakeRunner

BODY = {"domain": "example.com", "why": "eats an hour every evening"}


@pytest.fixture
def repo(sysroot: Path) -> Path:
    """A hosts-blocker checkout with an entries file and an installer."""
    base = sysroot / "home/tester/hosts-blocker"
    base.mkdir(parents=True)
    (base / _hosts_add.ENTRIES).write_text("# YouTube\n0.0.0.0 youtube.com\n")
    (base / _hosts_add.INSTALLER).write_text("#!/bin/bash\n")
    return base


def installer_argv(repo: Path) -> tuple[str, ...]:
    return ("/usr/bin/sudo", str(repo / _hosts_add.INSTALLER))


def ok_runner(repo: Path) -> FakeRunner:
    argv = installer_argv(repo)
    return FakeRunner(
        {argv: CommandResult(argv=argv, returncode=0, stdout="done", stderr="")}
    )


def test_a_domain_is_appended_and_the_installer_runs(repo: Path) -> None:
    runner = ok_runner(repo)
    result = _hosts_add.apply(runner, BODY)
    assert result.ok
    text = (repo / _hosts_add.ENTRIES).read_text()
    assert "0.0.0.0 example.com" in text
    assert installer_argv(repo) in runner.calls


def test_the_reason_rides_in_the_channel_the_guard_ignores(repo: Path) -> None:
    _hosts_add.apply(ok_runner(repo), BODY)
    text = (repo / _hosts_add.ENTRIES).read_text()
    assert "# @rule dns.example.com" in text
    assert 'why="eats an hour every evening"' in text
    # hosts_protect_custom.sh greps ^0\.0\.0\.0[[:space:]]+ and takes field 2,
    # so the comment cannot affect the entry set it diffs. Prove it with the
    # guard's own pattern rather than by assertion.
    guard = re.compile(
        r"^0\.0\.0\.0[[:space:]]+".replace("[[:space:]]", r"\s"), re.MULTILINE
    )
    entries = [line.split()[1] for line in text.splitlines() if guard.match(line)]
    assert entries == ["youtube.com", "example.com"]


def test_nothing_is_ever_removed(repo: Path) -> None:
    before = (repo / _hosts_add.ENTRIES).read_text()
    _hosts_add.apply(ok_runner(repo), BODY)
    after = (repo / _hosts_add.ENTRIES).read_text()
    # Add-only, structurally: the old content is a prefix of the new.
    assert after.startswith(before)


def test_an_already_blocked_domain_is_a_no_op(repo: Path) -> None:
    runner = ok_runner(repo)
    result = _hosts_add.apply(runner, {"domain": "youtube.com", "why": "already there"})
    assert result.ok
    assert "already blocked" in result.summary
    # No installer run, no duplicate line.
    assert runner.calls == []
    assert (repo / _hosts_add.ENTRIES).read_text().count("youtube.com") == 1


@pytest.mark.parametrize(
    "domain",
    [
        "not a domain",
        "no-dot",
        "",
        "-leading.com",
        "trailing-.com",
        "exam ple.com",
        "a" * 300 + ".com",
        "example.com\n0.0.0.0 evil.com",
        None,
        123,
    ],
)
def test_a_bad_domain_never_reaches_the_file(repo: Path, domain: object) -> None:
    runner = FakeRunner({})
    before = (repo / _hosts_add.ENTRIES).read_text()
    result = _hosts_add.apply(runner, {"domain": domain, "why": "a good long reason"})
    assert not result.ok
    assert runner.calls == []
    assert (repo / _hosts_add.ENTRIES).read_text() == before


def test_a_domain_is_normalised(repo: Path) -> None:
    _hosts_add.apply(ok_runner(repo), {"domain": "  EXAMPLE.COM. ", "why": BODY["why"]})
    assert "0.0.0.0 example.com" in (repo / _hosts_add.ENTRIES).read_text()


def test_a_missing_or_thin_reason_is_refused(repo: Path) -> None:
    for why in ("", "short"):
        result = _hosts_add.apply(FakeRunner({}), {"domain": "x.com", "why": why})
        assert not result.ok
        assert "why" in result.summary


def test_a_non_object_body_is_refused(repo: Path) -> None:
    assert not _hosts_add.apply(FakeRunner({}), "nope").ok


def test_a_failed_rebuild_keeps_the_queued_entry(repo: Path) -> None:
    argv = installer_argv(repo)
    runner = FakeRunner(
        {argv: CommandResult(argv=argv, returncode=1, stdout="", stderr="boom")}
    )
    result = _hosts_add.apply(runner, BODY)
    assert not result.ok
    assert "still queued" in result.summary
    # Removing it to "clean up" would be this dashboard performing the one edit
    # the whole protection exists to prevent.
    assert "0.0.0.0 example.com" in (repo / _hosts_add.ENTRIES).read_text()


def test_a_missing_checkout_is_reported(sysroot: Path) -> None:
    result = _hosts_add.apply(FakeRunner({}), BODY)
    assert not result.ok
    assert "hosts-blocker" in result.summary


def test_a_checkout_without_an_installer_is_reported(sysroot: Path) -> None:
    base = sysroot / "home/tester/hosts-blocker"
    base.mkdir(parents=True)
    (base / _hosts_add.ENTRIES).write_text("")
    assert "missing" in _hosts_add.apply(FakeRunner({}), BODY).summary


def test_an_unwritable_entries_file_is_reported(repo: Path) -> None:
    entries = repo / _hosts_add.ENTRIES
    entries.chmod(0o444)
    try:
        result = _hosts_add.apply(FakeRunner({}), BODY)
    finally:
        entries.chmod(0o644)
    assert not result.ok
    assert "Could not append" in result.summary


def test_an_unreadable_entries_file_does_not_crash_the_dedupe(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args: object, **_kwargs: object) -> str:
        msg = "denied"
        raise OSError(msg)

    monkeypatch.setattr(Path, "read_text", boom)
    assert not _hosts_add._already_blocked(repo / _hosts_add.ENTRIES, "x.com")


def test_the_real_guard_pattern_still_ignores_comments() -> None:
    # If hosts_protect_custom.sh ever stops filtering on ^0\.0\.0\.0, the
    # comment channel stops being free and this whole design breaks. Check the
    # real file rather than trusting a note.
    guard = Path("/home/kuhy/hosts-blocker/lib/hosts_protect_custom.sh")
    if not guard.is_file():
        pytest.skip("hosts-blocker is not checked out here")
    assert r"^0\.0\.0\.0[[:space:]]+" in guard.read_text(encoding="utf-8")
