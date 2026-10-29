# Founder OS — Phase 0 Audit

Audited 28-29 Oct 2026, branch `ccr-b2711e77-m8rmgm`, HEAD `1b1c990`. No application code was modified.

**Evidence labels.** VERIFIED = read in this repo this session. REPORTED = taken from existing docs
(`IMPLEMENTATION_AUDIT.md`, `docs/master/HANDOFF.md`), not re-checked. NOT RUN = could not be executed here.

## 0. Protocol and test baseline

**Protocol.** `docs/FOUNDER_OS_BUILD_PROTOCOL.md` was not on this branch when the audit was first written. It lives on
`origin/ccr-cf790779-6k71zs` (commit `dda7d41`) and is now merged into this branch. Its rules (one OS, not four agents;
business-context isolation; reuse before rewrite; additive reversible migrations; no destructive DB or production changes without approval) are
consistent with every recommendation below.

**Test baseline (VERIFIED, run this session).**
Command: `TEST_DATABASE_URL=postgresql://postgres@/t0?host=/var/tmp&port=5433 python3 -m unittest discover -s tests -t .`
against a throwaway local Postgres 16 (deleted afterwards, nothing touched Neon).
Result: **Ran 236 tests in 46.0s, OK.** Only noise is `ResourceWarning: Connection ... deleted while still open` from unclosed psycopg connections in tests (cosmetic debt).
Not covered by this run: live Gmail/PayPal/RPC/Anthropic calls, the deployed Vercel site, the real Neon DB.

**Corrections to protocol Section 0 (its claims, checked).**
| Protocol claim | Verdict |
|---|---|
| Python 3.13, stdlib handler, no framework | VERIFIED |
| Vercel rewrite to `/api/index`, one daily cron `/api/cron` | VERIFIED (`vercel.json`) |
| Postgres via `core/db.py`, migrations 001-006 | VERIFIED |
| Vanilla JS, strict CSP, PWA | VERIFIED |
| Three agents in `agents/` | VERIFIED; inventory in section 2 |
| No AI running (`SCOUT_CLIENT = None`) | VERIFIED in code (`dashboard/app.py:44`). Whether prod has an API key set is NOT VERIFIED |
| 236 tests | VERIFIED, all pass |
| Sibling repos (BuildFlow, Agriloop, mq5, Kadeform, NF-Fragrance) | NOT VERIFIED; out of scope for this repo |
| `status.mode` hard-coded "MOCK" (older audit) | OUTDATED: now `LIVE`/`LOCAL`; only the sidebar default text and a docstring say MOCK |

## 1. CURRENT ARCHITECTURE

- Python 3.13, stdlib `http.server`; one `handle()` in `dashboard/app.py` serves both the local runner
  (`scripts/run_local.py`) and Vercel (`api/index.py`, all paths rewritten via `vercel.json`).
- Postgres (Neon) through a thin wrapper `core/db.py` (`?` → `%s`). Deps: `psycopg[binary]`, `anthropic`. No framework, no ORM, no build step.
- ~8.5k lines of Python/JS/SQL (≈3.7k app code, ≈3.3k tests, rest frontend).
- Hosting: Vercel (function `maxDuration` 60 s) + one daily Vercel Cron (`0 7 * * *` → `/api/cron` → `core/scheduler.tick`).
- Single owner. One `handle()` of ~40 routes, no router abstraction, 4096-byte JSON body cap (CSV import is the exception).
- Frontend: vanilla JS, one file per page (overview, scout, operator, treasury, plan), strict CSP, PWA + service worker.
- Docs describe a different product (crypto "zero-to-revenue", SQLite, FastAPI "TBD") than the code (Postgres, Vercel, leads/PayPal/Gmail).
- Repo has no CI (`.github/` absent), no lint/format config, no `pyproject`.

## 2. OLD AGENT ARCHITECTURE (three-agent logic — full inventory)

Three agents share one queue, one policy gate, one audit log, one kill switch.

| Agent | Code | What it does |
|---|---|---|
| Scout | `agents/scout/*` (11 files) | Pulls public bounty/freelance feeds (Superteam, GitHub bounties, Freelancer.com, Remotive, Himalayas), sanitizes, scam-flags, scores 0–100 with spec weights, optional Claude enrichment (disabled), writes `opportunities`, enqueues Operator tasks |
| Operator | `agents/operator/*` (3 files) | Template drafts for proposals/outreach, approval-gated Gmail send, email job-application submit |
| Treasury | `agents/treasury/*` (2 files) | Read-only EVM balance/payment verification on 7 chains, PayPal order verification, ledger |

Every place the three-agent shape is hard-coded (these are the removal/refactor targets):

