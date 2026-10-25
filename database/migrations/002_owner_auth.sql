-- Single-owner authentication (password + TOTP). Exactly one credentials row can exist.
CREATE TABLE owner_credentials (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  password_hash TEXT NOT NULL,
  totp_secret TEXT NOT NULL,
  totp_last_step BIGINT NOT NULL DEFAULT 0,      -- replay protection: a code works once
  recovery_hashes TEXT NOT NULL DEFAULT '[]',    -- sha256 of single-use recovery codes
  setup_complete BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TEXT NOT NULL
);
CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY,                   -- sha256 of the bearer token; token itself is never stored
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE auth_attempts (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('login','setup')),
  ok BOOLEAN NOT NULL,
  at TEXT NOT NULL
);
CREATE INDEX auth_attempts_recent ON auth_attempts (kind, ok, at);
