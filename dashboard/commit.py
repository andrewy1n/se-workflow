"""Commit viewer: loads a revision from git and shows it as a screen."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Static

from dashboard import model
from dashboard.display import palette_from


@dataclass(frozen=True)
class Commit:
    sha: str
    author: str
    date: str
    subject: str
    message: str
    stat: list[str]


def latest_revision(events: list[model.TimelineEvent]) -> str | None:
    usable = [e for e in events if e.kind in ("execution-report", "check-run") and e.revision and e.revision != "dirty"]
    return max(usable, key=lambda e: e.recorded_at).revision if usable else None


def load_commit(root: Path, revision: str, width: int = 80) -> Commit | None:
    if revision.startswith("-"):
        return None
    command = ["git", "-C", str(root), "show", f"--stat={max(width, 20)}", "--format=%H%x1f%an%x1f%aI%x1f%s%x1f%b%x1e", revision, "--"]
    try:
        done = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    head, _, stat = done.stdout.partition("\x1e")
    fields = head.split("\x1f")
    if len(fields) != 5:
        return None
    return Commit(*fields[:4], fields[4].strip(), [line for line in stat.splitlines() if line.strip()])


def stat_width(app: App) -> int:
    return app.size.width - 4


def stat_line(line: str, colors: dict[str, str]) -> Text:
    text = Text(no_wrap=True, overflow="ellipsis")
    name, bar, graph = line.partition("|")
    text.append(name + bar)
    for match in re.finditer(r"\++|-+|[^+-]+", graph):
        piece = match.group()
        style = colors["success"] if piece[0] == "+" else colors["error"] if piece[0] == "-" else ""
        text.append(piece, style=style)
    return text


def commit_header(commit: Commit, colors: dict[str, str]) -> Text:
    text = Text()
    for index, (label, value) in enumerate((
        ("commit", commit.sha), ("author", commit.author), ("date", commit.date), ("subject", commit.subject),
    )):
        text.append("\n" if index else "")
        text.append(f"{label:<8}", style=colors["muted"])
        text.append(value)
    return text


class CommitScreen(Screen[None]):
    CSS = """
    #commit-bar { height: 1; padding: 0 1; background: $panel; }
    #commit { padding: 0 1; }
    #commit-header { margin-top: 1; }
    #commit-message { margin-top: 1; }
    #commit-stat { margin-top: 1; height: auto; }
    """
    AUTO_FOCUS = "#commit"
    BINDINGS = [Binding("escape", "back", "back")]

    def __init__(self, commit: Commit, root: Path, revision: str) -> None:
        super().__init__()
        self.commit = commit
        self.root = root
        self.revision = revision
        self.stat_cols = 0
        self.loaded = False

    def compose(self) -> ComposeResult:
        yield Static(id="commit-bar")
        with VerticalScroll(id="commit"):
            yield Static(id="commit-header")
            yield Static(id="commit-message")
            yield Static(id="commit-stat")
        yield Footer()

    def on_mount(self) -> None:
        self.stat_cols = stat_width(self.app)
        self.render_commit()

    def on_resize(self) -> None:
        if self.loaded and stat_width(self.app) != self.stat_cols:
            self.stat_cols = stat_width(self.app)
            self.reload_commit(self.stat_cols)

    @work(thread=True, exclusive=True, group="commit-stat")
    def reload_commit(self, width: int) -> None:
        commit = load_commit(self.root, self.revision, width)
        if commit is not None:
            self.app.call_from_thread(self.show_commit, commit)

    def show_commit(self, commit: Commit) -> None:
        self.commit = commit
        self.render_commit()

    def render_commit(self) -> None:
        colors = palette_from(self.app.get_css_variables())
        commit = self.commit
        bar = Text(no_wrap=True, overflow="ellipsis")
        bar.append(commit.sha[:7], style="bold")
        bar.append(f"  {commit.subject}")
        self.query_one("#commit-bar", Static).update(bar)
        self.query_one("#commit-header", Static).update(commit_header(commit, colors))
        message = self.query_one("#commit-message", Static)
        message.display = bool(commit.message)
        message.update(Text(commit.message))
        stat = self.query_one("#commit-stat", Static)
        stat.display = bool(commit.stat)
        joined = Text(no_wrap=True, overflow="ellipsis")
        for index, line in enumerate(commit.stat):
            joined.append("\n" if index else "")
            joined.append_text(stat_line(line, colors))
        stat.update(joined)
        self.loaded = True

    def action_back(self) -> None:
        self.app.pop_screen()
