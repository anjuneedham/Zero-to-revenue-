"""The 60-day cash challenge (1 Nov - 31 Dec 2026): target, offers, prospect pipeline, touches, deals.
Cash counted here is only what Treasury verified (ledger_entries receipts, VERIFIED, with a USD value) inside
the challenge window. A deal that has not been paid and verified is pipeline, never cash."""

import json
import math
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from agents.operator import pitches
from core.audit import audit
from core.db import money, now

VENTURES = ("buildflow", "agriloop")
STAGES = ("new", "contacted", "replied", "onboarding_booked", "trial", "paying", "lost")
OPEN_STAGES = ("new", "contacted", "replied", "onboarding_booked", "trial")
OUTCOMES = ("sent", "replied", "booked", "declined", "paid", "no_reply")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FOLLOW_UP_DAYS = 3

# Annual = 12 x the $50 monthly BuildFlow price; the two free months are on top. Agriloop has no fixed price
# anywhere in its repo (admin-set per country), so it stays unset until the owner decides.
DEFAULT_CONFIG = {
    "start": "2026-11-01", "end": "2026-12-31", "target_usd": 10000,
    "offers": {
        "buildflow": {"monthly_usd": 50, "annual_usd": 600, "free_months": 2},
        "agriloop": {"monthly_usd": None, "annual_usd": None, "free_months": 2},
    },
}

# Facts from each product's own readiness reports (25-28 Oct). Shown on the Challenge page so a sale is never
# made on a promise the product cannot keep.
BLOCKERS = {
    "buildflow": ["Firebase Storage is not provisioned: photo/file uploads fail until it is on (needs the Blaze plan)",
                  "No billing: take the first payments by PayPal/bank transfer and mark them paid here",
                  "Legal pages are placeholders; production refuses to start without company details",
                  "Never run on a real phone; no push notifications for new leads"],
    "agriloop": ["Marketplace data is in-memory demo data (AGRILOOP_DATA_SOURCE=memory): not safe for real customers yet",
                 "No automated tests; Prisma data adapter is the biggest remaining item",
                 "No subscription price exists in code: set one in the offer before selling"],
}


class ChallengeError(ValueError):
    pass


def _num(v, field, allow_none=False):
    if v is None or v == "":
        if allow_none:
            return None
        raise ChallengeError(f"{field} is required")
    try:
        d = Decimal(str(v))
    except InvalidOperation:
        raise ChallengeError(f"{field} must be a number") from None
    if d <= 0 or d > 1_000_000:
        raise ChallengeError(f"{field} must be between 0 and 1,000,000")
    return float(d)


def get_config(conn) -> dict:
    row = conn.execute("SELECT value FROM settings WHERE key='challenge'").fetchone()
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if row:
        try:
            saved = json.loads(row["value"])
            for k in ("start", "end", "target_usd"):
                cfg[k] = saved.get(k, cfg[k])
            for v in VENTURES:
                cfg["offers"][v].update(saved.get("offers", {}).get(v, {}))
        except (ValueError, AttributeError):
            pass
    return cfg


def set_config(conn, owner: str, data: dict) -> dict:
    cfg = get_config(conn)
    try:
        s, e = date.fromisoformat(str(data.get("start", cfg["start"]))), date.fromisoformat(str(data.get("end", cfg["end"])))
    except ValueError:
        raise ChallengeError("dates must look like 2026-11-01") from None
    if e <= s or (e - s).days > 400:
        raise ChallengeError("end must be after start")
    cfg["start"], cfg["end"] = s.isoformat(), e.isoformat()
    cfg["target_usd"] = _num(data.get("target_usd", cfg["target_usd"]), "target")
    for v in VENTURES:
        o = (data.get("offers") or {}).get(v)
        if o is None:
            continue
        cur = cfg["offers"][v]
        cur["annual_usd"] = _num(o.get("annual_usd"), f"{v} annual price", allow_none=True)
        cur["monthly_usd"] = _num(o.get("monthly_usd"), f"{v} monthly price", allow_none=True)
        fm = o.get("free_months", cur["free_months"])
        if not isinstance(fm, int) or isinstance(fm, bool) or not 0 <= fm <= 12:
            raise ChallengeError("free months must be a whole number from 0 to 12")
        cur["free_months"] = fm
    conn.execute("INSERT INTO settings(key, value, updated_at) VALUES ('challenge', ?, ?) ON CONFLICT (key) DO UPDATE "
                 "SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at", (json.dumps(cfg), now()))
    audit(conn, owner, "challenge.config", None, f"target={cfg['target_usd']} {cfg['start']}..{cfg['end']}")
    return cfg


