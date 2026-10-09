"""Unit tests for dashboard pager helpers (temp file + command choice)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from dashboard import pager


STUB_PAGER = """#!/usr/bin/env python3
import sys
from pathlib import Path
path = Path(sys.argv[1])
out = Path(sys.argv[0]).with_suffix(".out")
out.write_text(f"{path}\\n{path.read_text(encoding='utf-8')}", encoding="utf-8")
"""


@pytest.fixture()
def stub_pager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    script = tmp_path / "stub-pager"
    script.write_text(STUB_PAGER, encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PAGER", str(script))
    monkeypatch.setattr(pager.shutil, "which", lambda name: None)
    return script


def test_pager_command_prefers_glow(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(pager.shutil, "which", lambda name: "/usr/bin/glow" if name == "glow" else None)
    assert pager.pager_command("/tmp/doc.md") == ["glow", "-p", "/tmp/doc.md"]


def test_pager_command_uses_pager_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(pager.shutil, "which", lambda name: None)
    monkeypatch.setenv("PAGER", "view -f")
    assert pager.pager_command("/tmp/doc.md") == ["view", "-f", "/tmp/doc.md"]


def test_pager_command_falls_back_to_less(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(pager.shutil, "which", lambda name: None)
    monkeypatch.delenv("PAGER", raising=False)
    assert pager.pager_command("/tmp/doc.md") == ["less", "-R", "/tmp/doc.md"]


def test_page_text_writes_outside_store_stub_sees_contents_then_deletes(stub_pager: Path):
    text = "# Spec\n\nRequirement R11 body.\n"
    pager.page_text(text)

    out = stub_pager.with_suffix(".out")
    assert out.is_file(), "stub pager did not run"
    recorded_path_line, _, contents = out.read_text(encoding="utf-8").partition("\n")
    recorded = Path(recorded_path_line)
    assert recorded.suffix == ".md"
    assert ".artifacts" not in recorded.parts
    assert recorded.parent.resolve() == Path(tempfile.gettempdir()).resolve()
    assert contents == text
    assert not recorded.exists()
