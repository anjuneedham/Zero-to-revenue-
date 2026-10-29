-- Phase 3 (BuildFlow workspace): content tracking and customer feedback. Additive; both tables are business-scoped so later
-- workspaces can reuse them. Metrics are NULL until the founder records them (never defaulted to 0).
-- Rollback: database/rollback/009_workspace_content_feedback_down.sql (manual).
CREATE TABLE content_items (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  platform TEXT NOT NULL CHECK (platform IN ('youtube_shorts','tiktok','instagram','facebook','other')),
  topic TEXT, hook TEXT, format TEXT,
  status TEXT NOT NULL DEFAULT 'idea' CHECK (status IN ('idea','scripted','filmed','posted','dropped')),
  posted_at TEXT, url TEXT,
  views INTEGER CHECK (views IS NULL OR views >= 0), likes INTEGER CHECK (likes IS NULL OR likes >= 0),
  comments INTEGER CHECK (comments IS NULL OR comments >= 0), shares INTEGER CHECK (shares IS NULL OR shares >= 0),
  signups INTEGER CHECK (signups IS NULL OR signups >= 0), notes TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX content_items_business ON content_items(business_id, status);

CREATE TABLE feedback_items (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  source TEXT, contact TEXT, body TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'other' CHECK (kind IN ('bug','feature','pricing','onboarding','praise','other')),
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','triaged','actioned','dismissed')),
  work_task_id TEXT REFERENCES work_tasks(id),
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX feedback_items_business ON feedback_items(business_id, status);
