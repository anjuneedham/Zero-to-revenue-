"""Prospects, stages, outreach records, follow-ups and tasks. Every state change appends an activity event.

Nothing here contacts anyone. "Record a message sent" logs what the owner did; actually sending stays on the
existing approval-gated Gmail path (agents/operator/outreach.py)."""

import json

from psycopg.errors import UniqueViolation

from core.db import now
from core.sales.events import (ACTIVE, ALL_STAGES, CHANNELS, CLOSED, PARKED, PII_FIELDS, PRIORITY, PROSPECT_FIELDS, RANK,
                               SENTIMENTS, STAGE_LABEL, TASK_KINDS, NotFound, _EMAIL, add_days, amount, check_date, log,
                               new_id, num, occurred, parse_event, text, today)

LEAD_COLS = ("id,name,business,email,phone,contact_other,website,industry,location,source_channel,offer,research_notes,notes,"
             "qualification,stage,outcome,deal_value,revenue_won,currency,last_contact_at,next_followup_at,playbook_run_id,"
             "created_at,updated_at")


def _clean(row) -> dict:
    return {k: num(v) for k, v in dict(row).items()}


def get_lead(conn, lead_id) -> dict:
    r = conn.execute(f"SELECT {LEAD_COLS} FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not r:
        raise NotFound("prospect not found")
    return _clean(r)


def _fields(data: dict, partial=False) -> dict:
    out = {}
    for f in PROSPECT_FIELDS:
        if f not in data:
            continue
        v = data[f]
        if f == "deal_value":
            out[f] = amount(v, "deal value")
        elif f == "currency":
            c = (text(v, 8, f) or "USD").upper()
            out[f] = c
        elif f == "research_notes" or f == "notes":
            out[f] = text(v, 5000, f)
        else:
            out[f] = text(v, 300, f)
    if out.get("email"):
        out["email"] = out["email"].lower()
        if not _EMAIL.match(out["email"]):
            raise ValueError("that email address does not look right")
    return out


def create_prospect(conn, data: dict, occurred_at=None) -> dict:
    """Only a business name OR a contact name is required. Everything else can be filled in later."""
    f = _fields(data)
    if not (f.get("business") or f.get("name")):
        raise ValueError("enter a business name or a contact name")
    lid = new_id("ld")
    stamp = now()
    cols = {"id": lid, "source": "sales_os", "status": "NEW", "stage": "identified", "created_at": stamp, "updated_at": stamp}
    cols.update({k: v for k, v in f.items() if v is not None})
    try:
        conn.execute(f"INSERT INTO leads({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", tuple(cols.values()))
    except UniqueViolation:
        raise ValueError("a prospect with that email already exists") from None
    who = f.get("business") or f.get("name")
    log(conn, lid, "prospect_created", f"Prospect identified: {who}",
        {"business": f.get("business"), "industry": f.get("industry"), "source_channel": f.get("source_channel")}, occurred_at)
    return get_lead(conn, lid)


def update_prospect(conn, lead_id, data: dict) -> dict:
    cur = get_lead(conn, lead_id)
    f = _fields(data)
    changes = {}
    for k, v in f.items():
        old = cur.get(k)
        if (old or None) == (v or None) or (k == "deal_value" and old is not None and v is not None and float(old) == float(v)):
            continue
        changes[k] = {"changed": True} if k in PII_FIELDS else {"from": old, "to": num(v)}
    if not changes:
        return cur
    if not (f.get("business", cur["business"]) or f.get("name", cur["name"])):
        raise ValueError("a prospect needs a business name or a contact name")
    sets = ", ".join(f"{k}=?" for k in f) + ", updated_at=?"
    try:
        conn.execute(f"UPDATE leads SET {sets} WHERE id=?", (*f.values(), now(), lead_id))
    except UniqueViolation:
        raise ValueError("a prospect with that email already exists") from None
    log(conn, lead_id, "prospect_updated", "Details updated: " + ", ".join(sorted(changes)), {"changes": changes})
    return get_lead(conn, lead_id)


def delete_prospect(conn, lead_id) -> None:
    """Removes the prospect record and its open tasks/runs. Its activity history is deliberately kept."""
    get_lead(conn, lead_id)
    log(conn, lead_id, "prospect_deleted", "Prospect record deleted (history kept)")
    conn.execute("DELETE FROM sales_tasks WHERE lead_id=? AND status='open'", (lead_id,))
    conn.execute("UPDATE playbook_runs SET status='abandoned', completed_at=? WHERE lead_id=? AND status='in_progress'", (now(), lead_id))
    conn.execute("DELETE FROM leads WHERE id=?", (lead_id,))


def _set_stage(conn, lead, to):
    outcome = to if to in CLOSED or to in PARKED else None
    conn.execute("UPDATE leads SET stage=?, outcome=?, updated_at=? WHERE id=?", (to, outcome, now(), lead["id"]))
    lead["stage"], lead["outcome"] = to, outcome


def _advance(conn, lead, to):
    """Move forward through the active pipeline only; never backwards, never out of a closed state."""
    if lead["stage"] in RANK and RANK[lead["stage"]] < RANK[to]:
        _set_stage(conn, lead, to)


def move_stage(conn, lead_id, to, note=None, occurred_at=None) -> dict:
    """Manual stage change (either direction). Moving a closed/parked prospect back to an active stage reopens it."""
    if to not in ALL_STAGES:
        raise ValueError("unknown stage")
    if to in CLOSED or to in PARKED:
        raise ValueError("use 'close' to record an outcome")
    lead = get_lead(conn, lead_id)
    if lead["stage"] == to:
        return lead
    frm = lead["stage"]
    _set_stage(conn, lead, to)
    log(conn, lead_id, "stage_changed", f"Stage: {STAGE_LABEL[frm]} -> {STAGE_LABEL[to]}",
        {"from": frm, "to": to, "note": text(note, 500), "reopened": frm not in RANK}, occurred_at)
    return get_lead(conn, lead_id)


def record_research(conn, lead_id, notes, occurred_at=None) -> dict:
    notes = text(notes, 5000, "notes")
    if not notes:
        raise ValueError("write down what you found")
    lead = get_lead(conn, lead_id)
    conn.execute("UPDATE leads SET research_notes=?, updated_at=? WHERE id=?", (notes, now(), lead_id))
    _advance(conn, lead, "researched")
    log(conn, lead_id, "research_completed", "Research completed", {"notes": notes}, occurred_at)
    return get_lead(conn, lead_id)


def qualify(conn, lead_id, decision, reasons=None, occurred_at=None) -> dict:
    if decision not in ("qualified", "maybe", "not_qualified"):
        raise ValueError("decision must be qualified, maybe or not_qualified")
    lead = get_lead(conn, lead_id)
    conn.execute("UPDATE leads SET qualification=?, updated_at=? WHERE id=?", (decision, now(), lead_id))
    if decision == "qualified":
        _advance(conn, lead, "qualified")
    elif decision == "not_qualified":
        _close_side_effects(conn, lead_id, "not qualified")
        _set_stage(conn, lead, "not_qualified")
    log(conn, lead_id, "qualification_decision", f"Qualification decision: {decision.replace('_', ' ')}",
        {"decision": decision, "reasons": text(reasons, 1000)}, occurred_at)
    return get_lead(conn, lead_id)


def prepare_message(conn, lead_id, channel, angle, body, occurred_at=None) -> dict:
    if channel not in CHANNELS:
        raise ValueError("pick a channel")
    lead = get_lead(conn, lead_id)
    _advance(conn, lead, "outreach_prepared")
    log(conn, lead_id, "message_prepared", f"Message prepared ({channel})",
        {"channel": channel, "angle": text(angle, 120), "text": text(body, 3000)}, occurred_at)
    return get_lead(conn, lead_id)


def record_outreach(conn, lead_id, channel, angle=None, body=None, occurred_at=None, followup_in_days=None) -> dict:
    """The owner reports they sent a message. First one is the initial outreach; later ones are follow-ups."""
    if channel not in CHANNELS:
        raise ValueError("pick a channel")
    lead = get_lead(conn, lead_id)
    prior = conn.execute("SELECT count(*) n FROM activity_events WHERE lead_id=? AND kind='message_sent'", (lead_id,)).fetchone()["n"]
    conn.execute("UPDATE leads SET last_contact_at=?, updated_at=? WHERE id=?", (occurred(occurred_at), now(), lead_id))
    _advance(conn, lead, "contacted" if prior == 0 else "follow_up")  # a closed prospect stays closed until reopened
    log(conn, lead_id, "message_sent", f"{'Initial message' if prior == 0 else 'Follow-up message'} sent ({channel})",
        {"channel": channel, "angle": text(angle, 120), "text": text(body, 3000), "attempt": prior + 1, "initial": prior == 0},
        occurred_at)
    if followup_in_days:
        n = int(followup_in_days)
        if not 1 <= n <= 90:
            raise ValueError("follow-up must be 1 to 90 days away")
        schedule_followup(conn, lead_id, add_days(n, conn), "Follow up on your " + ("first message" if prior == 0 else "last follow-up"))
    return get_lead(conn, lead_id)


def record_response(conn, lead_id, body=None, sentiment="neutral", channel=None, occurred_at=None) -> dict:
    if sentiment not in SENTIMENTS:
        raise ValueError("sentiment must be positive, neutral or negative")
    if channel and channel not in CHANNELS:
        raise ValueError("unknown channel")
    lead = get_lead(conn, lead_id)
    skipped = conn.execute("UPDATE sales_tasks SET status='skipped', outcome='response received', completed_at=? "
                           "WHERE lead_id=? AND kind='follow_up' AND status='open'", (now(), lead_id)).rowcount
    conn.execute("UPDATE leads SET last_contact_at=?, updated_at=? WHERE id=?", (occurred(occurred_at), now(), lead_id))
    _advance(conn, lead, "responded")
    refresh_next_followup(conn, lead_id)
    log(conn, lead_id, "response_received", f"Response received ({sentiment})",
        {"sentiment": sentiment, "text": text(body, 3000), "channel": channel, "followups_skipped": skipped}, occurred_at)
    return get_lead(conn, lead_id)


def record_meeting(conn, lead_id, when, notes=None, held=False, occurred_at=None) -> dict:
    when = check_date(when, "meeting date")
    lead = get_lead(conn, lead_id)
    _advance(conn, lead, "meeting_booked")
    if held:  # the meeting happened, so its "booked" task is finished
        conn.execute("UPDATE sales_tasks SET status='done', outcome='meeting held', completed_at=? WHERE lead_id=? AND kind='meeting' AND status='open'",
                     (now(), lead_id))
    if not held:
        create_task(conn, {"lead_id": lead_id, "title": "Meeting: " + (lead["business"] or lead["name"] or "prospect"), "kind": "meeting",
                           "priority": "high", "due_date": when, "detail": text(notes, 1000)})
    log(conn, lead_id, "meeting_held" if held else "meeting_booked", ("Meeting held " if held else "Meeting booked for ") + when,
        {"when": when, "notes": text(notes, 1000)}, occurred_at)
    return get_lead(conn, lead_id)


def record_proposal(conn, lead_id, value=None, notes=None, occurred_at=None) -> dict:
    v = amount(value, "proposal value")
    lead = get_lead(conn, lead_id)
    if v is not None:
        conn.execute("UPDATE leads SET deal_value=?, updated_at=? WHERE id=?", (v, now(), lead_id))
    _advance(conn, lead, "proposal")
    log(conn, lead_id, "proposal_delivered", "Proposal delivered" + (f" ({lead['currency']} {v})" if v is not None else ""),
        {"value": num(v), "currency": lead["currency"], "notes": text(notes, 1000)}, occurred_at)
    return get_lead(conn, lead_id)


def add_note(conn, lead_id, body) -> dict:
    body = text(body, 3000, "note")
    if not body:
        raise ValueError("write a note first")
    get_lead(conn, lead_id)
    log(conn, lead_id, "note_added", "Note added", {"text": body})
    return get_lead(conn, lead_id)


def _close_side_effects(conn, lead_id, why):
    conn.execute("UPDATE sales_tasks SET status='skipped', outcome=?, completed_at=? WHERE lead_id=? AND status='open'",
                 ("prospect closed: " + why, now(), lead_id))
    conn.execute("UPDATE playbook_runs SET status='abandoned', completed_at=?, outcome_note=? WHERE lead_id=? AND status='in_progress'",
                 (now(), "prospect closed: " + why, lead_id))
    conn.execute("UPDATE leads SET playbook_run_id=NULL, next_followup_at=NULL WHERE id=?", (lead_id,))


def close_prospect(conn, lead_id, outcome, reason=None, revenue=None, resume_date=None, occurred_at=None) -> dict:
    if outcome not in CLOSED and outcome not in PARKED:
        raise ValueError("unknown outcome")
    lead = get_lead(conn, lead_id)
    frm = lead["stage"]
    rev = amount(revenue, "revenue")
    if outcome == "follow_up_later" and not resume_date:
        raise ValueError("pick the date to follow up")
    if resume_date:
        resume_date = check_date(resume_date, "follow-up date")
    reason = text(reason, 1000)
    _close_side_effects(conn, lead_id, outcome.replace("_", " "))
    _set_stage(conn, lead, outcome)
    if outcome == "won" and rev is not None:
        conn.execute("UPDATE leads SET revenue_won=? WHERE id=?", (rev, lead_id))
    detail = {"outcome": outcome, "reason": reason, "stage_at_close": frm}
    if outcome == "won":
        log(conn, lead_id, "deal_won", "Customer won" + (f" - {lead['currency']} {rev} recorded (owner-reported, not verified)" if rev is not None else ""),
            {**detail, "revenue": num(rev), "currency": lead["currency"]}, occurred_at)
    elif outcome == "lost":
        log(conn, lead_id, "deal_lost", "Deal lost" + (f": {reason}" if reason else ""), detail, occurred_at)
    else:
        log(conn, lead_id, "outcome_recorded", "Outcome: " + outcome.replace("_", " "), {**detail, "resume_date": resume_date}, occurred_at)
    if resume_date and outcome in PARKED:
        schedule_followup(conn, lead_id, resume_date, "Revisit: " + outcome.replace("_", " "))
    return get_lead(conn, lead_id)


# ---------------------------------------------------------------- tasks ---------------------------------------------

def refresh_next_followup(conn, lead_id):
    r = conn.execute("SELECT min(due_date) d FROM sales_tasks WHERE lead_id=? AND kind='follow_up' AND status='open'", (lead_id,)).fetchone()
    conn.execute("UPDATE leads SET next_followup_at=? WHERE id=?", (r["d"], lead_id))


def create_task(conn, data: dict) -> dict:
    title = text(data.get("title"), 200, "title")
    if not title:
        raise ValueError("give the task a title")
    kind = data.get("kind") or "other"
    if kind not in TASK_KINDS:
        raise ValueError("unknown task type")
    pr = data.get("priority", "normal")
    pr = PRIORITY.get(pr) if isinstance(pr, str) else pr
    if pr not in (1, 2, 3):
        raise ValueError("priority must be high, normal or low")
    due = check_date(data["due_date"], "due date") if data.get("due_date") else today(conn)
    lead_id = data.get("lead_id") or None
    if lead_id:
        get_lead(conn, lead_id)
    tid = new_id("tk")
    conn.execute("INSERT INTO sales_tasks(id,lead_id,title,detail,kind,priority,due_date,playbook_id,run_id,step_id,created_at) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 (tid, lead_id, title, text(data.get("detail"), 1000), kind, pr, due, data.get("playbook_id"), data.get("run_id"),
                  data.get("step_id"), now()))
    if kind == "follow_up" and lead_id:
        refresh_next_followup(conn, lead_id)
    return get_task(conn, tid)


