"""Phase screen pilots: tabs, open keys, content panes, Esc, and pager."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import time
from pathlib import Path

import pytest

pytest.importorskip("textual")

import helpers as h  # noqa: E402
from conftest import REPO_ROOT, stamped_store  # noqa: E402

import sys

sys.path.insert(0, str(REPO_ROOT))
from dashboard import artifact_store  # noqa: E402
from dashboard import app as app_module  # noqa: E402
from dashboard import model as model_module  # noqa: E402
from dashboard import pager  # noqa: E402
from dashboard import phase_screen as phase_module  # noqa: E402
from dashboard import requirement_detail as req_module  # noqa: E402
from dashboard import task_detail as detail_module  # noqa: E402
from test_dashboard_model import (  # noqa: E402
    _decision,
    _record,
    _report,
    _spec,
    _task,
)
from test_dashboard_pager import STUB_PAGER  # noqa: E402

_CLI_CACHE: dict = {}


def _store_digest(store):
    digest = hashlib.sha1()
    for path in sorted(store.rglob("*")):
        if path.is_file():
            digest.update(f"{path.relative_to(store)}\0".encode())
            digest.update(path.read_bytes())
    return digest.digest()


@pytest.fixture(autouse=True)
def _memoized_cli(monkeypatch):
    real = model_module._run

    def run(target, *args):
        key = (args, _store_digest(target.store))
        if key not in _CLI_CACHE:
            _CLI_CACHE[key] = real(target, *args)
        return copy.deepcopy(_CLI_CACHE[key])

    monkeypatch.setattr(model_module, "_run", run)


@pytest.fixture()
def defs(resolved_contract):
    return h.record_defs_by_id(resolved_contract)


def _phase(cli, defs, effort, subject, ordinal, *states):
    record = h.create_generic_record(
        cli, defs, "project:phase", subject=subject,
        extra_payload={"title": f"Phase {subject}", "ordinal": ordinal, "effort": effort},
    )
    h.transition(cli, "project:phase", record, *states)


def _goal(cli, defs, effort="alpha"):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject=effort,
        extra_payload={"goal": f"ship {effort}", "kind": "deliver"},
    )


STRUCTURED_SPEC = """## Non-goals

Keep it small.

## Requirements

R1: first holds
R2: second holds

## Acceptance criteria

ok

## Constraints

ok

## Invariants

ok

## Assumptions

ok
"""

STRUCTURED_DESIGN = """## Architecture

Use panes.

## Interfaces

- PhaseScreen

## Decisions

phase-screen-tabs

## Invariants

ok

## Assumptions

ok

## Tradeoffs

ok

## Risks

