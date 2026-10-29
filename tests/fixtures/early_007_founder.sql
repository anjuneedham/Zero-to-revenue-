-- Founder OS foundation (additive, forward-only; touches no existing table).
-- The four businesses are configuration rows (name + default priority), not metrics:
-- no tasks, KPIs, goals or usage are seeded. Priority is data: reorder via UPDATE ventures.
CREATE TABLE ventures (
  id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, priority INT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','PAUSED','ARCHIVED')),
  objective TEXT, description TEXT, created_at TEXT NOT NULL
);
CREATE TABLE goals (
  id TEXT PRIMARY KEY, venture_id TEXT NOT NULL REFERENCES ventures(id), title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DONE','DROPPED')), created_at TEXT NOT NULL
);
-- Named founder_tasks: `tasks` is the existing agent work queue (001_init).
CREATE TABLE founder_tasks (
  id TEXT PRIMARY KEY, venture_id TEXT NOT NULL REFERENCES ventures(id), goal_id TEXT REFERENCES goals(id),
  title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'TODO' CHECK (status IN ('TODO','IN_PROGRESS','BLOCKED','DONE')),
  due_date TEXT, effort_hours NUMERIC(8,2), impact INT CHECK (impact BETWEEN 1 AND 5),
  expected_outcome TEXT, next_step TEXT, depends_on TEXT REFERENCES founder_tasks(id),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT
);
CREATE INDEX founder_tasks_open ON founder_tasks (venture_id, status);
CREATE TABLE kpis (
  id TEXT PRIMARY KEY, venture_id TEXT NOT NULL REFERENCES ventures(id), goal_id TEXT REFERENCES goals(id),
  name TEXT NOT NULL, unit TEXT NOT NULL DEFAULT '', baseline NUMERIC, target NUMERIC,
  higher_is_better BOOLEAN NOT NULL DEFAULT TRUE, is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  period TEXT, created_at TEXT NOT NULL
);
CREATE TABLE kpi_readings (
  id TEXT PRIMARY KEY, kpi_id TEXT NOT NULL REFERENCES kpis(id), value NUMERIC NOT NULL, recorded_at TEXT NOT NULL
);
CREATE INDEX kpi_readings_kpi ON kpi_readings (kpi_id, recorded_at);
CREATE TABLE blockers (
  id TEXT PRIMARY KEY, venture_id TEXT NOT NULL REFERENCES ventures(id), task_id TEXT REFERENCES founder_tasks(id),
  description TEXT NOT NULL, impact TEXT, suggested_action TEXT,
  status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','RESOLVED')), opened_at TEXT NOT NULL, resolved_at TEXT
);
CREATE TABLE experiments (
  id TEXT PRIMARY KEY, venture_id TEXT NOT NULL REFERENCES ventures(id), name TEXT NOT NULL, hypothesis TEXT,
  status TEXT NOT NULL DEFAULT 'PLANNED' CHECK (status IN ('PLANNED','RUNNING','DONE','CANCELLED')),
  metric TEXT, baseline NUMERIC, target NUMERIC, review_date TEXT, next_action TEXT, created_at TEXT NOT NULL
);
CREATE TABLE decisions (
  id TEXT PRIMARY KEY, venture_id TEXT NOT NULL REFERENCES ventures(id), title TEXT NOT NULL, rationale TEXT,
  status TEXT NOT NULL DEFAULT 'DECIDED' CHECK (status IN ('DECIDED','REVISIT','REVERSED')), decided_at TEXT NOT NULL
);
INSERT INTO ventures (id, name, priority, objective, description, created_at) VALUES
 ('buildflow','BuildFlow',1,NULL,'Construction SaaS: contractor project/customer management and trusted-contractor discovery',to_char(now() at time zone 'utc','YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),
 ('agriloop','Agriloop',2,NULL,'Agriculture marketplace and community/education platform',to_char(now() at time zone 'utc','YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),
 ('fashion','Fashion Brand',3,NULL,'Consumer / e-commerce brand',to_char(now() at time zone 'utc','YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),
 ('trading','Trading Bot',4,NULL,'Trading strategy research and engineering (research and paper trading only)',to_char(now() at time zone 'utc','YYYY-MM-DD"T"HH24:MI:SS"+00:00"'));
