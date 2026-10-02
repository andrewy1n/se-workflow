import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from record_join import join


def at(h, m=0):
    return datetime(2026, 1, 1, h, m, tzinfo=timezone.utc)


def session(sid, cwd, start, end):
    return {"session_id": sid, "cwd": cwd, "start": start, "end": end,
            "file": f"{sid}.jsonl", "project": "x"}


def record(rid, store, when):
    return {"id": rid, "record_type": "t", "subject": "s", "effort": None,
            "recorded_at": when, "lifecycle_state": "open", "store": store}


S1 = session("s1", "/w/proj", "2026-01-01T01:00:00Z", "2026-01-01T03:00:00Z")
S2 = session("s2", "/other/proj", "2026-01-01T02:00:00Z", "2026-01-01T04:00:00Z")


def test_five_record_fixture_attaches_and_marks_overlap():
    s2 = session("s2", "/x/proj", "2026-01-01T02:00:00Z", "2026-01-01T04:00:00Z")
    records = [
        record("a", "proj", at(1, 30)),
        record("b", "proj", at(2, 30)),
        record("c", "proj", at(3, 30)),
        record("d", "proj", at(5)),
        record("e", "elsewhere", at(2, 30)),
    ]
    out = join([S1, s2], records)
    assert out["by_session"]["s1"] == {"records": ["a", "b"], "ambiguous": ["b"]}
    assert out["by_session"]["s2"] == {"records": ["b", "c"], "ambiguous": ["b"]}
    assert out["unattached"] == ["d", "e"]


def test_window_edges_are_inclusive():
    out = join([S1], [record("lo", "proj", at(1)), record("hi", "proj", at(3))])
    assert out["by_session"]["s1"]["records"] == ["lo", "hi"]
    assert out["unattached"] == []


def test_session_without_window_gets_nothing_but_stays_listed():
    s = session("s3", "/w/proj", None, "2026-01-01T03:00:00Z")
    out = join([s], [record("a", "proj", at(2))])
    assert out["by_session"]["s3"] == {"records": [], "ambiguous": []}
    assert out["unattached"] == ["a"]


def test_recorded_at_accepts_iso_string():
    out = join([S1], [record("a", "proj", "2026-01-01T02:00:00Z"),
                      record("b", "proj", "2026-01-01T02:00:00+00:00")])
    assert out["by_session"]["s1"]["records"] == ["a", "b"]


def test_output_holds_ids_only():
    r = record("a", "proj", at(2))
    r["body"] = "SECRET"
    assert "SECRET" not in repr(join([S1], [r]))
