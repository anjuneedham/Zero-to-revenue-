"""Removes clearly-spam opportunities after every Scout run (spec: Scout should not leave scam
listings cluttering the owner's view). Deletes only when BOTH are true:
  1. It is unmistakable junk (a scam-style risk score, or one of the hard spam flags), OR it does
     not fit any of the owner's configured skills at all (agents/scout/evaluate.py's "off_skill" flag).
  2. Nothing has touched it - no task, no payment. Anything the owner or Operator engaged with,
     however briefly, is left alone and archived data is never silently discarded for those.
A human-only listing with a clean score (risk 0) is NOT deleted: it is legitimate information the
owner can still choose to do by hand, just not auto-drafted. evaluate() never marks a human-only
listing "off_skill" for the same reason.
"""

from core.audit import audit

HARD_SPAM_FLAGS = ("non_cash_reward", "token_exchange_scheme", "duplicated_title_spam", "off_skill")
SCAM_RISK_FLOOR = 40


def purge_junk(conn) -> int:
    rows = conn.execute(
        "SELECT id, scam_indicators, risk_score FROM opportunities WHERE status='REVIEW_REQUIRED' "
        "AND NOT EXISTS (SELECT 1 FROM tasks t WHERE t.opportunity_id=opportunities.id) "
        "AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.opportunity_id=opportunities.id)").fetchall()
    to_delete = [r["id"] for r in rows if (r["risk_score"] or 0) >= SCAM_RISK_FLOOR
                or any(f in (r["scam_indicators"] or "") for f in HARD_SPAM_FLAGS)]
    if not to_delete:
        return 0
    conn.execute(f"DELETE FROM opportunities WHERE id IN ({','.join('?' * len(to_delete))})", to_delete)
    audit(conn, "scout", "scout.cleanup", None, f"removed {len(to_delete)} untouched junk opportunity(ies)")
    return len(to_delete)
