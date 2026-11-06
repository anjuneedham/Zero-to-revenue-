-- Sales execution system (additive only; nothing existing is altered or dropped).
-- leads becomes the prospect pipeline. Legacy columns/status stay valid for the CSV/Gmail flow.

ALTER TABLE leads
  ADD COLUMN industry TEXT,
  ADD COLUMN location TEXT,
  ADD COLUMN website TEXT,
  ADD COLUMN contact_other TEXT,          -- handle / WhatsApp / other way to reach them
  ADD COLUMN source_channel TEXT,         -- where the prospect came from
  ADD COLUMN offer TEXT,
  ADD COLUMN research_notes TEXT,
  ADD COLUMN qualification TEXT NOT NULL DEFAULT 'unqualified'
    CHECK (qualification IN ('unqualified','qualified','maybe','not_qualified')),
  ADD COLUMN stage TEXT NOT NULL DEFAULT 'identified',
  ADD COLUMN outcome TEXT,
  ADD COLUMN deal_value NUMERIC(14,2),
  ADD COLUMN revenue_won NUMERIC(14,2),   -- OWNER-RECORDED; not verified revenue (Treasury verifies)
  ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD',
  ADD COLUMN last_contact_at TEXT,
  ADD COLUMN next_followup_at TEXT,       -- YYYY-MM-DD, derived from open follow-up tasks
  ADD COLUMN playbook_run_id TEXT,
  ADD COLUMN updated_at TEXT;
CREATE INDEX leads_stage ON leads (stage);

-- Every business event. Append-only: history is never rewritten; corrections are new events.
-- at = when it was recorded (immutable). occurred_at = when it actually happened (owner-supplied, may be earlier).
CREATE TABLE activity_events (
  id BIGSERIAL PRIMARY KEY,
  at TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  lead_id TEXT,                           -- deliberately no FK: history outlives a deleted prospect
  kind TEXT NOT NULL,
  summary TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '{}',      -- JSON
  task_id TEXT,
  run_id TEXT,
  actor TEXT NOT NULL DEFAULT 'owner'
);
CREATE INDEX activity_lead ON activity_events (lead_id, id);
CREATE INDEX activity_at ON activity_events (at);
CREATE FUNCTION activity_events_immutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'activity_events is append-only'; END; $$ LANGUAGE plpgsql;
CREATE TRIGGER activity_no_update BEFORE UPDATE OR DELETE ON activity_events
  FOR EACH ROW EXECUTE FUNCTION activity_events_immutable();
CREATE TRIGGER activity_no_truncate BEFORE TRUNCATE ON activity_events
  FOR EACH STATEMENT EXECUTE FUNCTION activity_events_immutable();

CREATE TABLE sales_tasks (
  id TEXT PRIMARY KEY,
  lead_id TEXT,
  title TEXT NOT NULL,
  detail TEXT,
  kind TEXT NOT NULL DEFAULT 'other',
  priority INTEGER NOT NULL DEFAULT 2 CHECK (priority IN (1,2,3)),   -- 1 high, 2 normal, 3 low
  due_date TEXT,                          -- YYYY-MM-DD
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','done','skipped')),
  playbook_id TEXT,
  run_id TEXT,
  step_id TEXT,
  outcome TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT
);
CREATE INDEX sales_tasks_open ON sales_tasks (status, due_date);
CREATE INDEX sales_tasks_lead ON sales_tasks (lead_id);

CREATE TABLE playbooks (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  builtin_slug TEXT UNIQUE,               -- set for shipped playbooks; NULL for custom/duplicates
  parent_id TEXT,                         -- duplicated from
  objective TEXT NOT NULL DEFAULT '',
  intended_user TEXT NOT NULL DEFAULT '',
  when_to_use TEXT NOT NULL DEFAULT '',
  prerequisites TEXT NOT NULL DEFAULT '[]',        -- JSON list of strings
  steps TEXT NOT NULL DEFAULT '[]',                -- JSON list of {id,title,instruction}
  recommended_actions TEXT NOT NULL DEFAULT '[]',
  example_messages TEXT NOT NULL DEFAULT '[]',
  expected_outcome TEXT NOT NULL DEFAULT '',
  completion_criteria TEXT NOT NULL DEFAULT '',
  common_mistakes TEXT NOT NULL DEFAULT '[]',
  next_recommended TEXT NOT NULL DEFAULT '',
  version INTEGER NOT NULL DEFAULT 1,
  archived BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- A run snapshots the steps it started with, so later edits to a playbook never rewrite past executions.
CREATE TABLE playbook_runs (
  id TEXT PRIMARY KEY,
  playbook_id TEXT NOT NULL,
  playbook_name TEXT NOT NULL,
  playbook_version INTEGER NOT NULL,
  lead_id TEXT,
  steps TEXT NOT NULL,                    -- JSON snapshot
  progress TEXT NOT NULL DEFAULT '{}',    -- JSON {step_id: {done_at, note}}
  status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress','completed','abandoned')),
  started_at TEXT NOT NULL,
  completed_at TEXT,
  outcome_note TEXT
);
CREATE INDEX playbook_runs_lead ON playbook_runs (lead_id);
CREATE INDEX playbook_runs_pb ON playbook_runs (playbook_id);

-- Carry earlier lead records into the pipeline without inventing history. The legacy status is mapped to a stage and a
-- clearly labelled system event records that the stage came from the old status. No contact date is claimed: none was recorded.
UPDATE leads SET stage = CASE status WHEN 'SENT' THEN 'contacted' WHEN 'DRAFTED' THEN 'outreach_prepared'
                                     WHEN 'QUEUED' THEN 'outreach_prepared' ELSE 'identified' END,
                 updated_at = created_at
 WHERE status IN ('SENT','DRAFTED','QUEUED');
INSERT INTO activity_events(at, occurred_at, lead_id, kind, summary, detail, actor)
SELECT created_at, created_at, id, 'legacy_import',
       'Carried over from the earlier lead list (old status: ' || status || '). The date of any contact was not recorded.',
       '{"legacy_status":"' || status || '","stage_after":"' || stage || '"}', 'system'
  FROM leads;
