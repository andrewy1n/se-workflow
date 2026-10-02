import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import session_report

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "session_report.py"


def write(path, events, extra=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events) + extra)


def build(root):
    write(root / "projA" / "s1.jsonl", [
        {"type": "user", "sessionId": "s1", "timestamp": "2026-01-01T00:00:00Z",
         "message": {"role": "user", "content": "SECRET prompt"}},
        {"type": "assistant", "timestamp": "2026-01-01T00:01:00Z", "message": {"content": [
            {"type": "tool_use", "id": "1", "name": "Bash", "input": {"cmd": "SECRET"}}]}},
        {"type": "user", "timestamp": "2026-01-01T00:01:05Z", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "1", "content": "SECRET", "is_error": True}]}},
    ], extra="not json\n")
    write(root / "projA" / "s2.jsonl", [{"type": "user", "sessionId": "s2"}])
    write(root / "projB" / "s3.jsonl", [{"type": "user", "sessionId": "s3"}])
    write(root / "projB" / "s3" / "subagents" / "agent.jsonl", [{"type": "user"}])
    (root / "projB" / "notes.txt").write_text("x")


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True)


def test_prints_one_json_summary_per_top_level_session(tmp_path):
    build(tmp_path)
    proc = run(tmp_path)
    assert proc.returncode == 0
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    assert sorted(r["file"] for r in rows) == ["s1.jsonl", "s2.jsonl", "s3.jsonl"]
    s1 = next(r for r in rows if r["file"] == "s1.jsonl")
    assert s1["project"] == "projA"
    assert s1["session_id"] == "s1"
    assert s1["turns"] == 1
    assert s1["bad_lines"] == 1
    assert s1["tools"]["tools"]["Bash"]["errors"] == 1


def test_output_holds_no_message_text(tmp_path):
    build(tmp_path)
    assert "SECRET" not in run(tmp_path).stdout


def test_unreadable_file_reports_error_class_and_run_continues(tmp_path):
    build(tmp_path)
    (tmp_path / "projA" / "bad.jsonl").mkdir()
    proc = run(tmp_path)
    assert proc.returncode == 0
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    bad = next(r for r in rows if r["file"] == "bad.jsonl")
    assert bad["error"] == "IsADirectoryError"
    assert len(rows) == 4


def test_missing_projects_dir_prints_nothing_and_exits_zero(tmp_path):
    proc = run(tmp_path / "nope")
    assert proc.returncode == 0
    assert proc.stdout == ""


def build_records(root, cwd):
    write(root / "projA" / "s1.jsonl", [
        {"type": "user", "sessionId": "s1", "cwd": str(cwd),
         "timestamp": "2026-01-01T00:00:00Z"},
        {"type": "user", "timestamp": "2026-01-01T01:00:00Z"},
    ])
    write(root / "projA" / "s2.jsonl", [
        {"type": "user", "sessionId": "s2", "cwd": str(cwd),
         "timestamp": "2026-01-01T00:30:00Z"},
        {"type": "user", "timestamp": "2026-01-01T02:00:00Z"},
    ])
    write(root / "projB" / "s3.jsonl", [
        {"type": "user", "sessionId": "s3", "cwd": "/nowhere/nostore",
         "timestamp": "2026-01-01T00:00:00Z"},
        {"type": "user", "timestamp": "2026-01-01T01:00:00Z"},
    ])


def fake_run(calls):
    def runner(argv):
        calls.append(argv)
        rtype = argv[argv.index("--type") + 1]
        rows = {
            "project:work-item": [
                {"id": "r1", "record_type": rtype, "subject": "task-one",
                 "recorded_at": "2026-01-01T00:10:00Z", "payload": {"effort": "eff-a"}},
                {"id": "r2", "record_type": rtype, "subject": "task-two",
                 "recorded_at": "2026-01-01T00:40:00Z", "payload": {"effort": "eff-b"}},
            ],
            "project:finding": [
                {"id": "r3", "record_type": rtype, "subject": "SECRET-body",
                 "recorded_at": "2026-01-01T01:30:00Z", "payload": {"effort": "eff-a"}},
            ],
        }.get(rtype, [])
        return json.dumps({"records": rows})
    return runner


def run_records(tmp_path, capsys, calls):
    cwd = tmp_path / "stores_src" / "proj"
    cwd.mkdir(parents=True)
    store_root = tmp_path / "artifacts"
    (store_root / "proj").mkdir(parents=True)
    build_records(tmp_path / "projects", cwd)
    code = session_report.main(
        ["--records", str(tmp_path / "projects")],
        run=fake_run(calls), store_root=store_root)
    assert code == 0
    return capsys.readouterr().out


def parse(out):
    return {json.loads(l)["file"]: json.loads(l) for l in out.splitlines()}


def test_records_flag_adds_per_session_counts_by_type(tmp_path, capsys):
    rows = parse(run_records(tmp_path, capsys, []))
    s1 = rows["s1.jsonl"]["records"]
    assert s1 == {"total": 2, "by_type": {"project:work-item": 2},
                  "efforts": ["eff-a", "eff-b"], "tasks": ["task-one", "task-two"],
                  "ambiguous": 1}
    s2 = rows["s2.jsonl"]["records"]
    assert s2["total"] == 2
    assert s2["by_type"] == {"project:work-item": 1, "project:finding": 1}
    assert s2["tasks"] == ["task-two"]
    assert s2["ambiguous"] == 1


def test_session_without_matches_gets_zero_and_empty_collections(tmp_path, capsys):
    rows = parse(run_records(tmp_path, capsys, []))
    assert rows["s3.jsonl"]["records"] == {
        "total": 0, "by_type": {}, "efforts": [], "tasks": [], "ambiguous": 0}


def test_each_cwd_with_a_store_is_queried_once_per_type_and_others_skipped(tmp_path, capsys):
    calls = []
    run_records(tmp_path, capsys, calls)
    roots = {c[c.index("--root") + 1] for c in calls}
    assert roots == {str(tmp_path / "stores_src" / "proj")}
    types = [c[c.index("--type") + 1] for c in calls]
    assert len(types) == len(set(types))


def test_records_output_holds_no_record_text_or_ids(tmp_path, capsys):
    out = run_records(tmp_path, capsys, [])
    assert "SECRET" not in out
    assert '"r1"' not in out


def test_without_flag_output_is_unchanged_and_reader_is_not_called(tmp_path, capsys):
    build(tmp_path)

    def boom(argv):
        raise AssertionError("reader called")

    session_report.main([str(tmp_path)], run=boom)
    out = capsys.readouterr().out
    assert out == run(tmp_path).stdout
    assert all("records" not in json.loads(l) for l in out.splitlines())