def get_task(conn, tid) -> dict:
    r = conn.execute("SELECT t.*, l.business AS lead_business, l.name AS lead_name, p.name AS playbook_name FROM sales_tasks t "
                     "LEFT JOIN leads l ON l.id=t.lead_id LEFT JOIN playbooks p ON p.id=t.playbook_id WHERE t.id=?", (tid,)).fetchone()
    if not r:
        raise NotFound("task not found")
    return _clean(r)


def schedule_followup(conn, lead_id, due_date, note=None, priority="normal") -> dict:
    due_date = check_date(due_date, "follow-up date")
    lead = get_lead(conn, lead_id)
    who = lead["business"] or lead["name"] or "prospect"
    t = create_task(conn, {"lead_id": lead_id, "title": f"Follow up: {who}", "kind": "follow_up", "due_date": due_date,
                           "priority": priority, "detail": text(note, 1000)})
    log(conn, lead_id, "followup_scheduled", f"Follow-up scheduled for {due_date}", {"due_date": due_date, "note": text(note, 500)},
        task_id=t["id"])
    return t


def close_task(conn, tid, status, outcome=None) -> dict:
    """Low level: mark a task done/skipped without logging (callers log the right event)."""
    t = get_task(conn, tid)
    if t["status"] != "open":
        raise ValueError("that task is already " + t["status"])
    conn.execute("UPDATE sales_tasks SET status=?, outcome=?, completed_at=? WHERE id=?", (status, text(outcome, 1000), now(), tid))
    if t["lead_id"] and t["kind"] == "follow_up":
        refresh_next_followup(conn, t["lead_id"])
    return t


