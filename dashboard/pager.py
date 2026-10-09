"""Pager helpers: choose glow / $PAGER / less and page markdown outside the store."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path


def pager_command(path: str) -> list[str]:
    """Return argv to open *path*: glow -p, else $PAGER, else less -R."""
    if shutil.which("glow"):
        return ["glow", "-p", path]
    pager = os.environ.get("PAGER", "").strip()
    if pager:
        return [*shlex.split(pager), path]
    return ["less", "-R", path]


def page_text(text: str) -> None:
    """Write *text* to a temp .md under the system temp dir, run the pager, unlink."""
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        delete=False,
        encoding="utf-8",
    )
    path = Path(handle.name)
    try:
        with handle:
            handle.write(text)
        subprocess.run(pager_command(str(path)), check=False)
    finally:
        path.unlink(missing_ok=True)
