"""Load se-workflow.tmux into an isolated tmux server and read back the key bindings."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from conftest import REPO_ROOT

pytestmark = pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux is not installed")

ENTRY = REPO_ROOT / "se-workflow.tmux"


class Server:
    def __init__(self, tmp_path: Path):
        self.socket = f"se-wf-entry-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("TMUX")}
        self.env.update(HOME=str(tmp_path), SHELL="/bin/sh")
        self("new-session", "-d", "-s", "main", "-x", "120", "-y", "40")

    def __call__(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["tmux", "-L", self.socket, "-f", "/dev/null", *args],
            capture_output=True, text=True, env=self.env, timeout=10,
        )
        if check:
            assert result.returncode == 0, f"tmux {args}: {result.stdout}{result.stderr}"
        return result.stdout

    def load(self, entry: Path = ENTRY) -> None:
        self("run-shell", shlex.quote(str(entry)))

    def binding(self, key: str) -> str:
        return self("list-keys", "-T", "prefix", key, check=False)


@pytest.fixture()
def server(tmp_path):
    server = Server(tmp_path)
    try:
        yield server
    finally:
        server("kill-server", check=False)


def test_default_keys_bind_a_popup_and_a_side_pane_of_the_launcher_in_the_pane_directory(server):
    server.load()
    popup, side = server.binding("A"), server.binding("S")
    launcher = str(REPO_ROOT / "dashboard" / "bin" / "dashboard")
    assert "display-popup" in popup and '-d "#{pane_current_path}"' in popup and launcher in popup
    assert "split-window" in side and '-c "#{pane_current_path}"' in side and launcher in side


def test_default_keys_use_the_launcher_beside_the_script_when_the_repo_moves(server, tmp_path):
    moved = tmp_path / "plugin dir"
    shutil.copytree(REPO_ROOT / "dashboard", moved / "dashboard", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ENTRY, moved / ENTRY.name)
    server.load(moved / ENTRY.name)
    assert str(moved / "dashboard" / "bin" / "dashboard") in server.binding("A")
    assert str(moved / "dashboard" / "bin" / "dashboard") in server.binding("S")


def test_custom_keys_from_the_options_rebind_and_leave_the_defaults_unbound(server):
    server("set-option", "-g", "@dashboard-popup-key", "D")
    server("set-option", "-g", "@dashboard-pane-key", "P")
    server.load()
    assert "display-popup" in server.binding("D")
    assert "split-window" in server.binding("P")
    assert "dashboard" not in server.binding("A")
    assert "dashboard" not in server.binding("S")