def complete_task(conn, tid, outcome=None, occurred_at=None) -> dict:
    t = get_task(conn, tid)
    if t["status"] != "open":
        raise ValueError("that task is already " + t["status"])
    if t["run_id"] and t["step_id"]:  # a playbook step: completing it completes the step (which closes the task)
        from core.sales import playbooks
        playbooks.set_step(conn, t["run_id"], t["step_id"], True, outcome)
        return get_task(conn, tid)
    close_task(conn, tid, "done", outcome)
    kind = "followup_completed" if t["kind"] == "follow_up" else "task_completed"
    log(conn, t["lead_id"], kind, ("Follow-up completed" if t["kind"] == "follow_up" else "Task completed") + ": " + t["title"],
        {"outcome": text(outcome, 1000), "kind": t["kind"]}, occurred_at, task_id=tid)
    return get_task(conn, tid)


def skip_task(conn, tid, outcome=None) -> dict:
    t = close_task(conn, tid, "skipped", outcome)
    log(conn, t["lead_id"], "task_skipped", "Task skipped: " + t["title"], {"outcome": text(outcome, 1000)}, task_id=tid)
    return get_task(conn, tid)


def list_tasks(conn, status="open", lead_id=None, limit=200) -> list[dict]:
    q = ("SELECT t.*, l.business AS lead_business, l.name AS lead_name, p.name AS playbook_name FROM sales_tasks t "
         "LEFT JOIN leads l ON l.id=t.lead_id LEFT JOIN playbooks p ON p.id=t.playbook_id WHERE 1=1")
    args = []
    if status:
        q += " AND t.status=?"
        args.append(status)
    if lead_id:
        q += " AND t.lead_id=?"
        args.append(lead_id)
    q += " ORDER BY t.priority, t.due_date, t.created_at LIMIT ?"
    return [_clean(r) for r in conn.execute(q, (*args, min(limit, 500)))]


