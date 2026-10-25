"""Priority + dedupe notification service (spec sections 25, 26, 37)."""

import re
import uuid

from core.db import now

SECRET_PATTERNS = [
    re.compile(r"(?<![0-9a-fA-F])(?:0x)?[0-9a-fA-F]{64}(?![0-9a-fA-F])"),
    re.compile(r"(?i)(private key|seed phrase|recovery phrase|password|2fa)\s*[:=]"),
]


class SecretInNotification(ValueError):
    pass


def notify(conn, backend, to, priority, dedupe_key, title, body, channel="whatsapp") -> bool:
    """Returns True if a message was newly sent; duplicates are dropped silently.
    Delivery failures are recorded (never swallowed) and the row stays retryable."""
    for p in SECRET_PATTERNS:
        if p.search(title) or p.search(body):
            raise SecretInNotification("refusing to send possible secret material")
    nid = "ntf_" + uuid.uuid4().hex[:12]
    cur = conn.execute(
        "INSERT INTO notifications(id,priority,dedupe_key,channel,title,body,created_at) VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT (dedupe_key) DO NOTHING",
        (nid, priority, dedupe_key, channel, title, body, now()))
    if cur.rowcount == 0:
        return False
    try:
        backend.send(to, title, body)
        conn.execute("UPDATE notifications SET status='SENT', sent_at=? WHERE id=?", (now(), nid))
        return True
    except Exception as e:
        conn.execute("UPDATE notifications SET status='FAILED', error=? WHERE id=?", (str(e)[:300], nid))
        return False
