"""Stream Claude Code session transcripts as JSONL events."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReadStats:
    bad_lines: int = 0


def read_events(path: Path, stats: ReadStats | None = None) -> Iterator[dict]:
    stats = stats if stats is not None else ReadStats()
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                stats.bad_lines += 1
                continue
            if not isinstance(event, dict):
                stats.bad_lines += 1
                continue
            yield event
