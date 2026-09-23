"""Shared fixtures for the se-workflow contract/skill test suite.

Everything here drives the public `adaptive-artifacts` CLI as a subprocess —
never the runtime's Python modules directly — because the runtime's storage
layer is being rewritten underneath this contract and only the CLI's
observable behavior is a stable target.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
CONTRACT_PATH = REPO_ROOT / "contract" / "project-design.json"

_DEFAULT_AA_ROOT = Path.home() / "adaptive-artifacts"
AA_ROOT = Path(os.environ.get("ADAPTIVE_ARTIFACTS_ROOT", str(_DEFAULT_AA_ROOT))).expanduser().resolve()
CLI = AA_ROOT / "tools" / "artifacts.py"


def pytest_configure(config):
    if not CLI.is_file():
        raise pytest.UsageError(
            f"adaptive-artifacts CLI not found at {CLI}. "
            "Set ADAPTIVE_ARTIFACTS_ROOT to a checkout of adaptive-artifacts "
            "(the sibling runtime repo) or check one out at "
            f"{_DEFAULT_AA_ROOT}."
        )
    if not CONTRACT_PATH.is_file():
        raise pytest.UsageError(f"se-workflow contract not found at {CONTRACT_PATH}.")


def run_cli(*args: str, root: Path | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(CLI)]
    if root is not None:
        cmd.extend(["--root", str(root)])
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or REPO_ROOT))


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def make_git_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="se-workflow-test-"))
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "test")
    git(root, "commit", "--allow-empty", "-qm", "init")
    return root


def load_current_contract() -> dict:
    """Read the live se-workflow contract from disk, un-cached.

    Called at collection time (for parametrization) and again inside tests
    that build a store, so a concurrently-edited contract is always read
    fresh rather than pinned to whatever it looked like at import time.
    """
    return json.loads(CONTRACT_PATH.read_text())


def resolve_contract(root: Path) -> dict:
    """Resolve the current on-disk contract via the CLI and return it as a dict.

    `root` must already have `.artifacts/project-design.json` in place; the
    resolved contract lands next to it at `.artifacts/resolved-contract.json`.
    """
    result = run_cli("resolve", root=root)
    assert result.returncode == 0, f"resolve failed: {result.stdout}\n{result.stderr}"
    return json.loads((root / ".artifacts" / "resolved-contract.json").read_text())


@pytest.fixture()
def resolved_contract(tmp_path):
    """The current resolved contract, re-resolved fresh for this test."""
    design_dir = tmp_path / ".artifacts"
    design_dir.mkdir()
    (design_dir / "project-design.json").write_text(CONTRACT_PATH.read_text())
    return resolve_contract(tmp_path)


@pytest.fixture()
def store(tmp_path):
    """A fresh, disposable, git-backed artifact store initialized from the
    current on-disk contract. Torn down automatically with tmp_path."""
    root = make_git_repo()
    design_dir = root / ".artifacts"
    design_dir.mkdir()
    (design_dir / "project-design.json").write_text(CONTRACT_PATH.read_text())
    resolve_result = run_cli("resolve", root=root)
    assert resolve_result.returncode == 0, resolve_result.stdout + resolve_result.stderr
    init_result = run_cli("init", root=root)
    assert init_result.returncode == 0, init_result.stdout + init_result.stderr
    return root


@pytest.fixture()
def cli(store):
    """Bound CLI runner for the `store` fixture's root."""

    def _run(*args: str) -> subprocess.CompletedProcess:
        return run_cli(*args, root=store)

    return _run
