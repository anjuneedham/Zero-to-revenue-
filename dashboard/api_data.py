"""Read models and small writes for the payments page and the game-plan checklist."""

import json
import os
import re
import uuid
from decimal import Decimal, InvalidOperation

from core.audit import audit
from core.db import now
from core.policy import policy

PLAN_ID = re.compile(r"^[a-z0-9_-]{1,60}$")
MAX_TICKS = 300


def _clean(v):
    return float(v) if isinstance(v, Decimal) else v


def _rows(cur):
    return [{k: _clean(v) for k, v in dict(r).items()} for r in cur]


def is_live() -> bool:
    return bool(os.environ.get("VERCEL"))



def payments_overview(conn) -> dict:
    ledger = _rows(conn.execute("SELECT entry_id, date, type, asset, amount, usd_value, status, transaction_hash, chain_id, notes "
                                "FROM ledger_entries ORDER BY date DESC LIMIT 50"))
    return {"ledger": ledger,
            "revenue_usd": sum((e["usd_value"] or 0) for e in ledger if e["status"] == "VERIFIED" and e["type"] == "receipt"),
            "paypal": bool(os.environ.get("PAYPAL_CLIENT_ID")) and bool(os.environ.get("PAYPAL_CLIENT_SECRET")),
            "safety": {"wallet_mode": policy.WALLET_MODE, "signing": policy.TRANSACTION_SIGNING_ENABLED,
                       "spending": policy.AUTO_SPENDING_ENABLED, "trading": policy.TRADING_ENABLED}}


def create_manual_payment(conn, owner: str, title: str, amount: str, currency: str = "USD", organization: str = "") -> dict:
    """A payment the owner wants to collect for work with no pipeline record behind it - a
    BuildFlow subscription, a direct client, anything outside the challenge pipeline. Creates a
    minimal opportunity record to anchor it (every verified dollar must trace back to a named
    source - core.policy.counts_as_verified_revenue requires it) plus an AWAITING_PAYMENT row, so
    the existing PayPal/on-chain verification controls work on it exactly like an automated one."""
    title = (title or "").strip()[:300]
    if not title:
        raise ValueError("a title/description is required")
    try:
        amt = Decimal(str(amount))
    except InvalidOperation:
        raise ValueError("amount must be a number") from None
    if amt <= 0:
        raise ValueError("amount must be greater than zero")
    oid = "opp_manual_" + uuid.uuid4().hex[:12]
    pid = "pay_" + uuid.uuid4().hex[:12]
    conn.execute(
        "INSERT INTO opportunities(id,title,category,source,source_url,organization,discovered_at,status,approval_required) "
        "VALUES (?,?,'manual','owner',?,?,?,'APPROVED',0)",
        (oid, title, f"manual:{oid}", (organization or "").strip()[:200] or None, now()))
    conn.execute("INSERT INTO payments(id,opportunity_id,expected_amount,asset,status,created_at) VALUES (?,?,?,?,'AWAITING_PAYMENT',?)",
                 (pid, oid, amt, currency.strip().upper()[:10] or "USD", now()))
    audit(conn, owner, "payment.create_manual", pid, title)
    return {"payment_id": pid, "opportunity_id": oid}


def plan_get(conn) -> dict:
    row = conn.execute("SELECT value FROM settings WHERE key='plan_ticks'").fetchone()
    try:
        return {"ticks": json.loads(row["value"]) if row else {}}
    except ValueError:
        return {"ticks": {}}


def plan_set(conn, item_id: str, done: bool) -> dict:
    if not PLAN_ID.match(item_id or ""):
        raise ValueError("bad id")
    ticks = plan_get(conn)["ticks"]
    if done:
        if len(ticks) >= MAX_TICKS and item_id not in ticks:
            raise ValueError("too many items")
        ticks[item_id] = now()
    else:
        ticks.pop(item_id, None)
    conn.execute("INSERT INTO settings(key, value, updated_at) VALUES ('plan_ticks', ?, ?) ON CONFLICT (key) DO UPDATE "
                 "SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at", (json.dumps(ticks), now()))
    return {"ticks": ticks}