1. `core/policy/policy.py:12-16` `Agent` enum (scout/operator/treasury); `AGENT_PERMISSIONS` (l.106-124) keyed by it; `authorize()` indexes it.
2. `database/migrations/001_init.sql`: `agents.name CHECK IN ('scout','operator','treasury')`, seed `INSERT INTO agents`, `agent_runs.agent → agents`, `tasks.owner_agent → agents`.
3. `core/scheduler.py`: `tick()` calls Scout (gated 6 h), Operator, Treasury in fixed order; `_scout_due` queries `agent_runs WHERE agent='scout'`.
4. `core/queue/queue.py`: tasks claimed by `owner_agent`; `core/events/events.py` uses `source_agent`.
5. `core/budget.py` and `llm_usage.agent`: spend tracked per agent name.
6. `dashboard/app.py` routes `/api/scout/*`, `/api/operator/*`, `/api/treasury/*`; `dashboard/api_data.py` read models; `dashboard/mcp.py` tools.
7. UI: `dashboard/static/js/{scout,operator,treasury}.js`, nav built in `main.js`, `index.html` script tags.
8. `agents/scout/autodraft.py` hands Scout output to Operator by event/task (cross-agent coupling).
9. Docs: `MASTER_SYSTEM.md` §4-18, `README.md`, `docs/architecture/*`, `IMPLEMENTATION_AUDIT.md`.
10. Tests: `test_phases_3_6.py` (499 l.), `test_scout*.py` (~830 l.), `test_outreach.py`, `test_rates_cleanup.py`, `test_policy.py` all assert the old agents.

The domain model underneath is also old: `opportunities` (bounties with payment_asset, deadline, required_capital) is the
central object; `leads` (migration 006) is a 5-column side table.

## 3. DATABASE

VERIFIED from `database/migrations/001–006`, Postgres, ids and timestamps are `TEXT`.

- Auth: `users`, `owner_credentials` (single row), `sessions` (hashed tokens), `auth_attempts`.
- Control: `settings` (holds kill switch `paused`), `audit_events` (append-only, enforced by triggers, incl. TRUNCATE), `notifications`, `events`.
- Agent infra: `agents`, `agent_runs`, `tasks`, `task_events`, `user_actions`, `deliverables`, `submissions`, `llm_usage`.
- Old business: `opportunities`, `payments`, `wallets`, `transactions`, `ledger_entries`, `wallet_balances`, `leads`.
- No ventures/tenant concept, no customers, no metrics, experiments or decisions tables; `payments` anchors to `opportunity_id`.
- Migrations are plain numbered SQL, no runner/version table found, no down-migrations. How they are applied in prod is NOT VERIFIED.
- Neon backup/PITR settings: NOT VERIFIED (REPORTED unknown).

## 4. AI SYSTEM

- **No AI is running.** `SCOUT_CLIENT = None` (`dashboard/app.py:44`); `ANTHROPIC_API_KEY` has never been set (REPORTED); `LLM_PRICE_*` empty in `.env.example` keeps Claude disabled.
- Only AI code: `ClaudeClient` in `agents/scout/enrich.py` (text only, 3 numeric ratings + ≤3 flags, output validated, discarded otherwise) and one prompt, `prompts/scout/scout-enrich-v1.md` (1 line). `prompts/operator/` and `prompts/treasury/` are empty.
- Good pattern to keep: `core/budget.py` reserves worst-case cost under a lock before each call, so concurrent calls can't pass `LLM_MONTHLY_BUDGET_USD` (default 80).
- Missing: vision, tool use, retrieval/memory, prompt versioning/registry, eval harness, any agent-loop or planner. Everything "smart" today is regex and templates.
- `CLAUDE_MODEL` default in `.env.example` is `claude-sonnet-5-5`.

## 5. UI

- Pages: Overview (run agents, decisions, payments), Scout list (select/remove/send-to-Operator/sort), Operator board, Treasury (+PayPal controls), Game plan (BuildFlow launch checklist, persisted).
- PWA with service worker, light/dark theme, football-themed branding ("Matchday control room", "Z2R" crest) that will not fit Founder OS.
- `dashboard/static/app.js` (212 lines) is dead code: not referenced by `index.html`, `app.py` or `sw.js` (VERIFIED).
- No per-business views; navigation is per agent, not per business.
- `/api/status` now reports `LIVE`/`LOCAL` (`app.py:96`); the sidebar chip default text in `index.html` is still `MOCK`, and `app.py` docstring still says "Mode: MOCK".

## 6. INTEGRATIONS

