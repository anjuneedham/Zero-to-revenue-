"""Read models for the agent pages. Everything here is read-only except the plan ticks."""

import json
import os
import re
from decimal import Decimal

from core import budget
from core.db import now
from core.policy import policy
from core.policy.chains import KNOWN_EVM_CHAINS, ChainNotAllowed, allowed_chain_ids

EXPLORERS = {1: "https://etherscan.io", 56: "https://bscscan.com", 204: "https://opbnbscan.com",
             324: "https://explorer.zksync.io", 8453: "https://basescan.org",
             42161: "https://arbiscan.io", 59144: "https://lineascan.build"}
PLAN_ID = re.compile(r"^[a-z0-9_-]{1,60}$")
MAX_TICKS = 300


def _clean(v):
    return float(v) if isinstance(v, Decimal) else v


def _rows(cur):
    return [{k: _clean(v) for k, v in dict(r).items()} for r in cur]


def is_live() -> bool:
    return bool(os.environ.get("VERCEL"))


def scout_overview(conn) -> dict:
    runs = _rows(conn.execute("SELECT id, started_at, finished_at, outcome, error FROM agent_runs WHERE agent='scout' "
                              "ORDER BY started_at DESC LIMIT 10"))
    counts = {r["status"]: r["n"] for r in conn.execute("SELECT status, count(*) n FROM opportunities GROUP BY status")}
    by_source = _rows(conn.execute("SELECT source, count(*) n, max(discovered_at) last_seen FROM opportunities GROUP BY source ORDER BY n DESC"))
    cap, pin, pout = budget.monthly_cap(), *budget.prices()
    ai = {"enabled": budget.llm_enabled(), "monthly_cap_usd": float(cap), "spent_usd": float(budget.spent_this_month(conn)),
          "missing": [n for n, ok in (("LLM_MONTHLY_BUDGET_USD", cap > 0), ("LLM_PRICE_IN_PER_MTOK", pin > 0),
                                      ("LLM_PRICE_OUT_PER_MTOK", pout > 0), ("ANTHROPIC_API_KEY", bool(os.environ.get("ANTHROPIC_API_KEY")))) if not ok]}
    sources = [{"name": "superteam-earn", "label": "Superteam Earn", "note": "Vetted bounty listings with sponsor, deadline and entry count"},
               {"name": "github-bounty-label", "label": "GitHub bounty issues", "note": "Open issues labelled bounty; mostly spam, repo reputation is checked"}]
    seen = {r["source"]: r for r in by_source}
    for s in sources:
        s["found"] = seen.get(s["name"], {}).get("n", 0)
        s["last_seen"] = seen.get(s["name"], {}).get("last_seen")
    return {"runs": runs, "counts": counts, "sources": sources, "ai": ai,
            "skills": [x.strip() for x in os.environ.get("OWNER_SKILLS", "").split(",") if x.strip()]}


def operator_board(conn) -> dict:
    tasks = _rows(conn.execute(
        "SELECT t.id, t.kind, t.status, t.attempts, t.max_attempts, t.updated_at, t.blocked_reason, t.next_action, "
        "o.title, o.expected_payment, o.payment_asset, "
        "(SELECT action_id FROM user_actions a WHERE a.task_id=t.id ORDER BY created_at DESC LIMIT 1) AS action_id "
        "FROM tasks t LEFT JOIN opportunities o ON o.id=t.opportunity_id ORDER BY t.updated_at DESC LIMIT 120"))
    events = _rows(conn.execute(
        "SELECT e.created_at, e.event, e.detail, o.title FROM task_events e JOIN tasks t ON t.id=e.task_id "
        "LEFT JOIN opportunities o ON o.id=t.opportunity_id ORDER BY e.id DESC LIMIT 40"))
    return {"tasks": tasks, "events": events,
            "can": ["Research and draft in the database", "Write plans and checklists", "Ask you for decisions"],
            "cannot": ["Submit anything", "Send money or sign", "Contact anyone", "Accept contracts", "Bypass CAPTCHAs or logins"]}


def treasury_overview(conn) -> dict:
    addr = os.environ.get("OWNER_WALLET_ADDRESS", "").strip() or None
    try:
        chains = sorted(allowed_chain_ids())
        problem = None
    except ChainNotAllowed as e:
        chains, problem = [], str(e)
    out = []
    for c in chains:
        hist = conn.execute("SELECT balance_wei, at FROM wallet_balances WHERE chain_id=? ORDER BY id DESC LIMIT 30", (c,)).fetchall()
        pts = [{"at": h["at"], "v": int(h["balance_wei"]) / 1e18} for h in reversed(hist)]
        out.append({"chain_id": c, "name": KNOWN_EVM_CHAINS.get(c, str(c)), "balance": pts[-1]["v"] if pts else None,
                    "checked_at": pts[-1]["at"] if pts else None, "history": pts, "explorer": EXPLORERS.get(c)})
    ledger = _rows(conn.execute("SELECT entry_id, date, type, asset, amount, usd_value, status, transaction_hash, chain_id, notes "
                                "FROM ledger_entries ORDER BY date DESC LIMIT 50"))
    for e in ledger:
        base = EXPLORERS.get(e["chain_id"])
        e["tx_url"] = f"{base}/tx/{e['transaction_hash']}" if base and e["transaction_hash"] else None
    return {"address": addr, "address_url": f"{EXPLORERS[56]}/address/{addr}" if addr else None, "problem": problem,
            "chains": out, "ledger": ledger, "revenue_usd": sum((e["usd_value"] or 0) for e in ledger if e["status"] == "VERIFIED" and e["type"] == "receipt"),
            "min_confirmations": int(os.environ.get("MIN_CONFIRMATIONS", "12") or 12),
            "safety": {"wallet_mode": policy.WALLET_MODE, "signing": policy.TRANSACTION_SIGNING_ENABLED,
                       "spending": policy.AUTO_SPENDING_ENABLED, "trading": policy.TRADING_ENABLED}}


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
