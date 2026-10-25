-- Outreach leads (spec: Operator may draft outreach; sending always needs owner approval, see
-- Action.SEND_OUTREACH in core/policy/policy.py). No automated scraping writes here; only the
-- owner-supplied import endpoint does.
CREATE TABLE leads (
  id TEXT PRIMARY KEY,
  name TEXT, business TEXT, email TEXT, phone TEXT,
  source TEXT NOT NULL DEFAULT 'owner_supplied',
  status TEXT NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW','DRAFTED','QUEUED','SENT','SKIPPED')),
  notes TEXT,
  created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX leads_email ON leads (lower(email)) WHERE email IS NOT NULL AND email <> '';
