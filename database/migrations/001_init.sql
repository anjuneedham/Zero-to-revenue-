-- Phase 1 schema (PostgreSQL). The database is the source of truth (spec section 21).

CREATE TABLE users (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, firebase_uid TEXT UNIQUE,
  role TEXT NOT NULL DEFAULT 'owner' CHECK (role IN ('owner')),
  created_at TEXT NOT NULL
);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE agents (
  name TEXT PRIMARY KEY CHECK (name IN ('scout','operator','treasury')),
  status TEXT NOT NULL DEFAULT 'offline', last_run_at TEXT, mode TEXT NOT NULL DEFAULT 'MOCK'
);
CREATE TABLE agent_runs (
  id TEXT PRIMARY KEY, agent TEXT NOT NULL REFERENCES agents(name),
  started_at TEXT NOT NULL, finished_at TEXT, outcome TEXT, error TEXT
);
CREATE TABLE opportunities (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT, source TEXT, source_url TEXT,
  organization TEXT, discovered_at TEXT NOT NULL, deadline TEXT, eligibility TEXT,
  required_skills TEXT, required_capital NUMERIC(24,8) NOT NULL DEFAULT 0, expected_payment NUMERIC(24,8),
  payment_method TEXT, payment_asset TEXT, effort_estimate TEXT,
  opportunity_score INTEGER, risk_score INTEGER, confidence INTEGER,
  scam_indicators TEXT, missing_information TEXT, recommended_action TEXT,
  approval_required INTEGER NOT NULL DEFAULT 1, evidence TEXT,
  status TEXT NOT NULL DEFAULT 'DISCOVERED'
);
CREATE TABLE tasks (
  id TEXT PRIMARY KEY, opportunity_id TEXT REFERENCES opportunities(id),
  owner_agent TEXT NOT NULL REFERENCES agents(name),
  kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'NEW',
  priority INTEGER NOT NULL DEFAULT 5, risk TEXT NOT NULL DEFAULT 'LOW',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, due_at TEXT,
  attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
  idempotency_key TEXT NOT NULL UNIQUE,
  inputs TEXT, outputs TEXT, evidence TEXT, next_action TEXT, blocked_reason TEXT,
  lease_until TEXT
);
CREATE TABLE task_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
  event TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL
);
CREATE TABLE user_actions (
  action_id TEXT PRIMARY KEY, task_id TEXT, title TEXT NOT NULL, why_required TEXT NOT NULL,
  exact_action TEXT NOT NULL, deadline TEXT, estimated_value NUMERIC(24,8), risk TEXT,
  verified_url TEXT, status TEXT NOT NULL DEFAULT 'OPEN', created_at TEXT NOT NULL
);
CREATE TABLE deliverables (
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), path TEXT, summary TEXT, created_at TEXT NOT NULL
);
CREATE TABLE submissions (
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
  idempotency_key TEXT NOT NULL UNIQUE, approved_by TEXT, approved_at TEXT,
  submitted_at TEXT, proof TEXT, status TEXT NOT NULL DEFAULT 'DRAFT'
);
CREATE TABLE payments (
  id TEXT PRIMARY KEY, opportunity_id TEXT REFERENCES opportunities(id),
  expected_amount NUMERIC(24,8), asset TEXT, status TEXT NOT NULL DEFAULT 'AWAITING_PAYMENT', created_at TEXT NOT NULL
);
CREATE TABLE wallets (
  id TEXT PRIMARY KEY, address TEXT NOT NULL, chain_id INTEGER,
  mode TEXT NOT NULL DEFAULT 'READ_ONLY' CHECK (mode = 'READ_ONLY')
);
CREATE TABLE transactions (
  id TEXT PRIMARY KEY, wallet_id TEXT NOT NULL REFERENCES wallets(id), chain_id INTEGER NOT NULL,
  tx_hash TEXT NOT NULL, asset TEXT, amount TEXT, from_address TEXT, to_address TEXT,
  block_number INTEGER, final INTEGER NOT NULL DEFAULT 0, seen_at TEXT NOT NULL,
  UNIQUE (chain_id, tx_hash)
);
CREATE TABLE ledger_entries (
  entry_id TEXT PRIMARY KEY, date TEXT NOT NULL, type TEXT NOT NULL, source TEXT, description TEXT,
  asset TEXT, amount TEXT, usd_value NUMERIC(24,8), valuation_source TEXT, valuation_time TEXT,
  fee TEXT, net_amount TEXT, status TEXT NOT NULL, transaction_hash TEXT, chain_id INTEGER,
  evidence TEXT, notes TEXT,
  UNIQUE (chain_id, transaction_hash, type)
);
CREATE TABLE notifications (
  id TEXT PRIMARY KEY, priority TEXT NOT NULL CHECK (priority IN ('CRITICAL','HIGH','MEDIUM','LOW')),
  dedupe_key TEXT NOT NULL UNIQUE, channel TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING', created_at TEXT NOT NULL, sent_at TEXT, error TEXT
);
CREATE TABLE audit_events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, at TEXT NOT NULL, actor TEXT NOT NULL,
  action TEXT NOT NULL, target TEXT, detail TEXT
);
-- Audit log is append-only.
CREATE FUNCTION audit_events_immutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'audit_events is append-only'; END; $$ LANGUAGE plpgsql;
CREATE TRIGGER audit_no_update BEFORE UPDATE OR DELETE ON audit_events
  FOR EACH ROW EXECUTE FUNCTION audit_events_immutable();
CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE ON audit_events
  FOR EACH STATEMENT EXECUTE FUNCTION audit_events_immutable();

INSERT INTO agents(name) VALUES ('scout'),('operator'),('treasury');
INSERT INTO settings(key,value,updated_at) VALUES ('paused','0','1970-01-01T00:00:00+00:00');