ok
"""


def _seed_structured(cli, defs):
    _goal(cli, defs)
    _phase(cli, defs, "alpha", "one", 1, "in_progress", "done")
    done = _task(cli, defs, "one-task", "one", "R1", done=True)
    assert done["lifecycle_state"] == "done"
    _phase(cli, defs, "alpha", "focus", 2, "in_progress")
    _spec(cli, defs, "focus", "R1, R2", weight="full", body=STRUCTURED_SPEC, non_goals="Keep it small.")
    _record(cli, defs, "project:design", "focus", {
        "phase": "focus", "effort": "alpha", "decisions": "use-panes",
    }, STRUCTURED_DESIGN)
    _decision(cli, defs, "use-panes", "focus", "tabbed")
    _task(cli, defs, "focus-a", "focus", "R1")
    _task(cli, defs, "focus-b", "focus", "R2")
    _report(cli, defs, "focus", "pass", "none")
    _phase(cli, defs, "alpha", "next", 3, "in_progress")
    _spec(cli, defs, "next", "R1")
    _task(cli, defs, "next-task", "next", "R1")
    _phase(cli, defs, "alpha", "simple", 4, "in_progress")
    _task(cli, defs, "simple-task", "simple")
    _record(cli, defs, "project:constraint", "simple-limit", {
        "statement": "no network", "applies_to": "simple", "effort": "alpha",
    })
    _record(cli, defs, "project:decision", "simple-choice", {
        "choice": "go left", "alternatives": "right", "effort": "alpha", "phase": "simple",
    })


@pytest.fixture()
def structured(store, cli, defs):
    stamped_store(store, "phase-screen", lambda root, c, d: _seed_structured(c, d))
    return store


async def _until(pilot, condition, timeout=20.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        await pilot.pause(0.02)


async def _ready(app, pilot):
    await _until(pilot, lambda: app.snapshot is not None and bool(app.query("#goal")))
    await app.workers.wait_for_complete()
    await pilot.pause()


async def _phase_shown(app, pilot):
    await _until(
        pilot,
        lambda: isinstance(app.screen, phase_module.PhaseScreen) and app.screen.loaded,
    )
    await pilot.pause(0.2)
    return app.screen


def _tab_ids(screen):
    tabs = screen.query_one("#phase-tabs")
    return [pane.id for pane in tabs.query("TabPane")]


def _run(store, scenario, size=(120, 40), interval=60.0):
    async def go():
        app = app_module.DashboardApp(artifact_store.resolve(store), interval=interval)
        async with app.run_test(size=size) as pilot:
            await _ready(app, pilot)
            await scenario(app, pilot)

    asyncio.run(go())


def test_structured_phase_shows_full_tab_set(structured):
    async def scenario(app, pilot):
        app.select_phase("alpha", "focus")
        await pilot.pause()
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        assert _tab_ids(screen) == list(model_module.TABS)
        assert screen.active_tab() == "overview"

    _run(structured, scenario)


def test_simple_phase_shows_simple_tab_set(structured):
    async def scenario(app, pilot):
        app.select_phase("alpha", "simple")
        await pilot.pause()
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        assert _tab_ids(screen) == list(model_module.SIMPLE_TABS)
        assert "design" not in _tab_ids(screen)
        assert "evidence" not in _tab_ids(screen)

    _run(structured, scenario)


def test_open_p_s_e_from_main_screen_select_tabs(structured):
    async def scenario(app, pilot):
        app.select_phase("alpha", "focus")
        await pilot.pause()
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        assert screen.active_tab() == "overview"
        await pilot.press("escape")
        await _until(pilot, lambda: not isinstance(app.screen, phase_module.PhaseScreen))
        await pilot.press("s")
        screen = await _phase_shown(app, pilot)
        assert screen.active_tab() == "spec"
        await pilot.press("escape")
        await _until(pilot, lambda: not isinstance(app.screen, phase_module.PhaseScreen))
        await pilot.press("e")
        screen = await _phase_shown(app, pilot)
        assert screen.active_tab() == "evidence"

    _run(structured, scenario)


def test_open_e_on_simple_phase_opens_overview(structured):
    async def scenario(app, pilot):
        app.select_phase("alpha", "simple")
        await pilot.pause()
        await pilot.press("e")
        screen = await _phase_shown(app, pilot)
        assert screen.active_tab() == "overview"
        assert "evidence" not in _tab_ids(screen)

    _run(structured, scenario)


def test_letter_and_arrow_keys_switch_tabs(structured):
    async def scenario(app, pilot):
        app.select_phase("alpha", "focus")
        await pilot.pause()
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        await pilot.press("s")
        assert screen.active_tab() == "spec"
        await pilot.press("d")
        assert screen.active_tab() == "decisions"
        await pilot.press("e")
        assert screen.active_tab() == "evidence"
        await pilot.press("t")
        assert screen.active_tab() == "tasks"
        await pilot.press("p")
        assert screen.active_tab() == "overview"
        await pilot.press("right")
        assert screen.active_tab() == "spec"
        await pilot.press("left")
        assert screen.active_tab() == "overview"

    _run(structured, scenario)


def test_spec_renders_markdown_and_requirement_rows_open_detail(structured):
    async def scenario(app, pilot):
        app.select_phase("alpha", "focus")
        await pilot.pause()
        await pilot.press("s")
        screen = await _phase_shown(app, pilot)
        assert screen.active_tab() == "spec"
        source = screen.query_one("#spec-markdown Markdown").source
        assert "Keep it small" in source or "Non-goals" in source
        assert "## Requirements" not in source
        reqs = screen.query_one("#spec-requirements")
        assert reqs.option_count >= 2
        prompt = str(reqs.get_option_at_index(0).prompt)
        assert prompt.startswith("R1")
        assert "first holds" in prompt
        reqs.focus()
        reqs.highlighted = 0
        await pilot.press("enter")
        await _until(
            pilot,
            lambda: isinstance(app.screen, req_module.RequirementDetailScreen) and app.screen.loaded,
        )
        opened = app.screen
        assert (opened.effort, opened.phase, opened.requirement) == ("alpha", "focus", "R1")
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is screen)
        assert screen.active_tab() == "spec"
        assert screen.query_one("#spec-requirements").highlighted == 0

    _run(structured, scenario)


def test_design_renders_full_markdown(structured):
    async def scenario(app, pilot):
        app.select_phase("alpha", "focus")
        await pilot.pause()
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        await pilot.press("right")  # overview -> spec
        await pilot.press("right")  # spec -> design
        await pilot.pause()
        assert screen.active_tab() == "design"
        source = screen.query_one("#design-markdown").source
        assert "Architecture" in source or "Use panes" in source or "PhaseScreen" in source

    _run(structured, scenario)


def test_decision_expand_and_effort_history_toggles(structured, cli, defs):
    from test_dashboard_model import _supersede

    listed = json.loads(
        cli("list", "--type", "project:decision", "--where", "payload.phase=focus", "--full").stdout
    )["records"]
    active = next(r for r in listed if r["subject"] == "use-panes")
    _supersede(cli, defs, "project:decision", active, {"choice": "tabbed-v2"})

    async def scenario(app, pilot):
        app.select_phase("alpha", "focus")
        await pilot.pause()
        await pilot.press("p")
        screen = await _phase_shown(app, pilot)
        await pilot.press("d")
        await _until(pilot, lambda: screen.decision_log is not None)
        listing = screen.query_one("#phase-decisions-list")
        assert listing.option_count >= 1
        listing.focus()
        for index in range(listing.option_count):
            if (listing.get_option_at_index(index).id or "").startswith("dec:"):
                listing.highlighted = index
                break
        await pilot.press("enter")
        await pilot.pause()
        texts = [str(listing.get_option_at_index(i).prompt) for i in range(listing.option_count)]
        assert any("alternatives" in t or "rationale" in t or "counter" in t for t in texts)
        await pilot.press("a")
        await _until(pilot, lambda: screen.decisions_effort and screen.decision_log is not None)
        await pilot.pause(0.3)
        assert screen.decisions_effort
        await pilot.press("h")
        await _until(pilot, lambda: screen.decisions_history and screen.decision_log is not None)
        await pilot.pause(0.3)
        hist = [str(listing.get_option_at_index(i).prompt) for i in range(listing.option_count)]
        assert any("supersedes" in t for t in hist)

    _run(structured, scenario)


def test_evidence_and_task_match_today_and_esc_keeps_tab_row(structured):
    async def scenario(app, pilot):
        app.select_phase("alpha", "focus")
        await pilot.pause()
        await pilot.press("e")
        screen = await _phase_shown(app, pilot)
        assert screen.active_tab() == "evidence"
        reqs = screen.query_one("#phase-requirements")
        assert reqs.option_count >= 1
        assert screen.query_one("#evidence-integration").display
        await pilot.press("t")
        await pilot.pause()
        tasks = screen.query_one("#phase-tasks")
        assert tasks.option_count >= 2
        tasks.focus()
        tasks.highlighted = 1
        await pilot.press("enter")
        await _until(
            pilot,
            lambda: isinstance(app.screen, detail_module.TaskDetailScreen) and app.screen.loaded,
        )
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is screen)
        assert screen.active_tab() == "tasks"
        assert screen.query_one("#phase-tasks").highlighted == 1

    _run(structured, scenario)


def test_bracket_keys_move_to_neighbour_phase_keeping_tab(structured):
    async def scenario(app, pilot):
        app.select_phase("alpha", "focus")
        await pilot.pause()
        await pilot.press("s")
        screen = await _phase_shown(app, pilot)
        assert screen.phase_subject == "focus"
        assert screen.active_tab() == "spec"
        selection_before = app.selections.get("alpha")
        await pilot.press("]")
        await _until(
            pilot,
            lambda: isinstance(app.screen, phase_module.PhaseScreen)
            and app.screen.loaded
            and app.screen.phase_subject == "next",
        )
        nxt = app.screen
        assert nxt.active_tab() == "spec"
        assert app.selections.get("alpha") == selection_before
        await pilot.press("]")
        await _until(
            pilot,
            lambda: isinstance(app.screen, phase_module.PhaseScreen)
            and app.screen.loaded
            and app.screen.phase_subject == "simple",
        )
        simple = app.screen
        # simple lacks design/evidence; keep spec
        assert simple.active_tab() == "spec"
        assert "evidence" not in _tab_ids(simple)

    _run(structured, scenario)


def test_pager_pages_current_tab_and_removes_temp_file(structured, tmp_path, monkeypatch):
    script = tmp_path / "stub-pager"
    script.write_text(STUB_PAGER, encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PAGER", str(script))
    monkeypatch.setattr(pager.shutil, "which", lambda name: None)

    async def scenario(app, pilot):
        app.select_phase("alpha", "focus")
        await pilot.pause()
        await pilot.press("s")
        screen = await _phase_shown(app, pilot)
        # Avoid SuspendNotSupported in headless pilots.
        monkeypatch.setattr(app, "suspend", lambda: __import__("contextlib").nullcontext())
        await pilot.press("o")
        await pilot.pause(0.3)
        out = script.with_suffix(".out")
        assert out.is_file(), "stub pager did not run"
        recorded_path_line, _, contents = out.read_text(encoding="utf-8").partition("\n")
        recorded = Path(recorded_path_line)
        assert recorded.suffix == ".md"
        assert ".artifacts" not in recorded.parts
        assert "first holds" in contents or "Requirements" in contents or "Keep it small" in contents
        assert not recorded.exists()

    _run(structured, scenario)
