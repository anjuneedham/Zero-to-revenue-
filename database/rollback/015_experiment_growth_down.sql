-- Manual rollback for 015 (runner is forward-only). Drops the Phase 9 columns; the decision/knowledge rows they pointed at remain.
DROP INDEX IF EXISTS experiments_status;
ALTER TABLE experiments DROP COLUMN IF EXISTS knowledge_id;
ALTER TABLE experiments DROP COLUMN IF EXISTS decision_id;
ALTER TABLE experiments DROP COLUMN IF EXISTS decision_rationale;
ALTER TABLE experiments DROP COLUMN IF EXISTS decision;
ALTER TABLE experiments DROP COLUMN IF EXISTS result_source;
ALTER TABLE experiments DROP COLUMN IF EXISTS result_value;
ALTER TABLE experiments DROP COLUMN IF EXISTS duration_days;
ALTER TABLE experiments DROP COLUMN IF EXISTS metric_kpi_id;
