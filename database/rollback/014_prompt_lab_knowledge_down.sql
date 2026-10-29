-- Manual rollback for 014 (runner is forward-only). Drops Phase 8 data: sources, evidence, evals, citations.
DROP TABLE IF EXISTS ai_citations;
ALTER TABLE ai_usage DROP COLUMN IF EXISTS prompt_ref;
DROP TABLE IF EXISTS evidence;
DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS prompt_evals;
DROP TRIGGER IF EXISTS prompts_immutable ON prompts;
DROP FUNCTION IF EXISTS prompts_immutable();
DROP INDEX IF EXISTS prompts_one_active;
ALTER TABLE prompts DROP COLUMN IF EXISTS parent_id;
ALTER TABLE prompts DROP COLUMN IF EXISTS sha256;
ALTER TABLE prompts DROP COLUMN IF EXISTS source;
ALTER TABLE prompts DROP COLUMN IF EXISTS change_note;
