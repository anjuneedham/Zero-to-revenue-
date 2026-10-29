-- One-time repair. An early Phase 2 draft shipped its own migration (007_founder.sql, since removed) and a preview deploy applied it to the
-- shared Neon database. Its tables use the same names as the Phase 1 Founder OS tables (goals, kpis, experiments, decisions, ...),
-- so 007_founder_os_core would fail. Rename (never drop) them out of the way; their data stays available as early_*.
-- A no-op on every database that never had them. Sorts before 007_founder_os_core.sql on purpose.
DO $$
DECLARE t TEXT;
BEGIN
  IF to_regclass('ventures') IS NOT NULL AND to_regclass('founder_tasks') IS NOT NULL THEN
    FOREACH t IN ARRAY ARRAY['kpi_readings','blockers','founder_tasks','kpis','goals','experiments','decisions','ventures'] LOOP
      IF to_regclass(t) IS NOT NULL THEN
        EXECUTE format('ALTER TABLE %I RENAME TO %I', t, 'early_' || t);
      END IF;
    END LOOP;
  END IF;
END $$;
