-- Phase 9: Experiment and Growth Engine. Additive only; existing experiment rows stay valid.
-- Lifecycle (proposed -> running -> succeeded|failed, or abandoned) is enforced in core/growth.py; the generic CRUD can no longer move it.
ALTER TABLE experiments ADD COLUMN metric_kpi_id TEXT REFERENCES kpis(id);
ALTER TABLE experiments ADD COLUMN duration_days INTEGER CHECK (duration_days IS NULL OR duration_days BETWEEN 1 AND 365);
ALTER TABLE experiments ADD COLUMN result_value NUMERIC(24,8);
ALTER TABLE experiments ADD COLUMN result_source TEXT CHECK (result_source IS NULL OR result_source IN ('entered','kpi'));
ALTER TABLE experiments ADD COLUMN decision TEXT CHECK (decision IS NULL OR decision IN ('adopt','iterate','stop'));
ALTER TABLE experiments ADD COLUMN decision_rationale TEXT;
-- Concluding writes a decision record and a knowledge note (with evidence); the links make it idempotent and traceable.
ALTER TABLE experiments ADD COLUMN decision_id TEXT REFERENCES decisions(id);
ALTER TABLE experiments ADD COLUMN knowledge_id TEXT REFERENCES knowledge(id);
CREATE INDEX experiments_status ON experiments(business_id, status);