# ---- leads ------------------------------------------------------------------------------------------------

def _clip(v, n):
    return (v or "").strip()[:n] if isinstance(v, str) or v is None else str(v)[:n]


def add_lead(conn, owner: str, d: dict) -> dict:
    venture = d.get("venture", "buildflow")
    if venture not in VENTURES:
        raise ChallengeError("venture must be buildflow or agriloop")
    name, business = _clip(d.get("name"), 120), _clip(d.get("business"), 160)
    email, phone = _clip(d.get("email"), 160), _clip(d.get("phone"), 40)
    if not (name or business):
        raise ChallengeError("a name or business is required")
    if email and not EMAIL_RE.match(email):
        raise ChallengeError(f"'{email}' is not a valid email address")
    if not (email or phone or d.get("channel")):
        raise ChallengeError("add at least an email, a phone/WhatsApp number or the channel you found them on")
    lid = "lead_" + uuid.uuid4().hex[:12]
    cur = conn.execute(
        "INSERT INTO leads(id,name,business,email,phone,notes,source,venture,segment,location,channel,created_at) "
        "VALUES (?,?,?,?,?,?,'owner_supplied',?,?,?,?,?) ON CONFLICT (lower(email)) WHERE email IS NOT NULL AND email <> '' DO NOTHING",
        (lid, name, business, email or None, phone, _clip(d.get("notes"), 1000), venture, _clip(d.get("segment"), 80),
         _clip(d.get("location"), 80), _clip(d.get("channel"), 30) or None, now()))
    if not cur.rowcount:
        raise ChallengeError("a lead with that email already exists")
    audit(conn, owner, "challenge.lead_add", lid, f"{venture} {business or name}")
    return {"id": lid}


def set_stage(conn, owner: str, lead_id: str, stage: str, reason: str = "", next_days=None) -> dict:
    if stage not in STAGES:
        raise ChallengeError("unknown stage")
    lead = conn.execute("SELECT id, status FROM leads WHERE id=?", (lead_id,)).fetchone()
    if lead is None:
        raise ChallengeError("lead not found")
    status = "SKIPPED" if stage == "lost" else lead["status"]
    nxt = None
    if next_days is not None:
        if not isinstance(next_days, int) or isinstance(next_days, bool) or not 0 <= next_days <= 90:
            raise ChallengeError("next action must be 0-90 days")
        nxt = (datetime.now(timezone.utc) + timedelta(days=next_days)).isoformat()
    elif stage in ("contacted", "replied"):
        nxt = (datetime.now(timezone.utc) + timedelta(days=FOLLOW_UP_DAYS)).isoformat()
    conn.execute("UPDATE leads SET stage=?, status=?, lost_reason=?, next_action_at=? WHERE id=?",
                 (stage, status, _clip(reason, 200) or None if stage == "lost" else None,
                  None if stage in ("paying", "lost") else nxt, lead_id))
    audit(conn, owner, "challenge.stage", lead_id, stage)
    return {"ok": True}


def log_touch(conn, owner: str, lead_id: str, channel: str, outcome: str = "sent", direction: str = "out", body: str = "") -> dict:
    if channel not in pitches.channels():
        raise ChallengeError("unknown channel")
    if outcome not in OUTCOMES:
        raise ChallengeError("unknown outcome")
    if direction not in ("out", "in"):
        raise ChallengeError("direction must be out or in")
    lead = conn.execute("SELECT id, stage FROM leads WHERE id=?", (lead_id,)).fetchone()
    if lead is None:
        raise ChallengeError("lead not found")
    conn.execute("INSERT INTO lead_touches(id,lead_id,channel,direction,body,outcome,created_at) VALUES (?,?,?,?,?,?,?)",
                 ("tch_" + uuid.uuid4().hex[:12], lead_id, channel, direction, _clip(body, 4000), outcome, now()))
    conn.execute("UPDATE leads SET last_contacted_at=?, channel=COALESCE(channel, ?) WHERE id=?", (now(), channel, lead_id))
    # A touch moves the lead forward, never backward, and never resurrects a lost/paying lead.
    forward = {"sent": "contacted", "no_reply": "contacted", "replied": "replied", "booked": "onboarding_booked"}.get(outcome)
    order = {s: i for i, s in enumerate(STAGES)}
    if forward and lead["stage"] not in ("lost", "paying") and order[forward] > order[lead["stage"]]:
        set_stage(conn, owner, lead_id, forward)
    elif outcome == "declined":
        set_stage(conn, owner, lead_id, "lost", "declined")
    elif forward and lead["stage"] == "contacted" and outcome in ("sent", "no_reply"):
        conn.execute("UPDATE leads SET next_action_at=? WHERE id=?",
                     ((datetime.now(timezone.utc) + timedelta(days=FOLLOW_UP_DAYS)).isoformat(), lead_id))
    audit(conn, owner, "challenge.touch", lead_id, f"{channel} {direction} {outcome}")
    return {"ok": True}


