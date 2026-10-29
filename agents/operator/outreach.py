"""Outreach drafting (spec section 9-13). Every lead comes from the owner, never from automated
scraping: the only writer of the leads table is the owner-supplied import endpoint. A draft is
never sent by this code; it is queued as a USER_ACTION and the owner sends it themselves (or, once
an email-sending integration is approved, approves a batch send) - SEND_OUTREACH always needs
owner_approved in core.policy.policy.
"""

import csv
import io
import re
import uuid

from agents.operator.drafts import FILL
from core import challenge
from core.audit import audit
from core.db import now
from core.orchestrator.killswitch import is_paused
from core.policy.policy import Action, Agent, authorize
from integrations import gmail

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_IMPORT_ROWS = 500


class ImportError_(ValueError):
    pass


class SendError(ValueError):
    pass


def parse_subject_body(draft: str) -> tuple[str, str]:
    """Splits a draft of the shape 'Subject: ...\\n\\n<body>' into (subject, body)."""
    draft = draft or ""
    if draft.lower().startswith("subject:"):
        first, _, rest = draft.partition("\n")
        return first[len("subject:"):].strip(), rest.lstrip("\n")
    return "Following up", draft


def parse_csv(text: str) -> list[dict]:
    """name,business,email,phone,notes - header required, email mandatory and validated.
    Never silently drops a bad row: raises with the row number so the owner can fix it."""
    if len(text.encode()) > 200_000:
        raise ImportError_("file too large")
    reader = csv.DictReader(io.StringIO(text))
    required = {"name", "business", "email"}
    if reader.fieldnames is None or not required.issubset({f.strip().lower() for f in reader.fieldnames}):
        raise ImportError_("header must include at least: name,business,email (phone,notes optional)")
    rows = []
    for i, raw in enumerate(reader, start=2):
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(row.values()):
            continue
        if i - 1 > MAX_IMPORT_ROWS:
            raise ImportError_(f"too many rows (max {MAX_IMPORT_ROWS})")
        email = row.get("email", "")
        if not EMAIL_RE.match(email):
            raise ImportError_(f"row {i}: '{email}' is not a valid email address")
        rows.append({"name": row.get("name", ""), "business": row.get("business", ""), "email": email,
                     "phone": row.get("phone", ""), "notes": row.get("notes", "")})
    if not rows:
        raise ImportError_("no usable rows found")
    return rows


def import_leads(conn, owner: str, csv_text: str, venture: str = "buildflow") -> dict:
    if venture not in challenge.VENTURES:
        raise ImportError_("venture must be buildflow or agriloop")
    rows = parse_csv(csv_text)
    added = skipped = 0
    for r in rows:
        lid = "lead_" + uuid.uuid4().hex[:12]
        cur = conn.execute(
            "INSERT INTO leads(id,name,business,email,phone,notes,venture,channel,created_at) VALUES (?,?,?,?,?,?,?,'email',?) "
            "ON CONFLICT (lower(email)) WHERE email IS NOT NULL AND email <> '' DO NOTHING",
            (lid, r["name"], r["business"], r["email"], r["phone"], r["notes"], venture, now()))
        added += cur.rowcount
        skipped += 1 - cur.rowcount
    audit(conn, owner, "leads.import", None, f"venture={venture} added={added} skipped_duplicates={skipped} rows={len(rows)}")
    return {"added": added, "skipped_duplicates": skipped, "total_rows": len(rows)}


def draft_outreach(lead: dict) -> str:
    """Short, specific, low-pressure cold email. Never invents a reason the recipient should care,
    a relationship, or a claim about their business - those are left as [OWNER TO FILL]. Built
    around a few things that consistently work better than generic cold-outreach copy: one subject
    line that names the business (not a pitch), a single concrete offer instead of a feature list,
    an easy yes/no close, and no attachments or links that would get it flagged as spam."""
    name = lead["name"] or "there"
    business = lead["business"] or "your business"
    lines = [
        f"Subject: a quick idea for {business}",
        "",
        f"Hi {name},",
        "",
        f"{FILL} (one honest, specific sentence on why you're reaching out to {business} - something "
        "true you noticed about how they run, not a template compliment like \"I love what you do\").",
        "",
        "I build small, practical tools for local businesses - the kind of thing that answers a missed "
        "call with a text, or gives customers one link to see your work and book you. No big pitch: "
        "I'd like to put together a working example built around your business, free, so you can "
        "actually see it before deciding if it's worth anything.",
        "",
        f"{FILL} (if you have a live example or case study ready, link it here; otherwise delete this line).",
        "",
        f"Worth a quick look? If not, no worries - just reply 'not now' and I'll leave it there.",
        "",
        f"{FILL} (your name and number)",
    ]
    return "\n".join(lines)


