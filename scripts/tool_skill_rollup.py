def tool_skill_rollup(rows):
    tools = {}
    skills = {}
    for row in rows:
        if "error" in row:
            continue
        for name, stats in ((row.get("tools") or {}).get("tools") or {}).items():
            calls = stats.get("calls", 0)
            if calls <= 0:
                continue
            agg = tools.setdefault(name, {"calls": 0, "errors": 0, "retries": 0, "sessions": 0})
            agg["calls"] += calls
            agg["errors"] += stats.get("errors", 0)
            agg["retries"] += stats.get("retries", 0)
            agg["sessions"] += 1
        for name, count in (row.get("skills") or {}).items():
            if count <= 0:
                continue
            agg = skills.setdefault(name, {"invocations": 0, "sessions": 0})
            agg["invocations"] += count
            agg["sessions"] += 1
    tool_rows = [
        {
            "name": name,
            "calls": a["calls"],
            "errors": a["errors"],
            "error_rate": round(a["errors"] / a["calls"], 4) if a["calls"] else 0.0,
            "retries": a["retries"],
            "sessions": a["sessions"],
        }
        for name, a in tools.items()
    ]
    skill_rows = [{"name": name, **a} for name, a in skills.items()]
    tool_rows.sort(key=lambda r: (-r["calls"], r["name"]))
    skill_rows.sort(key=lambda r: (-r["invocations"], r["name"]))
    return {"tools": tool_rows, "skills": skill_rows}
