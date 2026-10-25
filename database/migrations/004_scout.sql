-- Scout (Phase 2): LLM spend ledger, structured agent events, opportunity dedupe.
CREATE TABLE llm_usage (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  at TEXT NOT NULL, agent TEXT NOT NULL, model TEXT NOT NULL, purpose TEXT NOT NULL,
  input_tokens BIGINT NOT NULL DEFAULT 0, output_tokens BIGINT NOT NULL DEFAULT 0,
  cost_usd NUMERIC(14,6) NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK (status IN ('RESERVED','DONE','FAILED'))
);
CREATE INDEX llm_usage_at ON llm_usage (at);
CREATE TABLE events (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  at TEXT NOT NULL, event TEXT NOT NULL, source_agent TEXT NOT NULL, payload TEXT NOT NULL,
  consumed_at TEXT
);
-- Unknown capital must stay unknown (NULL), never silently 0 = "zero capital".
ALTER TABLE opportunities ALTER COLUMN required_capital DROP NOT NULL;
ALTER TABLE opportunities ALTER COLUMN required_capital DROP DEFAULT;
CREATE UNIQUE INDEX opportunities_source_url ON opportunities (source_url) WHERE source_url IS NOT NULL;
