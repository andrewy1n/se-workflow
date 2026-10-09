#!/usr/bin/env bash
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
launcher="$dir/dashboard/bin/dashboard"
status_bin="$dir/dashboard/bin/dashboard-status"

option() {
  local value
  value="$(tmux show-option -gqv "$1")"
  printf '%s' "${value:-$2}"
}

popup_key="$(option @dashboard-popup-key A)"
pane_key="$(option @dashboard-pane-key S)"

tmux bind-key "$popup_key" display-popup -E -w 80% -h 80% -d '#{pane_current_path}' "\"$launcher\""
tmux bind-key "$pane_key" split-window -h -l 40% -c '#{pane_current_path}' "\"$launcher\""

if [ -n "${ADAPTIVE_ARTIFACTS_BIN:-}" ]; then
  tmux set-environment -g ADAPTIVE_ARTIFACTS_BIN "$ADAPTIVE_ARTIFACTS_BIN"
fi

if [ "$(option @dashboard-status-right on)" = "on" ]; then
  segment="#(cd '#{pane_current_path}' && \"$status_bin\" --tmux .)"
  current="$(tmux show-option -gqv status-right)"
  case "$current" in
    *dashboard-status*) ;;
    *)
      if [ -n "$current" ]; then
        tmux set-option -g status-right "$current $segment"
      else
        tmux set-option -g status-right "$segment"
      fi
      ;;
  esac
fi
