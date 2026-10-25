"""Outreach drafting (spec section 9-13). Every lead comes from the owner, never from automated
scraping: the only writer of the leads table is the owner-supplied import endpoint. A draft is
never sent by this code; it is queued as a USER_ACTION and the owner sends it themselves (or, once
an email-sending integration is approved, approves a batch send) - SEND_OUTREACH always needs
owner_approved in core.policy.policy.
"""

import csv
import io
import re
import uuid

from agents.operator.drafts import FILL
from core.audit import audit
from core.db import now

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_IMPORT_ROWS = 500


class ImportError_(ValueError):
    pass


def parse_csv(text: str) -> list[dict]:
    """name,business,email,phone,notes - header required, email mandatory and validated.
    Never silently drops a bad row: raises with the row number so the owner can fix it."""
    if len(text.encode()) > 200_000:
        raise ImportError_("file too large")
    reader = csv.DictReader(io.StringIO(text))
    required = {"name", "business", "email"}
    if reader.fieldnames is None or not required.issubset({f.strip().lower() for f in reader.fieldnames}):
        raise ImportError_("header must include at least: name,business,email (phone,notes optional)")
    rows = []
    for i, raw in enumerate(reader, start=2):
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(row.values()):
            continue
        if i - 1 > MAX_IMPORT_ROWS:
            raise ImportError_(f"too many rows (max {MAX_IMPORT_ROWS})")
        email = row.get("email", "")
        if not EMAIL_RE.match(email):
            raise ImportError_(f"row {i}: '{email}' is not a valid email address")
        rows.append({"name": row.get("name", ""), "business": row.get("business", ""), "email": email,
                     "phone": row.get("phone", ""), "notes": row.get("notes", "")})
    if not rows:
        raise ImportError_("no usable rows found")
    return rows


def import_leads(conn, owner: str, csv_text: str) -> dict:
    rows = parse_csv(csv_text)
    added = skipped = 0
    for r in rows:
        lid = "lead_" + uuid.uuid4().hex[:12]
        cur = conn.execute(
            "INSERT INTO leads(id,name,business,email,phone,notes,created_at) VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT (lower(email)) WHERE email IS NOT NULL AND email <> '' DO NOTHING",
            (lid, r["name"], r["business"], r["email"], r["phone"], r["notes"], now()))
        added += cur.rowcount
        skipped += 1 - cur.rowcount
    audit(conn, owner, "leads.import", None, f"added={added} skipped_duplicates={skipped} rows={len(rows)}")
    return {"added": added, "skipped_duplicates": skipped, "total_rows": len(rows)}


def draft_outreach(lead: dict) -> str:
    """Plain, honest draft. Never invents a reason the recipient should care, a relationship, or a
    claim about their business - those are left as [OWNER TO FILL]."""
    name = lead["name"] or "there"
    business = lead["business"] or "your business"
    lines = [
        f"Subject: Quick question about {business}'s online booking",
        "",
        f"Hi {name},",
        "",
        f"{FILL} (one honest sentence on why you're reaching out to {business} specifically - "
        "something true you noticed, not a template compliment).",
        "",
        "I build small, practical tools for local businesses - the kind of thing that answers a missed "
        "call with a text, or makes it easy for a customer to see your past work and book you. If that's "
        "useful, I'd like to show you a 10-minute example built around your business, no cost either way.",
        "",
        f"{FILL} (if you have a live example or case study ready, link it here; otherwise remove this line).",
        "",
        "Is there a better number or time to reach you?",
        "",
        f"{FILL} (your name and number)",
    ]
    return "\n".join(lines)
