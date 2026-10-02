import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

SCRIPT = ROOT / "scripts" / "session_aggregate.py"


def row(efforts, total, ambiguous):
    return {
        "session_id": "s",
        "turns": 5,
        "cost_usd": 1.0,
        "tools": {"tools": {}, "totals": {"calls": 2, "errors": 0, "retries": 0}},
        "records": {"total": total, "by_type": {}, "efforts": efforts, "tasks": [], "ambiguous": ambiguous},
    }


def run(text):
    return subprocess.run([sys.executable, str(SCRIPT)], input=text, capture_output=True, text=True)


def test_fixture_report_prints_all_sections():
    text = "\n".join(json.dumps(r) for r in [row(["a"], 4, 1), row(["a", "b"], 4, 0)]) + "\n"
    proc = run(text)
    assert proc.returncode == 0
    doc = json.loads(proc.stdout)
    assert set(doc) == {"sessions", "efforts", "tools", "skills", "outliers", "caveats"}
    assert doc["sessions"] == 2
    assert set(doc["efforts"]) == {"a", "b"}
    assert doc["caveats"]["attached_records"] == 8
    assert doc["caveats"]["ambiguous_records"] == 1
    assert doc["caveats"]["ambiguous_share"] == 0.125
    assert "approximate" in doc["caveats"]["note"]


def test_bad_and_blank_lines_are_counted_and_skipped():
    text = json.dumps(row(["a"], 2, 0)) + "\n\nnot json\n[1]\n"
    doc = json.loads(run(text).stdout)
    assert doc["sessions"] == 1
    assert doc["caveats"]["bad_input_lines"] == 2


def test_empty_input_gives_zero_share():
    doc = json.loads(run("").stdout)
    assert doc["caveats"]["ambiguous_share"] == 0.0
    assert doc["efforts"] == {}


def test_report_path_argument_is_read(tmp_path):
    p = tmp_path / "r.jsonl"
    p.write_text(json.dumps(row(["a"], 1, 0)) + "\n")
    proc = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
    assert json.loads(proc.stdout)["sessions"] == 1


def test_cost_coverage_counts_sessions_with_and_without_cost():
    no_cost = {**row(["a"], 1, 0), "cost_usd": None}
    text = "\n".join(json.dumps(r) for r in [row(["a"], 1, 0), no_cost, no_cost]) + "\n"
    doc = json.loads(run(text).stdout)
    assert doc["caveats"]["sessions_with_cost"] == 1
    assert doc["caveats"]["sessions_without_cost"] == 2
    assert "lower bound" in doc["caveats"]["cost_note"]
