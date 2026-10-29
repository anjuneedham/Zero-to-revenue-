-- Manual rollback for 015 (runner is forward-only). Experiments with status 'inconclusive' must be changed first.
DROP TRIGGER IF EXISTS experiments_lifecycle ON experiments;
DROP FUNCTION IF EXISTS experiments_lifecycle();
ALTER TABLE decisions DROP COLUMN IF EXISTS experiment_id;
ALTER TABLE experiments DROP COLUMN IF EXISTS learning_knowledge_id;
ALTER TABLE experiments DROP COLUMN IF EXISTS abandon_reason;
ALTER TABLE experiments DROP COLUMN IF EXISTS decision;
ALTER TABLE experiments DROP COLUMN IF EXISTS result_value;
ALTER TABLE experiments DROP COLUMN IF EXISTS sample_size;
ALTER TABLE experiments DROP COLUMN IF EXISTS min_sample;
ALTER TABLE experiments DROP COLUMN IF EXISTS duration_days;
ALTER TABLE experiments DROP COLUMN IF EXISTS kpi_id;
ALTER TABLE experiments DROP CONSTRAINT IF EXISTS experiments_status_check;
ALTER TABLE experiments ADD CONSTRAINT experiments_status_check CHECK (status IN ('proposed','running','succeeded','failed','abandoned'));
