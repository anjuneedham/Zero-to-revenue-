-- Phase 8: Prompt Lab, Research sources/evidence, knowledge citations. Additive only.

-- Prompts: versions become immutable (new body = new version). One active version per name.
ALTER TABLE prompts ADD COLUMN change_note TEXT;
ALTER TABLE prompts ADD COLUMN source TEXT NOT NULL DEFAULT 'lab' CHECK (source IN ('lab','file'));
ALTER TABLE prompts ADD COLUMN sha256 TEXT;
ALTER TABLE prompts ADD COLUMN parent_id TEXT REFERENCES prompts(id);
-- Before the unique index: keep only the newest active version per name (the old CRUD default was active=1 for all).
UPDATE prompts SET active = 0
 WHERE active = 1 AND id NOT IN (SELECT DISTINCT ON (name) id FROM prompts WHERE active = 1 ORDER BY name, version DESC);
CREATE UNIQUE INDEX prompts_one_active ON prompts(name) WHERE active = 1;

CREATE FUNCTION prompts_immutable() RETURNS trigger AS $$
BEGIN
  IF NEW.name <> OLD.name OR NEW.body <> OLD.body OR NEW.version <> OLD.version
     OR NEW.business_id IS DISTINCT FROM OLD.business_id THEN
    RAISE EXCEPTION 'prompt versions are immutable: create a new version';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER prompts_immutable BEFORE UPDATE ON prompts FOR EACH ROW EXECUTE FUNCTION prompts_immutable();

-- Scored outputs for a prompt version, entered by the founder (append-only).
CREATE TABLE prompt_evals (
  id TEXT PRIMARY KEY, prompt_id TEXT NOT NULL REFERENCES prompts(id),
  input TEXT NOT NULL, output TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5), notes TEXT, created_at TEXT NOT NULL
);
CREATE INDEX prompt_evals_prompt ON prompt_evals(prompt_id);

-- Research sources (where a claim came from). Always one business.
CREATE TABLE sources (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  title TEXT NOT NULL, url TEXT,
  kind TEXT NOT NULL DEFAULT 'web' CHECK (kind IN ('web','document','interview','dataset','internal','other')),
  publisher TEXT, retrieved_at TEXT,
  reliability TEXT NOT NULL DEFAULT 'unknown' CHECK (reliability IN ('high','medium','low','unknown')),
  notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX sources_business ON sources(business_id);

-- A single claim attached to a research item or a knowledge note, labelled verified / assumed / unknown.
-- "verified" is impossible without a source (also enforced in code with a clean message).
CREATE TABLE evidence (
  id TEXT PRIMARY KEY, business_id TEXT NOT NULL REFERENCES businesses(id),
  research_id TEXT REFERENCES research(id), knowledge_id TEXT REFERENCES knowledge(id),
  claim TEXT NOT NULL,
  label TEXT NOT NULL DEFAULT 'unknown' CHECK (label IN ('verified','assumed','unknown')),
  source_id TEXT REFERENCES sources(id), quote TEXT, note TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  CHECK (research_id IS NOT NULL OR knowledge_id IS NOT NULL),
  CHECK (label <> 'verified' OR source_id IS NOT NULL)
);
CREATE INDEX evidence_business ON evidence(business_id);
CREATE INDEX evidence_research ON evidence(research_id);
CREATE INDEX evidence_knowledge ON evidence(knowledge_id);

-- Which prompt version answered, and the claims/citations of each Command Center answer (append-only).
ALTER TABLE ai_usage ADD COLUMN prompt_ref TEXT;
CREATE TABLE ai_citations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ai_usage_id TEXT NOT NULL REFERENCES ai_usage(id), business_id TEXT NOT NULL REFERENCES businesses(id),
  claim TEXT NOT NULL, label TEXT NOT NULL CHECK (label IN ('verified','assumed','unknown')),
  source TEXT, created_at TEXT NOT NULL
);
CREATE INDEX ai_citations_usage ON ai_citations(ai_usage_id);
