# Founder OS Architecture (updated Phase 1, 29 Oct 2026)

Stack unchanged: Python 3.13 stdlib HTTP handler (`dashboard/app.py`, shared by local runner and Vercel `api/index.py`),
Postgres (Neon) via `core/db.py`, forward-only SQL migrations applied under an advisory lock, vanilla-JS dashboard.
Owner-only auth (scrypt + TOTP), append-only `audit_events`, approval gates and kill switch are reused as-is.

## Layers
1. **Core data (Phase 1, new)** - 12 entities in migration `007_founder_os_core.sql`, all scoped to a `business`.
2. **Data layer** - `core/founder.py`: one declarative spec per entity (allowed columns, types, enums, required fields,
   parent links). Generic list/create/update; parameterised SQL; every write audited; parents must be in the same business.
3. **API** - `dashboard/founder_api.py`, mounted in `dashboard/app.py` after owner-session verification.
4. **Legacy (kept, deprecated)** - Scout / Operator / Treasury agents and their tables. See "Legacy" below.

## Data model
```
businesses (buildflow, agriloop, fashion, trading)
 ├─ projects ─┐
 ├─ goals ────┴─ (goal.project_id)
 ├─ work_tasks  (project_id, goal_id)
 ├─ kpis ── kpi_readings (append-only history)
 ├─ experiments (goal_id)
 ├─ research
 ├─ knowledge   (business_id NULL = cross-business)
 ├─ decisions   (business_id NULL allowed)
 ├─ prompts     (business_id NULL allowed; UNIQUE(name, version))
 ├─ ai_usage    (append-only cost ledger; nothing writes it automatically yet)
 └─ automations (definitions only; enabled=0 and requires_approval=1 by default; nothing executes them)
```
Conventions: TEXT ids with a prefix (`prj_`, `goal_`, `wt_`, `kpi_`, `exp_`, `res_`, `kn_`, `dec_`, `pr_`, `use_`, `auto_`),
ISO-8601 TEXT timestamps, status enums enforced by CHECK constraints, booleans as 0/1 INTEGER (matches existing schema).

**Naming collision:** the legacy agent-queue table is already called `tasks`. It is untouched; the Founder OS Task is
`work_tasks`. When the legacy queue is retired, it can be renamed `agent_tasks` and `work_tasks` considered for renaming.

## Businesses
| slug | name | stage | basis |
|---|---|---|---|
| buildflow | BuildFlow | launched | repo `buildflow`, live; own report verdict NOT READY |
| agriloop | Agriloop | building | repo `agriloopmain`; in-memory data source, not production-safe |
| fashion | Fashion | idea | brand/storefront not yet confirmed by founder |
| trading | Trading | idea | repo `mq5`; no evidence of an edge yet |
Seeded with fixed ids (`biz_<slug>`) by the migration; stages are editable data, not code.

## API (all require the owner bearer token)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/founder/businesses` | the four businesses |
| GET | `/api/founder/businesses/<slug>` | business + record counts |
| GET/POST | `/api/founder/businesses/<slug>/<entity>` | list / create (business from path) |
| GET/POST | `/api/founder/<entity>` | list across businesses / create global-capable entities |
| POST | `/api/founder/<entity>/<id>` | update (ai-usage is immutable; business cannot change) |
| POST | `/api/founder/kpis/<id>/readings` | record a KPI value (appends history, updates current) |
`<entity>`: projects goals work-tasks kpis experiments research knowledge decisions prompts ai-usage automations.
Errors: 400 validation (message never contains driver text), 401 no session, 404 unknown business/id. Body limit 8 KiB.

## Legacy (not deleted; migration strategy)
Nothing was dropped or altered. Legacy tables (`agents`, `agent_runs`, `opportunities`, `tasks`, `task_events`, `user_actions`,
`deliverables`, `submissions`, `payments`, `wallets`, `transactions`, `ledger_entries`, `leads`, `notifications`) and the
three agents keep running, including the daily cron. Retirement plan, for a later phase: (1) copy open `leads` and verified
`payments`/`ledger_entries` into BuildFlow-scoped records, (2) stop scheduling the agents, (3) export then drop tables in a
separate, reversible migration after the owner confirms. Rollback for 007: `database/rollback/007_founder_os_core_down.sql`.

## Not built yet (by design)
AI calls, usage enforcement/budgets for `ai_usage`, automation execution, per-business dashboards/UI, business-specific
workspaces, migration of legacy data, auth beyond the single owner.
