-- Manual rollback for 013 (runner is forward-only). Loses the routing metadata only; ledger rows stay.
ALTER TABLE ai_usage DROP COLUMN IF EXISTS llm_usage_id;
ALTER TABLE ai_usage DROP COLUMN IF EXISTS outcome;
ALTER TABLE ai_usage DROP COLUMN IF EXISTS latency_ms;
ALTER TABLE ai_usage DROP COLUMN IF EXISTS task_type;
ALTER TABLE ai_usage DROP COLUMN IF EXISTS routing_level;
