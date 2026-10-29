-- Phase 7: AI Command Center. Additive columns on the business-scoped AI ledger.
-- Existing rows keep NULLs (they were written by hand through the CRUD API, not by the router).
ALTER TABLE ai_usage ADD COLUMN routing_level TEXT CHECK (routing_level IS NULL OR routing_level IN ('LOW','STANDARD','HIGH'));
ALTER TABLE ai_usage ADD COLUMN task_type TEXT;
ALTER TABLE ai_usage ADD COLUMN latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0);
ALTER TABLE ai_usage ADD COLUMN outcome TEXT CHECK (outcome IS NULL OR outcome IN ('ok','bad_output','error'));
-- Link to the budget ledger row (llm_usage) that enforced the cap for this call.
ALTER TABLE ai_usage ADD COLUMN llm_usage_id BIGINT;
