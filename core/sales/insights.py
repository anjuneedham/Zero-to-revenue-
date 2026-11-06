"""Daily command centre, targets, performance reporting and learning.

Every number here is computed from recorded events and prospect fields. Rates are shown as counts ("2 of 7");
a percentage is only produced once the denominator reaches MIN_SAMPLE, and even then it is labelled as a
recorded rate, not a prediction. Anything inferential is labelled a hypothesis or rule-based suggestion."""

import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import median

from core.db import now
from core.sales import pipeline
from core.sales.events import (ACTIVE, CHANNELS, CLOSED, RANK, STAGE_LABEL, STAGES, local_date, log, num, parse_event, tz_name, today)

MIN_SAMPLE = 30      # below this, no percentages are produced
HYPOTHESIS_MIN = 5   # below this many prospects, no hypothesis is offered

DEFAULT_TARGETS = [
    {"id": "research", "label": "Research prospects", "target": 5},
    {"id": "qualify", "label": "Qualify prospects", "target": 3},
    {"id": "initial", "label": "Send initial outreach", "target": 5},
    {"id": "followups", "label": "Complete follow-ups", "target": 3},
    {"id": "responses", "label": "Record responses received", "target": 0},
    {"id": "touched", "label": "Update the pipeline (prospects touched)", "target": 5},
]
METRICS = {d["id"] for d in DEFAULT_TARGETS}


def get_targets(conn) -> list[dict]:
    r = conn.execute("SELECT value FROM settings WHERE key='sales_targets'").fetchone()
    try:
        saved = json.loads(r["value"]) if r else {}
    except ValueError:
        saved = {}
    return [{**d, "target": int(saved.get(d["id"], d["target"]))} for d in DEFAULT_TARGETS]


def set_targets(conn, data: dict) -> list[dict]:
    saved = {}
    for k, v in (data.get("targets") or {}).items():
        if k not in METRICS:
            raise ValueError("unknown target")
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= 500:
            raise ValueError("a target must be a whole number from 0 to 500")
        saved[k] = v
    if "timezone" in data:
        tzv = data["timezone"]
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(tzv)
        except Exception:
            raise ValueError("unknown timezone (use a name like America/Jamaica)") from None
        conn.execute("INSERT INTO settings(key,value,updated_at) VALUES ('sales_timezone',?,?) ON CONFLICT (key) DO UPDATE "
                     "SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at", (tzv, now()))
    if saved:
        cur = {t["id"]: t["target"] for t in get_targets(conn)}
        cur.update(saved)
        conn.execute("INSERT INTO settings(key,value,updated_at) VALUES ('sales_targets',?,?) ON CONFLICT (key) DO UPDATE "
                     "SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at", (json.dumps(cur), now()))
    return get_targets(conn)


