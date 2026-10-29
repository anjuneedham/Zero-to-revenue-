-- Reverses database/migrations/008_ventures.sql. Drops the owner's ventures/tasks/decisions/experiments data.
-- Run by hand (psql -f) when you want to undo; afterwards the migration runner will re-apply 008 on the next start
-- unless you also delete the file.
DROP TABLE IF EXISTS venture_experiments;
DROP TABLE IF EXISTS venture_decisions;
DROP TABLE IF EXISTS venture_tasks;
DROP TABLE IF EXISTS ventures;
DELETE FROM schema_migrations WHERE name = '008_ventures.sql';
