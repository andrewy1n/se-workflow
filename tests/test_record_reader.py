import json
import sys
from datetime import timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from record_reader import DEFAULT_TYPES, RecordReadError, read_records

BODY = "SECRET BODY TEXT"


def _row(id_, rtype, effort=None):
    payload = {"title": "x", "notes": BODY}
    if effort:
        payload["effort"] = effort
    return {
        "id": id_,
        "record_type": rtype,
        "subject": "rj-record-reader",
        "lifecycle_state": "open",
        "revision": 1,
        "payload": payload,
        "recorded_at": "2026-09-30T12:30:00+00:00",
        "derived": {"ready": True},
        "body_excerpt": BODY,
    }


def _stub(by_type):
    calls = []

    def run(argv):
        calls.append(argv)
        rtype = argv[argv.index("--type") + 1]
        rows = by_type.get(rtype, [])
        return json.dumps({"records": rows, "count": len(rows)})

    run.calls = calls
    return run


def test_yields_metadata_with_utc_times_and_no_body():
    run = _stub({"project:work-item": [_row("wi-1", "project:work-item", "session-analysis")]})
    rows = read_records("/tmp/proj-x", types=["project:work-item"], run=run)
    assert rows == [
        {
            "id": "wi-1",
            "record_type": "project:work-item",
            "subject": "rj-record-reader",
            "effort": "session-analysis",
            "recorded_at": rows[0]["recorded_at"],
            "lifecycle_state": "open",
            "store": "proj-x",
        }
    ]
    assert rows[0]["recorded_at"].utcoffset() == timedelta(0)
    assert rows[0]["recorded_at"].tzinfo == timezone.utc
    assert BODY not in json.dumps(rows, default=str)


def test_effort_is_none_when_payload_has_none():
    run = _stub({"project:finding": [_row("f-1", "project:finding")]})
    assert read_records("/tmp/p", types=["project:finding"], run=run)[0]["effort"] is None


def test_command_is_read_only_list_per_type_with_root():
    run = _stub({})
    read_records("/tmp/p", types=["project:a", "project:b"], run=run)
    assert len(run.calls) == 2
    for argv, t in zip(run.calls, ["project:a", "project:b"]):
        assert "--read-only" in argv
        assert argv[argv.index("--root") + 1] == "/tmp/p"
        assert argv.index("--read-only") < argv.index("list")
        assert argv[argv.index("--type") + 1] == t


def test_store_is_resolved_under_home_artifacts_by_root_basename():
    run = _stub({})
    read_records("/tmp/proj-x", types=["project:a"], run=run)
    argv = run.calls[0]
    assert argv[argv.index("--store") + 1] == str(Path.home() / ".artifacts" / "proj-x")


def test_default_types_cover_project_types():
    run = _stub({})
    read_records("/tmp/p", run=run)
    assert [a[a.index("--type") + 1] for a in run.calls] == list(DEFAULT_TYPES)
    assert "project:work-item" in DEFAULT_TYPES


def test_failure_names_type_not_content():
    def run(argv):
        raise RuntimeError(BODY)

    with pytest.raises(RecordReadError) as err:
        read_records("/tmp/p", types=["project:decision"], run=run)
    assert "project:decision" in str(err.value)
    assert BODY not in str(err.value)


def test_invalid_json_names_type():
    with pytest.raises(RecordReadError, match="project:phase"):
        read_records("/tmp/p", types=["project:phase"], run=lambda argv: "not json")
