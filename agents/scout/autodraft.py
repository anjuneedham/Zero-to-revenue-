"""Automatic version of the owner's bulk "send to Operator" action (dashboard/api_data.py's
approve_for_drafting), run on every Scout pass instead of needing a manual click every time.

Only escalates a REVIEW_REQUIRED opportunity when the ONLY reasons it isn't already QUALIFIED are
administrative/economic, never a safety or scope judgment call:
  - insufficient_terms (payment amount/asset/method/deadline not fully documented)
  - under_$X_bar_... (below the one-off-job floor)
A single flag not in that benign set - risk indicators, human_only_listing, off_skill,
unverified_sponsor, duplicated_title_spam, requires_capital, unrealistic_payment, anything - blocks
it, same as a low risk_score ceiling as a second check. This still only ever queues a DRAFT:
Operator never submits/signs/pays, and the owner still approves each draft before anything goes
out, exactly like the automatic QUALIFIED path or a manual bulk approval.
"""

import json

from core.audit import audit
from core.queue import queue

RISK_CEILING = 20


def _benign(flags: list[str]) -> bool:
    return all(f in ("insufficient_terms", "unknown_organization", "unclear_payment_terms") or f.startswith("under_$")
               for f in flags if f)


def auto_send_safe(conn) -> int:
    rows = conn.execute(
        "SELECT id, opportunity_score, risk_score, scam_indicators FROM opportunities "
        "WHERE status='REVIEW_REQUIRED' AND (risk_score IS NULL OR risk_score <= ?) "
        "AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.opportunity_id=opportunities.id)", (RISK_CEILING,)).fetchall()
    sent = []
    for r in rows:
        flags = [f.strip() for f in (r["scam_indicators"] or "").split(";") if f.strip()]
        if not _benign(flags):
            continue
        conn.execute("UPDATE opportunities SET status='QUALIFIED' WHERE id=?", (r["id"],))
        score = r["opportunity_score"] or 50
        queue.enqueue(conn, "operator", "research_opportunity", f"opp:{r['id']}:research",
                      inputs=json.dumps({"opportunity_id": r["id"]}), opportunity_id=r["id"],
                      priority=max(1, 10 - score // 10))
        sent.append(r["id"])
    if sent:
        audit(conn, "scout", "scout.auto_draft", None, f"auto-sent {len(sent)} documentation/economics-only opportunity(ies) to Operator")
    return len(sent)