| Integration | Code | State |
|---|---|---|
| Gmail send | `integrations/gmail.py` | Live (REPORTED, real send verified). Refresh token expires ~7 days (OAuth app in Testing), around 2 Nov 2026 |
| PayPal | `integrations/paypal.py` | Sandbox verified; live creds checked against token endpoint only, no real-money order |
| EVM RPC | `agents/treasury/rpc.py`, `core/policy/chains.py` | Read-only, 7 chains |
| Twilio/WhatsApp | `integrations/notifications/*` | `RecordOnly`; nothing is delivered |
| Public job feeds | `agents/scout/sources.py`, `integrations/web/fetch.py` | Live, https-only host allowlist, no redirects, 1 MB cap |
| MCP connector | `dashboard/mcp.py` | Read-only status/opportunities/payments, token-in-URL auth |
| Anthropic | `agents/scout/enrich.py` | Wired but off |
| Vercel Cron | `vercel.json` | Daily only |
| Neon | `core/db.py` | Live |

Not integrated anywhere: BuildFlow, Agriloop, fashion brand, trading bot (all separate repos or absent; see §10).

## 7. REUSABLE COMPONENTS

Keep these almost as-is: `core/auth/owner_login.py` (scrypt + TOTP + recovery + hashed sessions + lockout), `core/audit.py` + the append-only triggers, `core/orchestrator/killswitch.py`, `core/budget.py`,
`core/db.py`, `core/envfile.py`, `core/rates.py`, `core/queue/queue.py` (leases, `SKIP LOCKED`, idempotency keys), `core/notifications/*`, `core/events/events.py`,
`core/policy` (approval-gate and forbidden-action design), `agents/scout/sanitize.py` (untrusted-text handling), `integrations/gmail.py`, `integrations/paypal.py`, `integrations/web/fetch.py`, `dashboard/mcp.py` pattern, PWA shell and `core.js` helpers, `tests/dbutil.py` / `tests/authutil.py`, `tests/security/test_no_secrets.py`.

## 8. TECHNICAL DEBT

1. Domain model is bounty-centric; nothing models a business, KPI, task, decision, or experiment.
2. Agent names are hard-coded into a CHECK constraint, an enum, the scheduler, routes and UI. Adding a module means editing five layers.
3. `dashboard/app.py::handle()` is one growing if-chain; no routing, no input schema validation layer.
4. TEXT timestamps/ids everywhere; no foreign keys on several flows; `payments` ties to opportunities.
5. Migrations have no runner, version table or rollback.
6. Stale/contradictory docs (§1); dead `app.js`; football theming; README says SQLite and "Phase 1".
7. Cron is daily only; Scout's 6-hour gate can't fire more often than the cron; no unattended finer loop exists.
8. Tests pass (236/236, VERIFIED) but only against a Postgres the developer supplies via `TEST_DATABASE_URL`; there is no CI, so nothing runs them automatically.
9. Operator drafts are static templates with `[OWNER TO FILL]` holes.
10. 4 KB body cap blocks uploads/long payloads; Vercel body ceiling ≈4.5 MB.
11. Secrets were pasted into chat in earlier sessions (REPORTED): PayPal live secret, Gmail client secret + refresh token, sandbox keys. Rotation outstanding.
12. `tests/security/test_no_secrets.py` passes only by pattern; a grep for `sk-ant|AKIA|BEGIN PRIVATE` found nothing in the working tree (VERIFIED).

## 9. WHAT TO KEEP / REFACTOR / REMOVE / BUILD

### KEEP
Auth, audit log, kill switch, budget cap, queue, notifications, events, policy *design*, sanitize/untrusted-data discipline, Gmail + PayPal clients, MCP connector, PWA shell, Postgres/Vercel/Neon stack, test helpers and security test.

### REFACTOR
- `core/policy`: replace the `Agent` enum with **Business Module** identity (`buildflow`, `agriloop`, `fashion`, `trading`) + `os` as the control actor; keep forbidden/approval sets.
- `agents`/`agent_runs`/`tasks.owner_agent`/`llm_usage.agent`/`events.source_agent` → keyed by module, via an additive migration (drop the CHECK, add `module` columns, backfill from old names).
- `core/scheduler.tick` → iterate registered modules instead of three hard-coded calls.
- `payments` → anchor to a customer/venture, not a synthetic opportunity (the `opp_manual_*` workaround).
- `leads` → grow into BuildFlow's prospect pipeline (stage, fit, channel, touches); don't create a competing table.
- `dashboard/app.py` → small route table; per-module route prefixes.
- Docs: rewrite README/MASTER_SYSTEM for Founder OS; archive the old spec.

### REMOVE (after Phase 1 replacements exist and are tested; nothing removed in Phase 0)
- `dashboard/static/app.js` (dead).
- Crypto/bounty Scout sources as a primary feed (demote or delete; owner decides), Treasury EVM wallet code **unless** needed for the trading module (decision D3).
- Football/"matchday" branding, "Z2R" crest, `MOCK` chip default.
- `agents/scout/autodraft.py` cross-agent hand-off, the three agent pages and their tests.
- `firebase_uid` remnants already dropped (003); stale Firebase references in docs.

