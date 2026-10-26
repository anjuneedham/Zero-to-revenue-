"""Read models for the agent pages. Everything here is read-only except the plan ticks and the
owner's own manual dismissal of opportunities."""

import json
import os
import re
from decimal import Decimal

from core import actions, budget
from core.audit import audit
from core.db import now
from core.policy import policy
from core.policy.chains import KNOWN_EVM_CHAINS, ChainNotAllowed, allowed_chain_ids
from core.queue import queue

EXPLORERS = {1: "https://etherscan.io", 56: "https://bscscan.com", 204: "https://opbnbscan.com",
             324: "https://explorer.zksync.io", 8453: "https://basescan.org",
             42161: "https://arbiscan.io", 59144: "https://lineascan.build"}
PLAN_ID = re.compile(r"^[a-z0-9_-]{1,60}$")
MAX_TICKS = 300
OPP_ID = re.compile(r"^opp_[a-f0-9]{12}$")
MAX_DISMISS_BATCH = 100


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
            "paypal": bool(os.environ.get("PAYPAL_CLIENT_ID")) and bool(os.environ.get("PAYPAL_CLIENT_SECRET")),
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


def approve_for_drafting(conn, owner: str, ids: list[str]) -> dict:
    """The owner's own bulk judgment call on a batch of REVIEW_REQUIRED opportunities: "these are
    fine, have Operator draft them" - instead of opening each one's drawer one at a time. This only
    ever queues a DRAFT; Operator still never submits/signs/pays, and the owner still approves each
    draft before anything goes out, same as the automatic QUALIFIED path.
    Never overrides a human_only_listing flag - that is the sponsor's own platform rule, not the
    owner's risk call, and a bulk approval can't be the thing that gets the owner's account banned
    for AI-produced work on a listing that explicitly forbids it."""
    clean = [i for i in dict.fromkeys(ids) if isinstance(i, str) and OPP_ID.match(i)][:MAX_DISMISS_BATCH]
    if not clean:
        return {"approved": 0, "skipped": len(ids)}
    rows = conn.execute(
        f"SELECT id, opportunity_score, scam_indicators FROM opportunities WHERE id IN ({','.join('?' * len(clean))}) "
        "AND status='REVIEW_REQUIRED'", clean).fetchall()
    approved = []
    for r in rows:
        if "human_only_listing" in (r["scam_indicators"] or ""):
            continue
        conn.execute("UPDATE opportunities SET status='QUALIFIED' WHERE id=?", (r["id"],))
        score = r["opportunity_score"] or 50
        queue.enqueue(conn, "operator", "research_opportunity", f"opp:{r['id']}:research",
                      inputs=json.dumps({"opportunity_id": r["id"]}), opportunity_id=r["id"],
                      priority=max(1, 10 - score // 10))
        approved.append(r["id"])
    if approved:
        audit(conn, owner, "scout.approve_for_drafting", None, f"owner sent {len(approved)} opportunity(ies) to Operator by hand")
    return {"approved": len(approved), "skipped": len(clean) - len(approved)}


def dismiss_opportunities(conn, owner: str, ids: list[str], force: bool = False) -> dict:
    """The owner manually picking which opportunities to remove - out of scope, not worth it,
    still looks spammy to them even though it cleared the automatic filters. Never deletes one with
    a payment: a verified or pending payment is real money and is never silently discarded.
    A task that was CANCELLED or FAILED is a dead end, not live work, so an opportunity whose only
    tasks are in those terminal states can always be removed by hand.
    A task that is still live (OPEN/IN_PROGRESS/etc.) blocks removal UNLESS force=True, in which
    case it is cancelled first - through the same path a rejected approval takes (any open
    user_actions for it are rejected too) - and removal proceeds. force is for "this was never a
    fit/was spammy, abandon it entirely," not a way to discard real paid work mid-flight."""
    clean = [i for i in dict.fromkeys(ids) if isinstance(i, str) and OPP_ID.match(i)][:MAX_DISMISS_BATCH]
    if not clean:
        return {"removed": 0, "skipped": len(ids)}
    has_payment = {r["id"] for r in conn.execute(
        f"SELECT DISTINCT opportunity_id AS id FROM payments WHERE opportunity_id IN ({','.join('?' * len(clean))})", clean)}
    candidates = [i for i in clean if i not in has_payment]
    if force and candidates:
        placeholders = ",".join("?" * len(candidates))
        for t in conn.execute(f"SELECT id FROM tasks WHERE opportunity_id IN ({placeholders}) "
                              "AND status NOT IN ('CANCELLED', 'FAILED')", candidates).fetchall():
            for a in conn.execute("SELECT action_id FROM user_actions WHERE task_id=? AND status='OPEN'", (t["id"],)).fetchall():
                actions.reject(conn, a["action_id"], owner)
            try:
                queue.set_status(conn, t["id"], "CANCELLED", detail="owner dismissed the opportunity")
            except (KeyError, ValueError):
                pass
    live_tasks = {r["id"] for r in conn.execute(
        f"SELECT DISTINCT opportunity_id AS id FROM tasks WHERE opportunity_id IN "
        f"({','.join('?' * len(candidates))}) AND status NOT IN ('CANCELLED', 'FAILED')", candidates)} if candidates else set()
    removable = [i for i in candidates if i not in live_tasks]
    if removable:
        placeholders = ",".join("?" * len(removable))
        # Dead (cancelled/failed) tasks are detached, not deleted, so the task/deliverable/audit
        # history survives the opportunity row being removed - opportunity_id is nullable for this.
        conn.execute(f"UPDATE tasks SET opportunity_id=NULL WHERE opportunity_id IN ({placeholders})", removable)
        conn.execute(f"DELETE FROM opportunities WHERE id IN ({placeholders})", removable)
        audit(conn, owner, "scout.dismiss", None, f"owner removed {len(removable)} opportunity(ies) by hand" + (" (force)" if force else ""))
    return {"removed": len(removable), "skipped": len(clean) - len(removable)}
