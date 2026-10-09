"""Tests for dashboard Landing git state (R5, R10, R11)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT, git, make_git_repo

sys.path.insert(0, str(REPO_ROOT))
from dashboard.landing import Landing, phase_landing  # noqa: E402

LANDING_BODY = """\
## Approach

Ship the phase.

## Landing

- Branch: `phase/human-gates`
- Worktree: `/tmp/example--human-gates`
- Base: `main`
"""

NO_LANDING_BODY = """\
## Approach

Ship the phase.
"""

DEFAULT_BRANCH_BODY = """\
## Landing

- Base: `main`
- Close actions: merge into main.
"""


def _scratch_main() -> Path:
    root = make_git_repo()
    git(root, "branch", "-M", "main")
    return root


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_phase_landing_reports_branch_ahead_and_not_merged():
    root = _scratch_main()
    git(root, "checkout", "-qb", "phase/human-gates")
    _write(root, "a.txt", "one\n")
    git(root, "add", "a.txt")
    git(root, "commit", "-qm", "ahead-1")
    _write(root, "a.txt", "two\n")
    git(root, "add", "a.txt")
    git(root, "commit", "-qm", "ahead-2")
    git(root, "checkout", "-q", "main")

    result = phase_landing(root, LANDING_BODY, "human-gates")
    assert result == Landing(branch="phase/human-gates", exists=True, ahead=2, merged=False)


def test_phase_landing_reports_merged():
    root = _scratch_main()
    git(root, "checkout", "-qb", "phase/human-gates")
    _write(root, "m.txt", "merged\n")
    git(root, "add", "m.txt")
    git(root, "commit", "-qm", "feature")
    git(root, "checkout", "-q", "main")
    git(root, "merge", "-q", "--no-ff", "phase/human-gates", "-m", "merge landing")

    result = phase_landing(root, LANDING_BODY, "human-gates")
    assert result == Landing(branch="phase/human-gates", exists=True, ahead=0, merged=True)


def test_phase_landing_no_landing_heading_returns_none():
    root = _scratch_main()
    assert phase_landing(root, NO_LANDING_BODY, "human-gates") is None


def test_phase_landing_missing_branch_exists_false():
    root = _scratch_main()
    result = phase_landing(root, LANDING_BODY, "human-gates")
    assert result == Landing(branch="phase/human-gates", exists=False, ahead=0, merged=False)


def test_phase_landing_defaults_branch_to_phase_subject():
    root = _scratch_main()
    result = phase_landing(root, DEFAULT_BRANCH_BODY, "human-gates")
    assert result == Landing(branch="phase/human-gates", exists=False, ahead=0, merged=False)


def test_phase_landing_nogr_returns_none(tmp_path):
    assert phase_landing(tmp_path, LANDING_BODY, "human-gates") is None


def test_phase_landing_no_git_returns_none(tmp_path, monkeypatch):
    root = _scratch_main()
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    assert phase_landing(root, LANDING_BODY, "human-gates") is None


def test_phase_landing_fail_returns_none(monkeypatch):
    root = _scratch_main()
    git(root, "checkout", "-qb", "phase/human-gates")
    git(root, "checkout", "-q", "main")

    real = subprocess.run

    def flaky(cmd, **kwargs):
        if isinstance(cmd, (list, tuple)) and "rev-list" in cmd:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=2)
        return real(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", flaky)
    assert phase_landing(root, LANDING_BODY, "human-gates") is None


def test_phase_landing_readonly_unchanged():
    root = _scratch_main()
    store = root / ".artifacts"
    store.mkdir()
    (store / "marker.txt").write_text("untouched\n")

    git(root, "checkout", "-qb", "phase/human-gates")
    _write(root, "r.txt", "x\n")
    git(root, "add", "r.txt")
    git(root, "commit", "-qm", "readonly-feature")
    git(root, "checkout", "-q", "main")

    before_status = git(root, "status", "--porcelain").stdout
    before_head = git(root, "rev-parse", "HEAD").stdout
    before_store = {p.relative_to(store): p.read_bytes() for p in store.rglob("*") if p.is_file()}

    result = phase_landing(root, LANDING_BODY, "human-gates")
    assert result is not None and result.exists

    assert git(root, "status", "--porcelain").stdout == before_status
    assert git(root, "rev-parse", "HEAD").stdout == before_head
    after_store = {p.relative_to(store): p.read_bytes() for p in store.rglob("*") if p.is_file()}
    assert after_store == before_store
    assert not any(name.endswith(".lock") for name in os.listdir(root / ".git"))


def test_phase_landing_readonly_missing_branch_leaves_repo():
    root = _scratch_main()
    store = root / ".artifacts"
    store.mkdir()
    (store / "keep").write_text("1\n")
    before_status = git(root, "status", "--porcelain").stdout
    before_files = sorted(p.relative_to(store).as_posix() for p in store.rglob("*"))

    assert phase_landing(root, LANDING_BODY, "human-gates") == Landing(
        branch="phase/human-gates", exists=False, ahead=0, merged=False,
    )

    assert git(root, "status", "--porcelain").stdout == before_status
    assert sorted(p.relative_to(store).as_posix() for p in store.rglob("*")) == before_files
