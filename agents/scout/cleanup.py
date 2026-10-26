"""Removes clearly-spam opportunities after every Scout run (spec: Scout should not leave scam
listings cluttering the owner's view). Deletes only when BOTH are true:
  1. It is unmistakable junk (a scam-style risk score, or one of the hard spam flags), OR it does
     not fit any of the owner's configured skills at all (agents/scout/evaluate.py's "off_skill" flag).
  2. No payment references it, and no task still referencing it is live (OPEN/IN_PROGRESS/etc) -
     a CANCELLED/FAILED task (e.g. from a rescore downgrade) doesn't protect it, since nothing real
     came of that task. Anything the owner or Operator genuinely engaged with, or any payment, is
     left alone and never silently discarded.
A human-only listing with a clean score (risk 0) is NOT deleted: it is legitimate information the
owner can still choose to do by hand, just not auto-drafted. evaluate() never marks a human-only
listing "off_skill" for the same reason.
"""

from core.audit import audit

HARD_SPAM_FLAGS = ("non_cash_reward", "token_exchange_scheme", "duplicated_title_spam", "off_skill", "commission_only_role")
SCAM_RISK_FLOOR = 40


def purge_junk(conn) -> int:
    rows = conn.execute(
        "SELECT id, scam_indicators, risk_score FROM opportunities WHERE status='REVIEW_REQUIRED' "
        "AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.opportunity_id=opportunities.id "
        "AND t.status NOT IN ('CANCELLED', 'FAILED')) "
        "AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.opportunity_id=opportunities.id)").fetchall()
    to_delete = [r["id"] for r in rows if (r["risk_score"] or 0) >= SCAM_RISK_FLOOR
                or any(f in (r["scam_indicators"] or "") for f in HARD_SPAM_FLAGS)]
    if not to_delete:
        return 0
    placeholders = ",".join("?" * len(to_delete))
    # Dead (cancelled/failed) tasks are detached, not deleted, so their own audit history survives
    # the opportunity row being removed - tasks.opportunity_id is nullable for exactly this.
    conn.execute(f"UPDATE tasks SET opportunity_id=NULL WHERE opportunity_id IN ({placeholders})", to_delete)
    conn.execute(f"DELETE FROM opportunities WHERE id IN ({placeholders})", to_delete)
    audit(conn, "scout", "scout.cleanup", None, f"removed {len(to_delete)} untouched junk opportunity(ies)")
    return len(to_delete)
