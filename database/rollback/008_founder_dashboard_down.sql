-- Manual rollback for 008 (the migration runner is forward-only). Loses the data in these columns/table.
DROP TABLE IF EXISTS blockers;
ALTER TABLE experiments DROP COLUMN IF EXISTS next_action, DROP COLUMN IF EXISTS review_date, DROP COLUMN IF EXISTS target_value, DROP COLUMN IF EXISTS baseline_value;
ALTER TABLE kpis DROP COLUMN IF EXISTS period, DROP COLUMN IF EXISTS is_primary, DROP COLUMN IF EXISTS baseline_value;
ALTER TABLE work_tasks DROP COLUMN IF EXISTS next_step, DROP COLUMN IF EXISTS expected_outcome, DROP COLUMN IF EXISTS depends_on, DROP COLUMN IF EXISTS effort_hours, DROP COLUMN IF EXISTS impact;
ALTER TABLE businesses DROP COLUMN IF EXISTS priority;