def send_outreach(conn, action_id: str, owner: str, edited_body: str | None = None) -> dict:
    """Sends one approved outreach email through Gmail. Requires the action to already be APPROVED
    (the owner's sign-off) - core.policy.policy keeps SEND_OUTREACH in APPROVAL_REQUIRED_ACTIONS, so
    this is refused even on an OPEN action. If edited_body is given (the owner's edit before
    sending), it replaces the stored draft so the record matches what was actually sent."""
    if not authorize(Agent.OPERATOR, Action.SEND_OUTREACH, paused=is_paused(conn), owner_approved=True).allowed:
        raise SendError("system is paused")
    a = conn.execute("SELECT * FROM user_actions WHERE action_id=?", (action_id,)).fetchone()
    if a is None:
        raise SendError("action not found")
    if a["kind"] != "send_outreach":
        raise SendError("this action is not outreach")
    if a["status"] != "APPROVED":
        raise SendError("approve the draft before sending it")
    if not action_id.startswith("ua_lead_"):
        raise SendError("no lead is attached to this action")
    lead = conn.execute("SELECT * FROM leads WHERE id=?", (action_id[len("ua_lead_"):],)).fetchone()
    if lead is None:
        raise SendError("lead not found")
    if lead["stage"] == "lost" or lead["status"] == "SKIPPED":
        raise SendError("this lead opted out or was marked lost; do not contact them again")
    if not lead["email"]:
        raise SendError("this lead has no email address")
    text = (edited_body or a["exact_action"] or "").strip()
    if not text:
        raise SendError("draft is empty")
    subject, body = parse_subject_body(text)
    if edited_body is not None:
        conn.execute("UPDATE user_actions SET exact_action=? WHERE action_id=?", (text, action_id))
    try:
        result = gmail.send_email(lead["email"], subject, body)
    except gmail.GmailError as e:
        raise SendError(str(e)) from e
    conn.execute("UPDATE user_actions SET status='DONE', resolved_at=? WHERE action_id=?", (now(), action_id))
    conn.execute("UPDATE leads SET status='SENT' WHERE id=?", (lead["id"],))
    challenge.log_touch(conn, owner, lead["id"], "email", "sent", "out", text)
    audit(conn, owner, "action.sent_via_gmail", action_id, result["message_id"])
    return {"sent": True, "message_id": result["message_id"]}


def send_submission_email(conn, action_id: str, owner: str, to_email: str, edited_body: str | None = None) -> dict:
    """Submits a job application/proposal by email, for a listing whose contact method is email
    rather than a platform login - the owner supplies the address (nothing here guesses or scrapes
    one). Same hard gate as outreach: core.policy.policy keeps SUBMIT_APPLICATION in
    APPROVAL_REQUIRED_ACTIONS, so this is refused on anything not already APPROVED. On success it
    goes through the same mark_submitted path a manual submission does (so Treasury starts
    watching for payment), with the Gmail message id as proof instead of a submission URL."""
    if not authorize(Agent.OPERATOR, Action.SUBMIT_APPLICATION, paused=is_paused(conn), owner_approved=True).allowed:
        raise SendError("system is paused")
    to_email = (to_email or "").strip()
    if not EMAIL_RE.match(to_email):
        raise SendError("a valid recipient email is required")
    a = conn.execute("SELECT * FROM user_actions WHERE action_id=?", (action_id,)).fetchone()
    if a is None:
        raise SendError("action not found")
    if a["kind"] == "send_outreach":
        raise SendError("use send_outreach for outreach, not a job submission")
    if a["status"] != "APPROVED":
        raise SendError("approve the draft before sending it")
    text = (edited_body or a["exact_action"] or "").strip()
    if not text:
        raise SendError("draft is empty")
    subject, body = parse_subject_body(text)
    if edited_body is not None:
        conn.execute("UPDATE user_actions SET exact_action=? WHERE action_id=?", (text, action_id))
    try:
        result = gmail.send_email(to_email, subject, body)
    except gmail.GmailError as e:
        raise SendError(str(e)) from e
    from core.actions import mark_submitted
    mark_submitted(conn, action_id, owner, "")
    audit(conn, owner, "action.submitted_via_gmail", action_id, f"to={to_email} message_id={result['message_id']}")
    return {"sent": True, "message_id": result["message_id"]}


def send_outreach_batch(conn, owner: str, action_ids: list[str]) -> dict:
    """Sends several already-approved outreach emails in one owner-triggered call. Each one still
    individually requires APPROVED status - this never sends anything the owner hasn't personally
    approved, it just lets them do several at once instead of one click per email."""
    sent, failed = [], []
    for aid in dict.fromkeys(action_ids):
        try:
            send_outreach(conn, aid, owner)
            sent.append(aid)
        except SendError as e:
            failed.append({"action_id": aid, "error": str(e)})
    return {"sent": len(sent), "failed": failed}
