"""Founder Dashboard (Phase 2): read model and next-action ranking over the Phase 1 tables.

Deterministic (no LLM) and read-only. Writes go through the Phase 1 API (core/founder.py).
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from core import budget

# ---------------------------------------------------------------- ranking ----

PRIORITY_STEP = 6          # points per priority rank above the lowest (rank 1 of 4 = +18)
URGENCY = ((0, 30), (1, 25), (3, 20), (7, 12))  # (days until due <=, points); overdue also 30
IMPACT_POINTS = 5          # per impact level 1..5 (unknown = 0, never guessed)
IN_PROGRESS_BONUS = 8
UNBLOCK_POINTS, UNBLOCK_CAP = 4, 12
GOAL_BONUS = 3
TASK_PRIORITY_STEP = 3  # work_tasks.priority 1..5 (1 = most important); 3 is the neutral default
CLOSED = ("done", "cancelled")


def _days_until(due: str | None, today: date):
    if not due:
        return None
    try:
        return (date.fromisoformat(due[:10]) - today).days
    except ValueError:
        return None


def rank_tasks(tasks: list[dict], businesses: dict, today: date) -> list[dict]:
    """Annotate open tasks with score, reasons, blocked flag and data gaps; sorted best-first.

    `businesses` maps id -> {"priority": int}. Blocked tasks are scored (so the founder can see
    them) but flagged `eligible=False`; they are never the recommendation.
    """
    by_id = {t["id"]: t for t in tasks}
    unblocks: dict[str, int] = {}
    for t in tasks:
        if t["status"] not in CLOSED and t.get("depends_on"):
            unblocks[t["depends_on"]] = unblocks.get(t["depends_on"], 0) + 1
    lowest = max([v["priority"] for v in businesses.values()] or [1])
    out = []
    for t in tasks:
        if t["status"] in CLOSED:
            continue
        v = businesses.get(t["business_id"], {"priority": lowest})
        score, why, gaps, blocked_by = 0.0, [], [], []
        p = max(0, lowest - v["priority"] + 1) * PRIORITY_STEP - PRIORITY_STEP
        score += p
        if v["priority"] == 1:
            why.append("belongs to your priority-1 business")
        d = _days_until(t.get("due_date"), today)
        if d is None:
            gaps.append("no due date")
        else:
            pts = 30 if d < 0 else next((pt for lim, pt in URGENCY if d <= lim), 4)
            score += pts
            why.append(f"overdue by {-d} day(s)" if d < 0 else "due today" if d == 0 else f"due in {d} day(s)")
        tp = t.get("priority")
        if tp and tp != 3:
            score += (3 - tp) * TASK_PRIORITY_STEP
            why.append(f"you set its priority to {tp}/5")
        if t.get("impact"):
            score += t["impact"] * IMPACT_POINTS
            why.append(f"impact {t['impact']}/5")
        else:
            gaps.append("no impact estimate")
        e = t.get("effort_hours")
        if e is None:
            gaps.append("no effort estimate")
        elif e <= 1:
            score += 6; why.append("quick win (<=1h)")
        elif e <= 4:
            score += 3; why.append(f"~{e:g}h of effort")
        elif e > 8:
            score -= 3; why.append(f"large (~{e:g}h)")
        if t["status"] == "doing":
            score += IN_PROGRESS_BONUS; why.append("already in progress")
        n = unblocks.get(t["id"], 0)
        if n:
            score += min(UNBLOCK_CAP, n * UNBLOCK_POINTS); why.append(f"unblocks {n} other task(s)")
        if t.get("goal_id") and t.get("goal_title"):
            score += GOAL_BONUS; why.append(f"serves goal: {t['goal_title']}")
        if t["status"] == "blocked":
            blocked_by.append("marked blocked")
        dep = by_id.get(t.get("depends_on")) if t.get("depends_on") else None
        if dep and dep["status"] not in CLOSED:
            blocked_by.append(f"waiting on task: {dep['title']}")
        if t.get("open_blockers"):
            blocked_by.append(f"{t['open_blockers']} open blocker(s)")
        out.append({**t, "score": round(score, 1), "why": why, "gaps": gaps, "blocked_by": blocked_by,
                    "eligible": not blocked_by, "days_until_due": d, "business_priority": v["priority"]})
    out.sort(key=lambda r: (not r["eligible"], -r["score"], r["business_priority"], r.get("due_date") or "9999", r["created_at"], r["id"]))
    return out


def recommend(ranked: list[dict], open_blockers: list[dict], businesses: dict) -> dict:
    """The single 'what next' suggestion, with its reasoning, or an honest list of what is missing."""
    eligible = [r for r in ranked if r["eligible"]]
    if eligible:
        top = eligible[0]
        risks = list(top["blocked_by"]) + [f"missing: {g}" for g in top["gaps"]]
        top_priority = min((v["priority"] for v in businesses.values()), default=1)
        if top["business_priority"] > top_priority and top["days_until_due"] is not None and top["days_until_due"] <= 1:
            risks.append("lower-priority business chosen because of its deadline")
        evidence = "high" if not top["gaps"] else "medium" if len(top["gaps"]) == 1 else "low"
        return {
            "task_id": top["id"], "business_id": top["business_id"], "business": top.get("business_name"),
            "action": top["title"], "why": top["why"] or ["highest score among open tasks (little data recorded)"],
            "expected_outcome": top.get("expected_outcome") or "not recorded", "effort_hours": top.get("effort_hours"),
            "risks": risks, "next_step": top.get("next_step") or "Open the task and start it (no next step recorded).",
            "score": top["score"], "evidence": evidence,
            "alternatives": [{"task_id": r["id"], "title": r["title"], "business": r.get("business_name"), "score": r["score"]} for r in eligible[1:4]],
        }
    if open_blockers:
        b = open_blockers[0]
        return {"task_id": b.get("task_id"), "business_id": b["business_id"], "business": b.get("business_name"),
                "action": "Resolve recorded blocker: " + b["description"], "why": ["every open task is blocked; the oldest recorded blocker is the way out"],
                "expected_outcome": b.get("impact") or "not recorded", "effort_hours": None, "risks": [], "evidence": "medium",
                "next_step": b.get("suggested_action") or "Decide what unblocks this and record it.", "score": None, "alternatives": []}
    missing = ["No open tasks are recorded for any business."] if not ranked else ["Every open task is blocked, and no blocker is recorded explaining why."]
    return {"action": None, "missing": missing, "hint": "Add a task (with an impact, due date and effort if you know them) so a recommendation can be made."}


def kpi_view(k: dict, readings: list[dict]) -> dict:
    """Current value, trend vs the previous reading, and progress only where it is meaningful."""
    cur = readings[-1] if readings else ({"value": k["current_value"], "recorded_at": k.get("updated_at")} if k.get("current_value") is not None else None)
    prev = readings[-2] if len(readings) > 1 else None
    out = {**k, "current": cur["value"] if cur else None, "last_updated": cur["recorded_at"] if cur else None,
           "trend": None, "progress_pct": None, "n_readings": len(readings)}
    if cur and prev:
        delta = cur["value"] - prev["value"]
        out["trend"] = {"delta": delta, "direction": "flat" if delta == 0 else "up" if delta > 0 else "down",
                        "good": None if delta == 0 else (delta > 0) == (k["direction"] == "up"), "since": prev["recorded_at"]}
    b, t = k.get("baseline_value"), k.get("target_value")
    if cur and b is not None and t is not None and t != b:  # zero baseline is fine; zero span is not
        out["progress_pct"] = round(max(0.0, min(100.0, (cur["value"] - b) / (t - b) * 100)), 1)
    return out


# ------------------------------------------------------------- read model ----

def _num(v):
    return float(v) if isinstance(v, Decimal) else v


def _rows(conn, sql, params=()):
    return [{k: _num(v) for k, v in dict(r).items()} for r in conn.execute(sql, params).fetchall()]


def _section(fn, *a):
    """One failing section must not take the dashboard down: report it, never fake success."""
    try:
        return fn(*a)
    except Exception:
        return {"error": "This section could not be loaded."}


OPEN = "status NOT IN ('done','cancelled')"
LIVE_BIZ = "(SELECT id FROM businesses WHERE status<>'archived')"


def dashboard(conn, today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    out: dict = {"today": today.isoformat()}
    businesses = _section(lambda: _rows(conn, "SELECT id,slug,name,priority,stage,status,description FROM businesses WHERE status<>'archived' "
                                              "ORDER BY priority NULLS LAST, name"))
    out["businesses"] = businesses
    bmap = {b["id"]: b for b in businesses} if isinstance(businesses, list) else {}
    for b in bmap.values():
        b["priority"] = b["priority"] if b["priority"] is not None else len(bmap) + 1  # unranked sorts last
    bname = {k: v["name"] for k, v in bmap.items()}

    def tasks_section():
        rows = _rows(conn, "SELECT t.*, g.title AS goal_title, (SELECT count(*) FROM blockers k WHERE k.work_task_id=t.id AND k.status='open') AS open_blockers "
                           f"FROM work_tasks t LEFT JOIN goals g ON g.id=t.goal_id WHERE t.business_id IN {LIVE_BIZ} "
                           "AND (t.status NOT IN ('done','cancelled') OR (t.status='done' AND t.completed_at >= ?))", (today.isoformat(),))
        for r in rows:
            r["business_name"] = bname.get(r["business_id"])
            r["business_slug"] = bmap.get(r["business_id"], {}).get("slug")
        return rows

    tasks = _section(tasks_section)
    ok_tasks = isinstance(tasks, list)
    ranked = rank_tasks([t for t in tasks if t["status"] != "done"], bmap, today) if ok_tasks else []
    out["priorities"] = ranked if ok_tasks else tasks
    out["done_today"] = [{"id": t["id"], "title": t["title"], "business_name": t["business_name"]} for t in tasks if t["status"] == "done"] if ok_tasks else []

    def blockers_section():
        rows = _rows(conn, "SELECT k.*, t.title AS task_title FROM blockers k LEFT JOIN work_tasks t ON t.id=k.work_task_id "
                           f"WHERE k.status='open' AND k.business_id IN {LIVE_BIZ} ORDER BY k.created_at")
        for r in rows:
            r["business_name"] = bname.get(r["business_id"])
            r["task_id"] = r["work_task_id"]
            r["kind"] = "recorded"
            try:
                r["days_open"] = max(0, (today - date.fromisoformat(r["created_at"][:10])).days)
            except ValueError:
                r["days_open"] = None
        return rows

    blockers = _section(blockers_section)
    out["blockers"] = blockers
    inferred = []  # derived from stored tasks and labelled as inferences, never as recorded facts
    for r in ranked:
        base = {"kind": "inferred", "business_id": r["business_id"], "business_name": r.get("business_name"), "task_id": r["id"]}
        if r["days_until_due"] is not None and r["days_until_due"] < 0:
            inferred.append({**base, "description": f"Task '{r['title']}' is overdue by {-r['days_until_due']} day(s)", "days_open": -r["days_until_due"]})
        elif r["blocked_by"] and not r["open_blockers"]:
            inferred.append({**base, "description": f"Task '{r['title']}' is held up: " + "; ".join(r["blocked_by"]), "days_open": None})
    out["inferred_risks"] = inferred

    def kpis_section():
        ks = _rows(conn, "SELECT k.* FROM kpis k WHERE k.business_id IN " + LIVE_BIZ + " ORDER BY k.is_primary DESC, k.created_at")
        rd: dict[str, list] = {}
        for r in _rows(conn, "SELECT kpi_id, value, recorded_at FROM kpi_readings ORDER BY recorded_at, id"):
            rd.setdefault(r["kpi_id"], []).append(r)
        views = [kpi_view(k, rd.get(k["id"], [])) for k in ks]
        for v in views:
            v["business_name"] = bname.get(v["business_id"])
        return views

    kpis = _section(kpis_section)
    out["kpis"] = kpis
    goals = _section(lambda: _rows(conn, f"SELECT id,business_id,title,target_metric,target_value,current_value,due_date,status FROM goals WHERE status='open' AND business_id IN {LIVE_BIZ} ORDER BY created_at"))
    if isinstance(goals, list):
        for g in goals:
            g["business_name"] = bname.get(g["business_id"])
    out["goals"] = goals
    out["experiments"] = _section(lambda: _rows(conn, "SELECT e.*, b.name AS business_name FROM experiments e JOIN businesses b ON b.id=e.business_id "
                                                      "WHERE e.status IN ('proposed','running') AND b.status<>'archived' "
                                                      "ORDER BY (e.review_date IS NULL), e.review_date, e.created_at LIMIT 20"))
    out["decisions"] = _section(lambda: _rows(conn, "SELECT d.*, COALESCE(b.name,'All businesses') AS business_name FROM decisions d "
                                                    "LEFT JOIN businesses b ON b.id=d.business_id ORDER BY COALESCE(d.decided_at, d.created_at) DESC LIMIT 8"))
    out["ai_usage"] = _section(ai_usage, conn, today)

    cards = []
    for b in (businesses if isinstance(businesses, list) else []):
        vt = [r for r in ranked if r["business_id"] == b["id"]]
        nxt = next((r for r in vt if r["eligible"]), None)
        vb = [k for k in blockers if k["business_id"] == b["id"]] if isinstance(blockers, list) else None
        vk = [k for k in kpis if k["business_id"] == b["id"]] if isinstance(kpis, list) else []
        primary = next((k for k in vk if k["is_primary"] and k["current"] is not None), None) or next((k for k in vk if k["current"] is not None), None)
        goal = next((g for g in goals if g["business_id"] == b["id"]), None) if isinstance(goals, list) else None
        cards.append({"id": b["id"], "slug": b["slug"], "name": b["name"], "priority": b["priority"], "stage": b["stage"], "status": b["status"],
                      "description": b["description"], "objective": goal["title"] if goal else None, "primary_kpi": primary,
                      "bottleneck": vb[0] if vb else None, "next_action": {"id": nxt["id"], "title": nxt["title"]} if nxt else None,
                      "open_tasks": len(vt) if ok_tasks else None, "blocked_tasks": sum(1 for r in vt if not r["eligible"]) if ok_tasks else None,
                      "open_blockers": len(vb) if vb is not None else None})
    out["cards"] = cards
    open_b = blockers if isinstance(blockers, list) else []
    out["recommendation"] = recommend(ranked, open_b, bmap) if ok_tasks else {"action": None, "missing": ["Tasks could not be loaded."]}
    out["attention"] = {"overdue": sum(1 for r in ranked if r["days_until_due"] is not None and r["days_until_due"] < 0),
                        "due_today": sum(1 for r in ranked if r["days_until_due"] == 0), "open_blockers": len(open_b)} if ok_tasks else None
    return out


def ai_usage(conn, today: date) -> dict:
    """Real logged rows only, from the two ledgers that exist: `llm_usage` (written by Scout; no business column) and
    `ai_usage` (Phase 1; business-scoped, nothing writes it yet). Requests, tokens and USD stay separate measures."""
    start = datetime(today.year, today.month, 1, tzinfo=timezone.utc).isoformat()
    day = datetime(today.year, today.month, today.day, tzinfo=timezone.utc).isoformat()
    q1 = ("SELECT count(*) AS requests, COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens, "
          "COALESCE(SUM(cost_usd),0) AS cost_usd, count(*) FILTER (WHERE status='FAILED') AS failed FROM llm_usage WHERE at >= ?")
    q2 = ("SELECT count(*) AS requests, COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens, "
          "COALESCE(SUM(cost_usd),0) AS cost_usd, 0 AS failed FROM ai_usage WHERE created_at >= ?")
    sources = []
    for name, q, note in (("Scout (llm_usage)", q1, "RESERVED rows are worst-case holds; FAILED rows keep theirs."), ("Founder OS (ai_usage)", q2, "")):
        m, d = _rows(conn, q, (start,))[0], _rows(conn, q, (day,))[0]
        if m["requests"]:
            sources.append({"name": name, "month": m, "today": d, "note": note})
    if not sources:
        return {"available": False}
    by_business = _rows(conn, "SELECT COALESCE(b.name,'Not assigned') AS business_name, count(*) AS requests, COALESCE(SUM(u.cost_usd),0) AS cost_usd "
                              "FROM ai_usage u LEFT JOIN businesses b ON b.id=u.business_id WHERE u.created_at >= ? GROUP BY 1 ORDER BY 3 DESC", (start,))
    cap = float(budget.monthly_cap())
    return {"available": True, "sources": sources, "by_business": by_business, "monthly_cap_usd": cap or None}