def draft_for(conn, lead_id: str, channel: str = "email", follow_up: bool = False) -> dict:
    if channel not in pitches.channels():
        raise ChallengeError("unknown channel")
    lead = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if lead is None:
        raise ChallengeError("lead not found")
    offer = get_config(conn)["offers"][lead["venture"]]
    fn = pitches.follow_up if follow_up else pitches.draft
    return {"draft": fn(dict(lead), offer, channel), "channel": channel}


# ---- deals ------------------------------------------------------------------------------------------------

def create_deal(conn, owner: str, lead_id: str, amount=None) -> dict:
    """Records a sale and creates the payment Treasury will verify (PayPal link / on-chain). The amount defaults
    to the venture's annual price; Agriloop has none until the owner sets one."""
    from dashboard.api_data import create_manual_payment  # same anchor every other manual payment uses

    lead = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if lead is None:
        raise ChallengeError("lead not found")
    if conn.execute("SELECT 1 FROM deals WHERE lead_id=? AND status<>'cancelled'", (lead_id,)).fetchone():
        raise ChallengeError("this lead already has a deal")
    offer = get_config(conn)["offers"][lead["venture"]]
    amt = _num(amount if amount not in (None, "") else offer.get("annual_usd"), "amount")
    label = pitches.PRODUCT[lead["venture"]]["name"]
    who = lead["business"] or lead["name"] or "customer"
    pay = create_manual_payment(conn, owner, f"{label} annual plan - {who}", str(amt), "USD", who)
    did = "deal_" + uuid.uuid4().hex[:12]
    conn.execute("INSERT INTO deals(id,lead_id,venture,amount_usd,free_months,payment_id,created_at) VALUES (?,?,?,?,?,?,?)",
                 (did, lead_id, lead["venture"], amt, int(offer.get("free_months") or 0), pay["payment_id"], now()))
    audit(conn, owner, "challenge.deal", did, f"{lead['venture']} {amt}")
    return {"deal_id": did, "payment_id": pay["payment_id"], "amount_usd": amt}


def set_onboarding(conn, owner: str, deal_id: str, status: str) -> dict:
    if status not in ("to_schedule", "scheduled", "done"):
        raise ChallengeError("bad onboarding status")
    if not conn.execute("UPDATE deals SET onboarding_status=? WHERE id=?", (status, deal_id)).rowcount:
        raise ChallengeError("deal not found")
    audit(conn, owner, "challenge.onboarding", deal_id, status)
    return {"ok": True}


def _sync_paid(conn):
    """A deal is paid only when Treasury has verified its payment. Pulls that fact into deals and leads."""
    rows = conn.execute("SELECT d.id, d.lead_id, p.verified_at FROM deals d JOIN payments p ON p.id=d.payment_id "
                        "WHERE d.status='open' AND p.status='PAYMENT_VERIFIED'").fetchall()
    for r in rows:
        conn.execute("UPDATE deals SET status='paid', paid_at=? WHERE id=?", (r["verified_at"] or now(), r["id"]))
        conn.execute("UPDATE leads SET stage='paying', next_action_at=NULL WHERE id=?", (r["lead_id"],))


# ---- the numbers --------------------------------------------------------------------------------------------

