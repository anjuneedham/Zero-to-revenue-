"""Experiment lifecycle (Phase 9): proposed -> running -> succeeded | failed | inconclusive, or abandoned.

Records only. Nothing here runs, sends or changes anything outside the database: the founder runs the experiment and records
what happened. Rules, each covered by tests/unit/test_experiments.py (and the DB trigger in migration 015):
* Starting needs a success metric and a duration; the plan (hypothesis, metric, baseline, target, duration) is locked from then on.
* A baseline left empty is taken from the linked KPI's current value (real data), never invented.
* Concluding needs a result (number or text), what was learned, and a decision (scale / iterate / stop). The result is then fixed.
* The recorded outcome may not contradict the recorded numbers (e.g. "succeeded" with a result worse than baseline). `scale` needs
  a succeeded outcome.
* Concluding writes the decision record and the learning back to the business's knowledge as an ASSUMED evidence row: it is only
  as good as one founder-entered result, and it becomes verified only through the normal evidence flow (with a source).
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from core import founder
from core.audit import audit
from core.db import now
from core.founder import FounderError, NotFound

PLAN_FIELDS = {"hypothesis", "method", "success_metric", "kpi_id", "baseline_value", "target_value", "duration_days", "min_sample", "goal_id"}
OUTCOMES = ("succeeded", "failed", "inconclusive")
DECISIONS = ("scale", "iterate", "stop")
MAX_TEXT = 2000


def _num(v):
    return float(v) if isinstance(v, Decimal) else v


def _get(conn, eid):
    r = conn.execute("SELECT * FROM experiments WHERE id=?", (eid,)).fetchone()
    if not r:
        raise NotFound("not found")
    return dict(r)


def guard_plan_edit(conn, eid, values):
    r = conn.execute("SELECT status FROM experiments WHERE id=?", (eid,)).fetchone()
    if r and r["status"] != "proposed" and set(values) & PLAN_FIELDS:
        raise FounderError("the plan of a started experiment cannot be changed: note what changed in learnings, or start a new experiment")


def _text(v, field, required=True):
    if v is None or (isinstance(v, str) and not v.strip()):
        if required:
            raise FounderError(f"{field} is required")
        return None
    if not isinstance(v, str) or len(v) > MAX_TEXT:
        raise FounderError(f"{field}: text up to {MAX_TEXT} characters")
    return v.strip()


def _number(v, field):
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        raise FounderError(f"{field}: must be a number")
    try:
        d = Decimal(str(v))
    except Exception:
        raise FounderError(f"{field}: must be a number") from None
    if not d.is_finite():
        raise FounderError(f"{field}: must be a finite number")
    return d


def _parse(ts):
    return datetime.fromisoformat(ts) if ts else None


def evaluate(e: dict, direction: str = "up") -> dict:
    """Deterministic reading of the recorded numbers against baseline and target. Advisory: it never decides the outcome."""
    rv, base, tgt = _num(e.get("result_value")), _num(e.get("baseline_value")), _num(e.get("target_value"))
    sign = 1 if direction != "down" else -1
    warnings = []
    if rv is None:
        code, verdict = "no_result", "No numeric result recorded."
    elif base is None:
        code, verdict = "no_baseline", "No baseline recorded: improvement cannot be judged."
    else:
        delta = (rv - base) * sign
        met = tgt is not None and (rv - tgt) * sign >= 0
        if met:
            code, verdict = "met", f"Result {rv:g} reached the target {tgt:g} (baseline {base:g})."
        elif delta > 0:
            code, verdict = "improved", f"Result {rv:g} is better than baseline {base:g}" + (f" but short of target {tgt:g}." if tgt is not None else " (no target set).")
        elif delta == 0:
            code, verdict = "flat", f"Result {rv:g} equals the baseline {base:g}."
        else:
            code, verdict = "worse", f"Result {rv:g} is worse than baseline {base:g}."
    if e["status"] in OUTCOMES:
        ss, ms = e.get("sample_size"), e.get("min_sample")
        if ss is None:
            warnings.append("No sample size recorded: treat the result as an anecdote.")
        elif ms is not None and ss < ms:
            warnings.append(f"Sample size {ss} is below the minimum you set ({ms}).")
        s, t = _parse(e.get("started_at")), _parse(e.get("ended_at"))
        if s and t and e.get("duration_days") and (t - s) < timedelta(days=e["duration_days"]):
            warnings.append("Concluded before the planned duration.")
        warnings.append("One result from one run: it is evidence, not proof, and a number moving is not proof of cause.")
    return {"code": code, "verdict": verdict, "warnings": warnings}


def view(conn, e: dict) -> dict:
    e = {k: _num(v) for k, v in dict(e).items()}
    kpi = conn.execute("SELECT name, unit, direction FROM kpis WHERE id=?", (e["kpi_id"],)).fetchone() if e.get("kpi_id") else None
    ends = _parse(e["started_at"]) + timedelta(days=e["duration_days"]) if e["status"] == "running" and e.get("started_at") and e.get("duration_days") else None
    e["kpi_name"] = kpi["name"] if kpi else None
    e["ends_on"] = ends.date().isoformat() if ends else None
    e["ready_to_conclude"] = bool(ends and datetime.now(timezone.utc) >= ends)
    e["evaluation"] = evaluate(e, kpi["direction"] if kpi else "up") if e["status"] != "proposed" else None
    return e


def start(conn, eid, actor) -> dict:
    e = _get(conn, eid)
    if e["status"] != "proposed":
        raise FounderError("only a proposed experiment can be started")
    if not e["success_metric"]:
        raise FounderError("set the success metric before starting")
    if not e["duration_days"]:
        raise FounderError("set the planned duration (days) before starting")
    base = e["baseline_value"]
    if base is None and e["kpi_id"]:
        base = conn.execute("SELECT current_value FROM kpis WHERE id=?", (e["kpi_id"],)).fetchone()["current_value"]
    ts = now()
    conn.execute("UPDATE experiments SET status='running', started_at=?, baseline_value=?, review_date=COALESCE(review_date, ?), updated_at=? WHERE id=?",
                 (ts, base, (datetime.fromisoformat(ts) + timedelta(days=e["duration_days"])).date().isoformat(), ts, eid))
    audit(conn, actor, "experiment.start", eid)
    return view(conn, _get(conn, eid))


def abandon(conn, eid, reason, actor) -> dict:
    e = _get(conn, eid)
    if e["status"] not in ("proposed", "running"):
        raise FounderError("this experiment is already closed")
    ts = now()
    conn.execute("UPDATE experiments SET status='abandoned', abandon_reason=?, ended_at=?, updated_at=? WHERE id=?", (_text(reason, "reason"), ts, ts, eid))
    audit(conn, actor, "experiment.abandon", eid)
    return view(conn, _get(conn, eid))


def conclude(conn, eid, actor, outcome, result=None, result_value=None, sample_size=None, learnings=None, decision=None, decision_note=None) -> dict:
    e = _get(conn, eid)
    if e["status"] != "running":
        raise FounderError("only a running experiment can be concluded")
    if outcome not in OUTCOMES:
        raise FounderError("outcome must be one of " + ", ".join(OUTCOMES))
    if decision not in DECISIONS:
        raise FounderError("decision must be one of " + ", ".join(DECISIONS))
    result, learnings = _text(result, "result", required=False), _text(learnings, "learnings")
    rv = _number(result_value, "result_value")
    if result is None and rv is None:
        raise FounderError("record a result: a number, a description, or both")
    if sample_size is not None and (isinstance(sample_size, bool) or not isinstance(sample_size, int) or sample_size < 0):
        raise FounderError("sample_size: whole number, 0 or more")
    if decision == "scale" and outcome != "succeeded":
        raise FounderError("only a succeeded experiment can be scaled; choose iterate or stop")
    kpi = conn.execute("SELECT direction FROM kpis WHERE id=?", (e["kpi_id"],)).fetchone() if e["kpi_id"] else None
    check = evaluate({**e, "status": "running", "result_value": rv}, kpi["direction"] if kpi else "up")
    if outcome == "succeeded" and check["code"] == "worse":
        raise FounderError("the recorded result is worse than baseline, so this cannot be 'succeeded': " + check["verdict"] + " Use failed or inconclusive, or correct the numbers.")
    if outcome == "failed" and check["code"] == "met":
        raise FounderError("the recorded result reached the target, so this cannot be 'failed': " + check["verdict"] + " Use succeeded or inconclusive, or correct the numbers.")
    note = _text(decision_note, "decision_note", required=False)
    ts = now()
    with conn.transaction():
        conn.execute("UPDATE experiments SET status=?, result=?, result_value=?, sample_size=?, learnings=?, decision=?, ended_at=?, updated_at=? WHERE id=?",
                     (outcome, result, rv, sample_size, learnings, decision, ts, ts, eid))
        did = f"dec_{uuid.uuid4().hex[:12]}"
        conn.execute("INSERT INTO decisions(id,business_id,title,context,decision,rationale,status,decided_at,created_at,updated_at,experiment_id) VALUES (?,?,?,?,?,?, 'decided', ?, ?, ?, ?)",
                     (did, e["business_id"], ("Experiment: " + e["hypothesis"])[:200], f"Experiment {eid} ended as {outcome}.",
                      decision + (": " + note if note else ""), (check["verdict"] + " " + (result or ""))[:1000].strip(), ts, ts, ts, eid))
        kid, sid, evid = f"kn_{uuid.uuid4().hex[:12]}", f"src_{uuid.uuid4().hex[:12]}", f"ev_{uuid.uuid4().hex[:12]}"
        conn.execute("INSERT INTO knowledge(id,business_id,title,body,tags,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                     (kid, e["business_id"], ("Learning: " + e["hypothesis"])[:200], f"{learnings}\n\nOutcome: {outcome}. {check['verdict']} Sample: {sample_size if sample_size is not None else 'not recorded'}.",
                      "experiment", ts, ts))
        conn.execute("INSERT INTO sources(id,business_id,title,kind,reliability,notes,created_at,updated_at) VALUES (?,?,?,'internal','unknown',?,?,?)",
                     (sid, e["business_id"], f"Experiment {eid}: result entered by the founder", "Numbers were typed in, not imported or independently checked.", ts, ts))
        conn.execute("INSERT INTO evidence(id,business_id,knowledge_id,claim,label,source_id,note,created_at,updated_at) VALUES (?,?,?,?, 'assumed', ?, ?, ?, ?)",
                     (evid, e["business_id"], kid, learnings[:500], sid, "From one experiment run; verify with an independent source before treating as fact.", ts, ts))
        conn.execute("UPDATE experiments SET learning_knowledge_id=? WHERE id=?", (kid, eid))
    audit(conn, actor, "experiment.conclude", eid, f"{outcome}/{decision}")
    return view(conn, _get(conn, eid))


def for_business(conn, slug) -> dict:
    biz = founder.get_business(conn, slug)
    rows = [view(conn, r) for r in conn.execute("SELECT * FROM experiments WHERE business_id=? ORDER BY (status IN ('proposed','running')) DESC, created_at DESC LIMIT 100", (biz["id"],))]
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in founder.STATUSES["experiments"]}
    return {"business": slug, "experiments": rows, "counts": counts, "ready_to_conclude": [r["id"] for r in rows if r["ready_to_conclude"]]}
