"""Owner-supplied lead import. Every lead comes from the owner (CSV), never from scraping: the only writer of
the leads table outside the challenge pipeline is the import endpoint."""

import csv
import io
import re
import uuid

from core import challenge
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


def import_leads(conn, owner: str, csv_text: str, venture: str = "buildflow") -> dict:
    if venture not in challenge.VENTURES:
        raise ImportError_("venture must be buildflow or agriloop")
    rows = parse_csv(csv_text)
    added = skipped = 0
    for r in rows:
        lid = "lead_" + uuid.uuid4().hex[:12]
        cur = conn.execute(
            "INSERT INTO leads(id,name,business,email,phone,notes,venture,channel,created_at) VALUES (?,?,?,?,?,?,?,'email',?) "
            "ON CONFLICT (lower(email)) WHERE email IS NOT NULL AND email <> '' DO NOTHING",
            (lid, r["name"], r["business"], r["email"], r["phone"], r["notes"], venture, now()))
        added += cur.rowcount
        skipped += 1 - cur.rowcount
    audit(conn, owner, "leads.import", None, f"venture={venture} added={added} skipped_duplicates={skipped} rows={len(rows)}")
    return {"added": added, "skipped_duplicates": skipped, "total_rows": len(rows)}
