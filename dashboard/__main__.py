#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["textual>=0.80"]
# ///
"""Textual dashboard for the project's artifact store. `--once` prints one plain-text frame."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dashboard.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
