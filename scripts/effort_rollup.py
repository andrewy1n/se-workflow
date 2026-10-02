def effort_rollup(rows):
    out = {}
    for row in rows:
        records = row.get("records")
        if "error" in row or not records:
            continue
        efforts = records.get("efforts") or []
        totals = (row.get("tools") or {}).get("totals") or {}
        cost = row.get("cost_usd") or 0
        exclusive = len(efforts) == 1
        for name in efforts:
            e = out.setdefault(name, {
                "sessions": 0, "exclusive_sessions": 0, "turns": 0, "tool_calls": 0,
                "errors": 0, "retries": 0, "cost_shared": 0.0, "cost_exclusive": 0.0,
            })
            e["sessions"] += 1
            e["turns"] += row.get("turns") or 0
            e["tool_calls"] += totals.get("calls") or 0
            e["errors"] += totals.get("errors") or 0
            e["retries"] += totals.get("retries") or 0
            e["cost_shared"] += cost
            if exclusive:
                e["exclusive_sessions"] += 1
                e["cost_exclusive"] += cost
    return {name: out[name] for name in sorted(out)}
