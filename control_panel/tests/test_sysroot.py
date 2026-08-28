from __future__ import annotations

from pathlib import Path

import pytest

from control_panel import _sysroot


def test_missing_root_raises_rather_than_reading_the_real_system(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_sysroot.ROOT_ENV)
    with pytest.raises(KeyError):
        _sysroot.sysroot()


def test_empty_root_means_the_real_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    # Path("") normalises to Path("."), which would silently turn every
    # absolute lookup into a relative one and report every ExecStart missing.
    monkeypatch.setenv(_sysroot.ROOT_ENV, "")
    assert _sysroot.sysroot_path("/usr/bin/dufs") == Path("/usr/bin/dufs")


def test_root_prefixes_absolute_paths(sysroot: Path) -> None:
    assert _sysroot.sysroot_path("/etc/hosts") == sysroot / "etc/hosts"


def test_user_path_resolves_under_home(sysroot: Path) -> None:
    assert _sysroot.user_path(".config/x") == sysroot / "home/tester/.config/x"


def test_exists_reports_presence(sysroot: Path) -> None:
    (sysroot / "etc/hosts").write_text("x")
    assert _sysroot.exists("/etc/hosts")
    assert not _sysroot.exists("/etc/nope")


def test_exists_swallows_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_self: Path) -> bool:
        msg = "permission denied"
        raise OSError(msg)

    monkeypatch.setattr(Path, "exists", boom)
    assert not _sysroot.exists("/etc/hosts")
