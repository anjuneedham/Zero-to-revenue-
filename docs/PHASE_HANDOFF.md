# Phase Handoff - end of Phase 1 (29 Oct 2026)

## Read this first: Phase 0 docs were missing
`docs/FOUNDER_OS_BUILD_PROTOCOL.md`, `docs/PHASE_HANDOFF.md` (Phase 0 version) and `docs/PHASE_0_AUDIT.md` did **not exist**
on either remote branch (`ccr-61f6bbc1-7gtbiy`, `ccr-a240a1bc-iekqji`) or anywhere in history. So the Phase 0 handoff could
not be verified, and the build protocol was not followed because it could not be read. Repo state was used instead, plus
`IMPLEMENTATION_AUDIT.md` and `docs/master/HANDOFF.md` (the closest existing equivalents). **If the protocol exists
elsewhere, add it and check this phase against it.** Verified from the repo: the "three-agent foundation" is Scout /
Operator / Treasury (`agents/`, `agents` table CHECK constraint).

## What changed
- New Founder OS core data model (12 entities + `kpi_readings`), four seeded businesses, authenticated CRUD API, tests, docs.
- Additive only. Legacy agents, tables, dashboard pages, cron and tests are untouched (hence "replace" = new foundation
  added and legacy marked deprecated; deletion deferred, see strategy in `docs/FOUNDER_OS_ARCHITECTURE.md`).

## Database migrations
- `database/migrations/007_founder_os_core.sql` (auto-applied on next cold start / `db.migrate`): creates `businesses, projects,
  goals, work_tasks, kpis, kpi_readings, experiments, research, knowledge, decisions, prompts, ai_usage, automations`; seeds
  BuildFlow, Agriloop, Fashion, Trading (`biz_*` ids).
- `database/rollback/007_founder_os_core_down.sql`: manual, not auto-run (runner is forward-only).
- Naming: Founder OS Task = `work_tasks` because legacy `tasks` (agent queue) still exists.
- Not yet applied to production Neon; it applies itself on the first request after deploy. Back up/branch Neon first if wanted
  (PITR settings remain unverified per the earlier audit).

## Files
Added: `core/founder.py`, `dashboard/founder_api.py`, `database/migrations/007_founder_os_core.sql`,
`database/rollback/007_founder_os_core_down.sql`, `tests/unit/test_founder_os.py`, `docs/FOUNDER_OS_ARCHITECTURE.md`, this file.
Modified: `dashboard/app.py` (import + 3-line mount after session verification).

## APIs
`/api/founder/...` - full table in `docs/FOUNDER_OS_ARCHITECTURE.md`. Owner bearer token required; 8 KiB body cap.

## Tests
`tests/unit/test_founder_os.py` (16 tests: schema, idempotent migrate, seeds, auth, CRUD for all entities, validation,
cross-business parent check, KPI history, immutability, audit, automations default off). Full suite: **252 pass** (236
existing + 16) against local Postgres 16 via `TEST_DATABASE_URL`. Ran once, at the end, per the token policy.

## Known issues / limits
- Phase 0 docs missing (above).
- No UI for any of this yet; API only. The existing dashboard still shows the legacy agent pages.
- `ai_usage` and `automations` are inert storage: no spend enforcement, no execution.
- Stages/descriptions of the four businesses come from `docs/master/HANDOFF.md` evidence; Fashion's brand is unconfirmed
  (open founder decision). Seeded `updated_at` is a fixed date, not deploy time.
- Single owner, no per-business permissions. Booleans are 0/1 integers to match the existing schema.
- `MCP` read-only connector (`dashboard/mcp.py`) does not expose Founder OS data yet.
- Pre-existing, unchanged: Gmail token expires ~2 Nov; MOCK label in status; dead `dashboard/static/app.js`.

## Next phase requirements (Phase 2 suggestion)
1. Supply/confirm the build protocol and Phase 0 audit; reconcile.
2. Founder OS dashboard: business switcher + per-business overview (tasks, goals, KPIs, decisions) using these endpoints.
3. Seed real first records per business (BuildFlow blockers as `work_tasks`, KPIs such as paying customers) once the owner
   confirms them; decide Fashion brand.
4. Legacy retirement migration (leads/payments -> BuildFlow records), then drop in a separate reversible migration.
5. Only after that: AI layer (needs `ANTHROPIC_API_KEY`, writes `ai_usage`, budget enforcement) and automation execution
   behind the existing approval gates.
