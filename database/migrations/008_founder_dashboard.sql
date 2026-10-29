-- Founder Dashboard (Phase 2): additive columns + one table on top of 007_founder_os_core.
-- Nothing is dropped or rewritten. Rollback: database/rollback/008_founder_dashboard_down.sql (manual).

-- Business priority is data (1 = highest). Backfilled to the founder's stated order; NULL sorts last.
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS priority INTEGER CHECK (priority IS NULL OR priority >= 1);
UPDATE businesses SET priority = CASE slug WHEN 'buildflow' THEN 1 WHEN 'agriloop' THEN 2 WHEN 'fashion' THEN 3 WHEN 'trading' THEN 4 END
  WHERE priority IS NULL AND slug IN ('buildflow','agriloop','fashion','trading');

-- Inputs for the next-action ranking. All optional: unknown stays NULL (never guessed).
ALTER TABLE work_tasks ADD COLUMN IF NOT EXISTS impact INTEGER CHECK (impact IS NULL OR impact BETWEEN 1 AND 5);
ALTER TABLE work_tasks ADD COLUMN IF NOT EXISTS effort_hours NUMERIC(8,2) CHECK (effort_hours IS NULL OR effort_hours >= 0);
ALTER TABLE work_tasks ADD COLUMN IF NOT EXISTS depends_on TEXT REFERENCES work_tasks(id);
ALTER TABLE work_tasks ADD COLUMN IF NOT EXISTS expected_outcome TEXT;
ALTER TABLE work_tasks ADD COLUMN IF NOT EXISTS next_step TEXT;

ALTER TABLE kpis ADD COLUMN IF NOT EXISTS baseline_value NUMERIC(24,8);
ALTER TABLE kpis ADD COLUMN IF NOT EXISTS is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0,1));
ALTER TABLE kpis ADD COLUMN IF NOT EXISTS period TEXT;

ALTER TABLE experiments ADD COLUMN IF NOT EXISTS baseline_value NUMERIC(24,8);
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS target_value NUMERIC(24,8);
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS review_date TEXT;
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS next_action TEXT;

-- Recorded blockers (facts the founder entered), optionally tied to a task.
CREATE TABLE IF NOT EXISTS blockers (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  work_task_id TEXT REFERENCES work_tasks(id),
  description TEXT NOT NULL, impact TEXT, suggested_action TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved')),
  resolved_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS blockers_business_status ON blockers(business_id, status);
