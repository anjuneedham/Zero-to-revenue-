-- Multi-venture workspace (docs/master/MASTER_PLAN.md). Additive only: nothing existing is altered.
-- Reverse with database/migrations/down/007_ventures_down.sql (drops only these tables).
CREATE TABLE ventures (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  repo TEXT,
  stage TEXT NOT NULL DEFAULT 'BUILD' CHECK (stage IN ('DECIDE','RESEARCH','BUILD','VALIDATE','SELL','SCALE','KILLED')),
  priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 9),
  doc_path TEXT,
  kill_criterion TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE venture_tasks (
  id TEXT PRIMARY KEY,
  venture_id TEXT NOT NULL REFERENCES ventures(id),
  title TEXT NOT NULL,
  owner TEXT NOT NULL DEFAULT 'founder' CHECK (owner IN ('founder','agent','both')),
  status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','DOING','DONE','BLOCKED','DROPPED')),
  due_at TEXT,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX venture_tasks_v ON venture_tasks (venture_id, status);
CREATE TABLE decisions (
  id TEXT PRIMARY KEY,
  venture_id TEXT REFERENCES ventures(id),
  question TEXT NOT NULL,
  decision TEXT,
  rationale TEXT,
  status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','DECIDED')),
  decided_at TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE experiments (
  id TEXT PRIMARY KEY,
  venture_id TEXT NOT NULL REFERENCES ventures(id),
  hypothesis TEXT NOT NULL,
  metric TEXT,
  success_threshold TEXT,
  status TEXT NOT NULL DEFAULT 'PLANNED' CHECK (status IN ('PLANNED','RUNNING','SUCCEEDED','FAILED','ABANDONED')),
  result TEXT,
  created_at TEXT NOT NULL,
  closed_at TEXT
);
CREATE TABLE metrics (
  id BIGSERIAL PRIMARY KEY,
  venture_id TEXT NOT NULL REFERENCES ventures(id),
  name TEXT NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  source TEXT NOT NULL DEFAULT 'owner',
  at TEXT NOT NULL
);
CREATE INDEX metrics_v ON metrics (venture_id, name, at);
CREATE TABLE venture_allocation (
  venture_id TEXT NOT NULL REFERENCES ventures(id),
  weekday INTEGER NOT NULL CHECK (weekday BETWEEN 1 AND 7),  -- ISO: 1 = Monday
  focus TEXT NOT NULL,
  PRIMARY KEY (venture_id, weekday)
);
CREATE TABLE effort_logs (
  id BIGSERIAL PRIMARY KEY,
  venture_id TEXT NOT NULL REFERENCES ventures(id),
  day TEXT NOT NULL,
  hours DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (hours >= 0 AND hours <= 24),
  claude_sessions INTEGER NOT NULL DEFAULT 0 CHECK (claude_sessions >= 0),
  note TEXT,
  source TEXT NOT NULL DEFAULT 'self_reported'
);

-- Seed from docs/master. ON CONFLICT keeps this safe if a venture was created by hand first.
INSERT INTO ventures(id, name, repo, stage, priority, doc_path, kill_criterion, created_at) VALUES
 ('buildflow','BuildFlow','buildflow','BUILD',1,'docs/master/ventures/BUILDFLOW.md','30 real contractor conversations with 0 willingness to pay at any tested price', to_char(now() at time zone 'utc','YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),
 ('agriloop','Agriloop','agriloopmain','BUILD',2,'docs/master/ventures/AGRILOOP.md','0 completed deals in 8 weeks after persistence ships', to_char(now() at time zone 'utc','YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),
 ('ecommerce','E-commerce','Kadeform- or NF-Fragrance- (founder to choose)','DECIDE',3,'docs/master/ventures/ECOMMERCE.md','Ad spend reaches the cap with CPA above break-even and no downward trend', to_char(now() at time zone 'utc','YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),
 ('trading','Trading','mq5','RESEARCH',4,'docs/master/ventures/TRADING.md','Negative expectancy after costs, or paper drawdown beyond the preset limit', to_char(now() at time zone 'utc','YYYY-MM-DD"T"HH24:MI:SS"+00:00"'))
ON CONFLICT (id) DO NOTHING;
INSERT INTO venture_allocation(venture_id, weekday, focus) VALUES
 ('buildflow',1,'Build / fix'),('agriloop',2,'Build / fix'),('trading',3,'Research'),('ecommerce',4,'Build / test'),
 ('buildflow',5,'Growth / sales'),('agriloop',6,'Growth / pilot')
ON CONFLICT DO NOTHING;
