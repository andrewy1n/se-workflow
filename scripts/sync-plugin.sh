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
  "$DEST/.claude-plugin" \
  "$DEST/.cursor-plugin"

cp -a "$ROOT/skills/." "$DEST/skills/"
cp -a "$ROOT/contract/." "$DEST/contract/"
cp -a "$ROOT/.claude-plugin/." "$DEST/.claude-plugin/"
cp -a "$ROOT/.cursor-plugin/." "$DEST/.cursor-plugin/"
cp -a "$ROOT/README.md" "$DEST/"

printf '%s\n' "$DEST"
