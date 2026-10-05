"""Work-item size and estimate_minutes are optional contract fields."""

from __future__ import annotations

import json

from conftest import REPO_ROOT

SIZE_ENUM = ["XS", "S", "M", "L", "XL"]


def _record(name: str) -> dict:
    design = json.loads((REPO_ROOT / "contract" / "project-design.json").read_text())
    return next(record for record in design["records"] if record["name"] == name)


def _fields(record: dict) -> set[str]:
    return set(record.get("payload") or []) | set(record.get("optional_payload") or [])


def test_work_item_size_enum_is_optional():
    work_item = _record("work-item")
    assert work_item["payload_enum"]["size"] == SIZE_ENUM
    assert "size" in work_item["payload"]
    assert "size" in work_item["optional_payload"]


def test_phase_record_does_not_gain_size():
    phase = _record("phase")
    assert phase["payload"] == ["title", "ordinal", "effort"]
    assert "size" not in _fields(phase)
    assert "size" not in (phase.get("payload_enum") or {})


def test_estimate_minutes_is_optional_and_not_an_enum():
    work_item = _record("work-item")
    assert "estimate_minutes" in work_item["payload"]
    assert "estimate_minutes" in work_item["optional_payload"]
    assert "estimate_minutes" not in (work_item.get("payload_enum") or {})


def test_work_item_has_no_minutes_or_hours_field():
    fields = _fields(_record("work-item"))
    assert "minutes" not in fields
    assert "hours" not in fields


def test_phase_payload_omits_estimate_minutes():
    phase = _record("phase")
    assert "estimate_minutes" not in _fields(phase)
    assert "estimate_minutes" not in (phase.get("payload_enum") or {})
