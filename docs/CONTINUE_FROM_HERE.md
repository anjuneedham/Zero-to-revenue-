# Continue from here (written 2026-10-29, after Phase 6)

Everything needed to resume in a new Claude Code chat. Source of truth is the repo; read `docs/PHASE_HANDOFF.md` (newest entry on top) for details.

## State
- Repo `anjuneedham/Zero-to-revenue-`, branch `ccr-9e3eecee-aucmfd`, PR #1 (base `ccr-a240a1bc-iekqji`). Phases 0-6 are on this branch: protocol and audit (0), data model and CRUD API (1), Founder Dashboard (2), BuildFlow (3), Agriloop (4), Fashion (5), Trading research (6).
- 325 tests pass against a local Postgres 16. No lint/type/build tooling exists in the repo.
- **Next phase: 7, AI Command Center.** Phases 8-12 follow the roadmap in `docs/FOUNDER_OS_BUILD_PROTOCOL.md`.

## Do not skip
1. **Production database is untouched by Phases 1-6, apart from one accidental change.** Vercel preview and production share one Neon `DATABASE_URL`, and the first API request on any deployment runs pending migrations. An early draft's migration (`007_founder.sql`, since removed) was applied to production by a preview request; `007_a_retire_early_dashboard_schema.sql` renames those tables to `early_*`. Migrations 007_a, 007, 008-012 are NOT yet applied. **Do not open or request any preview/production URL of this branch until the founder has taken a Neon backup/branch and said "apply to Neon".**
2. `AUTH_DISABLED=1` (skips login) is set on Vercel for this branch's Preview only and is ignored on production. Preview carries live PayPal/Gmail env; keep Vercel Deployment Protection on; remove the variable when finished.
3. Trading is research and paper only: there is no live mode (API enums and DB CHECKs). Never add one without an explicit founder-approved phase.
4. No `ANTHROPIC_API_KEY` or `LLM_*` pricing env vars exist in the dev sandbox. Do not claim any model call works unless it was actually executed.
5. Open founder items: Gmail OAuth token expires about 2 Nov; Fashion `businesses.name` is still "Fashion" (description has the brand); Agriloop's live data source is unverified.

## Local test recipe
```
service postgresql start
su postgres -c "psql -c \"ALTER USER postgres PASSWORD 'pw'\""
export TEST_DATABASE_URL=postgresql://postgres:pw@localhost:5432/postgres
pip install "psycopg[binary]>=3.2"
python3 -m unittest discover -s tests -t .      # expect 325 OK
```
Run the app locally without login: `AUTH_DISABLED=1 DATABASE_URL=<throwaway db> python3 -m dashboard.app` (never point it at the production DATABASE_URL).

## Where things are
- Data: `database/migrations/007_founder_os_core.sql` (Phase 1), `008` dashboard, `009` content/feedback, `010` marketplace, `011` shop, `012` trading; rollbacks in `database/rollback/`.
- Logic: `core/founder.py` (generic validated CRUD; ENTITIES spec), `core/founder_dashboard.py` (ranking, recommendation), `core/workspace.py` (per-business workspaces), `core/trading_eval.py`.
- API: `dashboard/founder_api.py` (CRUD), `dashboard/app.py` (dashboard + workspace routes).
- UI: `dashboard/static/js/{founder,buildflow,agriloop,fashion,trading}.js`, nav in `main.js`.

## Paste into the new chat
```
Read /docs/CONTINUE_FROM_HERE.md, then /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md (Phase 6 entry first) and /docs/FOUNDER_OS_ARCHITECTURE.md.
Verify the repo first: set up the local Postgres from the recipe, run the tests (expect 325 OK), and inspect core/budget.py, agents/scout/enrich.py (the only existing model caller), core/workspace.py and core/founder.py.
Do not open or request any preview/production URL of this branch until I say the Neon backup is done.
Implement only Phase 7: AI Command Center: task classification, one config location for NO AI / LOW / STANDARD / HIGH routing, business-scoped context selection, structured outputs, usage logging to the existing ledgers, hard budget. Do not claim a model call works unless it was executed. Update /docs/PHASE_HANDOFF.md and stop. Do not start Phase 8.
```
