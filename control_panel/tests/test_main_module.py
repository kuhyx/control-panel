from __future__ import annotations

import runpy

import pytest

from control_panel import _web_server


def test_python_m_control_panel_dispatches_to_the_cli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_web_server, "serve", lambda port: 0)
    monkeypatch.setattr("sys.argv", ["control-panel", "serve"])
    with pytest.raises(SystemExit) as raised:
        runpy.run_module("control_panel", run_name="__main__")
    assert raised.value.code == 0
