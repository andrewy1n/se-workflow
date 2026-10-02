#!/usr/bin/env bash
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
launcher="$dir/dashboard/bin/dashboard"

option() {
  local value
  value="$(tmux show-option -gqv "$1")"
  printf '%s' "${value:-$2}"
}

popup_key="$(option @dashboard-popup-key A)"
pane_key="$(option @dashboard-pane-key S)"

tmux bind-key "$popup_key" display-popup -E -w 80% -h 80% -d '#{pane_current_path}' "\"$launcher\""
tmux bind-key "$pane_key" split-window -h -l 40% -c '#{pane_current_path}' "\"$launcher\""
