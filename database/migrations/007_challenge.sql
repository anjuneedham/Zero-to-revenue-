-- 60-day $10k challenge (1 Nov - 31 Dec 2026): the leads table becomes the BuildFlow / Agriloop prospect
-- pipeline. Additive only; existing rows keep working (they default to the BuildFlow venture, stage 'new').
ALTER TABLE leads ADD COLUMN venture TEXT NOT NULL DEFAULT 'buildflow' CHECK (venture IN ('buildflow','agriloop'));
ALTER TABLE leads ADD COLUMN stage TEXT NOT NULL DEFAULT 'new'
  CHECK (stage IN ('new','contacted','replied','onboarding_booked','trial','paying','lost'));
ALTER TABLE leads ADD COLUMN segment TEXT;          -- trade (BuildFlow) or crop / buyer type (Agriloop)
ALTER TABLE leads ADD COLUMN location TEXT;
ALTER TABLE leads ADD COLUMN channel TEXT;          -- how the owner first reached them
ALTER TABLE leads ADD COLUMN last_contacted_at TEXT;
ALTER TABLE leads ADD COLUMN next_action_at TEXT;
ALTER TABLE leads ADD COLUMN lost_reason TEXT;
CREATE INDEX leads_stage ON leads (venture, stage);

-- Every touch and outcome: the raw data for "which channel actually converts".
CREATE TABLE lead_touches (
  id TEXT PRIMARY KEY,
  lead_id TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,                             -- email / whatsapp / instagram / facebook / call / in_person / other
  direction TEXT NOT NULL DEFAULT 'out' CHECK (direction IN ('out','in')),
  body TEXT,
  outcome TEXT NOT NULL DEFAULT 'sent' CHECK (outcome IN ('sent','replied','booked','declined','paid','no_reply')),
  created_at TEXT NOT NULL
);
CREATE INDEX lead_touches_lead ON lead_touches (lead_id, created_at);

-- A sold offer. The money itself lives in payments / ledger_entries (verified by Treasury); a deal is
-- 'paid' only once its payment is PAYMENT_VERIFIED.
CREATE TABLE deals (
  id TEXT PRIMARY KEY,
  lead_id TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  venture TEXT NOT NULL,
  plan TEXT NOT NULL DEFAULT 'annual',
  amount_usd NUMERIC(12,2) NOT NULL CHECK (amount_usd > 0),
  free_months INTEGER NOT NULL DEFAULT 2,
  payment_id TEXT REFERENCES payments(id),
  onboarding_status TEXT NOT NULL DEFAULT 'to_schedule' CHECK (onboarding_status IN ('to_schedule','scheduled','done')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','paid','cancelled')),
  created_at TEXT NOT NULL,
  paid_at TEXT
);
CREATE INDEX deals_status ON deals (status);
