# Continue from here (written 2026-10-29, after Phase 9: 384 tests, next is Phase 10)

Everything needed to resume in a new Claude Code chat. Source of truth is the repo; read `docs/PHASE_HANDOFF.md` (newest entry on top) for details.

## State
- Repo `anjuneedham/Zero-to-revenue-`. Phases 0-8 are on branch `ccr-edf0723c-id0y6l` (Phase 8 head `9b907a7`), created from `966a8d3` (Phase 7 head, branch `ccr-79ad6026-fa1uuh`). Phase 9 is committed locally on branch `phase-9-experiments` (from `9b907a7`) and has **not been pushed** (founder's choice; ask where to push). None of these is on the default branch. Phases: protocol/audit (0), data model and CRUD API (1), Founder Dashboard (2), BuildFlow (3), Agriloop (4), Fashion (5), Trading research (6), AI Command Center (7), Prompt Lab / Research / Knowledge (8), Experiments and Growth (9).
- 384 tests pass against a local Postgres 16 (older numbers 325/348/367 are out of date). No lint/type/build tooling exists in the repo.
- **Next phase: 10, Automation Engine.** Phases 11-12 follow the roadmap in `docs/FOUNDER_OS_BUILD_PROTOCOL.md`.

## Do not skip
1. **Production database is untouched by Phases 1-8, apart from one accidental change.** Vercel preview and production share one Neon `DATABASE_URL`, and the first API request on any deployment runs pending migrations. An early draft's migration (`007_founder.sql`, since removed) was applied to production by a preview request; `007_a_retire_early_dashboard_schema.sql` renames those tables to `early_*`. Migrations 007_a, 007, 008-015 are NOT yet applied. **Do not open or request any preview/production URL of this branch until the founder has taken a Neon backup/branch and said "apply to Neon".** Pushing a branch can itself trigger a preview deployment: do not push to `ccr-79ad6026-fa1uuh` or `ccr-edf0723c-id0y6l`; work on a new branch and hold pushes until the founder names one.
2. `AUTH_DISABLED=1` (skips login) is set on Vercel for this branch's Preview only and is ignored on production. Preview carries live PayPal/Gmail env; keep Vercel Deployment Protection on; remove the variable when finished.
3. Trading is research and paper only: there is no live mode (API enums and DB CHECKs). Never add one without an explicit founder-approved phase.
4. No `ANTHROPIC_API_KEY` or `LLM_*` pricing env vars exist in the dev sandbox. **No real model call has ever been executed** (Phase 7 `AnthropicClient`, Phase 8 prompt resolution/citations are only tested with a fake client; Phase 9 has no model call). Do not claim any model call works unless it was actually executed.
5. Experiments are records only: status moves only through start/conclude/abandon, results are fixed once concluded, learnings enter knowledge as ASSUMED evidence.
6. Facts vs assumptions: evidence is `verified` (needs a source), `assumed` or `unknown`; note/research trust is derived from evidence. Never store or present an assumption as a fact. Prompt versions are immutable; change = new version.
7. Open founder items: Gmail OAuth token expires about 2 Nov; Fashion `businesses.name` is still "Fashion" (description has the brand); Agriloop's live data source is unverified.

## Local test recipe
```
service postgresql start
su postgres -c "psql -c \"ALTER USER postgres PASSWORD 'pw'\""
export TEST_DATABASE_URL=postgresql://postgres:pw@localhost:5432/postgres
pip install "psycopg[binary]>=3.2" --break-system-packages
python3 -m unittest discover -s tests -t .      # expect 384 OK
```
Run the app locally without login: create a throwaway database, then `AUTH_DISABLED=1 DATABASE_URL=<throwaway db> python3 -m dashboard.app` (never point it at the production DATABASE_URL). Do not use `pkill -f dashboard.app` (it kills your own shell); find the PID by matching /proc/<pid>/cmdline exactly (`ss` is not installed).

## Where things are
- Data: `database/migrations/007_founder_os_core.sql` (Phase 1), `008` dashboard, `009` content/feedback, `010` marketplace, `011` shop, `012` trading, `013` AI command center, `014` prompt lab / sources / evidence / citations, `015` experiments lifecycle; rollbacks in `database/rollback/`.
- Logic: `core/founder.py` (generic validated CRUD; ENTITIES spec), `core/founder_dashboard.py`, `core/workspace.py`, `core/trading_eval.py`, `core/ai.py` + `core/ai_config.py` (Command Center, the only model path), `core/budget.py`, `core/prompt_lab.py`, `core/knowledge.py`, `core/experiments.py`, `core/growth.py`.
- API: `dashboard/founder_api.py` (CRUD), `dashboard/lab_api.py` (`/api/lab/*`, `/api/knowledge/*`), `dashboard/growth_api.py` (`/api/growth/*`), `dashboard/app.py` (dashboard, workspace and `/api/ai/*` routes; `READ_LIMIT` caps request reads).
- UI: `dashboard/static/js/{founder,buildflow,agriloop,fashion,trading,lab,growth}.js`, nav in `main.js`.

## Paste into the new chat
The ready-to-paste Phase 10 instruction is at the bottom of the Phase 9 entry in `docs/PHASE_HANDOFF.md` ("Ready-to-paste next-chat instruction").
