def _errors(row):
    return row.get("tools", {}).get("totals", {}).get("errors") or 0


def _retries(row):
    return row.get("tools", {}).get("totals", {}).get("retries") or 0


def _cost(row):
    return round(row.get("cost_usd") or 0, 4)


_METRICS = {"errors": _errors, "retries": _retries, "cost": _cost}


def _entry(row, value):
    return {
        "session_id": row.get("session_id"),
        "file": row.get("file"),
        "project": row.get("project"),
        "branch": row.get("branch"),
        "efforts": list((row.get("records") or {}).get("efforts") or []),
        "value": value,
    }


def outliers(rows, top=5):
    usable = [r for r in rows if "error" not in r]
    result = {}
    for name, getter in _METRICS.items():
        scored = [(getter(r), r) for r in usable]
        scored = [(v, r) for v, r in scored if v]
        scored.sort(key=lambda p: (-p[0], str(p[1].get("session_id"))))
        result[name] = [_entry(r, v) for v, r in scored[:top]]
    return result
