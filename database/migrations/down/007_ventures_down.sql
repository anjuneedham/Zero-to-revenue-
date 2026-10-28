-- Not applied automatically (the runner only reads database/migrations/*.sql). Run by hand to reverse 007.
DROP TABLE IF EXISTS effort_logs, venture_allocation, metrics, experiments, decisions, venture_tasks, ventures CASCADE;
DELETE FROM schema_migrations WHERE name = '007_ventures.sql';