# ---------------------------------------------------------------- reads ---------------------------------------------

def list_prospects(conn, stage=None, q=None, limit=300) -> list[dict]:
    sql, args = f"SELECT {LEAD_COLS} FROM leads WHERE 1=1", []
    if stage:
        if stage not in ALL_STAGES:
            raise ValueError("unknown stage")
        sql += " AND stage=?"
        args.append(stage)
    if q:
        sql += " AND (lower(coalesce(business,'')) LIKE ? OR lower(coalesce(name,'')) LIKE ?)"
        like = "%" + q.lower()[:60].replace("%", "") + "%"
        args += [like, like]
    sql += " ORDER BY coalesce(updated_at, created_at) DESC LIMIT ?"
    return [_clean(r) for r in conn.execute(sql, (*args, min(limit, 500)))]


def timeline(conn, lead_id, limit=1000) -> list[dict]:
    rows = conn.execute("SELECT id,at,occurred_at,lead_id,kind,summary,detail,task_id,run_id,actor FROM activity_events "
                        "WHERE lead_id=? ORDER BY id LIMIT ?", (lead_id, limit)).fetchall()
    return [parse_event(r) for r in rows]


def business_activity(conn, limit=100, before_id=None) -> list[dict]:
    q = ("SELECT e.id,e.at,e.occurred_at,e.lead_id,e.kind,e.summary,e.detail,e.task_id,e.run_id,e.actor, l.business, l.name "
         "FROM activity_events e LEFT JOIN leads l ON l.id=e.lead_id")
    args = []
    if before_id:
        q += " WHERE e.id < ?"
        args.append(int(before_id))
    q += " ORDER BY e.id DESC LIMIT ?"
    return [parse_event(r) for r in conn.execute(q, (*args, min(limit, 300)))]


def prospect_view(conn, lead_id) -> dict:
    from core.sales import playbooks
    lead = get_lead(conn, lead_id)
    runs = playbooks.runs_for_lead(conn, lead_id)
    active = next((r for r in runs if r["status"] == "in_progress"), None)
    return {"prospect": lead, "stage_label": STAGE_LABEL.get(lead["stage"], lead["stage"]), "timeline": timeline(conn, lead_id),
            "tasks": list_tasks(conn, "open", lead_id), "runs": runs, "active_run": active}
