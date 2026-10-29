"""Experiment lifecycle and growth funnels (Phase 9).

* Lifecycle: proposed -> running -> succeeded | failed, or abandoned from proposed/running. Only these functions move it (the
  generic CRUD locks status/result/learnings). Nothing runs an experiment or contacts anyone: a founder starts and concludes.
* Concluding writes, in one transaction, a decision record and a knowledge note in the SAME business, with the learning as
  evidence. The evidence is `assumed` unless the founder names a source in this business (then `verified`). An experiment's own
  result never makes a claim verified.
* Funnels are computed from existing rows (content, marketplace, shop). A step with no rows is reported as no data, never 0%
  conversion invented from nothing; metrics the founder never recorded stay null.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from core import founder
from core.audit import audit
from core.db import now

OUTCOMES = ("succeeded", "failed")
DECISIONS = ("adopt", "iterate", "stop")


def _exp(conn, eid):
    row = conn.execute("SELECT * FROM experiments WHERE id=?", (eid,)).fetchone()
    if not row:
        raise founder.NotFound("not found")
    return dict(row)


def _parse(ts):
    try:
        d = datetime.fromisoformat(ts)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def due_date(exp):
    """started_at + duration_days, or None when it has not started or has no duration."""
    s = _parse(exp.get("started_at"))
    return (s + timedelta(days=exp["duration_days"])).isoformat() if s and exp.get("duration_days") else None


def decorate(exp):
    exp = dict(exp)
    exp["ends_at"] = due_date(exp)
    due = _parse(exp["ends_at"])
    exp["overdue"] = bool(exp["status"] == "running" and due and due < datetime.now(timezone.utc))
    return exp


def start(conn, eid, actor):
    e = _exp(conn, eid)
    if e["status"] != "proposed":
        raise founder.FounderError(f"only a proposed experiment can start (this one is {e['status']})")
    if not (e["success_metric"] or e["metric_kpi_id"]):
        raise founder.FounderError("set a success metric (text or a KPI) before starting")
    if not e["duration_days"]:
        raise founder.FounderError("set a duration in days before starting")
    ts = now()
    baseline = e["baseline_value"]
    if baseline is None and e["metric_kpi_id"]:
        k = conn.execute("SELECT current_value FROM kpis WHERE id=?", (e["metric_kpi_id"],)).fetchone()
        baseline = k["current_value"] if k else None  # real recorded value, or NULL if the KPI has none
    conn.execute("UPDATE experiments SET status='running', started_at=?, baseline_value=?, updated_at=? WHERE id=?", (ts, baseline, ts, eid))
    audit(conn, actor, "growth.experiment.start", eid)
    return decorate(_exp(conn, eid))


def abandon(conn, eid, reason, actor):
    e = _exp(conn, eid)
    if e["status"] not in ("proposed", "running"):
        raise founder.FounderError(f"cannot abandon an experiment that is {e['status']}")
    reason = (reason or "").strip()
    if not reason or len(reason) > founder.MAX_TEXT:
        raise founder.FounderError("a reason is required")
    ts = now()
    conn.execute("UPDATE experiments SET status='abandoned', ended_at=?, result=?, updated_at=? WHERE id=?", (ts, "Abandoned: " + reason, ts, eid))
    audit(conn, actor, "growth.experiment.abandon", eid)
    return decorate(_exp(conn, eid))


def conclude(conn, eid, d, actor):
    """d: outcome, result (text), decision, decision_rationale, learnings, result_value?, source_id?"""
    e = _exp(conn, eid)
    if e["status"] != "running":
        raise founder.FounderError(f"only a running experiment can be concluded (this one is {e['status']})")
    outcome, decision = d.get("outcome"), d.get("decision")
    if outcome not in OUTCOMES:
        raise founder.FounderError("outcome must be succeeded or failed")
    if decision not in DECISIONS:
        raise founder.FounderError("decision must be adopt, iterate or stop")
    text = {k: founder._coerce("experiments", k, founder.T, None, d.get(k)) for k in ("result", "decision_rationale", "learnings")}
    for k in ("result", "learnings"):
        if not text[k]:
            raise founder.FounderError(f"{k} is required")
    value = founder._coerce("experiments", "result_value", founder.N, None, d.get("result_value"))
    vsrc = "entered" if value is not None else None
    if value is None and e["metric_kpi_id"]:
        k = conn.execute("SELECT current_value FROM kpis WHERE id=?", (e["metric_kpi_id"],)).fetchone()
        if k and k["current_value"] is not None:
            value, vsrc = k["current_value"], "kpi"
    source_id = d.get("source_id") or None
    if source_id:
        s = conn.execute("SELECT business_id FROM sources WHERE id=?", (source_id,)).fetchone()
        if not s or s["business_id"] != e["business_id"]:
            raise founder.FounderError("source_id: not found in this business")
    ts = now()
    title = ("Experiment: " + " ".join(e["hypothesis"].split()))[:120]
    with conn.transaction():
        did, kid, evid = (f"{p}_{uuid.uuid4().hex[:12]}" for p in ("dec", "kn", "ev"))
        conn.execute("INSERT INTO decisions(id,business_id,title,context,decision,rationale,status,decided_at,created_at,updated_at) VALUES (?,?,?,?,?,?, 'decided', ?, ?, ?)",
                     (did, e["business_id"], f"{title} -> {decision}", e["hypothesis"], decision, text["decision_rationale"], ts, ts, ts))
        body = (f"Hypothesis: {e['hypothesis']}\nOutcome: {outcome}\nResult: {text['result']}\nLearning: {text['learnings']}\n"
                f"[from experiment {eid}; recorded by the founder, not independently verified]")
        conn.execute("INSERT INTO knowledge(id,business_id,title,body,tags,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                     (kid, e["business_id"], title, body, "experiment,learning", ts, ts))
        conn.execute("INSERT INTO evidence(id,business_id,knowledge_id,claim,label,source_id,note,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                     (evid, e["business_id"], kid, text["learnings"], "verified" if source_id else "assumed", source_id,
                      f"Result of experiment {eid} ({outcome}); this is the founder's own observation unless a source is attached", ts, ts))
        conn.execute("UPDATE experiments SET status=?, ended_at=?, result=?, learnings=?, result_value=?, result_source=?, decision=?, decision_rationale=?, "
                     "decision_id=?, knowledge_id=?, updated_at=? WHERE id=?",
                     (outcome, ts, text["result"], text["learnings"], value, vsrc, decision, text["decision_rationale"], did, kid, ts, eid))
    audit(conn, actor, "growth.experiment.conclude", eid, f"{outcome}/{decision} -> {did}, {kid}")
    return {"experiment": decorate(_exp(conn, eid)), "decision_id": did, "knowledge_id": kid, "evidence_label": "verified" if source_id else "assumed"}


# ---- funnels from real data ----

def _step(label, n, table):
    return {"label": label, "count": n, "from": table}


def _with_rates(steps):
    prev = None
    for s in steps:
        s["rate_from_previous"] = round(s["count"] / prev, 4) if prev else None  # None when there is no previous step with data
        if s["count"]:
            prev = s["count"]
    return steps


def _pipeline(conn, bid, table, stages, extra="", params=()):
    """Cumulative 'reached at least this stage' counts for a status pipeline."""
    counts = {r["status"]: r["n"] for r in conn.execute(f"SELECT status, count(*) AS n FROM {table} WHERE business_id=? {extra} GROUP BY status", (bid, *params))}
    steps = [_step(st, sum(counts.get(x, 0) for x in stages[i:]), table) for i, st in enumerate(stages)]
    return _with_rates(steps), counts


def funnels(conn, slug):
    b = founder.get_business(conn, slug)
    bid, out = b["id"], []
    steps, counts = _pipeline(conn, bid, "content_items", ["idea", "scripted", "filmed", "posted"])
    if sum(counts.values()):
        posted = conn.execute("SELECT count(*) AS n, sum(views) AS views, sum(signups) AS signups, count(views) AS with_views, count(signups) AS with_signups "
                              "FROM content_items WHERE business_id=? AND status='posted'", (bid,)).fetchone()
        if posted["n"]:
            steps.append(_step("views (posts where entered)", int(posted["views"] or 0), "content_items"))
            steps.append(_step("signups (posts where entered)", int(posted["signups"] or 0), "content_items"))
        out.append({"name": "Content to signups", "steps": steps, "dropped": counts.get("dropped", 0),
                    "coverage": {"posted": posted["n"], "posts_with_views": posted["with_views"], "posts_with_signups": posted["with_signups"]},
                    "note": "Views/signups are summed only from posts where you entered them; unentered values are not counted as zero. Step ratios between content stages and views are not conversion rates."})
    for role in ("farmer", "buyer"):
        steps, counts = _pipeline(conn, bid, "market_parties", ["lead", "onboarded", "active"], "AND role=?", (role,))
        if sum(counts.values()):
            out.append({"name": f"{role.title()} onboarding", "steps": steps, "dropped": counts.get("churned", 0), "note": "Counts of parties currently at or beyond each stage (churned shown separately)."})
    steps, counts = _pipeline(conn, bid, "market_transactions", ["proposed", "agreed", "completed"])
    if sum(counts.values()):
        out.append({"name": "Marketplace transactions", "steps": steps, "dropped": counts.get("cancelled", 0), "note": "Proposed -> agreed -> completed."})
    camp = conn.execute("SELECT count(*) AS n, sum(spend) AS spend, sum(orders) AS orders, sum(attributed_revenue) AS rev FROM shop_campaigns WHERE business_id=? AND status IN ('running','done')", (bid,)).fetchone()
    if camp["n"]:
        out.append({"name": "Shop campaigns", "steps": [_step("campaigns run", camp["n"], "shop_campaigns")], "totals": {
            "spend": camp["spend"], "orders": camp["orders"], "attributed_revenue": camp["rev"]},
            "note": "Totals are founder-entered campaign figures; null/zero means not recorded. Attribution is not verified."})
    sales = conn.execute("SELECT count(*) AS n, sum(revenue) AS rev FROM shop_sales WHERE business_id=?", (bid,)).fetchone()
    if sales["n"]:
        out.append({"name": "Shop sales", "steps": [_step("recorded sales", sales["n"], "shop_sales")], "totals": {"revenue": sales["rev"]}, "note": "Revenue of recorded sales rows."})
    return out


def kpi_trends(conn, bid):
    res = []
    for k in conn.execute("SELECT * FROM kpis WHERE business_id=? ORDER BY is_primary DESC, name", (bid,)).fetchall():
        rd = [dict(r) for r in conn.execute("SELECT value, recorded_at FROM kpi_readings WHERE kpi_id=? ORDER BY recorded_at DESC LIMIT 12", (k["id"],))][::-1]
        first, last = (rd[0]["value"], rd[-1]["value"]) if rd else (None, None)
        change = (last - first) if len(rd) >= 2 and isinstance(first, Decimal) else None
        res.append({"id": k["id"], "name": k["name"], "unit": k["unit"], "direction": k["direction"], "current_value": k["current_value"],
                    "target_value": k["target_value"], "readings": rd, "change": change})
    return res


def overview(conn, slug):
    b = founder.get_business(conn, slug)
    exps = [decorate(dict(r)) for r in conn.execute(
        "SELECT * FROM experiments WHERE business_id=? ORDER BY (status IN ('proposed','running')) DESC, created_at DESC LIMIT 100", (b["id"],))]
    by = {s: sum(1 for e in exps if e["status"] == s) for s in founder.STATUSES["experiments"]}
    return {"business": {"slug": b["slug"], "name": b["name"]}, "experiments": exps, "by_status": by,
            "overdue": [e["id"] for e in exps if e["overdue"]], "funnels": funnels(conn, slug), "kpis": kpi_trends(conn, b["id"])}
