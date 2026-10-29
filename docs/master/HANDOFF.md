# Handoff for the Zero to Hero OS master-plan chat (28 Oct 2026)

Start a NEW chat with: "Read docs/master/HANDOFF.md in anjuneedham/Zero-to-revenue- and continue." Nothing else needed.

## Token rules for every chat (policy, not optional)
- One task per chat; new chat when a task is done. Never reuse a chat across days.
- Read files with offsets/limits or `jq`/`grep`; never dump whole files or API results into the chat.
- Write findings to files, then refer to the file. Do not paste repo contents back in prose.
- No sub-agents, no repeated deploys, no re-reading what this file already states.
- Docs first, code second; one phase per chat; run tests once at the end of a phase.
- Weekly plan: Mon BuildFlow, Tue Agriloop, Wed trading, Thu e-commerce, Fri BuildFlow growth, Sat Agriloop growth, Sun OS review. Each day's chat touches ONLY that venture's folder.

## Evidence gathered (verified 28 Oct, commands run this session)
**Repos reachable** (35 on the account; relevant ones cloned shallow under /home/user and /home/user/anjuneedham):
- Zero to Hero OS = `Zero-to-revenue-` (Python, Neon Postgres, Vercel, live 200 at zero-to-revenue-neon.vercel.app). 284 tests (own suite). See IMPLEMENTATION_AUDIT.md.
- BuildFlow = `buildflow` (Next.js 16, Firebase project build-6fa95, live 200 at buildflow-app-beta.vercel.app, Capacitor Android shell). Its own report (25 Oct): verdict NOT READY. Blockers: Firebase Storage not provisioned (uploads fail), legal pages placeholder, never run on real Firebase prod project, no billing (Stripe-ready seam only, manual mode), no push/email notifications. 32 unit + rules + e2e + QA suites exist; I did NOT re-run them.
- Agriloop = `agriloopmain` (private; same commit 03eba34 as public `farm-market-place`; `agriloop` is the older 204-file predecessor). Next.js 16, Supabase Auth + RLS migrations, Capacitor Android, live 200 at agriloopmain.vercel.app (/market 200). Repo docs say marketplace data uses an IN-MEMORY data source (`AGRILOOP_DATA_SOURCE=memory`, "NOT production-safe"); Prisma adapter is "largest remaining item, blocker for real production traffic". No automated tests (only Android boilerplate). UNVERIFIED: what the live Vercel env sets for the data source (I was about to check via Vercel MCP `filter_project_envs` without decrypt when the chat was interrupted).
- Trading = `mq5` (MQL5 "Synthetic Edge EA" for Deriv synthetic indices; 20 files, last commit 26 Sep). Has an in-MT5 unit-test script. NO backtest results, paper-trading journal or statistics in the repo, so there is no evidence of an edge. Cannot run MT5 in this sandbox.
- E-commerce: two real storefronts, neither is fashion: `Kadeform-` (Shopify/Dawn theme, single hero product FlexBack Pro lumbar support, 446 files) and `NF-Fragrance-` (static Netlify site, five colognes, 24 files). No fashion repo found (checked Tonysperformance = mechanic site, Convoy-supply = cab storage, Theo-s- = empty). `Echo-Ai` is private and not accessible. Founder must confirm which is "the brand".

## Known gaps in the OS vs the brief (from IMPLEMENTATION_AUDIT.md)
Single-tenant, opportunity/lead-centric model; no projects, tasks (beyond agent queue), decisions, experiments, metrics, or per-venture workspaces. Exists: owner auth (scrypt+TOTP), append-only audit log, approval gates, kill switch. UNVERIFIED: Neon backup/PITR settings. Claude usage cannot be read or enforced by the app; the allocation can only be a plan plus self-reported usage.

## Next steps (one chat each)
1. docs/master/CURRENT_STATE_AUDIT.md + MASTER_PLAN.md (use the evidence above, do not re-gather).
2. docs/master/ventures/{BUILDFLOW,AGRILOOP,TRADING,ECOMMERCE}.md with: report, audit, risks, MVP scope, roadmap, growth plan, metrics, acceptance criteria.
3. Phase 1 build: `ventures`, `tasks`, `decisions`, `experiments`, `metrics` tables (reversible migration 007), venture-scoped views, weekly-allocation page. Keep Python/Neon/Vercel stack.
4. Then the BuildFlow sidekick work from the earlier brief (needs ANTHROPIC_API_KEY).
Open decisions: which e-commerce repo is the brand; Gmail token expires ~2 Nov; Agriloop live data source.

## Phase 10 status (29 Oct, closed out)
Built earlier: migration 007 (prospect pipeline on `leads`, `lead_touches`, `deals`), `core/challenge.py`, `agents/operator/pitches.py`, `/api/challenge/*`, Challenge page (default), send->touch logging, opt-out enforcement, daily report challenge line, removed dead `static/app.js` and the hardcoded MOCK label. Operating guide: docs/runbooks/CHALLENGE.md.

## FINISH_PROMPT outcome (29 Oct, second chat)
| Step | Result |
|---|---|
| 1 Deploy | Production deployment of `3084b9e` live (the earlier ones were previews). Server answers 401 (not 503) on `/api/challenge`, so the DB connected and migrations ran on cold start. NOT verified from the sandbox: the config payload and the logged-in page (no owner credentials there). Do that smoke yourself once. |
| 2 PayPal | Deal card has **Copy PayPal message**: `POST /api/challenge/paypal-message` creates the order on first tap, reuses it after, returns a ready message with the link. AgriLoop deals ask for confirmation first. Live $1 order NOT run: owner said PayPal already works. |
| 3 Gmail | Skipped on the owner's instruction. Token still expires ~2 Nov; email send will fail until re-issued (OAuth app is in Testing). |
| 4 Screenshots | `core/ingest.py`, `POST /api/challenge/ingest`, "From screenshot / paste" drawer. Pasted text works now without AI (emails, phones, @handles). Screenshots need `ANTHROPIC_API_KEY` + `LLM_MONTHLY_BUDGET_USD` + `LLM_PRICE_IN_PER_MTOK` + `LLM_PRICE_OUT_PER_MTOK`; without them the API says so. Nothing stored, nothing created or sent until the owner presses Add lead. Live vision call is UNTESTED (fake client only). Also fixed: handlers truncated bodies at 4 KB, so CSV imports over 4 KB failed; per-route limits in `dashboard.app.BODY_LIMITS`. |
| 5 Weekly report | `core/weekly.py`, `GET /api/challenge/weekly`, Challenge card, Sunday scheduler tick (once per ISO week, via the daily cron). It is recorded as a notification only: Twilio WhatsApp is record-only, so it is not pushed to the phone. "Sent" now counts only outcome sent/no_reply (the Booked button used to inflate it). |
| 6 Tables | Migration 008: `ventures` (seeded buildflow, agriloop, trading, ecommerce), `venture_tasks` (the name `tasks` is the agent queue), `decisions`, `experiments`. Rollback: `database/rollbacks/008_ventures.down.sql` (outside `migrations/` because the runner applies every `*.sql` there). `/api/ventures/*`, Ventures page. `metrics` table NOT built (not requested this time). |
| 7 Docs | This file, CHALLENGE.md, README. |

Open: Gmail token; ANTHROPIC_API_KEY; AgriLoop live DB (no AgriLoop payment until confirmed); BuildFlow Storage/billing/legal; which e-commerce repo is the brand; Scout/Operator gig-era features kept (see docs/master/OS_REVIEW.md); rotate secrets that were pasted into chats.
