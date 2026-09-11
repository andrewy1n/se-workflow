#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: plant.sh [--no-init] <target-repo>" >&2
  exit 1
}

init=1
if [[ "${1:-}" == "--no-init" ]]; then
  init=0
  shift
fi
[[ $# -eq 1 ]] || usage

src="$(cd "$(dirname "$0")/.." && pwd)"
dest="$(cd "$1" && pwd)"

if [[ "$dest" == "$src" ]]; then
  echo "plant.sh: refusing to plant into the se-workflow source repo" >&2
  exit 1
fi

mkdir -p \
  "$dest/.artifacts" \
  "$dest/.cursor/rules" \
  "$dest/.cursor/skills" \
  "$dest/.claude/skills"

cp "$src/.artifacts/project-design.json" "$dest/.artifacts/project-design.json"
cp "$src/templates/artifacts.mdc" "$dest/.cursor/rules/artifacts.mdc"

for skill in se-plan-phase se-execute-phase se-verify-work; do
  rm -rf "$dest/.cursor/skills/$skill" "$dest/.claude/skills/$skill"
  cp -a "$src/skills/$skill" "$dest/.cursor/skills/$skill"
  cp -a "$src/skills/$skill" "$dest/.claude/skills/$skill"
done

section_file="$src/templates/CLAUDE.md"
if [[ -f "$dest/CLAUDE.md" ]] && grep -q "se-workflow contract" "$dest/CLAUDE.md"; then
  :
elif [[ -f "$dest/CLAUDE.md" ]]; then
  printf '\n%s\n' "$(cat "$section_file")" >> "$dest/CLAUDE.md"
else
  cp "$section_file" "$dest/CLAUDE.md"
fi

adaptive-artifacts --root "$dest" resolve

if [[ "$init" -eq 1 ]]; then
  if git -C "$dest" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    adaptive-artifacts --root "$dest" init
  else
    echo "plant.sh: $dest is not a git repo; skipped init (design-only is valid)" >&2
  fi
fi

echo "planted se-workflow into $dest"
