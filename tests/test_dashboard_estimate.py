"""Task detail chips for size, minutes, and executor."""

from __future__ import annotations

import pytest

pytest.importorskip("textual")

import helpers as h  # noqa: E402
from dashboard import task_detail as detail_module  # noqa: E402
from test_dashboard_app import (  # noqa: E402
    _estimate_goal,
    _estimate_task,
    _open_by_enter,
    _open_phase,
    _phase_body,
    _run,
    _shown,
    _text,
    _until,
)

SIZE_TOKENS = {"XS", "S", "M", "L", "XL"}


@pytest.fixture()
def defs(resolved_contract):
    return h.record_defs_by_id(resolved_contract)


def _parts(chips: str) -> list[str]:
    return [part for line in chips.splitlines() for part in line.split(" · ")]


async def _chip_text(app, pilot, task_id: str) -> str:
    await _open_by_enter(app, pilot, task_id)
    screen = await _shown(app, pilot)
    chips = _text(screen, "#detail-chips")
    await pilot.press("escape")
    await _until(pilot, lambda: not isinstance(app.screen, detail_module.TaskDetailScreen))
    return chips


def test_estimate_view_chips(store, cli, defs):
    _estimate_goal(cli, defs)
    _open_phase(cli, defs, "est", 1, "Estimate phase", _phase_body(defs))
    sized = _estimate_task(
        cli, defs, "sized", "est", size="M", estimate_minutes=25, executor="subagent",
    )
    zero = _estimate_task(cli, defs, "zero", "est", estimate_minutes=0, executor="inline")
    blank = _estimate_task(cli, defs, "blank", "est")

    async def scenario(app, pilot):
        await _until(pilot, lambda: app.query("#tasks") and app.query_one("#tasks").row_count >= 4)
        sized_parts = _parts(await _chip_text(app, pilot, sized["id"]))
        assert "M" in sized_parts
        assert "25m" in sized_parts
        assert "executor subagent" in sized_parts

        zero_parts = _parts(await _chip_text(app, pilot, zero["id"]))
        assert "0m" in zero_parts
        assert "executor inline" in zero_parts

        blank_chips = await _chip_text(app, pilot, blank["id"])
        blank_parts = _parts(blank_chips)
        assert "executor subagent" in blank_parts
        assert "0m" not in blank_chips
        assert not (set(blank_parts) & SIZE_TOKENS)

    _run(store, 60, scenario)
