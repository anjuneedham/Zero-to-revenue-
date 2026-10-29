"""Founder Dashboard: read model, next-action ranking and the owner's own record-keeping writes.

Everything here is deterministic (no LLM). Writes only create/update the owner's own records
(tasks, goals, KPIs, blockers, experiments, decisions); nothing triggers agents, spending or trading.
"""

import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from core import budget
from core.audit import audit
from core.db import now

# ---------------------------------------------------------------- ranking ----

PRIORITY_STEP = 6          # points per priority rank above the lowest (rank 1 of 4 = +18)
URGENCY = ((0, 30), (1, 25), (3, 20), (7, 12))  # (days until due <=, points); overdue also 30
IMPACT_POINTS = 5          # per impact level 1..5 (unknown = 0, never guessed)
IN_PROGRESS_BONUS = 8
UNBLOCK_POINTS, UNBLOCK_CAP = 4, 12
GOAL_BONUS = 3


def _days_until(due: str | None, today: date):
    if not due:
        return None
    try:
        return (date.fromisoformat(due[:10]) - today).days
    except ValueError:
        return None


def rank_tasks(tasks: list[dict], ventures: dict, today: date) -> list[dict]:
    """Annotate open tasks with score, reasons, blocked flag and data gaps; sorted best-first.

    `ventures` maps id -> {"priority": int}. Blocked tasks are scored (so the founder can see
    them) but flagged `eligible=False`; they are never the recommendation.
    """
    by_id = {t["id"]: t for t in tasks}
    unblocks: dict[str, int] = {}
    for t in tasks:
        if t["status"] != "DONE" and t.get("depends_on"):
            unblocks[t["depends_on"]] = unblocks.get(t["depends_on"], 0) + 1
    lowest = max([v["priority"] for v in ventures.values()] or [1])
    out = []
    for t in tasks:
        if t["status"] == "DONE":
            continue
        v = ventures.get(t["venture_id"], {"priority": lowest})
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
        if t["status"] == "IN_PROGRESS":
            score += IN_PROGRESS_BONUS; why.append("already in progress")
        n = unblocks.get(t["id"], 0)
        if n:
            score += min(UNBLOCK_CAP, n * UNBLOCK_POINTS); why.append(f"unblocks {n} other task(s)")
        if t.get("goal_id") and t.get("goal_title"):
            score += GOAL_BONUS; why.append(f"serves goal: {t['goal_title']}")
        if t["status"] == "BLOCKED":
            blocked_by.append("marked blocked")
        dep = by_id.get(t.get("depends_on")) if t.get("depends_on") else None
        if dep and dep["status"] != "DONE":
            blocked_by.append(f"waiting on task: {dep['title']}")
        if t.get("open_blockers"):
            blocked_by.append(f"{t['open_blockers']} open blocker(s)")
        out.append({**t, "score": round(score, 1), "why": why, "gaps": gaps, "blocked_by": blocked_by,
                    "eligible": not blocked_by, "days_until_due": d, "venture_priority": v["priority"]})
    out.sort(key=lambda r: (not r["eligible"], -r["score"], r["venture_priority"], r.get("due_date") or "9999", r["created_at"], r["id"]))
    return out


def recommend(ranked: list[dict], open_blockers: list[dict], ventures: dict) -> dict:
    """The single 'what next' suggestion, with its reasoning, or an honest list of what is missing."""
    eligible = [r for r in ranked if r["eligible"]]
    if eligible:
        top = eligible[0]
        risks = list(top["blocked_by"]) + [f"missing: {g}" for g in top["gaps"]]
        top_priority = min((v["priority"] for v in ventures.values()), default=1)
        if top["venture_priority"] > top_priority and top["days_until_due"] is not None and top["days_until_due"] <= 1:
            risks.append("lower-priority business chosen because of its deadline")
        evidence = "high" if not top["gaps"] else "medium" if len(top["gaps"]) == 1 else "low"
        return {
            "task_id": top["id"], "venture_id": top["venture_id"], "venture": top.get("venture_name"),
            "action": top["title"], "why": top["why"] or ["highest score among open tasks (little data recorded)"],
            "expected_outcome": top.get("expected_outcome") or "not recorded", "effort_hours": top.get("effort_hours"),
            "risks": risks, "next_step": top.get("next_step") or "Open the task and start it (no next step recorded).",
            "score": top["score"], "evidence": evidence,
            "alternatives": [{"task_id": r["id"], "title": r["title"], "venture": r.get("venture_name"), "score": r["score"]} for r in eligible[1:4]],
        }
    if open_blockers:
        b = open_blockers[0]
        return {"task_id": b.get("task_id"), "venture_id": b["venture_id"], "venture": b.get("venture_name"),
                "action": "Resolve recorded blocker: " + b["description"], "why": ["every open task is blocked; the oldest recorded blocker is the way out"],
                "expected_outcome": b.get("impact") or "not recorded", "effort_hours": None, "risks": [], "evidence": "medium",
                "next_step": b.get("suggested_action") or "Decide what unblocks this and record it.", "score": None, "alternatives": []}
    missing = ["No open tasks are recorded for any business."] if not ranked else ["Every open task is blocked, and no blocker is recorded explaining why."]
    return {"action": None, "missing": missing, "hint": "Add a task (with an impact, due date and effort if you know them) so a recommendation can be made."}


