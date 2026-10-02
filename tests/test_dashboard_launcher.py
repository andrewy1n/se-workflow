"""Tests for dashboard/bin/dashboard: store and binary resolution, and the messages it prints instead of exec'ing."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import helpers as h
from conftest import AA_ROOT, REPO_ROOT, make_git_repo
from test_dashboard_status import _goal, _work_item

SCRIPT = REPO_ROOT / "dashboard" / "bin" / "dashboard"

FAKE_UV = """#!/usr/bin/env python3
import json, os, sys
print(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(), "aa_bin": os.environ.get("ADAPTIVE_ARTIFACTS_BIN")}))
"""
APP = REPO_ROOT / "dashboard" / "__main__.py"


def _write_store(store: Path, contract_ref: str | None = None) -> Path:
    store.mkdir(parents=True, exist_ok=True)
    contract = store / "resolved-contract.json"
    contract.write_text(json.dumps({"views": []}))
    (store / "meta.json").write_text(json.dumps({"store_version": 1, "contract": contract_ref or str(contract)}))
    return store


def _fake_uv(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(FAKE_UV)
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


def _run(
    cwd: Path, home: Path, *args: str, uv: Path | None = None, aa_bin: Path | None = None, path: str | None = None,
) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("ADAPTIVE_ARTIFACTS_BIN", "SE_WORKFLOW_UV")}
    env["HOME"] = str(home)
    if uv is not None:
        env["SE_WORKFLOW_UV"] = str(uv)
    if aa_bin is not None:
        env["ADAPTIVE_ARTIFACTS_BIN"] = str(aa_bin)
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        [str(SCRIPT), *args], capture_output=True, text=True, cwd=str(cwd), env=env,
        stdin=subprocess.DEVNULL, timeout=60,
    )


def _exec_record(result: subprocess.CompletedProcess) -> dict:
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_runs_the_app_through_uv_from_the_repo_root(home, repo, tmp_path):
    _write_store(repo / ".artifacts")
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    record = _exec_record(_run(sub, home, uv=_fake_uv(tmp_path / "uv")))
    assert record["argv"] == ["run", "--script", str(APP)]
    assert Path(record["cwd"]).resolve() == repo.resolve()


def test_passes_extra_args_to_the_app(home, repo, tmp_path):
    _write_store(repo / ".artifacts")
    argv = _exec_record(_run(repo, home, "--once", "--interval", "5", uv=_fake_uv(tmp_path / "uv")))["argv"]
    assert argv == ["run", "--script", str(APP), "--once", "--interval", "5"]


def test_runs_with_a_home_store_and_no_repo_store(home, repo, tmp_path):
    _write_store(home / ".artifacts" / repo.name)
    assert _exec_record(_run(repo, home, uv=_fake_uv(tmp_path / "uv")))["argv"][:2] == ["run", "--script"]


def test_runs_with_a_repo_store_when_home_dir_has_no_meta(home, repo, tmp_path):
    (home / ".artifacts" / repo.name).mkdir(parents=True)
    _write_store(repo / ".artifacts")
    assert _exec_record(_run(repo, home, uv=_fake_uv(tmp_path / "uv")))["argv"][:2] == ["run", "--script"]


def test_does_not_require_the_dashboard_view(home, repo, tmp_path):
    _write_store(repo / ".artifacts")
    result = _run(repo, home, uv=_fake_uv(tmp_path / "uv"))
    assert result.returncode == 0 and "dashboard view" not in result.stdout


def test_finds_uv_on_path(home, repo, tmp_path):
    _write_store(repo / ".artifacts")
    _fake_uv(tmp_path / "bin" / "uv")
    record = _exec_record(_run(repo, home, path=f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"))
    assert record["argv"] == ["run", "--script", str(APP)]


def test_finds_uv_in_the_home_local_bin(home, repo):
    _write_store(repo / ".artifacts")
    _fake_uv(home / ".local" / "bin" / "uv")
    bare = tmp_bare_path(home)
    assert _exec_record(_run(repo, home, path=bare))["argv"] == ["run", "--script", str(APP)]


def tmp_bare_path(home: Path) -> str:
    links = home / "bare"
    links.mkdir()
    for name in ("git", "python3", "env"):
        found = shutil.which(name)
        if found:
            (links / name).symlink_to(found)
    return str(links)


def test_prints_install_hint_when_uv_is_missing(home, repo):
    _write_store(repo / ".artifacts")
    result = _run(repo, home, path=tmp_bare_path(home))
    assert result.returncode == 1
    assert "uv" in result.stdout and "install" in result.stdout.lower()


def test_prints_no_store_message(home, repo, tmp_path):
    result = _run(repo, home, uv=_fake_uv(tmp_path / "uv"))
    assert result.returncode == 1
    assert "no artifact store" in result.stdout.lower()
    assert str(home / ".artifacts" / repo.name) in result.stdout
    assert '"argv"' not in result.stdout


def test_env_bin_reaches_the_app(home, repo, tmp_path):
    _write_store(repo / ".artifacts")
    record = _exec_record(_run(repo, home, uv=_fake_uv(tmp_path / "uv"), aa_bin=tmp_path / "aa"))
    assert record["aa_bin"] == str(tmp_path / "aa")


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")
def test_renders_a_seeded_store_once_with_the_textual_app(home, store, cli, resolved_contract):
    defs = h.record_defs_by_id(resolved_contract)
    _goal(cli, defs, "launchfx")
    _work_item(cli, defs, "launchfx", "lx-ready")
    cache = os.environ.get("UV_CACHE_DIR") or str(Path.home() / ".cache" / "uv")
    result = _run_real(store, home, cache)
    assert result.returncode == 0, result.stdout + result.stderr
    for text in ("launchfx", "ship launchfx", "title of lx-ready", "3 Ready 1", "2 Running 0"):
        assert text in result.stdout, result.stdout


def _run_real(cwd: Path, home: Path, cache: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, HOME=str(home), UV_CACHE_DIR=cache, ADAPTIVE_ARTIFACTS_BIN=str(AA_ROOT / "bin" / "adaptive-artifacts"))
    env.pop("SE_WORKFLOW_UV", None)
    return subprocess.run(
        [str(SCRIPT), "--once"], capture_output=True, text=True, cwd=str(cwd), env=env,
        stdin=subprocess.DEVNULL, timeout=120,
    )
