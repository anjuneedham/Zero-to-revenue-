-- Manual rollback for 007 (not auto-run; the runner is forward-only). Destroys all Founder OS data.
DROP TABLE IF EXISTS automations, ai_usage, prompts, decisions, knowledge, research, experiments,
  kpi_readings, kpis, work_tasks, goals, projects, businesses CASCADE;
DELETE FROM schema_migrations WHERE name = '007_founder_os_core.sql';
