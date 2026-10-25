-- Authentication moved from Firebase to Postgres-stored credentials (002); the column is unused.
ALTER TABLE users DROP COLUMN IF EXISTS firebase_uid;
