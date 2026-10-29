# Founder OS Phase Handoff

Latest entry on top. Rules and templates: [FOUNDER_OS_BUILD_PROTOCOL.md](FOUNDER_OS_BUILD_PROTOCOL.md).

## Phase 4: Agriloop Workspace. Completed 2026-10-29

**Overall status: PARTIAL.** Built and tested locally (303 tests + browser check at 3 sizes). Not applied to production Neon (awaiting founder approval + backup); no lint/type/build tooling. Phase 3 was reviewed before starting (no defects found; its handoff lists its limits).
**Branch:** `ccr-9e3eecee-aucmfd` (stacked, PR #1).

### Objective
Agriloop marketplace workspace: farmers, buyers, supply, demand, matching, transactions, retention, partner-opportunity validation, using only recorded data.

### Work completed
- Migration `010_marketplace.sql`: `market_parties` (role farmer|buyer, stage lead/onboarded/active/churned), `market_listings` (supply, must belong to a farmer), `market_demand` (buyer requests, must belong to a buyer), `market_transactions` (proposed/agreed/completed/cancelled). Business-scoped; money rows carry their own currency.
- `core/workspace.py`: `marketplace` section for `agriloop` (funnel by role/stage, liquidity per product, suggested matches, deal summary, repeat buyers). Pure, tested helpers `suggest_matches`, `liquidity`, `transaction_summary`.
- Matching is rule-based and labelled **inference**: same product (case-insensitive) required; a known location mismatch or a known price above the buyer's max (same currency) rules a pair out; unknown fields neither help nor hurt and are listed as unknowns. Score = 50 base + location/price/quantity evidence. One click records a *proposed* deal; nothing is auto-confirmed.
- Money: completed deal value is summed per currency, never across currencies; completed deals without an amount/currency are counted but not valued.
- Partner hypothesis: knowledge notes tagged `partner-hypothesis` render as "HYPOTHESIS, not validated"; nothing about a partner is stored as fact.
- UI `dashboard/static/js/agriloop.js` (`#agriloop`: Overview, Supply & demand, Matches, Deals, People, Notes). Overview/Notes are shared with BuildFlow via `Z.ws`. Side-nav entry; phones reach it from the Founder business card.

### Files
- Created: `database/migrations/010_marketplace.sql`, `database/rollback/010_marketplace_down.sql`, `dashboard/static/js/agriloop.js`, `tests/unit/test_marketplace.py`.
- Modified: `core/founder.py` (4 entities, party-role check, `occurred_at` stamping), `core/workspace.py`, `dashboard/static/js/buildflow.js` (shared helpers, `Z.ws`), `main.js`, `index.html`, `sw.js`, docs.
- Removed: none.

### Tests
| Command | Result | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -t .` (local Postgres 16) | **303 OK** (12 new in `test_marketplace.py`: matching rules, liquidity, currency-safe money, end-to-end flow, farmer/buyer role enforcement, cross-business rejection, validation, repeat buyers) | PASS |
| Headless Chromium, 6 tabs x phone/tablet/desktop | 0 px overflow, 0 console errors; match shown, add farmer via form | PASS |
| Production Neon, the real Agriloop product/data source, real users | not exercised | NOT TESTED |

### Acceptance criteria
- Farmers/buyers/supply/demand/matching/transactions views: PASS
- Retention: PARTIAL (funnel stage and repeat-buyer count only; no cohort or time-based retention)
- Partner opportunity as hypothesis: PASS (tag-based; no formal validation workflow, see Phase 9)
- Experiments/metrics/decisions: PASS (shared Overview/Notes)
- Business isolation: PASS (tested)
- Geographic expansion: NOT BUILT (location is free text; no parish/region model or expansion tracking)
- Integration with the live Agriloop product: NOT BUILT (audit says its marketplace may be on an in-memory store; unverified)

### Known issues and technical debt
- All data is manual entry. Matching is naive text equality on product names (no synonyms, units are not converted).
- No edit for all fields of listings/requests; no delete UI.
- Migrations 007_a, 007, 008, 009, 010 are all unapplied on production Neon.

### Decisions and assumptions
- Matching is a suggestion list, never an automatic action. Currency never mixed. A proposed deal is the only thing the UI creates from a match.

### Unfinished work
Geography model, retention cohorts, product integration, unit conversion/product catalogue, partner validation workflow.

### Next phase
Phase 5: Fashion Workspace ("Yaad n Abroad": Pain into Art, Jamaican-inspired wear). Prerequisites: founder approval + Neon backup before any deployment is requested. The `fashion` business row is named "Fashion" with a description that says the brand is unconfirmed; updating it to the real brand name is a data change for the founder to approve.

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md (Phase 4 entry first), then /docs/FOUNDER_OS_ARCHITECTURE.md.
Verify first: tests against a throwaway Postgres (expect 303 OK); inspect core/workspace.py, core/founder.py, dashboard/static/js/{buildflow,agriloop}.js, migrations 007-010.
Preview and production share one Neon database and migrate on first request: do not open any preview/production URL until I approve and back up Neon.
Implement only Phase 5: Fashion Workspace (slug 'fashion'): consumer/e-commerce, NOT SaaS metrics. Reuse the workspace pattern. Update /docs/PHASE_HANDOFF.md and stop.
```

---

## Phase 3: BuildFlow Workspace. Completed 2026-10-29

**Overall status: PARTIAL.** Built, tested (291 tests) and exercised in a real browser against a local Postgres 16. Not applied to or verified on production Neon (still awaiting founder approval + backup); no lint/type/build tooling exists.
**Branch:** `ccr-9e3eecee-aucmfd` (stacked on Phase 2, same PR #1). Phase 2 was reviewed first: no defects found in its code (the automated review only flagged pre-existing planning docs, not this work).

### Objective
Priority-1 business workspace: objectives, KPIs, tasks, blockers, experiments, decisions, knowledge/constraints, plus a measurable content workflow and a customer-feedback-to-action workflow, scoped to BuildFlow only.

### Work completed
- Migration `009_workspace_content_feedback.sql`: `content_items` (platform, topic, hook, format, status, posted_at, url, views/likes/comments/shares/signups, all NULL until recorded) and `feedback_items` (source, contact, body, kind, status, `work_task_id`). Business-scoped, so Phases 4-5 can reuse them.
- `core/workspace.py` + `GET /api/founder/workspace/<slug>`: per-business read model (generic for any slug; BuildFlow adds the legacy `leads` pipeline counts). Sections fail independently. Nothing from another business is returned (tested).
- Content workflow: add idea -> update to posted + record metrics. Summary shows posted today / last 7 days / posted-without-metrics and breakdowns by platform, format and topic. Averages use ONLY posts with recorded views and carry a small-sample caveat; no targets are invented.
- Feedback workflow: log feedback -> "Create task" (`POST /api/founder/feedback-items/<id>/to-task`, atomic and idempotent, same business) or triage/dismiss.
- "Import launch plan as tasks": creates work tasks once each from the owner's own `plan.json` (BuildFlow launch plan), honouring ticked items. Only runs when clicked.
- UI `dashboard/static/js/buildflow.js`: page `#buildflow` with Overview / Content / Feedback / Pipeline / Notes tabs. Side-nav entry; on phones reach it from the Founder business card ("Open workspace") to keep the tab bar at 6 items. Form builder from Phase 2 refactored into reusable `Z.formDialog`.

### Files
- Created: `core/workspace.py`, `dashboard/static/js/buildflow.js`, `database/migrations/009_workspace_content_feedback.sql`, `database/rollback/009_workspace_content_feedback_down.sql`, `tests/unit/test_workspace.py`.
- Modified: `core/founder.py` (entities `content_items`, `feedback_items`, `feedback_to_task`, `posted_at` stamping), `dashboard/founder_api.py` (to-task route), `dashboard/app.py` (workspace routes), `dashboard/static/js/founder.js` (reusable form dialog, workspace link), `main.js`, `index.html`, `sw.js`, `tests/unit/test_founder_dashboard.py`, docs.
- Removed: none.

### Tests
| Command | Result | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -t .` (local Postgres 16) | **291 OK** (13 new in `test_workspace.py`: content math, isolation, content flow, feedback-to-task idempotency, plan import, legacy leads, section failure, auth) | PASS |
| Headless Chromium, 5 tabs x phone/tablet/desktop | 0 px overflow, 0 console errors; feedback->task, plan import, add content verified | PASS |
| Production Neon, deployed site, real BuildFlow product, social platform APIs | not exercised | NOT TESTED |

### Acceptance criteria
- Objectives/KPIs/tasks/blockers/experiments/decisions/knowledge views: PASS
- Measurable content workflow: PASS (manual metrics entry; no platform API integration)
- Feedback-to-action workflow: PASS
- Business isolation: PASS (tested)
- Customers/projects/contractor-discovery views: PARTIAL (only the legacy outreach `leads` counts exist; there is no BuildFlow customer/contractor data source, and no integration with the BuildFlow product was verified or built)
- Loading/empty/error states: PARTIAL (per-section error tested via API; browser error path not exercised)
- Mobile/tablet/desktop: PASS
- Tests: PARTIAL (no lint/type/build tools exist)

### Known issues and technical debt
- Content metrics are typed in by hand; nothing is pulled from YouTube/TikTok/Instagram/Facebook. Attribution of signups to a post is the founder's own judgement.
- No edit UI for goals/KPIs/knowledge; no BuildFlow product integration (read-only Firebase/Vercel metrics would be a future, separately verified step).
- Creates are not idempotent server-side (buttons disable while saving).
- `leads` stays a legacy table; the audit's plan to extend it into a prospect pipeline is not done.
- Migrations 007_a, 007, 008, 009 are all unapplied on production Neon. Preview and production share one database and migrate on first request.

### Decisions and assumptions
- Content/feedback tables are generic (business-scoped), BuildFlow-specific only in the UI. Decisions on the workspace show only that business's rows (cross-business ones stay on the Founder dashboard).
- Assumption: manual metrics are acceptable for now; platform APIs need separate verification.

### Unfinished work
Product integration, contractor/customer CRM, edit/delete UI, retirement of legacy agent pages.

### Next phase
Phase 4: Agriloop Workspace. Prerequisites: founder approval + Neon backup before any deployment is requested; confirm Agriloop's real data source (audit says marketplace may be on an in-memory store).

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md (Phase 3 entry first), then /docs/FOUNDER_OS_ARCHITECTURE.md.
Verify first: run the tests against a throwaway Postgres (expect 291 OK); inspect core/workspace.py, core/founder.py, dashboard/static/js/buildflow.js and migrations 007-009.
Preview and production share one Neon database and migrate on first request: do not open any preview/production URL until I approve and back up Neon.
Implement only Phase 4: Agriloop Workspace (slug 'agriloop'), reusing core/workspace.py and the Phase 3 patterns. Update /docs/PHASE_HANDOFF.md and stop.
```

---

## Phase 2: Founder Dashboard. Completed 2026-10-29

**Overall status: PARTIAL.** Built, tested against a local Postgres 16 and in a real browser; not verified on the real Neon database or the deployed site, and no lint/type/build tooling exists in the repo.
**Branch:** `ccr-9e3eecee-aucmfd` (PR #1). Merged here: Phase 0 branch `ccr-b2711e77-m8rmgm` (protocol, audit) and Phase 1 branch `ccr-61f6bbc1-7gtbiy` (data model + CRUD API).

### Objective
One mobile-first founder home across the four businesses: next-action recommendation, ranked tasks, blockers, goals/KPIs, experiments, AI usage, decisions, quick actions.

### Discrepancies found at start of phase (read this)
- My first Phase 2 pass was built on `main`'s base **without** the protocol, Phase 0 audit or Phase 1, because only the default branch was visible. It created its own tables (`ventures`, `founder_tasks`, ...) that collided with Phase 1's. It was rebuilt on Phase 1: its migration and API were deleted, and the dashboard now reads Phase 1 tables.
- **Production database side effect (needs founder awareness).** Preview and production share one Neon `DATABASE_URL` (verified via Vercel env list), and the first API request on any new deployment runs pending migrations. A preview of the first draft therefore applied the draft's `007_founder.sql` to **production Neon** (verified: its `/api/founder/dashboard` returned the seeded four businesses from the real DB; no user data in it). This was done without the approval the protocol requires. It is repaired by `007_a_retire_early_dashboard_schema.sql`, which renames (never drops) those tables to `early_*` before Phase 1's migration runs. Tested on a simulated copy of that state (`EarlyDraftRepairTest`); NOT yet run on Neon.
- Nothing from Phase 1 (007_founder_os_core) or 008 has run on production yet. Any request to a deployment of this branch (preview or production) will apply 007_a, 007_founder_os_core and 008 to the shared Neon DB. Take or verify a Neon backup/branch first; Neon PITR is unverified.

### Work completed
- `core/founder_dashboard.py`: read model + ranking + recommendation + KPI progress/trend. Each section is isolated, so one failing query shows an error card with Retry while the rest renders.
- `GET /api/founder/dashboard` (in `dashboard/app.py`, mounted before Phase 1's router). All writes reuse the Phase 1 API (`/api/founder/businesses/<slug>/<entity>`, `/api/founder/<entity>/<id>`, KPI readings); the dashboard adds no write endpoints.
- `dashboard/static/js/founder.js`: new first nav item "Founder" (default landing page): header + "What should I do next?", recommendation card (with founder override), four business cards, today's priorities (filters), blockers (recorded vs inferred), goals/KPIs, experiments, AI usage, decisions, quick actions.
- `AUTH_DISABLED=1` (local and Vercel preview only; ignored when `VERCEL_ENV=production`) skips login. Set on Vercel for the Preview of branch `ccr-9e3eecee-aucmfd` only. Preview has live PayPal/Gmail env and the shared DB: keep Vercel Deployment Protection on, and remove the variable when finished.

### Files
- Created: `core/founder_dashboard.py`, `dashboard/static/js/founder.js`, `database/migrations/007_a_retire_early_dashboard_schema.sql`, `database/migrations/008_founder_dashboard.sql`, `database/rollback/008_founder_dashboard_down.sql`, `tests/unit/test_founder_dashboard.py`, `tests/fixtures/early_007_founder.sql`, `docs/screenshots/founder-*.png`.
- Modified: `core/founder.py` (new columns on work_tasks/kpis/experiments, new `blockers` entity, `decided_at` and `resolved_at` handling), `dashboard/app.py`, `dashboard/pages/index.html`, `dashboard/static/js/main.js`, `core.js`, `css/app.css`, `sw.js`, `docs/PHASE_HANDOFF.md`, `docs/FOUNDER_OS_ARCHITECTURE.md`.
- Removed: none (the first draft's migration/tests/API never existed on the target base).

### Changes by area
- **Database (008, additive):** `businesses.priority` (backfilled 1-4); `work_tasks.impact, effort_hours, depends_on, expected_outcome, next_step`; `kpis.baseline_value, is_primary, period`; `experiments.baseline_value, target_value, review_date, next_action`; new `blockers` table. Rollback file is manual.
- **API:** one new read route; Phase 1 CRUD extended with the new fields and `blockers` entity (same-business checks apply to `depends_on` and `work_task_id`).
- **UI:** see above. **AI:** none; the recommendation is deterministic. **Integrations:** none new. AI usage reads `llm_usage` (Scout) and `ai_usage` (Phase 1, currently inert).

### Recommendation logic (all constants in `core/founder_dashboard.py`)
Score per open task: business priority `(lowest_rank - rank) * 6`; urgency overdue +30, today +25, <=3 d +20, <=7 d +12, later +4; your task priority 1-5 `(3 - p) * 3` (3 = neutral default); impact `5 * (1..5)`; effort <=1h +6, <=4h +3, >8h -3; doing +8; unblocks others +4 each (cap 12); serves an open goal +3. Tasks marked blocked, waiting on an unfinished task or with an open blocker are shown but never recommended; if all are blocked the oldest recorded blocker is recommended; with no tasks it lists what is missing. Evidence quality (high/medium/low) comes from missing impact/effort/due data. Limitations: heuristic weights, not an optimum; revenue potential and risk of inaction only enter through the impact field; no time-available input; the override ("choose it yourself") is stored per device in browser localStorage.

### Tests
| Command | Result | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -t .` (local Postgres 16, `TEST_DATABASE_URL`) before changes | 236 OK | PASS |
| Same after merging Phase 1 | 252 OK (Phase 1 reported 252) | PASS |
| Same at end | **278 OK** (26 new in `test_founder_dashboard.py`: ranking, KPI math, auth, isolation, validation via API, section failure, AI usage, no-login flag, early-draft repair) | PASS |
| Headless Chromium at 390/820/1366 px, empty and populated data, no-login mode | 0 px overflow, 0 console errors; task created through the form, task marked done | PASS |
| Production Neon, deployed site, Gmail/PayPal, lint/type/build | not run (none exist / not exercised) | NOT TESTED |

### Acceptance criteria
- Reachable in the real app: PASS (local; preview exists but not re-verified after the rebuild)
- Four business cards from stored records and priorities: PASS (priority is `businesses.priority`)
- Data from the supported layer: PASS
- Priorities grounded in tasks with reasons: PASS
- Documented recommendation logic: PASS
- Founder override: PARTIAL (per device only)
- Blockers recorded vs inferred: PASS
- Goals/KPIs incl. bad baselines: PASS
- Experiments/decisions: PASS
- AI usage real or unavailable: PASS (unit-tested; not seen with live data)
- Visible quick actions work: PARTIAL (task form and status in browser; other forms via API tests only)
- Business isolation: PASS for cross-references; single-owner app, no per-business permissions
- Loading/empty/error/partial states: PARTIAL (skeleton, empty, per-section error unit-tested; failed-mutation toast and session expiry not browser-tested)
- Mobile/tablet/desktop: PASS
- Tests/build checks: PARTIAL (tests yes; lint/type/build do not exist)
- Regressions addressed: PASS (all prior tests green)
- Docs/handoff: PASS

### Known issues and technical debt
- Default landing page is now Founder. Mobile tab bar has 6 tabs.
- Creates are not idempotent server-side (buttons disable while saving); business priority has no UI (UPDATE `businesses.priority`).
- Tasks, goals, KPIs, experiments, decisions cannot be edited or deleted from the UI (the Phase 1 API can update them); no business detail pages; AI usage cannot be split per business for Scout's ledger.
- `early_*` tables on production (from the repair) can be dropped by the founder once confirmed empty.
- Phase 1 limits still apply (seed timestamps fixed, legacy agents/pages remain, Fashion brand unconfirmed).

### Decisions and assumptions
- Reuse Phase 1 tables; add only what the dashboard needs (008). Task `priority` default 3 is treated as neutral. Cross-business decisions (`business_id` NULL) are shown as "All businesses".
- Assumption: preview shares production Neon (verified from env list, not by querying the DB directly).

### Unfinished work
Edit/close UI, business workspaces (Phase 3+), per-business AI cost, lint/build pipeline, owner-approved application of 007/008 on Neon.

### Next phase
Phase 3: BuildFlow Workspace. Prerequisites: founder approves and backs up before migrations 007_a/007/008 reach Neon; enter real BuildFlow tasks/KPIs; PR #1 reviewed/merged; confirm the Fashion brand if relevant.

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md (Phase 2 entry first), then /docs/FOUNDER_OS_ARCHITECTURE.md and /docs/PHASE_0_AUDIT.md.
Verify the repo before changing anything: run the test suite against a throwaway Postgres (expect 278 OK) and inspect core/founder.py, core/founder_dashboard.py, dashboard/founder_api.py, dashboard/static/js/founder.js, database/migrations/007*, 008.
NOTE: preview and production share one Neon database and migrations run on the first request of any deployment. Do not open or request a preview/production URL of this branch until I have approved and backed up Neon.
Implement only Phase 3: BuildFlow Workspace (businesses.slug = 'buildflow'), reusing the Phase 1 entities and the Phase 2 dashboard patterns. Update /docs/PHASE_HANDOFF.md at the end and stop. Do not start Phase 4.
```

---

## Phase 1: Foundation and Architecture. Completed 2026-10-29 (original entry, preserved verbatim from branch `ccr-61f6bbc1-7gtbiy`)

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

---

## Phase 0: Audit and Reset. Completed 2026-10-29

**PHASE 0 COMPLETE**
**Overall status:** PASS (read-only audit; baseline tests green)
**Branch / last commit:** `ccr-b2711e77-m8rmgm`, based on `1b1c990`, merged with protocol commit `dda7d41`

### Objective
Establish the verified truth about the repo and decide what to keep, adapt or retire. No application code, schema, config or infrastructure changes.

### Work completed
- Inspected the whole repo: architecture, DB, APIs, auth, AI, agents, prompts, UI, integrations, scheduler, tests, config, docs (PASS)
- Located every piece of three-agent logic (audit section 2) (PASS)
- Ran the full test suite against a throwaway local Postgres (PASS, below)
- Checked protocol Section 0 claim by claim (audit section 0) (PASS)
- Merged the protocol file from `origin/ccr-cf790779-6k71zs`; it was absent from this branch at first (PASS)

### Files
- Created: `docs/PHASE_0_AUDIT.md`
- Modified: `docs/PHASE_HANDOFF.md` (this entry added on top; the Protocol Setup entry is kept below)
- Added via merge: `docs/FOUNDER_OS_BUILD_PROTOCOL.md`
- Removed: none

### Changes by area
- Database / API / UI / AI / Integrations: none (audit only)

### Tests
| Command | Result | Status |
|---|---|---|
| `TEST_DATABASE_URL=postgresql://postgres@/t0?host=/var/tmp&port=5433 python3 -m unittest discover -s tests -t .` (throwaway Postgres 16, deleted after) | Ran 236 tests in 46.0s, OK | PASS |
| Live site, real Neon DB, Gmail, PayPal, RPC, Anthropic | not exercised | NOT TESTED |

### Discrepancies found at start of phase
- Protocol file was not on this branch (it exists on another branch); now merged.
- Older audit says status mode is hard-coded "MOCK"; code now returns `LIVE`/`LOCAL` (only a default chip label and a docstring still say MOCK).
- Docs (`README`, `MASTER_SYSTEM`, `docs/architecture/*`) describe the old crypto/SQLite product, not the code.
- `dashboard/static/app.js` is unreferenced dead code.

### Known issues and technical debt
See audit section 8. Main ones: three-agent names hard-coded in policy enum, `agents` CHECK constraint, scheduler, queue/budget/events columns, routes, UI and tests; bounty-centric data model; no migration runner or rollback; no CI; no AI running; payments anchored to opportunities; `ResourceWarning` noise in tests.

### Decisions and assumptions
- Decision: keep Python + Neon + Vercel and the `core/` layer; retire the three-agent shape in stages (audit section 9).
- Decision: remaining founder questions (fashion repo, EVM code, API key, CI, sibling repos, credential rotation) are **non-blocking**. Phase 1 uses the defaults in audit section 12 and does not re-ask them.
- Assumption (unverified): Neon prod has the same migration state as 001-006 and has backups.

### Unfinished work
Nothing inside Phase 0. Not verified: Neon backups, prod env vars, sibling repos.

### Next phase
- Phase 1: Foundation and Architecture
- Prerequisites: protocol merged (done); baseline tests green (done, 236/236); a local throwaway Postgres to run tests (recipe: `initdb` in `/var/tmp`, start on port 5433 as the `postgres` user, set `TEST_DATABASE_URL`).

### Risks and recommended next actions
- Run the tests before and after every Phase 1 step; keep the 236 green.
- Take/verify a Neon backup before anyone applies migration 007 to production. Applying it is a production change needing founder approval in that chat.
- Gmail OAuth token lapses around 2 Nov and leaked credentials still need rotation (owner actions, outside Phase 1).
- Phase 1 scope per protocol: business-context model (`buildflow`, `agriloop`, `fashion`, `trading`), additive reversible migrations (businesses, tasks, decisions, metrics, experiments, knowledge placeholders), module boundaries, model-routing config and usage logging, app shell and navigation, reuse of auth/audit/kill switch/policy, retire or wrap the three-agent structure. Out of scope: workspaces, dashboard content, command center, automations.

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md, then /docs/PHASE_0_AUDIT.md.
Begin Phase 1: Foundation and Architecture.
Prerequisites to verify first: protocol present (PASS); 236 baseline tests green against a throwaway Postgres (PASS in Phase 0, re-run to confirm).
Known issues carried forward: three-agent coupling (audit section 2), no migration runner, no CI, AI disabled, bounty-centric data model.
Open founder questions are non-blocking; use the defaults in audit section 12 and do not re-ask them.
Then follow the protocol's start-of-phase checklist, complete only Phase 1, update /docs/PHASE_HANDOFF.md, report verified results, and stop.
Do not apply migrations to production or change infrastructure without my approval in that chat.
```

---

## Protocol Setup. Completed 2026-10-28
**Overall status:** PASS (documentation only)

- `docs/FOUNDER_OS_BUILD_PROTOCOL.md` created. `docs/PHASE_HANDOFF.md` created.
- No phase was completed by that task; no application code was audited, run, tested or modified.
- Section 0 of the protocol was an unverified snapshot; Phase 0 has now checked it (see the Phase 0 entry above and audit section 0).
- Legacy planning note `docs/master/HANDOFF.md` was treated as unverified input to Phase 0.
