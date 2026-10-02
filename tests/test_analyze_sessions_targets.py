import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from session_aggregate import aggregate

TARGETS = ROOT / "skills" / "analyze-sessions" / "targets.md"
HEADINGS = [
    "se-workflow skills",
    "artifact contract",
    "CLAUDE.md and steering files",
    "automated checks",
]
ROW = {
    "session_id": "s",
    "turns": 5,
    "cost_usd": 1.0,
    "file": "f",
    "project": "p",
    "branch": "b",
    "tools": {"tools": {"Bash": {"calls": 2, "errors": 1, "retries": 1}}, "totals": {"calls": 2, "errors": 1, "retries": 1}},
    "skills": {"engage": 1},
    "records": {"total": 4, "by_type": {}, "efforts": ["a"], "tasks": [], "ambiguous": 1},
}


def paths(obj, prefix=""):
    found = set()
    if isinstance(obj, dict):
        for key, val in obj.items():
            found |= paths(val, f"{prefix}.{key}" if prefix else key)
            found.add(f"{prefix}.{key}" if prefix else key)
    elif isinstance(obj, list):
        for item in obj:
            found |= paths(item, f"{prefix}[]")
    return found


def valid_paths():
    result = {re.sub(r"^efforts\.a\b", "efforts.*", p) for p in paths(aggregate([__import__("json").dumps(ROW)]))}
    return result


def sections():
    parts = re.split(r"^## ", TARGETS.read_text(), flags=re.M)[1:]
    return {p.splitlines()[0].strip(): p for p in parts}


def test_one_section_per_target():
    assert sorted(sections()) == sorted(HEADINGS)


def test_each_section_has_pattern_with_real_fields():
    valid = valid_paths()
    for name, body in sections().items():
        bullets = [l for l in body.splitlines() if l.startswith("- ") and "->" in l]
        assert bullets, name
        for line in bullets:
            fields = re.findall(r"`([^`]+)`", line)
            assert fields, line
            for field in fields:
                assert field in valid, f"{name}: {field}"
