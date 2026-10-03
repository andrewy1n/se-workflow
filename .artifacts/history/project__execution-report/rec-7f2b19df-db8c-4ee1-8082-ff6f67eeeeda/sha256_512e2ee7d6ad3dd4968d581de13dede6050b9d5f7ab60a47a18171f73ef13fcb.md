---
{
  "base_kind": "observation",
  "id": "rec-7f2b19df-db8c-4ee1-8082-ff6f67eeeeda",
  "identity": "unknown",
  "lifecycle_state": "recorded",
  "payload": {
    "assignment": "dashboard-launcher-switch",
    "result": "pass",
    "revision": "3e52964",
    "verdict": "pass",
    "work_item": "dashboard-launcher-switch"
  },
  "provenance": {
    "sources": [
      "dashboard-launcher-switch"
    ]
  },
  "record_type": "project:execution-report",
  "recorded_at": "2026-09-30T19:18:59+00:00",
  "relationships": {},
  "revision": "sha256:512e2ee7d6ad3dd4968d581de13dede6050b9d5f7ab60a47a18171f73ef13fcb",
  "subject": "dashboard-launcher-switch",
  "time": {
    "observed": "2026-09-30T19:18:59+00:00",
    "recorded": "2026-09-30T19:18:59+00:00"
  }
}
---

```
subject: dashboard-launcher-switch
kind: deliver
result: pass
revision: 3e52964
evidence: Tests first, red: 12 failed and 4 passed on the changed launcher and tmux tests. After the launcher change, `python3 -m pytest tests/test_dashboard_launcher.py tests/test_tmux_integration.py -q` gave 16 passed. `tests/test_e2e_dashboard.py` gave 1 passed. `python3 -m pytest tests -q` gave 142 passed, 1 skipped. `uv run --with textual --with pytest python -m pytest tests -q` gave 160 passed. New launcher tests: test_runs_the_app_through_uv_from_the_repo_root, test_passes_extra_args_to_the_app, test_runs_with_a_home_store_and_no_repo_store, test_runs_with_a_repo_store_when_home_dir_has_no_meta, test_does_not_require_the_dashboard_view, test_finds_uv_on_path, test_finds_uv_in_the_home_local_bin, test_prints_install_hint_when_uv_is_missing, test_prints_no_store_message, test_env_bin_reaches_the_app, test_renders_a_seeded_store_once_with_the_textual_app.
verdict: pass
needs_human: false
```

Behaviour: scripts/dashboard execs `uv run --script scripts/dashboard_app.py <argv>` from the repo toplevel; no project:dashboard view check; uv lookup $SE_WORKFLOW_UV, PATH, ~/.local/bin/uv, install hint if missing. README updated. tests/helpers.py Tmux passes UV_CACHE_DIR; tmux and e2e tests wait on app text. Left: DASHBOARD_VIEW/has_view stay for dashboard-status.
