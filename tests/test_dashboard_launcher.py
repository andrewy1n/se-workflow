"""Tests for scripts/dashboard: store and binary resolution, and the messages it prints instead of exec'ing."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import AA_ROOT, REPO_ROOT, make_git_repo

SCRIPT = REPO_ROOT / "scripts" / "dashboard"

FAKE_BIN = """#!/usr/bin/env python3
import json, os, sys
print(json.dumps({"bin": os.path.basename(sys.argv[0]), "argv": sys.argv[1:]}))
"""


def _write_store(store: Path, views: list[str], contract_ref: str | None = None) -> Path:
    store.mkdir(parents=True, exist_ok=True)
    contract = store / "resolved-contract.json"
    contract.write_text(json.dumps({"views": [{"id": view} for view in views]}))
    (store / "meta.json").write_text(json.dumps({"store_version": 1, "contract": contract_ref or str(contract)}))
    return store


def _fake_bin(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(FAKE_BIN)
    path.chmod(0o755)
    return path


@pytest.fixture()
def home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture()
def repo():
    return make_git_repo()


def _run(cwd: Path, home: Path, *args: str, bin_path: Path | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "ADAPTIVE_ARTIFACTS_BIN"}
    env["HOME"] = str(home)
    if bin_path is not None:
        env["ADAPTIVE_ARTIFACTS_BIN"] = str(bin_path)
    return subprocess.run(
        [str(SCRIPT), *args], capture_output=True, text=True, cwd=str(cwd), env=env,
        stdin=subprocess.DEVNULL, timeout=30,
    )


def _exec_record(result: subprocess.CompletedProcess) -> dict:
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def _flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def test_uses_home_store_named_after_the_repo(home, repo, tmp_path):
    store = _write_store(home / ".artifacts" / repo.name, ["project:dashboard"])
    _write_store(repo / ".artifacts", ["project:dashboard"])
    argv = _exec_record(_run(repo, home, bin_path=_fake_bin(tmp_path / "aa")))["argv"]
    assert _flag(argv, "--store") == str(store)
    assert _flag(argv, "--root") == str(repo.resolve())
    assert argv[-3:] == ["watch", "--id", "project:dashboard"]


def test_uses_repo_store_when_home_has_none(home, repo, tmp_path):
    store = _write_store(repo / ".artifacts", ["project:dashboard"])
    argv = _exec_record(_run(repo, home, bin_path=_fake_bin(tmp_path / "aa")))["argv"]
    assert _flag(argv, "--store") == str(store.resolve())


def test_resolves_the_toplevel_from_a_subdirectory(home, repo, tmp_path):
    store = _write_store(repo / ".artifacts", ["project:dashboard"])
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    argv = _exec_record(_run(sub, home, bin_path=_fake_bin(tmp_path / "aa")))["argv"]
    assert _flag(argv, "--store") == str(store.resolve())


def test_ignores_a_home_store_dir_without_meta(home, repo, tmp_path):
    (home / ".artifacts" / repo.name).mkdir(parents=True)
    store = _write_store(repo / ".artifacts", ["project:dashboard"])
    argv = _exec_record(_run(repo, home, bin_path=_fake_bin(tmp_path / "aa")))["argv"]
    assert _flag(argv, "--store") == str(store.resolve())


def test_passes_extra_args_to_watch(home, repo, tmp_path):
    _write_store(repo / ".artifacts", ["project:dashboard"])
    argv = _exec_record(_run(repo, home, "--once", bin_path=_fake_bin(tmp_path / "aa")))["argv"]
    assert argv[-4:] == ["watch", "--id", "project:dashboard", "--once"]


def test_finds_a_relative_contract_inside_the_store(home, repo, tmp_path):
    store = _write_store(home / ".artifacts" / repo.name, ["project:dashboard"], contract_ref="resolved-contract.json")
    argv = _exec_record(_run(repo, home, bin_path=_fake_bin(tmp_path / "aa")))["argv"]
    assert _flag(argv, "--contract") == str(store / "resolved-contract.json")


def test_prints_no_store_message(home, repo, tmp_path):
    result = _run(repo, home, bin_path=_fake_bin(tmp_path / "aa"))
    assert result.returncode == 1
    assert "no artifact store" in result.stdout.lower()
    assert str(home / ".artifacts" / repo.name) in result.stdout
    assert '"argv"' not in result.stdout


def test_prints_missing_view_message(home, repo, tmp_path):
    _write_store(repo / ".artifacts", ["project:handoff"])
    result = _run(repo, home, bin_path=_fake_bin(tmp_path / "aa"))
    assert result.returncode == 1
    assert "project:dashboard" in result.stdout
    assert "no dashboard view" in result.stdout.lower()
    assert '"argv"' not in result.stdout


def test_env_bin_overrides_the_home_checkout(home, repo, tmp_path):
    _write_store(repo / ".artifacts", ["project:dashboard"])
    _fake_bin(home / "adaptive-artifacts" / "bin" / "adaptive-artifacts")
    assert _exec_record(_run(repo, home, bin_path=_fake_bin(tmp_path / "override")))["bin"] == "override"


def test_uses_the_home_checkout_bin_without_env(home, repo):
    _write_store(repo / ".artifacts", ["project:dashboard"])
    _fake_bin(home / "adaptive-artifacts" / "bin" / "adaptive-artifacts")
    assert _exec_record(_run(repo, home))["bin"] == "adaptive-artifacts"


def test_renders_a_real_store_once(home, store):
    result = _run(store, home, "--once", bin_path=AA_ROOT / "bin" / "adaptive-artifacts")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Project Dashboard" in result.stdout


def test_tmux_conf_binds_popup_and_side_pane_in_the_pane_directory():
    lines = (REPO_ROOT / "scripts" / "tmux-dashboard.conf").read_text().splitlines()
    popup = next(line for line in lines if line.startswith("bind-key A "))
    side = next(line for line in lines if line.startswith("bind-key S "))
    assert "display-popup" in popup and "-d '#{pane_current_path}'" in popup
    assert "split-window" in side and "-c '#{pane_current_path}'" in side
    assert all("/dashboard" in line for line in (popup, side))
