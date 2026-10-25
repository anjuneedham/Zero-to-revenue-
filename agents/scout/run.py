"""Scout run loop (spec section 4). Read-only research; writes only to the database."""

import json
import traceback  # noqa: F401  (errors are stored as text, never swallowed)

from agents.scout import sources as src
from agents.scout.rescore import rescore
from agents.scout.enrich import EXTRA_FLAG_RISK, enrich
from agents.scout.evaluate import evaluate
from core.audit import audit
from core.db import now
from core.events.events import emit
from core.orchestrator.killswitch import is_paused
from core.policy.policy import Action, Agent, OpportunityStatus, authorize
from core.queue import queue

import uuid


def _store(conn, ev) -> bool:
    cols = list(ev.row)
    cur = conn.execute(
        f"INSERT INTO opportunities({','.join(cols)}, discovered_at) VALUES ({','.join('?' * len(cols))}, ?) "
        "ON CONFLICT DO NOTHING", (*[ev.row[c] for c in cols], now()))
    return cur.rowcount == 1


def run_scout(conn, sources=None, client=None) -> dict:
    """One Scout pass. Idempotent: a re-seen source_url is never duplicated or re-queued."""
    for action in (Action.READ_EXTERNAL, Action.WRITE_DATABASE):
        d = authorize(Agent.SCOUT, action, paused=is_paused(conn))
        if not d.allowed:
            return {"ran": False, "reason": d.reason}
    rescored = rescore(conn)
    sources = [s() if isinstance(s, type) else s for s in (sources if sources is not None else src.DEFAULT_SOURCES)]
    run_id = "run_" + uuid.uuid4().hex[:12]
    conn.execute("INSERT INTO agent_runs(id, agent, started_at) VALUES (?, 'scout', ?)", (run_id, now()))
    conn.execute("UPDATE agents SET status='online', last_run_at=? WHERE name='scout'", (now(),))
    stats = {"ran": True, "seen": 0, "new": 0, "qualified": 0, "errors": [], "rescored": rescored}
    for source in sources:
        try:
            items = source.items()
        except Exception as e:  # recorded, not swallowed; other sources still run
            stats["errors"].append(f"{getattr(source, 'name', source)}: {type(e).__name__}: {str(e)[:150]}")
            continue
        for item in items:
            stats["seen"] += 1
            try:
                ev = evaluate(item)
                if client is not None:
                    s = enrich(conn, client, item)
                    if s and s["risk_flags"]:
                        ev.row["risk_score"] = min(100, ev.risk + EXTRA_FLAG_RISK * len(s["risk_flags"]))
                        ev.row["scam_indicators"] = "; ".join(filter(None, [ev.row["scam_indicators"], *[f"ai:{f}" for f in s["risk_flags"]]]))
                        ev.row["status"] = OpportunityStatus.REVIEW_REQUIRED.value if ev.row["risk_score"] > 35 else ev.row["status"]
                    if s and s["note"]:
                        ev.row["recommended_action"] = (ev.row["recommended_action"] + " | AI note: " + s["note"])[:500]
                if not _store(conn, ev):
                    continue
                stats["new"] += 1
                if ev.row["status"] == OpportunityStatus.QUALIFIED.value:
                    stats["qualified"] += 1
                    emit(conn, "opportunity.qualified", "scout",
                         {"opportunity_id": ev.id, "score": ev.score, "risk": ev.row["risk_score"]})
                    queue.enqueue(conn, "operator", "research_opportunity", f"opp:{ev.id}:research",
                                  inputs=json.dumps({"opportunity_id": ev.id}), opportunity_id=ev.id,
                                  priority=max(1, 10 - ev.score // 10))
            except Exception as e:
                stats["errors"].append(f"item {item.source_url[:80]}: {type(e).__name__}: {str(e)[:150]}")
    outcome = "ok" if not stats["errors"] else ("error" if stats["seen"] == 0 else "partial")
    conn.execute("UPDATE agent_runs SET finished_at=?, outcome=?, error=? WHERE id=?",
                 (now(), outcome, "; ".join(stats["errors"])[:1000] or None, run_id))
    conn.execute("UPDATE agents SET status=? WHERE name='scout'", ("online" if outcome != "error" else "error",))
    audit(conn, "scout", "scout.run", run_id, json.dumps({k: v for k, v in stats.items() if k not in ("errors", "rescored")}))
    stats["outcome"] = outcome
    return stats
