-- Phase 3-6: Operator drafts + owner approvals, Treasury verification, notifications, scheduler.
ALTER TABLE deliverables ADD COLUMN content TEXT;
ALTER TABLE user_actions ADD COLUMN kind TEXT NOT NULL DEFAULT 'generic';
ALTER TABLE user_actions ADD COLUMN submission_id TEXT;
ALTER TABLE user_actions ADD COLUMN resolved_at TEXT;
ALTER TABLE payments ADD COLUMN chain_id INTEGER;
ALTER TABLE payments ADD COLUMN tx_hash TEXT;
ALTER TABLE payments ADD COLUMN verified_at TEXT;
ALTER TABLE payments ADD COLUMN ledger_entry_id TEXT;
CREATE TABLE wallet_balances (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  chain_id INTEGER NOT NULL, balance_wei TEXT NOT NULL, at TEXT NOT NULL
);
CREATE INDEX wallet_balances_chain ON wallet_balances (chain_id, id);
