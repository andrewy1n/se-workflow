"""Pilot tests for the requirement detail screen."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import sys
import time

import pytest

pytest.importorskip("textual")

import helpers as h  # noqa: E402
from conftest import REPO_ROOT, stamped_store  # noqa: E402

sys.path.insert(0, str(REPO_ROOT))
from dashboard import artifact_store  # noqa: E402
from dashboard import app as app_module  # noqa: E402
from dashboard import model as model_module  # noqa: E402
from dashboard import requirement_detail as requirement_module  # noqa: E402
from dashboard import task_detail as detail_module  # noqa: E402

WIDTHS = (60, 120)
PHASE = "evidence-view"
EFFORT = "alpha"
R1_TEXT = (
    "The dashboard shows the requirement text from the specification, "
    "including a sentence long enough to wrap inside a sixty-column pane."
)


def _record(cli, defs, record_type: str, subject: str, payload: dict, body: str | None = None) -> dict:
    args = ["create", "--type", record_type, "--subject", subject, "--payload", json.dumps(payload)]
    body = body if body is not None else h.generic_body(defs[record_type])
    if body:
        args.extend(["--body", body])
    result = cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _body(defs, record_type: str, fills: dict | None = None) -> str | None:
    required = defs[record_type].get("required_sections") or []
    if not required:
        return None
    fills = fills or {}
    return "\n\n".join(f"## {name}\n\n{fills.get(name, 'placeholder.')}" for name in required)


def _phase(cli, defs, subject: str, ordinal: int, *states: str) -> None:
    record = h.create_generic_record(
        cli, defs, "project:phase", subject=subject,
        extra_payload={"title": f"Phase {subject}", "ordinal": ordinal, "effort": EFFORT},
    )
    h.transition(cli, "project:phase", record, *states)


def _supersede(cli, defs, record_type: str, record: dict, payload: dict) -> dict:
    merged = {**record["payload"], **payload}
    args = [
        "supersede", "--type", record_type, "--id", record["id"],
        "--expected-revision", record["revision"], "--payload", json.dumps(merged),
    ]
    body = h.generic_body(defs[record_type])
    if body:
        args.extend(["--body", body])
    result = cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)["record"]


def _seed(cli, defs):
    h.create_generic_record(
        cli, defs, "project:active-goal", subject=EFFORT,
        extra_payload={"goal": "ship the requirement screen", "kind": "deliver"},
    )
    _phase(cli, defs, PHASE, 1, "in_progress")
    _record(cli, defs, "project:specification", PHASE, {
        "weight": "full", "phase": PHASE, "effort": EFFORT, "requirements": "R1, R2",
    }, _body(defs, "project:specification", {
        "Requirements": f"R1: {R1_TEXT}\nR2: An unassessed requirement keeps its latest check.",
        "Non-goals": "no second product",
    }))
    _record(cli, defs, "project:decision", "evidence-under-phase", {
        "choice": "live under the phase", "alternatives": "a separate effort",
        "phase": PHASE, "effort": EFFORT,
    })
    _record(cli, defs, "project:decision", "unassessed-requirement-status", {
        "choice": "dim the latest check", "alternatives": "hide the row",
        "phase": PHASE, "effort": EFFORT,
    })
    traced = _record(cli, defs, "project:work-item", "trace-r1", {
        "title": "Requirement detail screen", "phase": PHASE, "kind": "deliver", "assignee": "",
        "effort": EFFORT, "requirements": "R1",
        "decisions": "evidence-under-phase, unassessed-requirement-status",
    })
    other = _record(cli, defs, "project:work-item", "trace-r2", {
        "title": "Unassessed requirement", "phase": PHASE, "kind": "deliver", "assignee": "",
        "effort": EFFORT, "requirements": "R2", "decisions": "unassessed-requirement-status",
    })
    _record(cli, defs, "project:work-item", "trace-other", {
        "title": "Not this requirement", "phase": PHASE, "kind": "deliver", "assignee": "",
        "effort": EFFORT, "requirements": "R9",
    })
    acceptance = _record(cli, defs, "project:acceptance", "r1-pilot", {
        "criterion": "pilot shows the requirement", "method": "check", "phase": PHASE,
        "effort": EFFORT, "verify_command": "pytest -q", "requirement": "R1",
    })
    quiet = _record(cli, defs, "project:acceptance", "r2-check", {
        "criterion": "unassessed check stays visible", "method": "check", "phase": PHASE,
        "effort": EFFORT, "verify_command": "true", "requirement": "R2",
    })
    _record(cli, defs, "project:check-run", "r1-pass", {
        "criterion_id": acceptance["id"], "revision": "dirty", "result": "pass", "effort": EFFORT,
        "method": "check", "signed_by": "ayin", "requirement": "R1", "evidence_kind": "unit",
    })
    _record(cli, defs, "project:check-run", "r2-fail", {
        "criterion_id": quiet["id"], "revision": "dirty", "result": "fail", "effort": EFFORT,
        "method": "check", "signed_by": "ayin", "requirement": "R2", "evidence_kind": "unit",
    })
    first = _record(cli, defs, "project:assessment", f"{PHASE}-R1", {
        "requirement": "R1", "phase": PHASE, "effort": EFFORT, "missing": "",
        "confidence": "low", "status": "failed", "next": "execute", "level": "implementation",
    })
    active = _supersede(cli, defs, "project:assessment", first, {
        "status": "verified", "level": "verification", "next": "release", "confidence": "high",
    })
    return {
        "task": traced["id"], "other": other["id"], "acceptance": acceptance["id"],
        "first": first["id"], "active": active["id"],
    }


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


@pytest.fixture()
def seeded(store):
    return store, stamped_store(store, "requirement-screen", lambda root, cli, defs: _seed(cli, defs))


def _text(screen, selector):
    return str(screen.query_one(selector).render())


async def _until(pilot, condition, timeout=30.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        await pilot.pause(0.02)


def _run(store, width, scenario, interval=60.0, height=40):
    async def go():
        app = app_module.DashboardApp(artifact_store.resolve(store), interval=interval)
        async with app.run_test(size=(width, height)) as pilot:
            app.push_screen(requirement_module.RequirementDetailScreen(
                app.target, EFFORT, PHASE, "R1",
            ))
            await _until(pilot, lambda: isinstance(app.screen, requirement_module.RequirementDetailScreen) and app.screen.loaded)
            await app.workers.wait_for_complete()
            await scenario(app, pilot)

    asyncio.run(go())


def _acceptance_rows(screen):
    return [
        f"{row.query_one('.mark').render()} {row.query_one('.body').render()}"
        for row in screen.query(".acceptance") if row.query(".mark") and row.query(".body")
    ]


def _history_lines(screen):
    return [line.strip() for line in _text(screen, "#requirement-history").splitlines() if line.strip()]


def _visual_lines(widget):
    return [widget.render_line(y).text.rstrip() for y in range(widget.size.height)]


def _assert_fits(screen):
    for widget in list(screen.query("Static")) + list(screen.query("OptionList")):
        if not widget.display or widget.size.width <= 0 or widget.size.height <= 0:
            continue
        for line in _visual_lines(widget):
            assert len(line) <= widget.size.width, line


@pytest.mark.parametrize("width", WIDTHS)
def test_requirement_screen_shows_text_status_decisions_tasks_acceptances_and_history(seeded, width):
    store, seeded_ids = seeded

    async def scenario(app, pilot):
        screen = app.screen
        assert R1_TEXT in _text(screen, "#requirement-text")
        chips = _text(screen, "#detail-chips")
        assert "R1" in chips and "verified" in chips and "release" in chips and f"phase {PHASE}" in chips
        decisions = _text(screen, "#requirement-decisions")
        assert "evidence-under-phase: live under the phase" in decisions
        assert "unassessed-requirement-status: dim the latest check" in decisions
        links = screen.query_one("#detail-links")
        prompts = [str(links.get_option_at_index(index).prompt) for index in range(links.option_count)]
        assert prompts == ["● trace-r1  Requirement detail screen"]
        assert seeded_ids["other"] not in " ".join(prompts)
        rows = _acceptance_rows(screen)
        assert rows == ["✓ pilot shows the requirement\npass · unit"]
        assert _history_lines(screen) == [
            "failed · implementation · execute · low",
            "verified · verification · release · high",
        ]
        _assert_fits(screen)
        assert all(key.region.right <= width for key in screen.query("FooterKey"))

    _run(store, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_unassessed_requirement_shows_unassessed_with_the_latest_check_dimmed(seeded, width):
    store, _ = seeded

    async def scenario(app, pilot):
        app.push_screen(requirement_module.RequirementDetailScreen(app.target, EFFORT, PHASE, "R2"))
        await _until(pilot, lambda: isinstance(app.screen, requirement_module.RequirementDetailScreen) and app.screen.requirement == "R2" and app.screen.loaded)
        screen = app.screen
        chips = screen.query_one("#detail-chips").render()
        assert "unassessed" in chips.plain and "fail" in chips.plain
        start = chips.plain.index("fail")
        covering = [span for span in chips.spans if span.start <= start < span.end]
        assert covering and ("dim" in str(covering[-1].style))
        assert "An unassessed requirement keeps its latest check." in _text(screen, "#requirement-text")
        assert "unassessed-requirement-status: dim the latest check" in _text(screen, "#requirement-decisions")
        assert not screen.query_one("#requirement-history").display
        assert _acceptance_rows(screen) == ["✗ unassessed check stays visible\nfail · unit"]
        _assert_fits(screen)

    _run(store, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_enter_on_a_traced_task_opens_its_detail_and_escape_returns(seeded, width):
    store, seeded_ids = seeded

    async def scenario(app, pilot):
        requirement = app.screen
        dashboard = app.screen_stack[0]
        links = requirement.query_one("#detail-links")
        links.focus()
        await pilot.press("enter")
        await _until(
            pilot,
            lambda: type(app.screen) is detail_module.TaskDetailScreen and app.screen.loaded,
        )
        opened = app.screen
        assert opened.task_id == seeded_ids["task"]
        assert opened.detail.subject == "trace-r1"
        assert len(app.screen_stack) == 3
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is requirement)
        assert len(app.screen_stack) == 2
        assert R1_TEXT in _text(app.screen, "#requirement-text")
        await pilot.press("escape")
        await _until(pilot, lambda: app.screen is dashboard)
        assert len(app.screen_stack) == 1

    _run(store, width, scenario)


@pytest.mark.parametrize("width", WIDTHS)
def test_requirement_screen_redraws_when_the_store_changes(seeded, cli, defs, width):
    store, seeded_ids = seeded

    async def scenario(app, pilot):
        screen = app.screen
        assert "pass · unit" in "\n".join(_acceptance_rows(screen))
        _record(cli, defs, "project:check-run", "r1-fail", {
            "criterion_id": seeded_ids["acceptance"], "revision": "dirty", "result": "fail", "effort": EFFORT,
            "method": "check", "signed_by": "ayin", "requirement": "R1", "evidence_kind": "integration",
        })
        await _until(pilot, lambda: _acceptance_rows(screen) == ["✗ pilot shows the requirement\nfail · integration"])

    _run(store, width, scenario, interval=0.3)
