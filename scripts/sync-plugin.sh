#!/usr/bin/env bash
# Payload for Cursor local install and Claude marketplace add.
# Do not sync a live .artifacts/ store.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-${HOME}/.cursor/plugins/local/se-workflow}"

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
mkdir -p \
  "$DEST/skills" \
  "$DEST/contract" \
  "$DEST/scripts" \
  "$DEST/.claude-plugin" \
  "$DEST/.cursor-plugin"

cp -a "$ROOT/skills/." "$DEST/skills/"
cp -a "$ROOT/contract/." "$DEST/contract/"
# Skills invoke these by path, so an install without them is a broken install.
# Copy the directory rather than naming files: a hand-maintained list is how
# close_batch.py came to be missing from every install in the first place.
cp -a "$ROOT/scripts/." "$DEST/scripts/"
rm -f "$DEST/scripts/sync-plugin.sh"
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} +
cp -a "$ROOT/.claude-plugin/." "$DEST/.claude-plugin/"
cp -a "$ROOT/.cursor-plugin/." "$DEST/.cursor-plugin/"
cp -a "$ROOT/README.md" "$DEST/"

printf '%s\n' "$DEST"
