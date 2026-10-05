"""plan-phase records size and estimate_minutes on every new work-item."""

from __future__ import annotations

import re

from conftest import REPO_ROOT
from skill_extraction import extract_invocations

SKILL = REPO_ROOT / "skills" / "plan-phase" / "SKILL.md"
SIZES = {"XS", "S", "M", "L", "XL"}


def _text() -> str:
    return SKILL.read_text()


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _work_item_payloads(text: str) -> list[dict]:
    payloads = []
    for inv in extract_invocations(text):
        if inv["type"] == "project:work-item" and inv["payload"]:
            payloads.append(inv["payload"])
        for part in inv["records"] or []:
            if part.get("type") == "project:work-item":
                payloads.append(part["payload"])
    return payloads


def test_write_size_and_estimate_minutes_on_every_work_item():
    raw = _text()
    text = _flat(raw)
    payloads = _work_item_payloads(raw)
    assert payloads
    for payload in payloads:
        assert payload["size"] in SIZES
        minutes = payload["estimate_minutes"]
        assert type(minutes) is int
        assert minutes >= 0
    assert "Every new work-item payload includes `size` and `estimate_minutes`." in text
    assert "`XS` a trivial or local change" in text
    assert "`S` a small change" in text
    assert "`M` a moderate change" in text
    assert "`L` a substantial or multi-file change" in text
    assert "`XL` a large or high-risk change" in text
    assert (
        "`estimate_minutes` is a non-negative integer for that task's executor."
        in text
    )
    assert "Absent means unset." in text
    assert "Zero is a real estimate." in text
    assert "A missing executor means the minutes are for a subagent." in text


def test_rollup_adds_inline_minutes_and_takes_the_subagent_wave_maximum():
    text = _flat(_text())
    assert "Inline minutes in a wave add." in text
    assert (
        "A subagent wave's elapsed estimate is the longest `estimate_minutes` among its tasks."
        in text
    )
    assert "Phase elapsed time adds those wave figures in wave order." in text
    assert "Blank estimates are skipped." in text
    assert "A wave whose estimates are all blank has no elapsed estimate." in text


def test_sitting_shape_stays_and_the_phase_record_stores_neither_field():
    text = _flat(_text())
    assert "size as `one sitting` or `more than one`" in text
    assert (
        "The phase body still records session shape as `one sitting` or `more than one`."
        in text
    )
    assert "`size` and `estimate_minutes` are not derived from each other." in text
    assert "The phase record stores neither field." in text
