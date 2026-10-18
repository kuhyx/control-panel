"""scripts/test_changed.sh routes mcp-server/ changes to the subproject venv."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "test_changed.sh"
GIT = "/usr/bin/git"
BASH = "/bin/bash"


def _git(repo: Path, *args: str) -> None:
    subprocess.run([GIT, "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts" / "test_changed.sh")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    return root


def _run(repo: Path, mcp_python: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "MCP_PYTHON": str(mcp_python)}
    return subprocess.run(
        [BASH, "scripts/test_changed.sh"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_mcp_changes_run_in_the_subproject_venv(repo: Path, tmp_path: Path) -> None:
    (repo / "mcp-server").mkdir()
    (repo / "mcp-server" / "x.py").write_text("x = 1\n", encoding="utf-8")
    fake = tmp_path / "python"
    fake.write_text('#!/bin/bash\necho "ran $PWD $*"\n', encoding="utf-8")
    fake.chmod(0o755)
    done = _run(repo, fake)
    assert done.returncode == 0
    assert done.stdout.strip() == f"ran {repo / 'mcp-server'} -m pytest -q --tb=short"


def test_mcp_changes_fail_closed_without_the_venv(repo: Path, tmp_path: Path) -> None:
    (repo / "mcp-server").mkdir()
    (repo / "mcp-server" / "x.py").write_text("x = 1\n", encoding="utf-8")
    done = _run(repo, tmp_path / "missing")
    assert done.returncode == 1
    assert "setup_mcp.sh" in done.stderr


def test_other_changes_still_reach_the_main_suite(repo: Path, tmp_path: Path) -> None:
    (repo / "mcp-server").mkdir()
    (repo / "mcp-server" / "x.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "notes.txt").write_text("n\n", encoding="utf-8")
    fake = tmp_path / "python"
    fake.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    fake.chmod(0o755)
    done = _run(repo, fake)
    assert done.returncode == 0
    assert "no python changes: nothing to test" in done.stdout