def summary(conn, today: date | None = None) -> dict:
    _sync_paid(conn)
    cfg = get_config(conn)
    today = today or datetime.now(timezone.utc).date()
    start, end = date.fromisoformat(cfg["start"]), date.fromisoformat(cfg["end"])
    total_days = (end - start).days + 1
    elapsed = min(max((today - start).days + 1, 0), total_days)
    window_end = (end + timedelta(days=1)).isoformat()
    cash = money(conn.execute(
        "SELECT COALESCE(SUM(usd_value),0) FROM ledger_entries WHERE type='receipt' AND status='VERIFIED' AND date >= ? AND date < ?",
        (cfg["start"], window_end)).fetchone()[0])
    target = float(cfg["target_usd"])
    remaining = max(0.0, target - cash)
    pace_target = target * elapsed / total_days
    paid = conn.execute("SELECT count(*) n, COALESCE(avg(amount_usd),0) a FROM deals WHERE status='paid'").fetchone()
    prices = [o["annual_usd"] for o in cfg["offers"].values() if o.get("annual_usd")]
    avg_deal = float(paid["a"]) if paid["n"] else (min(prices) if prices else 0)
    open_deals = conn.execute("SELECT count(*) n, COALESCE(sum(amount_usd),0) s FROM deals WHERE status='open'").fetchone()
    days_left = max(0, (end - max(today, start)).days + 1) if today <= end else 0

    funnel = {v: {s: 0 for s in STAGES} for v in VENTURES}
    for r in conn.execute("SELECT venture, stage, count(*) n FROM leads GROUP BY venture, stage"):
        funnel[r["venture"]][r["stage"]] = r["n"]

    t0 = datetime.now(timezone.utc).isoformat()
    due = [dict(r) for r in conn.execute(
        "SELECT id,name,business,venture,stage,channel,email,phone,next_action_at,last_contacted_at FROM leads "
        "WHERE stage IN ('new','contacted','replied','onboarding_booked','trial') "
        "AND (stage='new' OR (next_action_at IS NOT NULL AND next_action_at <= ?)) "
        "ORDER BY (stage='replied') DESC, (stage='onboarding_booked') DESC, (stage='new'), next_action_at, created_at LIMIT 15", (t0,))]
    week = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    touches_week = conn.execute("SELECT count(*) FROM lead_touches WHERE direction='out' AND created_at >= ?", (week,)).fetchone()[0]
    by_channel = [dict(r) for r in conn.execute(
        "SELECT t.channel, count(*) FILTER (WHERE t.direction='out') AS sent, "
        "count(DISTINCT t.lead_id) FILTER (WHERE t.outcome IN ('replied','booked','paid')) AS replies, "
        "count(DISTINCT t.lead_id) FILTER (WHERE l.stage='paying') AS paying "
        "FROM lead_touches t JOIN leads l ON l.id=t.lead_id GROUP BY t.channel ORDER BY sent DESC")]
    deals = [dict((k, (float(v) if isinstance(v, Decimal) else v)) for k, v in dict(r).items()) for r in conn.execute(
        "SELECT d.id,d.venture,d.amount_usd,d.status,d.onboarding_status,d.payment_id,d.created_at,d.paid_at,d.free_months,"
        "l.business,l.name FROM deals d JOIN leads l ON l.id=d.lead_id ORDER BY d.created_at DESC LIMIT 50")]
    return {
        "config": cfg, "blockers": BLOCKERS,
        "day": elapsed, "total_days": total_days, "days_left": days_left,
        "state": "before" if today < start else "after" if today > end else "running",
        "starts_in_days": max(0, (start - today).days),
        "cash_usd": cash, "target_usd": target, "remaining_usd": remaining,
        "pace_target_usd": round(pace_target, 2), "ahead_by_usd": round(cash - pace_target, 2),
        "deals_paid": paid["n"], "deals_open": open_deals["n"], "pipeline_usd": float(open_deals["s"]),
        "avg_deal_usd": avg_deal,
        "deals_needed": math.ceil(remaining / avg_deal) if avg_deal else None,
        "per_week_needed": math.ceil(remaining / avg_deal / max(days_left / 7, 1)) if avg_deal and days_left else None,
        "funnel": funnel, "due": due, "touches_week": touches_week, "by_channel": by_channel, "deals": deals,
    }


def list_leads(conn, venture: str = "", stage: str = "") -> list[dict]:
    where, args = [], []
    if venture in VENTURES:
        where.append("venture=?"); args.append(venture)
    if stage in STAGES:
        where.append("stage=?"); args.append(stage)
    sql = ("SELECT id,name,business,email,phone,venture,stage,segment,location,channel,notes,last_contacted_at,next_action_at,"
           "lost_reason,created_at FROM leads" + (" WHERE " + " AND ".join(where) if where else "") +
           " ORDER BY created_at DESC LIMIT 300")
    return [dict(r) for r in conn.execute(sql, tuple(args))]