def kpi_view(k: dict, readings: list[dict]) -> dict:
    """Current value, trend vs the previous reading, and progress only where it is meaningful."""
    cur = readings[-1] if readings else None
    prev = readings[-2] if len(readings) > 1 else None
    out = {**k, "current": cur["value"] if cur else None, "last_updated": cur["recorded_at"] if cur else None,
           "trend": None, "progress_pct": None, "n_readings": len(readings)}
    if cur and prev:
        delta = cur["value"] - prev["value"]
        out["trend"] = {"delta": delta, "direction": "flat" if delta == 0 else "up" if delta > 0 else "down",
                        "good": None if delta == 0 else (delta > 0) == k["higher_is_better"], "since": prev["recorded_at"]}
    b, t = k.get("baseline"), k.get("target")
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


def dashboard(conn, today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    out: dict = {"today": today.isoformat()}
    ventures = _section(lambda: _rows(conn, "SELECT id,name,priority,status,objective,description FROM ventures WHERE status<>'ARCHIVED' ORDER BY priority,name"))
    out["ventures"] = ventures
    vmap = {v["id"]: v for v in ventures} if isinstance(ventures, list) else {}
    vname = {k: v["name"] for k, v in vmap.items()}

    def tasks_section():
        rows = _rows(conn, "SELECT t.*, g.title AS goal_title, (SELECT count(*) FROM blockers b WHERE b.task_id=t.id AND b.status='OPEN') AS open_blockers "
                           "FROM founder_tasks t LEFT JOIN goals g ON g.id=t.goal_id WHERE t.venture_id IN (SELECT id FROM ventures WHERE status<>'ARCHIVED') "
                           "AND (t.status<>'DONE' OR t.completed_at >= ?)", ((today.isoformat()),))
        for r in rows:
            r["venture_name"] = vname.get(r["venture_id"])
        return rows

    tasks = _section(tasks_section)
    out["tasks_error"] = tasks.get("error") if isinstance(tasks, dict) else None
    ranked = rank_tasks([t for t in tasks if t["status"] != "DONE"], vmap, today) if isinstance(tasks, list) else []
    done_today = [t for t in tasks if t["status"] == "DONE"] if isinstance(tasks, list) else []
    out["priorities"] = ranked if isinstance(tasks, list) else tasks
    out["done_today"] = [{"id": t["id"], "title": t["title"], "venture_name": t["venture_name"]} for t in done_today]

    def blockers_section():
        rows = _rows(conn, "SELECT b.*, t.title AS task_title FROM blockers b LEFT JOIN founder_tasks t ON t.id=b.task_id "
                           "WHERE b.status='OPEN' AND b.venture_id IN (SELECT id FROM ventures WHERE status<>'ARCHIVED') ORDER BY b.opened_at")
        for r in rows:
            r["venture_name"] = vname.get(r["venture_id"])
            r["kind"] = "recorded"
            try:
                r["days_open"] = max(0, (today - date.fromisoformat(r["opened_at"][:10])).days)
            except ValueError:
                r["days_open"] = None
        return rows

    blockers = _section(blockers_section)
    out["blockers"] = blockers
    # Inferred risks are derived from the same stored records, and labelled as inferences.
    inferred = []
    for r in ranked:
        if r["days_until_due"] is not None and r["days_until_due"] < 0:
            inferred.append({"kind": "inferred", "venture_id": r["venture_id"], "venture_name": r.get("venture_name"), "task_id": r["id"],
                             "description": f"Task '{r['title']}' is overdue by {-r['days_until_due']} day(s)", "days_open": -r["days_until_due"]})
        elif r["blocked_by"] and not r["open_blockers"]:
            inferred.append({"kind": "inferred", "venture_id": r["venture_id"], "venture_name": r.get("venture_name"), "task_id": r["id"],
                             "description": f"Task '{r['title']}' is held up: " + "; ".join(r["blocked_by"]), "days_open": None})
    out["inferred_risks"] = inferred

    def kpis_section():
        ks = _rows(conn, "SELECT k.*, g.title AS goal_title FROM kpis k LEFT JOIN goals g ON g.id=k.goal_id "
                         "WHERE k.venture_id IN (SELECT id FROM ventures WHERE status<>'ARCHIVED') ORDER BY k.is_primary DESC, k.created_at")
        rd: dict[str, list] = {}
        for r in _rows(conn, "SELECT kpi_id, value, recorded_at FROM kpi_readings ORDER BY recorded_at, id"):
            rd.setdefault(r["kpi_id"], []).append(r)
        views = [kpi_view(k, rd.get(k["id"], [])) for k in ks]
        for v in views:
            v["venture_name"] = vname.get(v["venture_id"])
        return views

    kpis = _section(kpis_section)
    out["kpis"] = kpis
    out["goals"] = _section(lambda: _rows(conn, "SELECT id,venture_id,title,status,created_at FROM goals WHERE status='ACTIVE' AND venture_id IN "
                                                "(SELECT id FROM ventures WHERE status<>'ARCHIVED') ORDER BY created_at"))
    if isinstance(out["goals"], list):
        for g in out["goals"]:
            g["venture_name"] = vname.get(g["venture_id"])
    out["experiments"] = _section(lambda: _rows(conn, "SELECT e.*, v.name AS venture_name FROM experiments e JOIN ventures v ON v.id=e.venture_id "
                                                      "WHERE e.status IN ('PLANNED','RUNNING') AND v.status<>'ARCHIVED' ORDER BY (e.review_date IS NULL), e.review_date, e.created_at LIMIT 20"))
    out["decisions"] = _section(lambda: _rows(conn, "SELECT d.*, v.name AS venture_name FROM decisions d JOIN ventures v ON v.id=d.venture_id "
                                                    "ORDER BY d.decided_at DESC LIMIT 8"))
    out["ai_usage"] = _section(ai_usage, conn, today)

    # Business cards: only facts that are stored; absent data stays absent.
    cards = []
    if isinstance(ventures, list):
        for v in ventures:
            vt = [r for r in ranked if r["venture_id"] == v["id"]]
            nxt = next((r for r in vt if r["eligible"]), None)
            vb = [b for b in blockers if b["venture_id"] == v["id"]] if isinstance(blockers, list) else None
            vk = [k for k in kpis if k["venture_id"] == v["id"]] if isinstance(kpis, list) else None
            primary = next((k for k in vk or [] if k["is_primary"] and k["current"] is not None), None) or next((k for k in vk or [] if k["current"] is not None), None)
            goal = next((g for g in out["goals"] if g["venture_id"] == v["id"]), None) if isinstance(out["goals"], list) else None
            cards.append({"id": v["id"], "name": v["name"], "priority": v["priority"], "status": v["status"],
                          "objective": v["objective"] or (goal["title"] if goal else None), "primary_kpi": primary,
                          "bottleneck": vb[0] if vb else None, "next_action": {"id": nxt["id"], "title": nxt["title"]} if nxt else None,
                          "open_tasks": len(vt) if isinstance(tasks, list) else None, "blocked_tasks": sum(1 for r in vt if not r["eligible"]) if isinstance(tasks, list) else None,
                          "open_blockers": len(vb) if vb is not None else None})
    out["cards"] = cards
    open_b = blockers if isinstance(blockers, list) else []
    out["recommendation"] = recommend(ranked, open_b, vmap) if isinstance(tasks, list) else {"action": None, "missing": ["Tasks could not be loaded."]}
    out["attention"] = {"overdue": sum(1 for r in ranked if r["days_until_due"] is not None and r["days_until_due"] < 0),
                        "due_today": sum(1 for r in ranked if r["days_until_due"] == 0),
                        "open_blockers": len(open_b)} if isinstance(tasks, list) else None
    return out


def ai_usage(conn, today: date) -> dict:
    """Real rows of llm_usage only. Tokens, requests and USD are reported separately; the monthly cap
    is shown only when it is actually configured. Rows carry no business, so no per-business split."""
    start = datetime(today.year, today.month, 1, tzinfo=timezone.utc).isoformat()
    day = datetime(today.year, today.month, today.day, tzinfo=timezone.utc).isoformat()
    q = ("SELECT count(*) AS requests, COALESCE(SUM(input_tokens),0) AS input_tokens, COALESCE(SUM(output_tokens),0) AS output_tokens, "
         "COALESCE(SUM(cost_usd),0) AS cost_usd, count(*) FILTER (WHERE status='FAILED') AS failed, count(*) FILTER (WHERE status='RESERVED') AS unsettled "
         "FROM llm_usage WHERE at >= ?")
    month, today_ = _rows(conn, q, (start,))[0], _rows(conn, q, (day,))[0]
    if month["requests"] == 0:
        return {"available": False}
    by = _rows(conn, "SELECT purpose, model, count(*) AS requests, COALESCE(SUM(cost_usd),0) AS cost_usd FROM llm_usage WHERE at >= ? GROUP BY purpose, model ORDER BY cost_usd DESC LIMIT 6", (start,))
    cap = float(budget.monthly_cap())
    return {"available": True, "month": month, "today": today_, "by_purpose": by,
            "monthly_cap_usd": cap or None,
            "note": "Cost is recorded per request; 'RESERVED' rows are worst-case holds, 'FAILED' rows keep their worst-case hold."}


# ------------------------------------------------------------------ writes ----

class FounderError(ValueError):
    pass


KEY_RE = re.compile(r"^[a-z0-9_]{8,64}$")
ID_RE = re.compile(r"^[a-z0-9_]{1,80}$")


def _s(d, k, required=False, mx=300):
    v = d.get(k)
    if v is None or v == "":
        if required:
            raise FounderError(f"{k} is required")
        return None
    if not isinstance(v, str):
        raise FounderError(f"{k} must be text")
    v = v.strip()
    if required and not v:
        raise FounderError(f"{k} is required")
    if len(v) > mx:
        raise FounderError(f"{k} is too long")
    return v or None


def _n(d, k, lo=None, hi=None):
    v = d.get(k)
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        raise FounderError(f"{k} must be a number")
    try:
        x = Decimal(str(v).strip())
    except InvalidOperation:
        raise FounderError(f"{k} must be a number")
    if not x.is_finite() or abs(x) > Decimal("1e12"):
        raise FounderError(f"{k} must be a number")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        raise FounderError(f"{k} is out of range")
    return x


def _d(d, k):
    v = _s(d, k, mx=10)
    if v is None:
        return None
    try:
        return date.fromisoformat(v).isoformat()
    except ValueError:
        raise FounderError(f"{k} must be a date (YYYY-MM-DD)")


def _enum(d, k, allowed, default):
    v = d.get(k, default) or default
    if v not in allowed:
        raise FounderError(f"{k} is invalid")
    return v


def _bool(d, k):
    v = d.get(k, False)
    if not isinstance(v, bool):
        raise FounderError(f"{k} must be true or false")
    return v


def _ref(conn, table, rid, venture_id=None):
    """A referenced record must exist and (when a business is given) belong to that same business."""
    if rid in (None, ""):
        return None
    if not isinstance(rid, str) or not ID_RE.match(rid):
        raise FounderError("reference is invalid")
    row = conn.execute(f"SELECT venture_id FROM {table} WHERE id=?", (rid,)).fetchone()
    if row is None or (venture_id and row["venture_id"] != venture_id):
        raise FounderError("referenced record not found in this business")
    return rid


def _venture(conn, d):
    vid = d.get("venture_id")
    if not isinstance(vid, str) or not ID_RE.match(vid) or conn.execute("SELECT 1 FROM ventures WHERE id=? AND status<>'ARCHIVED'", (vid,)).fetchone() is None:
        raise FounderError("choose a business")
    return vid


def create(conn, owner: str, kind: str, d: dict) -> dict:
    """Create one record. `client_key` makes a double-submit idempotent (same key -> same record)."""
    key = d.get("client_key")
    if not isinstance(key, str) or not KEY_RE.match(key):
        raise FounderError("client_key is required")
    ts = now()
    rid = f"{kind[:3]}_{key}"
    if kind == "task":
        vid = _venture(conn, d)
        cols = dict(id=rid, venture_id=vid, goal_id=_ref(conn, "goals", d.get("goal_id"), vid), title=_s(d, "title", True, 200),
                    status=_enum(d, "status", ("TODO", "IN_PROGRESS", "BLOCKED"), "TODO"), due_date=_d(d, "due_date"),
                    effort_hours=_n(d, "effort_hours", 0, 1000), impact=(int(_n(d, "impact", 1, 5)) if _n(d, "impact", 1, 5) is not None else None),
                    expected_outcome=_s(d, "expected_outcome", mx=300), next_step=_s(d, "next_step", mx=300),
                    depends_on=_ref(conn, "founder_tasks", d.get("depends_on"), vid), created_at=ts, updated_at=ts)
        table = "founder_tasks"
    elif kind == "goal":
        vid = _venture(conn, d)
        cols, table = dict(id=rid, venture_id=vid, title=_s(d, "title", True, 200), created_at=ts), "goals"
    elif kind == "kpi":
        vid = _venture(conn, d)
        cols, table = dict(id=rid, venture_id=vid, goal_id=_ref(conn, "goals", d.get("goal_id"), vid), name=_s(d, "name", True, 120), unit=_s(d, "unit", mx=20) or "",
                           baseline=_n(d, "baseline"), target=_n(d, "target"), higher_is_better=_bool(d, "higher_is_better") if "higher_is_better" in d else True,
                           is_primary=_bool(d, "is_primary") if "is_primary" in d else False, period=_s(d, "period", mx=40), created_at=ts), "kpis"
    elif kind == "reading":
        kid = _ref(conn, "kpis", d.get("kpi_id"))
        if kid is None:
            raise FounderError("choose a KPI")
        value = _n(d, "value")
        if value is None:
            raise FounderError("value is required")
        cols, table = dict(id=rid, kpi_id=kid, value=value, recorded_at=ts), "kpi_readings"
    elif kind == "blocker":
        vid = _venture(conn, d)
        cols, table = dict(id=rid, venture_id=vid, task_id=_ref(conn, "founder_tasks", d.get("task_id"), vid), description=_s(d, "description", True, 400),
                           impact=_s(d, "impact", mx=300), suggested_action=_s(d, "suggested_action", mx=300), opened_at=ts), "blockers"
    elif kind == "experiment":
        vid = _venture(conn, d)
        cols, table = dict(id=rid, venture_id=vid, name=_s(d, "name", True, 160), hypothesis=_s(d, "hypothesis", mx=400),
                           status=_enum(d, "status", ("PLANNED", "RUNNING"), "PLANNED"), metric=_s(d, "metric", mx=120), baseline=_n(d, "baseline"),
                           target=_n(d, "target"), review_date=_d(d, "review_date"), next_action=_s(d, "next_action", mx=300), created_at=ts), "experiments"
    elif kind == "decision":
        vid = _venture(conn, d)
        cols, table = dict(id=rid, venture_id=vid, title=_s(d, "title", True, 200), rationale=_s(d, "rationale", mx=600),
                           status=_enum(d, "status", ("DECIDED", "REVISIT"), "DECIDED"), decided_at=ts), "decisions"
    else:
        raise FounderError("unknown record type")
    names = list(cols)
    cur = conn.execute(f"INSERT INTO {table} ({','.join(names)}) VALUES ({','.join('?' * len(names))}) ON CONFLICT (id) DO NOTHING RETURNING id",
                       tuple(cols[n] for n in names))
    created = cur.fetchone() is not None
    if created:
        audit(conn, owner, f"founder.{kind}.create", rid)
    return {"id": rid, "created": created}


def set_task_status(conn, owner: str, task_id: str, status: str) -> dict:
    if status not in ("TODO", "IN_PROGRESS", "BLOCKED", "DONE"):
        raise FounderError("status is invalid")
    ts = now()
    row = conn.execute("UPDATE founder_tasks SET status=?, updated_at=?, completed_at=CASE WHEN ?='DONE' THEN ? ELSE NULL END WHERE id=? RETURNING id",
                       (status, ts, status, ts, task_id)).fetchone()
    if row is None:
        raise FounderError("task not found")
    audit(conn, owner, "founder.task.status", task_id, status)
    return {"id": task_id, "status": status}


def resolve_blocker(conn, owner: str, blocker_id: str) -> dict:
    row = conn.execute("UPDATE blockers SET status='RESOLVED', resolved_at=? WHERE id=? AND status='OPEN' RETURNING id", (now(), blocker_id)).fetchone()
    if row is None:
        raise FounderError("open blocker not found")
    audit(conn, owner, "founder.blocker.resolve", blocker_id)
    return {"id": blocker_id, "status": "RESOLVED"}
