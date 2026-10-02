"""Find the adaptive-artifacts store and runtime binary for a directory."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

DASHBOARD_VIEW = "project:dashboard"


@dataclass(frozen=True)
class Target:
    root: Path
    store: Path | None
    contract: Path | None

    def home_store(self) -> Path:
        return Path.home() / ".artifacts" / self.root.name

    def repo_store(self) -> Path:
        return self.root / ".artifacts"

    def has_view(self, view_id: str) -> bool:
        if self.contract is None:
            return False
        try:
            views = json.loads(self.contract.read_text()).get("views") or []
        except (OSError, ValueError, AttributeError):
            return False
        return any(isinstance(view, dict) and view.get("id") == view_id for view in views)

    def cli_args(self) -> list[str]:
        return ["--root", str(self.root), "--store", str(self.store), "--contract", str(self.contract)]


def project_root(directory: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return directory.resolve()


def _contract_path(store: Path) -> Path | None:
    try:
        ref = json.loads((store / "meta.json").read_text()).get("contract")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(ref, str) or not ref:
        return None
    path = Path(ref)
    if path.is_absolute():
        return path if path.is_file() else None
    # The runtime resolves a relative ref against the store's parent; flat stores keep it inside the store.
    for candidate in (store.parent / path, store / path):
        if candidate.is_file():
            return candidate.resolve()
    return None


def resolve(directory: Path) -> Target:
    root = project_root(directory)
    for store in (Path.home() / ".artifacts" / root.name, root / ".artifacts"):
        if (store / "meta.json").is_file():
            return Target(root, store, _contract_path(store))
    return Target(root, None, None)


def binary() -> str:
    override = os.environ.get("ADAPTIVE_ARTIFACTS_BIN")
    if override:
        return override
    checkout = Path.home() / "adaptive-artifacts" / "bin" / "adaptive-artifacts"
    if os.access(checkout, os.X_OK):
        return str(checkout)
    return shutil.which("adaptive-artifacts") or "adaptive-artifacts"
