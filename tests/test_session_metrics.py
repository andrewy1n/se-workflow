import inspect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from session_metrics import ReadStats, read_events  # noqa: E402


def write_lines(tmp_path, lines):
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return path


def test_parse_keeps_valid_events_and_counts_one_malformed_line(tmp_path):
    path = write_lines(tmp_path, [
        json.dumps({"type": "user", "sessionId": "s1"}),
        '{"type": "assistant", broken',
        json.dumps({"type": "never-seen-before", "extra": [1, 2]}),
        json.dumps({"type": "assistant", "future_field": True}),
    ])
    stats = ReadStats()
    events = list(read_events(path, stats))
    assert [e["type"] for e in events] == ["user", "never-seen-before", "assistant"]
    assert stats.bad_lines == 1


def test_parse_counts_non_object_json_as_bad(tmp_path):
    path = write_lines(tmp_path, ["[1, 2]", "42", '"text"', "null", json.dumps({"type": "user"})])
    stats = ReadStats()
    assert len(list(read_events(path, stats))) == 1
    assert stats.bad_lines == 4


def test_parse_skips_blank_lines_without_counting_them(tmp_path):
    path = write_lines(tmp_path, ["", json.dumps({"type": "user"}), "   "])
    stats = ReadStats()
    assert len(list(read_events(path, stats))) == 1
    assert stats.bad_lines == 0


def test_parse_survives_invalid_utf8_bytes(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_bytes(b'{"type": "user"}\n\xff\xfe\n{"type": "system"}\n')
    stats = ReadStats()
    assert len(list(read_events(path, stats))) == 2
    assert stats.bad_lines == 1


def test_parse_reader_is_lazy_generator_that_streams(tmp_path):
    path = write_lines(tmp_path, [json.dumps({"type": "user"}), "not json"])
    stats = ReadStats()
    reader = read_events(path, stats)
    assert inspect.isgenerator(reader)
    assert stats.bad_lines == 0
    assert next(reader) == {"type": "user"}
    assert stats.bad_lines == 0
    assert list(reader) == []
    assert stats.bad_lines == 1


def test_parse_empty_file_yields_nothing(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    stats = ReadStats()
    assert list(read_events(path, stats)) == []
    assert stats.bad_lines == 0
