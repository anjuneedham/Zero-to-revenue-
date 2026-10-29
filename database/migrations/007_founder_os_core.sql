-- Founder OS core data architecture (Phase 1). Additive only: no existing table is altered or dropped.
-- Legacy objects (agents, agent_runs, opportunities, tasks, leads, ...) are kept so existing data and
-- the Scout/Operator/Treasury flows keep working until a later phase retires them with a data migration.
-- NOTE: the legacy agent-queue table `tasks` keeps its name; the Founder OS Task is `work_tasks`.
-- Rollback: database/rollback/007_founder_os_core_down.sql

CREATE TABLE businesses (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE CHECK (slug ~ '^[a-z][a-z0-9_-]{1,40}$'),
  name TEXT NOT NULL,
  description TEXT,
  stage TEXT NOT NULL DEFAULT 'idea' CHECK (stage IN ('idea','building','launched','growing','paused')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','archived')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

CREATE TABLE projects (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  name TEXT NOT NULL, description TEXT,
  status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','active','blocked','done','cancelled')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX projects_business ON projects(business_id);

CREATE TABLE goals (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  project_id TEXT REFERENCES projects(id),
  title TEXT NOT NULL, description TEXT, target_metric TEXT,
  target_value NUMERIC(24,8), current_value NUMERIC(24,8), due_date TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','achieved','missed','cancelled')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX goals_business ON goals(business_id);

CREATE TABLE work_tasks (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  project_id TEXT REFERENCES projects(id), goal_id TEXT REFERENCES goals(id),
  title TEXT NOT NULL, description TEXT,
  status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','doing','blocked','done','cancelled')),
  priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
  due_date TEXT, completed_at TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX work_tasks_business_status ON work_tasks(business_id, status);

CREATE TABLE kpis (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  name TEXT NOT NULL, unit TEXT, target_value NUMERIC(24,8), current_value NUMERIC(24,8),
  direction TEXT NOT NULL DEFAULT 'up' CHECK (direction IN ('up','down')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE (business_id, name)
);
-- Append-only history of KPI values (the kpis row holds only the latest).
CREATE TABLE kpi_readings (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, kpi_id TEXT NOT NULL REFERENCES kpis(id),
  value NUMERIC(24,8) NOT NULL, note TEXT, recorded_at TEXT NOT NULL
);

CREATE TABLE experiments (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  goal_id TEXT REFERENCES goals(id),
  hypothesis TEXT NOT NULL, method TEXT, success_metric TEXT, result TEXT, learnings TEXT,
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','running','succeeded','failed','abandoned')),
  started_at TEXT, ended_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX experiments_business ON experiments(business_id);

CREATE TABLE research (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  title TEXT NOT NULL, question TEXT, summary TEXT, source_url TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','done','archived')),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX research_business ON research(business_id);

-- business_id NULL = cross-business knowledge.
CREATE TABLE knowledge (
  id TEXT PRIMARY KEY, business_id TEXT REFERENCES businesses(id),
  title TEXT NOT NULL, body TEXT NOT NULL, tags TEXT, source_url TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX knowledge_business ON knowledge(business_id);

CREATE TABLE decisions (
  id TEXT PRIMARY KEY, business_id TEXT REFERENCES businesses(id),
  title TEXT NOT NULL, context TEXT, decision TEXT, rationale TEXT, alternatives TEXT,
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','decided','reversed')),
  decided_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX decisions_business ON decisions(business_id);

CREATE TABLE prompts (
  id TEXT PRIMARY KEY, business_id TEXT REFERENCES businesses(id),
  name TEXT NOT NULL, purpose TEXT, body TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE (name, version)
);

-- Ledger of AI spend. Phase 1 only stores rows; nothing calls a model yet.
CREATE TABLE ai_usage (
  id TEXT PRIMARY KEY, business_id TEXT REFERENCES businesses(id),
  provider TEXT NOT NULL DEFAULT 'anthropic', model TEXT NOT NULL, purpose TEXT,
  input_tokens INTEGER NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
  output_tokens INTEGER NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
  cost_usd NUMERIC(14,6) NOT NULL DEFAULT 0 CHECK (cost_usd >= 0),
  created_at TEXT NOT NULL
);
CREATE INDEX ai_usage_business ON ai_usage(business_id, created_at);

-- Definitions only in Phase 1: nothing executes them. enabled defaults to 0 (off).
CREATE TABLE automations (
  id TEXT PRIMARY KEY, business_id TEXT REFERENCES businesses(id),
  name TEXT NOT NULL, description TEXT,
  trigger_kind TEXT NOT NULL DEFAULT 'manual' CHECK (trigger_kind IN ('manual','schedule','event')),
  schedule TEXT, config TEXT,
  enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0,1)),
  requires_approval INTEGER NOT NULL DEFAULT 1 CHECK (requires_approval IN (0,1)),
  last_run_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);

-- The four businesses (idempotent ids; descriptions are factual per docs/master/HANDOFF.md).
INSERT INTO businesses(id, slug, name, description, stage, status, created_at, updated_at) VALUES
 ('biz_buildflow','buildflow','BuildFlow','Construction/trades job-management app (Next.js, Firebase, Capacitor Android). Live; first-revenue blockers tracked as tasks.','launched','active', '2026-10-29T00:00:00+00:00','2026-10-29T00:00:00+00:00'),
 ('biz_agriloop','agriloop','Agriloop','Farm marketplace (Next.js, Supabase). Live, but marketplace data layer is not yet production-safe.','building','active','2026-10-29T00:00:00+00:00','2026-10-29T00:00:00+00:00'),
 ('biz_fashion','fashion','Fashion','E-commerce brand. Which storefront/brand this is has not been confirmed by the founder yet.','idea','active','2026-10-29T00:00:00+00:00','2026-10-29T00:00:00+00:00'),
 ('biz_trading','trading','Trading','Algorithmic trading (MQL5 EA on Deriv synthetic indices). No evidence of an edge yet; research/paper-trading stage.','idea','active','2026-10-29T00:00:00+00:00','2026-10-29T00:00:00+00:00');