### BUILD
1. Module registry + Founder OS control layer (modules, status, enable/disable, per-module kill switch inside the global one).
2. Core tables: `ventures`/`modules`, `projects`, `tasks` (human + AI), `decisions`, `metrics`, `experiments`, `customers`; migration runner with version table.
3. BuildFlow module (primary): prospect pipeline, touches, fit scoring, outreach drafts, customers, revenue anchoring, weekly learning report.
4. AI layer: Anthropic client with vision, versioned prompt registry, cost cap, output-schema validation, eval fixtures.
5. Agriloop, then Fashion, then Trading modules: each as a thin module behind the same interface.
6. Founder dashboard: one page per module + a cross-business "what needs me today".
7. CI (GitHub Actions) running the Postgres-backed test suite.

## 10. RISKS

| # | Risk | Severity |
|---|---|---|
| 1 | (resolved) Protocol file found and merged | - |
| 2 | Refactoring `agents` CHECK / FKs on a live Neon DB with no migration runner, no rollback, backups unverified | High |
| 3 | No CI: the green baseline only holds while someone runs it by hand with a local Postgres | Medium |
| 4 | Gmail refresh token lapses ~2 Nov → outreach silently stops | High, near-term |
| 5 | Leaked secrets from earlier chats still valid | High |
| 6 | Spend: AI enabled with a single global cap; no per-module budget | Medium |
| 7 | Trading module: policy hard-disables trading (`TRADING_ENABLED=False`, `Action.TRADE` forbidden). Building a bot means a deliberate security-policy change; the `mq5` repo has no evidence of an edge | High |
| 8 | Sibling repos not in scope: BuildFlow (REPORTED "NOT READY": storage, legal pages, no billing), Agriloop (REPORTED in-memory data source, no tests), "fashion brand" repo unidentified (Kadeform, NF-Fragrance, neither is fashion) | High |
| 9 | PII/outbound email: Gmail personal account sending cold outreach without suppression list | Medium |
| 10 | Prompt injection through screenshots/pasted text once vision is added | Medium |
| 11 | Single-owner, single-region, daily cron: no resilience, 60 s function limit for long AI jobs | Medium |
| 12 | Deleting old agents loses working approval-gated send paths if done before replacement | Medium |

## 11. RECOMMENDED ARCHITECTURE

**Founder OS = control layer; business modules plug in.** Keep Python + Neon + Vercel (no stack change in Phase 1).

```
Founder OS (control layer)
├─ core/        auth · audit · killswitch · policy · budget · queue · events · notifications · scheduler  (existing, kept)
├─ os/          module registry · projects · tasks · decisions · metrics · experiments · attention inbox   (new)
├─ ai/          client · vision · prompt registry · budget · schema validators · evals                    (new, extracted from enrich.py)
├─ integrations/ gmail · paypal · (twilio) · (broker/exchange later)                                       (existing)
└─ modules/     buildflow (1) · agriloop (2) · fashion (3) · trading (4)
                each: manifest, tables prefixed by module, jobs, routes under /api/<module>/, UI page, tests
```

Principles:
- Modules do not call each other; they talk through the OS (events, tasks, metrics).
- One policy gate; modules declare their allowed actions; approval-gated external writes stay.
- Additive migrations only, versioned and with down-scripts; no destructive change until replacements pass tests.
- Every module reports the same metrics contract (revenue, pipeline, next actions) so the OS dashboard is generic.
- Trading is last and stays read-only/paper unless the owner explicitly changes the policy.

Suggested module order: BuildFlow, Agriloop, Fashion, Trading. This matches the brief.

## 12. OPEN FOUNDER DECISIONS (none block Phase 1)

Phase 1 can proceed on safe defaults; each default is listed so no one has to re-answer.

| # | Question | Default Phase 1 will use |
|---|---|---|
| D2 | Which repo is the fashion brand? | Create the `fashion` business context empty; build nothing against a repo until confirmed (protocol Phase 5) |
| D3 | Keep EVM Treasury code? | Keep it untouched and dormant; revisit in Phase 6/11 |
| D4 | `ANTHROPIC_API_KEY`, pricing vars, $80 cap | Build routing/usage logging with AI disabled; the existing budget guard stays |
| D5 | CI / test database | Use a local throwaway Postgres as done here |
| D6 | Integrate sibling product repos by API or merge? | Treat them as external; Phase 3/4 decide |
| D7 | Rotate leaked credentials; Gmail 7-day token (~2 Nov) | Out of scope for Phase 1; flagged as owner action, not touched |
