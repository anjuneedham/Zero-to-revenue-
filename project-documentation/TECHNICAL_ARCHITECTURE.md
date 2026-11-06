# Technical Architecture

## Stack (unchanged)
Python 3.13, stdlib `http.server` handler shared by the local runner (`scripts/run_local.py`) and Vercel (`api/index.py`). Postgres
(Neon in production) through `psycopg`; forward-only SQL migrations applied under an advisory lock. Vanilla-JS PWA, no build step,
strict CSP (`script-src 'self'`), all DOM built with `createElement`/`textContent`. Owner-only auth: scrypt + TOTP + hashed bearer sessions.

## What was added (this work)

```
database/migrations/007_sales_os.sql      additive: leads columns, activity_events, sales_tasks, playbooks, playbook_runs
core/sales/events.py                      constants, validation, append-only log(), timezone-aware today()
core/sales/pipeline.py                    prospects, stages, outreach/response/meeting/proposal/close, follow-ups, tasks, reads
core/sales/playbooks.py                   editable playbooks + runs (snapshot steps, one live task per run)
core/sales/seed.py                        12 built-in playbooks as plain data (inserted once by slug, never overwritten)
core/sales/insights.py                    Today view, targets, performance, learning
dashboard/sales_api.py                    /api/sales/* dispatcher (auth is done by dashboard.app before it is reached)
dashboard/static/js/{sales,playbooks,insights}.js   pages: Today, Pipeline, Prospect, Playbooks, Playbook, Insights
tests/unit/test_sales.py                  24 tests, real Postgres, through the real HTTP handler + auth
tests/e2e/journey.js                      Playwright journey against a local server
```

## Data model
- **leads** (existing table, extended): `stage`, `qualification`, `outcome`, `deal_value`, `revenue_won` (owner-recorded), `currency`, `industry`,
  `location`, `website`, `contact_other`, `source_channel`, `offer`, `research_notes`, `last_contact_at`, `next_followup_at` (derived from open
  follow-up tasks), `playbook_run_id`. Legacy `status` is untouched and still drives the older CSV/Gmail flow.
- **activity_events** (append-only; BEFORE UPDATE/DELETE/TRUNCATE triggers raise). `at` = recorded time, `occurred_at` = when it happened.
  `lead_id` has no foreign key, so history survives deleting a prospect. `detail` is JSON including `stage_after` for playback.
  Personal data (email, phone, contact name) is never copied into `detail`; edits to those fields log `{"changed": true}`.
- **sales_tasks**: priority 1-3, due date, kind, status (open/done/skipped), optional lead/playbook/run/step, outcome.
- **playbooks**: all fields as plain text or JSON lists; `steps` = ordered `[{id,title,instruction}]`; `version` increments on every save.
- **playbook_runs**: copies `steps` at start and keeps `progress` per step. Editing a playbook never alters a past run.

## Pipeline semantics
Active stages (ordered): identified, researched, qualified, outreach_prepared, contacted, follow_up, responded, conversation, meeting_booked,
proposal, negotiation. Closed: won, lost, not_interested, not_qualified, no_response, unreachable. Parked: future_opportunity, follow_up_later.
Recording work moves a prospect **forward only** (logging earlier work never moves it back; a closed prospect is not silently reopened).
`move_stage` is the explicit manual override (either direction) and the only way to reopen. Closing skips the prospect's open tasks and abandons
its live playbook run, and each of those is visible in history.

## API (all require the owner bearer token; 401 otherwise)
`GET  /api/sales/{meta,today,targets,prospects,prospects/{id},tasks,activity,activity/before/{id},playbooks,playbooks/{id},playbooks/{id}/runs,runs,runs/{id},insights/performance,insights/learning}`
`POST /api/sales/{prospects, prospects/{id}/{update|research|qualify|stage|prepare|outreach|response|followup|meeting|proposal|close|note|playbook|delete}, tasks, tasks/{id}/{complete|skip}, targets, review, playbooks, playbooks/{id}/{update|duplicate|archive|unarchive|start}, runs/{id}/{step|abandon}}`
Validation errors return 400 with a plain message; unknown ids 404; anything unexpected becomes the app's generic 503 (never driver text).
Body limit: 64 KB for `/api/sales/*`. Every other route keeps its 4 KB limit (the socket read cap was raised to the largest per-route limit; this also
fixes the existing 200 KB CSV import route, which was being truncated at 4 KB).

## Decisions and trade-offs
- **Extend `leads`, do not add a parallel table** (as the 26 Oct audit recommended): the existing CSV import and approval-gated Gmail send keep working.
- **Reports computed in Python from events**, not SQL over JSON: clearer and testable, fine for one user (capped at 20,000 events read).
- **No AI.** No model key exists. Every suggestion is a labelled rule; hypotheses need at least 5 prospects per approach; percentages need n >= 30.
- **Nothing sends.** The platform records what the owner did. Sending stays on the existing approval-gated path.
- **Revenue honesty.** `revenue_won` is owner-recorded and labelled as not verified; Treasury remains the only source of verified revenue.
- **Timezone.** "Today" uses a configurable IANA timezone (setting `sales_timezone`, else `SALES_TIMEZONE`, else UTC). It defaults to UTC because the
  owner's timezone is not recorded anywhere in the repos; set it on the Today page.

## Known limits
Single user, single tenant. Sales pages are not yet in the MCP connector. No import for outreach done elsewhere (a CSV back-fill route would be the next step).
Reminders are in-app only (no email/WhatsApp push). Offline use shows the shell only (existing service-worker behaviour).
