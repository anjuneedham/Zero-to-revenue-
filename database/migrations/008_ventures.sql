-- Venture workspace: ventures, their tasks, decisions and experiments (HANDOFF step 3). Additive only.
-- The agent queue already owns the name `tasks`, and the production database already had an unrelated `decisions` table
-- (found when this migration failed on 29 Oct), so every table here carries the `venture_` prefix and none touches those.
-- Roll back with database/rollbacks/008_ventures.down.sql (kept outside this folder: the runner applies every *.sql here).
CREATE TABLE ventures (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('software','trading','ecommerce','other')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','archived')),
  position INTEGER NOT NULL DEFAULT 0,  -- display order
  plan_day TEXT,                       -- weekly rhythm from docs/master/HANDOFF.md, e.g. 'Mon, Fri'
  notes TEXT,
  created_at TEXT NOT NULL
);
INSERT INTO ventures (id, name, kind, position, plan_day, created_at) VALUES
  ('buildflow', 'BuildFlow', 'software', 1, 'Mon, Fri', to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),
  ('agriloop', 'AgriLoop', 'software', 2, 'Tue, Sat', to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),
  ('trading', 'Trading', 'trading', 3, 'Wed', to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),
  ('ecommerce', 'E-commerce', 'ecommerce', 4, 'Thu', to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"'));

CREATE TABLE venture_tasks (
  id TEXT PRIMARY KEY,
  venture_id TEXT NOT NULL REFERENCES ventures(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','doing','blocked','done')),
  priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('high','normal','low')),
  due_date TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  done_at TEXT
);
CREATE INDEX venture_tasks_open ON venture_tasks (venture_id, status);

CREATE TABLE venture_decisions (
  id TEXT PRIMARY KEY,
  venture_id TEXT REFERENCES ventures(id) ON DELETE SET NULL,   -- NULL = applies to the whole OS
  title TEXT NOT NULL,
  context TEXT,
  decision TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','decided','reversed')),
  created_at TEXT NOT NULL,
  decided_at TEXT
);
CREATE INDEX venture_decisions_status ON venture_decisions (status, created_at);

CREATE TABLE venture_experiments (
  id TEXT PRIMARY KEY,
  venture_id TEXT NOT NULL REFERENCES ventures(id) ON DELETE CASCADE,
  hypothesis TEXT NOT NULL,
  metric TEXT NOT NULL,                -- what you will count to judge it, e.g. 'replies per 20 WhatsApp messages'
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','won','lost','inconclusive','stopped')),
  result TEXT,
  created_at TEXT NOT NULL,
  closed_at TEXT
);
CREATE INDEX venture_experiments_status ON venture_experiments (venture_id, status);
