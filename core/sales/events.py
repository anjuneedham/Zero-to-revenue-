"""Shared pieces of the sales system: constants, validation, and the append-only activity log.

History is never rewritten. `at` is when something was recorded (set by the server, immutable via a
database trigger); `occurred_at` is when it actually happened (owner-supplied, so earlier work can be
back-filled honestly). A correction is a new event, not an edit."""

import json
import os
import re
import uuid
from zoneinfo import ZoneInfo
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from core.db import now


class NotFound(Exception):
    pass


STAGES = [("identified", "Prospect identified"), ("researched", "Research"), ("qualified", "Qualified"),
          ("outreach_prepared", "Outreach prepared"), ("contacted", "Contacted"), ("follow_up", "Follow-up"),
          ("responded", "Response received"), ("conversation", "Conversation"), ("meeting_booked", "Meeting booked"),
          ("proposal", "Proposal"), ("negotiation", "Negotiation")]
ACTIVE = [s for s, _ in STAGES]
RANK = {s: i for i, s in enumerate(ACTIVE)}
CLOSED = ("won", "lost", "not_interested", "not_qualified", "no_response", "unreachable")
PARKED = ("future_opportunity", "follow_up_later")
ALL_STAGES = ACTIVE + list(CLOSED) + list(PARKED)
STAGE_LABEL = dict(STAGES, won="Customer won", lost="Lost", not_interested="Not interested", not_qualified="Not qualified",
                   no_response="No response", unreachable="Unreachable", future_opportunity="Future opportunity",
                   follow_up_later="Follow up later")
CHANNELS = ("email", "whatsapp", "instagram", "facebook", "linkedin", "phone", "sms", "in_person", "other")
SENTIMENTS = ("positive", "neutral", "negative")
PRIORITY = {"high": 1, "normal": 2, "low": 3}
TASK_KINDS = ("follow_up", "research", "outreach", "qualify", "meeting", "proposal", "playbook", "daily", "other")

PROSPECT_FIELDS = ("name", "business", "email", "phone", "contact_other", "website", "industry", "location",
                   "source_channel", "offer", "research_notes", "notes", "deal_value", "currency")
PII_FIELDS = ("name", "email", "phone", "contact_other")  # changes are logged as "changed", never with values
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def text(v, limit=2000, field="field") -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError(f"{field} must be text")
    v = v.strip()
    return v[:limit] or None


def tz_name(conn=None) -> str:
    """The owner's timezone decides what 'today' means. Setting 'sales_timezone', else $SALES_TIMEZONE, else UTC."""
    name = ""
    if conn is not None:
        r = conn.execute("SELECT value FROM settings WHERE key='sales_timezone'").fetchone()
        name = r["value"] if r else ""
    for cand in (name, os.environ.get("SALES_TIMEZONE", ""), "UTC"):
        try:
            ZoneInfo(cand)
            return cand
        except Exception:
            continue
    return "UTC"


def today(conn=None) -> str:
    return datetime.now(ZoneInfo(tz_name(conn))).date().isoformat()


def local_date(iso: str, conn=None) -> str:
    try:
        dt = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZoneInfo(tz_name(conn))).date().isoformat()


def check_date(v, field="date") -> str:
    if not isinstance(v, str) or not _DATE.match(v):
        raise ValueError(f"{field} must look like 2026-11-30")
    try:
        date.fromisoformat(v)
    except ValueError:
        raise ValueError(f"{field} is not a real date") from None
    return v


def add_days(n: int, conn=None) -> str:
    return (date.fromisoformat(today(conn)) + timedelta(days=n)).isoformat()


def amount(v, field="amount"):
    if v in (None, ""):
        return None
    try:
        d = Decimal(str(v))
    except InvalidOperation:
        raise ValueError(f"{field} must be a number") from None
    if d < 0 or d > Decimal("100000000"):
        raise ValueError(f"{field} must be between 0 and 100,000,000")
    return d


def occurred(v) -> str:
    """When it happened. Date or ISO datetime; may be in the past (back-fill), not meaningfully in the future."""
    if v in (None, ""):
        return now()
    if not isinstance(v, str):
        raise ValueError("occurred_at must be text")
    try:
        dt = datetime.fromisoformat(v + "T12:00:00+00:00") if _DATE.match(v) else datetime.fromisoformat(v)
    except ValueError:
        raise ValueError("occurred_at must be a date like 2026-11-02") from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if dt > datetime.now(timezone.utc) + timedelta(days=1):
        raise ValueError("occurred_at cannot be in the future")
    return dt.isoformat()


def num(v):
    return float(v) if isinstance(v, Decimal) else v


def log(conn, lead_id, kind, summary, detail=None, occurred_at=None, task_id=None, run_id=None, actor="owner"):
    """Append one event. stage_after is stamped from the prospect's current stage so playback can show
    the state at that moment without recomputing."""
    d = dict(detail or {})
    if lead_id and "stage_after" not in d:
        r = conn.execute("SELECT stage FROM leads WHERE id=?", (lead_id,)).fetchone()
        if r:
            d["stage_after"] = r["stage"]
    ts = now()
    conn.execute("INSERT INTO activity_events(at,occurred_at,lead_id,kind,summary,detail,task_id,run_id,actor) "
                 "VALUES (?,?,?,?,?,?,?,?,?)",
                 (ts, occurred(occurred_at) if occurred_at else ts, lead_id, kind, summary[:300],
                  json.dumps(d, default=str), task_id, run_id, actor))


def parse_event(r) -> dict:
    d = dict(r)
    try:
        d["detail"] = json.loads(d.get("detail") or "{}")
    except ValueError:
        d["detail"] = {}
    return d
