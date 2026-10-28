# Handoff for the Zero to Hero OS master-plan chat (28 Oct 2026)

Start a NEW chat with just: "continue". CLAUDE.md loads automatically and points to docs/master/STATE.md, which holds current facts, decisions and the next step. This file is the evidence appendix (verified 28 Oct); STATE.md wins on any conflict.

## Token rules for every chat (policy, not optional)
- One task per chat; new chat when a task is done. Never reuse a chat across days.
- Read files with offsets/limits or `jq`/`grep`; never dump whole files or API results into the chat.
- Write findings to files, then refer to the file. Do not paste repo contents back in prose.
- No sub-agents, no repeated deploys, no re-reading what this file already states.
- Docs first, code second; one phase per chat; run tests once at the end of a phase.
- Weekly plan: Mon BuildFlow, Tue Agriloop, Wed trading, Thu e-commerce, Fri BuildFlow growth, Sat Agriloop growth, Sun OS review. Each day's chat touches ONLY that venture's folder.

## Evidence gathered (verified 28 Oct, commands run this session)
**Repos reachable** (35 on the account; relevant ones cloned shallow under /home/user and /home/user/anjuneedham):
- Zero to Hero OS = `Zero-to-revenue-` (Python, Neon Postgres, Vercel, live 200 at zero-to-revenue-neon.vercel.app). 236 tests (own suite). See IMPLEMENTATION_AUDIT.md.
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
