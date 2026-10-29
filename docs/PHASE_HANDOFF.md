# FOUNDER OS PHASE HANDOFF

> History note: no earlier `PHASE_HANDOFF.md` existed. The repo's prior handoff is `docs/master/HANDOFF.md` (28 Oct, master-plan chat) and is unchanged. This file starts the Founder OS phase record.

## Phase Completed
Phase 2 — Founder Dashboard

## Completion Status
**PARTIAL.** The dashboard is built, reachable, and tested against a real local PostgreSQL 16 (257/257 tests pass, browser-checked at 3 sizes). It is PARTIAL because (a) the documents the brief says to read (`FOUNDER_OS_BUILD_PROTOCOL.md`, a previous `PHASE_HANDOFF.md`, `FOUNDER_OS_ARCHITECTURE.md`) do not exist in the repo, so Phase 1 could not be verified against a spec and a minimal data foundation had to be created here; (b) it has not been run against the production Neon database or deployed; (c) no lint/type-check/build tooling exists in this repo to run.

## Date
2026-10-29

## Objective
One founder command surface over four businesses: next-action recommendation, ranked tasks, blockers, goals/KPIs, experiments, AI usage, decisions, quick actions.

## What Was Built
- Migration `007_founder.sql`: `ventures` (seeded with the 4 businesses + default priority 1-4, nothing else seeded), `goals`, `founder_tasks`, `kpis`, `kpi_readings`, `blockers`, `experiments`, `decisions`.
- `core/founder.py`: ranking, recommendation, KPI progress/trend, dashboard read model (each section isolated so one failure doesn't break the rest), validated idempotent writes.
- API: `GET /api/founder/dashboard`, `POST /api/founder/{task|goal|kpi|reading|blocker|experiment|decision}`, `POST /api/founder/tasks/<id>/status`, `POST /api/founder/blockers/<id>/resolve`.
- UI: `dashboard/static/js/founder.js`, new first nav item "Founder" (also the default landing page).

## Files Created
`database/migrations/007_founder.sql`, `core/founder.py`, `dashboard/static/js/founder.js`, `tests/unit/test_founder.py`, `docs/PHASE_HANDOFF.md`, `docs/screenshots/founder-desktop.png`, `docs/screenshots/founder-phone.png`.

## Files Modified
`dashboard/app.py` (routes), `dashboard/pages/index.html` (script tag), `dashboard/static/js/main.js` (nav, default page), `dashboard/static/js/core.js` (icon), `dashboard/static/css/app.css` (6-column tab bar, hero contrast), `dashboard/static/sw.js` (cache v5 + new file).

## Files Removed
None.

## Database Changes
Additive migration 007, applied automatically by `db.migrate` on startup (advisory-locked, forward-only). No existing table touched. The Phase-1 table name `tasks` was already taken by the agent work queue, so the founder's table is `founder_tasks`. Seeded rows: 4 `ventures` only (configuration, not metrics). Reorder priority with `UPDATE ventures SET priority=... WHERE id=...`; there is no UI for this yet.

## API and Data Access Changes
All routes sit behind the existing owner session bearer token (401 otherwise). Writes: server-side validation (lengths, enums, dates, finite numbers, 1-5 impact), references must exist and belong to the same business, `client_key` makes double submits idempotent (`ON CONFLICT DO NOTHING`), every write is audited (`founder.*` in `audit_events`). Errors return generic messages; no SQL details leak. Writes only create/update the owner's own records; nothing starts agents, spends money or trades.

## UI and Navigation Changes
"Founder" added to side nav and mobile tab bar (now 6 tabs). Sections: header + "What should I do next?" button, recommendation card, four business cards, today's priorities (filters: business/status/urgency; Start / Mark done / Blocked / Details), blockers (recorded vs. "inferred, not verified"), goals & KPIs, active experiments, AI usage, recent decisions, quick actions. Business cards link to a filtered task list (no business workspaces exist yet).

## Recommendation Logic
Score per open task (all constants in `core/founder.py`): business priority `(lowest_rank - rank) * 6` (+18 for priority 1 of 4); urgency overdue +30, due today +25, <=3 days +20, <=7 days +12, later +4; impact `5 * (1..5)`; effort <=1h +6, <=4h +3, >8h -3; in progress +8; unblocks other tasks +4 each (cap 12); serves an active goal +3. Tasks that are marked BLOCKED, wait on an unfinished task, or have an open blocker are shown but never recommended. If every task is blocked the oldest recorded blocker is recommended instead; with no tasks it says what is missing. Ties break by priority, due date, age. The recommendation reports evidence quality (high/medium/low by missing impact/effort/due data) and notes when a lower-priority business wins on a deadline.
Limitations: heuristic weights, not an optimum; revenue potential, risk of inaction and strategic value are only captured through the manual impact (1-5) and goal link; there is no time-available input; the founder override ("choose it yourself") is stored per device in browser localStorage, not in the database. No AI is used.

## Authentication and Permissions
Reuses the single-owner login (password + TOTP, bearer session). No multi-user model exists in this app, so "authorized businesses" = all businesses; per-business isolation is enforced for cross-references (goal/task/blocker links must be in the same business).

**Skipping login (owner convenience).** `AUTH_DISABLED=1` makes the API skip the password/TOTP check. `auth_disabled()` in `dashboard/app.py` ignores it whenever `VERCEL_ENV=production`, so the live site always requires login. It is set on Vercel only for the preview of branch `ccr-9e3eecee-aucmfd` (Preview target, branch-scoped); remove it in Vercel > Settings > Environment Variables. Local runs honour it too. Anyone who can open that preview URL can use every agent action (including Gmail send), so keep Vercel Deployment Protection on. Tested in `AuthDisabledTest` (258 tests OK).

## Integrations
None added. AI usage reads the existing `llm_usage` table (no business column, so no per-business split; cap shown only if `LLM_MONTHLY_BUDGET_USD` is set).

## Tests Run
- Baseline before changes: `python3 -m unittest discover -s tests -t .` with a local Postgres 16 → 236 tests OK.
- After changes, same command → **257 tests OK** (21 new in `tests/unit/test_founder.py`: ranking, blocked handling, missing data, KPI progress/trend, auth, validation, cross-business isolation, idempotency, section-failure isolation, AI usage from real rows, text returned as data).
- Real browser (Playwright/Chromium against a local server and throwaway schema): empty and populated dashboards at 390, 820, 1366 px wide — 0 px horizontal overflow, 0 console errors; created a task through the form, marked a task done (shows under "Done today"). Screenshots in `docs/screenshots/founder-*.png`. This was an ad-hoc script (not committed).
- Lint, type-check, build: **not run — the repo has none configured.** Not run: the Vercel entry against production.

## Acceptance Criteria
- Reachable through the real app: PASS (local server)
- Four businesses from stored records: PASS
- Priority order from data: PASS (test reorders via SQL)
- Cards accurate + honest empties: PASS
- Priorities from real tasks with reasons: PASS
- Transparent recommendation logic: PASS
- Founder can override: PASS (per-device only)
- Blockers recorded vs inferred: PASS
- Goals/KPIs: PASS
- Experiments/decisions: PASS (detail drawers; no separate record pages)
- AI usage only from real records: PASS (unit-tested; not seen with live data)
- Quick actions real: PASS (forms exercised via API tests; task form + status via browser; other forms not clicked in browser)
- Auth/authorization/relationships: PASS (single-owner model)
- Loading/empty/error states: PARTIAL (skeleton, empty, per-section error unit-tested; the failed-mutation toast and session-expiry paths use existing shared code and were not browser-tested)
- Phone/tablet/desktop: PASS (no overflow; screenshots reviewed)
- Existing routes not broken: PASS (all 236 prior tests)
- Lint/type/build: NOT TESTED (none exist)
- Handoff updated + Phase 3 entry: PASS

## Known Issues
- Default landing page is now Founder instead of Overview.
- Founder override is per device.
- `Mark done` / status changes have no undo besides setting status again.
- Tasks cannot be edited or deleted; goals/KPIs/experiments/decisions cannot be edited or closed from the UI (create-only, except blocker resolve and task status).
- No business-detail pages; "Show its tasks" only filters the list.
- Not tested on Neon/Vercel; migration 007 uses `to_char(now() ...)` seeded timestamps that match the app's ISO-text convention.

## Technical Debt
`create()` is one long function; dashboard filters are client-side (list capped at 15 shown); experiments/decisions lists are capped at 20/8 server-side; no pagination.

## Decisions Made
Founder table named `founder_tasks` to avoid the agent queue; deterministic scoring; KPI percentage only when baseline and target both exist and differ; the four businesses seeded as configuration in the migration.

## Assumptions
"Phase 1" = the ventures/tasks/decisions/experiments/metrics build named in `docs/master/HANDOFF.md` step 3, which did not exist and was created minimally here. Business ids: `buildflow`, `agriloop`, `fashion`, `trading`.

## Unfinished Work
Business detail views; editing/closing records; configurable weights; per-business AI spend; a lint/build pipeline.

## Phase 3 Prerequisites
Apply migration 007 to Neon (automatic on first request/cold start). Confirm the real e-commerce brand (open decision in `docs/master/HANDOFF.md`). Enter real tasks/KPIs for BuildFlow.

## Next Phase
Phase 3 — BuildFlow Workspace.

## Phase 3 Entry Instructions
In a new chat: read this file and `docs/master/HANDOFF.md`; note the Founder OS protocol/architecture docs named in the brief do not exist (supply them if they live elsewhere). Verify the repo: run `TEST_DATABASE_URL=<throwaway postgres> python3 -m unittest discover -s tests -t .` (expect 257 OK). Inspect first: `core/founder.py`, `database/migrations/007_founder.sql`, `dashboard/app.py` (founder routes), `dashboard/static/js/founder.js`, and `dashboard/static/js/main.js` (page registry/nav). Build only the BuildFlow workspace on the `ventures.id='buildflow'` records. Do not start Phase 4+.

## Risks
Scoring can mislead if impact/due dates are guessed; empty data makes the dashboard look idle; production migration untested; single-owner auth is the only access control.
