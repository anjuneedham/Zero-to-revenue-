-- Phase 9: experiment lifecycle, results, decisions and learnings. Additive; nothing here executes anything.
ALTER TABLE experiments DROP CONSTRAINT IF EXISTS experiments_status_check;
ALTER TABLE experiments ADD CONSTRAINT experiments_status_check
  CHECK (status IN ('proposed','running','succeeded','failed','inconclusive','abandoned'));
ALTER TABLE experiments ADD COLUMN kpi_id TEXT REFERENCES kpis(id);
ALTER TABLE experiments ADD COLUMN duration_days INTEGER CHECK (duration_days IS NULL OR duration_days BETWEEN 1 AND 365);
ALTER TABLE experiments ADD COLUMN min_sample INTEGER CHECK (min_sample IS NULL OR min_sample >= 1);
ALTER TABLE experiments ADD COLUMN sample_size INTEGER CHECK (sample_size IS NULL OR sample_size >= 0);
ALTER TABLE experiments ADD COLUMN result_value NUMERIC(24,8);
ALTER TABLE experiments ADD COLUMN decision TEXT CHECK (decision IS NULL OR decision IN ('scale','iterate','stop'));
ALTER TABLE experiments ADD COLUMN abandon_reason TEXT;
ALTER TABLE experiments ADD COLUMN learning_knowledge_id TEXT REFERENCES knowledge(id);
ALTER TABLE decisions ADD COLUMN experiment_id TEXT REFERENCES experiments(id);

-- Lifecycle is enforced in the database too: proposed -> running -> succeeded|failed|inconclusive; proposed|running -> abandoned.
-- The plan is locked once started; a concluded or abandoned experiment keeps its record (only learnings/next_action/review_date and the
-- learning link may change).
CREATE FUNCTION experiments_lifecycle() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NEW.status <> 'proposed' THEN RAISE EXCEPTION 'a new experiment starts as proposed'; END IF;
    RETURN NEW;
  END IF;
  IF NEW.status <> OLD.status AND NOT (
       (OLD.status = 'proposed' AND NEW.status IN ('running','abandoned')) OR
       (OLD.status = 'running' AND NEW.status IN ('succeeded','failed','inconclusive','abandoned'))) THEN
    RAISE EXCEPTION 'illegal experiment status change % -> %', OLD.status, NEW.status;
  END IF;
  IF OLD.status <> 'proposed' AND (
       NEW.hypothesis <> OLD.hypothesis OR NEW.method IS DISTINCT FROM OLD.method OR NEW.success_metric IS DISTINCT FROM OLD.success_metric
       OR NEW.kpi_id IS DISTINCT FROM OLD.kpi_id OR NEW.baseline_value IS DISTINCT FROM OLD.baseline_value
       OR NEW.target_value IS DISTINCT FROM OLD.target_value OR NEW.duration_days IS DISTINCT FROM OLD.duration_days
       OR NEW.min_sample IS DISTINCT FROM OLD.min_sample OR NEW.started_at IS DISTINCT FROM OLD.started_at) THEN
    RAISE EXCEPTION 'the plan of a started experiment cannot be changed';
  END IF;
  IF OLD.status NOT IN ('proposed','running') AND (
       NEW.status <> OLD.status OR NEW.result IS DISTINCT FROM OLD.result OR NEW.result_value IS DISTINCT FROM OLD.result_value
       OR NEW.sample_size IS DISTINCT FROM OLD.sample_size OR NEW.decision IS DISTINCT FROM OLD.decision
       OR NEW.ended_at IS DISTINCT FROM OLD.ended_at OR NEW.abandon_reason IS DISTINCT FROM OLD.abandon_reason) THEN
    RAISE EXCEPTION 'a concluded experiment keeps its recorded result';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER experiments_lifecycle BEFORE INSERT OR UPDATE ON experiments FOR EACH ROW EXECUTE FUNCTION experiments_lifecycle();