def _events(conn, since_days=None, limit=20000) -> list[dict]:
    rows = conn.execute("SELECT id,at,occurred_at,lead_id,kind,summary,detail FROM activity_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [parse_event(r) for r in reversed(rows)]


def record_review(conn, note=None) -> dict:
    """The end-of-day review is a recorded event, so 'review today's performance' is checkable, not a vibe."""
    log(conn, None, "daily_review", "Daily review completed", {"note": (note or "")[:1000] if isinstance(note, str) else ""})
    return {"ok": True}


# ---------------------------------------------------------------- today ---------------------------------------------

def _progress(conn, evs, day):
    todays = [e for e in evs if local_date(e["occurred_at"], conn) == day]
    c = Counter(e["kind"] for e in todays)
    value = {"research": c["research_completed"], "qualify": c["qualification_decision"],
             "initial": sum(1 for e in todays if e["kind"] == "message_sent" and e["detail"].get("initial")),
             "followups": c["followup_completed"], "responses": c["response_received"],
             "touched": len({e["lead_id"] for e in todays if e["lead_id"] and e["kind"] not in ("prospect_deleted",)})}
    return value, any(e["kind"] == "daily_review" for e in todays), todays


def _days_since(day_iso, d0):
    try:
        return (d0 - date.fromisoformat(day_iso[:10])).days
    except (TypeError, ValueError):
        return None


def today_view(conn) -> dict:
    day = today(conn)
    d0 = date.fromisoformat(day)
    evs = _events(conn, limit=5000)
    value, reviewed, _ = _progress(conn, evs, day)
    targets = [{**t, "done": value[t["id"]], "met": value[t["id"]] >= t["target"]} for t in get_targets(conn) if t["target"] > 0]

    open_tasks = pipeline.list_tasks(conn, "open", limit=500)
    for t in open_tasks:
        t["overdue_days"] = max(0, _days_since(t["due_date"], d0) or 0)
    followups = [t for t in open_tasks if t["kind"] == "follow_up" and t["due_date"] <= day]
    meetings = [t for t in open_tasks if t["kind"] == "meeting" and t["due_date"] <= (d0 + timedelta(days=7)).isoformat()]
    others = [t for t in open_tasks if t["kind"] not in ("follow_up", "meeting") and t["due_date"] <= day]

    leads = pipeline.list_prospects(conn, limit=500)
    by_stage = Counter(l["stage"] for l in leads)
    active = [l for l in leads if l["stage"] in RANK]
    opps = [l for l in active if RANK[l["stage"]] >= RANK["responded"]]
    open_value = defaultdict(float)
    for l in active:
        if l["deal_value"]:
            open_value[l["currency"]] += l["deal_value"]

    has_open_followup = {t["lead_id"] for t in open_tasks if t["kind"] == "follow_up"}
    attention, recs = [], []

    def name(l):
        return l["business"] or l["name"] or "Unnamed prospect"

    for l in active:
        st, idle = l["stage"], _days_since(l["last_contact_at"] or l["updated_at"] or l["created_at"], d0)
        if st in ("responded", "conversation"):
            attention.append({"lead_id": l["id"], "business": name(l), "reason": f"They responded; stage is still '{STAGE_LABEL[st]}'", "suggestion": "Reply, or record the next step"})
        elif st in ("contacted", "follow_up") and l["id"] not in has_open_followup and (idle or 0) >= 3:
            attention.append({"lead_id": l["id"], "business": name(l), "reason": f"Contacted {idle} day(s) ago with no follow-up scheduled", "suggestion": "Schedule a follow-up"})
        elif st in ("qualified", "outreach_prepared"):
            attention.append({"lead_id": l["id"], "business": name(l), "reason": "Qualified but no message recorded as sent", "suggestion": "Send the first message"})
        elif st == "identified" and (idle or 0) >= 1:
            attention.append({"lead_id": l["id"], "business": name(l), "reason": f"Identified {idle} day(s) ago, not yet researched", "suggestion": "Research this prospect"})
        elif st in ("meeting_booked", "proposal", "negotiation") and l["id"] not in has_open_followup and (idle or 0) >= 3:
            attention.append({"lead_id": l["id"], "business": name(l), "reason": f"In '{STAGE_LABEL[st]}' with no activity for {idle} day(s) and no follow-up set", "suggestion": "Set a follow-up date"})
    overdue = [t for t in followups if t["overdue_days"] > 0]
    if overdue:
        recs.append({"text": f"Clear {len(overdue)} overdue follow-up(s) first", "why": "Recorded follow-up tasks are past their due date.", "kind": "rule"})
    waiting = [a for a in attention if "responded" in a["reason"]]
    if waiting:
        recs.append({"text": f"Reply to {len(waiting)} prospect(s) who responded", "why": "A response is recorded and the stage has not moved on.", "kind": "rule"})
    unmet = [t for t in targets if not t["met"]]
    if unmet:
        t = unmet[0]
        recs.append({"text": f"{t['label']}: {t['done']} of {t['target']} done today", "why": "This is your own daily target.", "kind": "rule"})
    if not leads:
        recs.append({"text": "Add your first prospect", "why": "The pipeline is empty. Only a business name is required.", "kind": "rule"})
    return {"date": day, "timezone": tz_name(conn), "targets": targets, "review_done": reviewed, "followups_due": followups,
            "tasks": others, "meetings": meetings, "attention": attention[:12], "active_opportunities": opps[:12],
            "pipeline": {"by_stage": dict(by_stage), "total": len(leads), "open_value": dict(open_value),
                         "value_note": "Deal values are your estimates, not revenue."},
            "recent_activity": [e for e in reversed(evs[-12:])], "recommendations": recs[:5]}


# ---------------------------------------------------------------- performance ---------------------------------------

def _pct(n, of):
    return {"n": n, "of": of, "label": f"{n} of {of}", "pct": round(100 * n / of) if of >= MIN_SAMPLE else None,
            "note": None if of >= MIN_SAMPLE else f"Only {of} in the sample, too few to read as a rate."}


def _distinct(evs, kind, pred=lambda e: True):
    return {e["lead_id"] for e in evs if e["kind"] == kind and e["lead_id"] and pred(e)}


def performance(conn) -> dict:
    evs = _events(conn)
    disc = _distinct(evs, "prospect_created")
    researched = _distinct(evs, "research_completed")
    qualified = _distinct(evs, "qualification_decision", lambda e: e["detail"].get("decision") == "qualified")
    notq = _distinct(evs, "qualification_decision", lambda e: e["detail"].get("decision") == "not_qualified")
    contacted = _distinct(evs, "message_sent")
    responded = _distinct(evs, "response_received")
    positive = _distinct(evs, "response_received", lambda e: e["detail"].get("sentiment") == "positive")
    meetings = _distinct(evs, "meeting_booked")
    proposals = _distinct(evs, "proposal_delivered")
    won, lost = _distinct(evs, "deal_won"), _distinct(evs, "deal_lost")
    revenue = defaultdict(float)
    for e in evs:
        if e["kind"] == "deal_won" and e["detail"].get("revenue") is not None:
            revenue[e["detail"].get("currency") or "USD"] += float(e["detail"]["revenue"])
    open_followups = pipeline.list_tasks(conn, "open", limit=500)
    d0 = date.fromisoformat(today(conn))
    overdue = [t for t in open_followups if t["kind"] == "follow_up" and t["due_date"] < d0.isoformat()]
    counts = {"prospects_discovered": len(disc), "prospects_researched": len(researched), "prospects_qualified": len(qualified),
              "not_qualified": len(notq), "initial_messages_sent": sum(1 for e in evs if e["kind"] == "message_sent" and e["detail"].get("initial")),
              "followup_messages_sent": sum(1 for e in evs if e["kind"] == "message_sent" and not e["detail"].get("initial")),
              "followups_completed": sum(1 for e in evs if e["kind"] == "followup_completed"),
              "responses_received": len(responded), "positive_responses": len(positive), "meetings_booked": len(meetings),
              "proposals_sent": len(proposals), "customers_won": len(won), "customers_lost": len(lost),
              "followups_outstanding": len([t for t in open_followups if t["kind"] == "follow_up"]), "followups_overdue": len(overdue)}
    conversion = [{"step": "Qualified of researched", **_pct(len(qualified & researched), len(researched))},
                  {"step": "Contacted of qualified", **_pct(len(contacted & qualified), len(qualified))},
                  {"step": "Responded of contacted", **_pct(len(responded & contacted), len(contacted))},
                  {"step": "Meeting of responded", **_pct(len(meetings & responded), len(responded))},
                  {"step": "Proposal of meetings", **_pct(len(proposals & meetings), len(meetings))},
                  {"step": "Won of proposals", **_pct(len(won & proposals), len(proposals))}]
    # time between milestones (uses when things happened, not when recorded)
    first = defaultdict(dict)
    for e in evs:
        if e["lead_id"] and e["kind"] in ("prospect_created", "message_sent", "response_received", "meeting_booked", "proposal_delivered", "deal_won"):
            first[e["lead_id"]].setdefault(e["kind"], e["occurred_at"])
    pairs = [("prospect_created", "message_sent", "Identified to first message"), ("message_sent", "response_received", "First message to first response"),
             ("response_received", "meeting_booked", "Response to meeting booked"), ("meeting_booked", "proposal_delivered", "Meeting to proposal"),
             ("proposal_delivered", "deal_won", "Proposal to won")]
    timing = []
    for a, b, label in pairs:
        ds = []
        for m in first.values():
            if a in m and b in m:
                da, db_ = local_date(m[a], conn), local_date(m[b], conn)
                if da and db_ and db_ >= da:
                    ds.append((date.fromisoformat(db_) - date.fromisoformat(da)).days)
        timing.append({"step": label, "n": len(ds), "median_days": median(ds) if ds else None, "min_days": min(ds) if ds else None, "max_days": max(ds) if ds else None})
    return {"counts": counts, "conversion": conversion, "timing": timing,
            "revenue_recorded": dict(revenue), "revenue_note": "Owner-recorded when a prospect is marked won. Not verified revenue: Treasury verifies payments.",
            "sample_note": f"Percentages appear only when the sample is at least {MIN_SAMPLE}. Until then, read the counts."}


# ---------------------------------------------------------------- learning ------------------------------------------

def _group(evs, leads, keyfn):
    """prospects messaged / responded / positive / meeting / won, grouped by keyfn(lead, first_message_event)."""
    first_msg = {}
    for e in evs:
        if e["kind"] == "message_sent" and e["lead_id"] and e["lead_id"] not in first_msg:
            first_msg[e["lead_id"]] = e
    responded, positive = _distinct(evs, "response_received"), _distinct(evs, "response_received", lambda e: e["detail"].get("sentiment") == "positive")
    meet, won = _distinct(evs, "meeting_booked"), _distinct(evs, "deal_won")
    g = defaultdict(lambda: {"prospects": 0, "responded": 0, "positive": 0, "meetings": 0, "won": 0})
    for lid, m in first_msg.items():
        k = keyfn(leads.get(lid), m)
        if not k:
            continue
        row = g[k]
        row["prospects"] += 1
        row["responded"] += lid in responded
        row["positive"] += lid in positive
        row["meetings"] += lid in meet
        row["won"] += lid in won
    return [{"name": k, **v} for k, v in sorted(g.items(), key=lambda kv: -kv[1]["prospects"])]


def learning(conn) -> dict:
    evs = _events(conn)
    leads = {l["id"]: l for l in pipeline.list_prospects(conn, limit=500)}
    by_channel = _group(evs, leads, lambda l, m: m["detail"].get("channel"))
    by_angle = _group(evs, leads, lambda l, m: m["detail"].get("angle"))
    by_industry = _group(evs, leads, lambda l, m: (l or {}).get("industry"))
    by_source = _group(evs, leads, lambda l, m: (l or {}).get("source_channel"))
    lost = Counter()
    stage_lost = Counter()
    for e in evs:
        if e["kind"] in ("deal_lost", "outcome_recorded"):
            d = e["detail"]
            lost[(d.get("outcome") or "lost").replace("_", " ") + (": " + d["reason"][:80] if d.get("reason") else "")] += 1
            stage_lost[STAGE_LABEL.get(d.get("stage_at_close"), d.get("stage_at_close") or "?")] += 1
    d0 = date.fromisoformat(today(conn))
    days = {(d0 - timedelta(days=i)).isoformat(): 0 for i in range(14)}
    for e in evs:
        if e["kind"] in ("message_sent", "followup_completed", "research_completed", "qualification_decision"):
            ld = local_date(e["occurred_at"], conn)
            if ld in days:
                days[ld] += 1
    overdue = [t for t in pipeline.list_tasks(conn, "open", limit=500) if t["kind"] == "follow_up" and t["due_date"] < d0.isoformat()]
    runs = conn.execute("SELECT playbook_id, playbook_name, steps, progress, status FROM playbook_runs").fetchall()
    pb = defaultdict(lambda: {"runs": 0, "completed": 0, "abandoned": 0, "in_progress": 0, "stopped_at": Counter()})
    for r in runs:
        row = pb[r["playbook_name"]]
        row["runs"] += 1
        row[r["status"]] += 1
        if r["status"] == "abandoned":
            steps, prog = json.loads(r["steps"]), json.loads(r["progress"] or "{}")
            nxt = next((s["title"] for s in steps if s["id"] not in prog), None)
            if nxt:
                row["stopped_at"][nxt] += 1
    playbooks = [{"name": k, **{x: v[x] for x in ("runs", "completed", "abandoned", "in_progress")},
                  "most_common_stop": (v["stopped_at"].most_common(1)[0][0] if v["stopped_at"] else None)} for k, v in pb.items()]

    facts = []
    for label, rows in (("channel", by_channel), ("approach (angle)", by_angle), ("industry", by_industry), ("prospect source", by_source)):
        for r in rows:
            facts.append({"text": f"By {label} '{r['name']}': {r['prospects']} prospect(s) messaged, {r['responded']} responded, {r['positive']} positive, {r['meetings']} meeting(s), {r['won']} won.", "n": r["prospects"]})
    for k, n in lost.most_common(5):
        facts.append({"text": f"Closed without winning: {k} ({n}).", "n": n})
    facts.append({"text": f"Active on {sum(1 for v in days.values() if v)} of the last 14 days (counting research, qualification, messages and follow-ups).", "n": 14})
    facts.append({"text": f"{len(overdue)} follow-up(s) are overdue.", "n": len(overdue)})

    hyp = []
    for label, rows in (("approach", by_angle), ("channel", by_channel)):
        for r in rows:
            if r["prospects"] >= HYPOTHESIS_MIN and r["responded"] == 0:
                hyp.append({"text": f"Hypothesis: the {label} '{r['name']}' may not be working. 0 responses from {r['prospects']} prospects. Try a changed version and compare.", "n": r["prospects"]})
        eligible = [r for r in rows if r["prospects"] >= HYPOTHESIS_MIN]
        if len(eligible) >= 2:
            eligible.sort(key=lambda r: -r["responded"] / r["prospects"])
            top, bottom = eligible[0], eligible[-1]
            if top["responded"] / top["prospects"] >= 2 * max(bottom["responded"] / bottom["prospects"], 0.01):
                hyp.append({"text": f"Hypothesis: '{top['name']}' ({top['responded']} of {top['prospects']} responded) is out-performing '{bottom['name']}' ({bottom['responded']} of {bottom['prospects']}). Samples are small; repeat before concluding.", "n": top["prospects"] + bottom["prospects"]})
    for p in playbooks:
        if p["runs"] >= 3 and p["completed"] / p["runs"] < 0.5:
            stop = f" It is most often abandoned before '{p['most_common_stop']}'." if p["most_common_stop"] else ""
            hyp.append({"text": f"Hypothesis: playbook '{p['name']}' may need simplifying. {p['completed']} of {p['runs']} runs completed.{stop}", "n": p["runs"]})
    recs = []
    if overdue:
        recs.append({"text": f"Work through the {len(overdue)} overdue follow-up(s).", "why": "Recorded tasks are past due."})
    if not hyp:
        recs.append({"text": "Not enough recorded outreach yet to compare approaches. Keep recording the channel and a short approach label on every message.", "why": f"A comparison needs at least {HYPOTHESIS_MIN} prospects per approach."})
    return {"facts": facts, "hypotheses": hyp, "recommendations": recs,
            "tables": {"by_channel": by_channel, "by_angle": by_angle, "by_industry": by_industry, "by_source": by_source, "playbooks": playbooks,
                       "activity_last_14_days": [{"date": k, "actions": v} for k, v in sorted(days.items())]},
            "legend": {"fact": "Computed from what you recorded.", "hypothesis": "A possible pattern in a small sample. Not proven.",
                       "recommendation": "A rule-based suggestion, not an AI judgement."}}
