# Handoff for the Zero to Hero OS master-plan chat (28 Oct 2026)

Start a NEW chat with: "Read docs/master/HANDOFF.md in anjuneedham/Zero-to-revenue- and continue." Nothing else needed. (CLAUDE.md in this repo now carries the Skills rules; the skills library phase is recorded below.)

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

## Phase done: Skills Library (30 Oct 2026, branch `claude/skills-library-phase-ylmbxk`)
Scope kept to this phase only: no preview/production URL opened, Neon untouched, no model calls, no scripts from the skills executed.

**What was installed** (all in `.claude/skills/`, committed, no runtime downloads; 4.05 MiB, 518 files; `python3 scripts/skills/verify_skills.py` passes):
- **70 vendored open-source skills**, pinned to commit hashes in `ATTRIBUTION.md` and `docs/skills-manifest.json`: SaaS growth 19, Engineering 15, Fashion/e-commerce 9, Trading 10, Investing 4, Sales/offers/copy 7, Documents/ops 6. Sources: coreyhaines31/marketingskills, phuryn/pm-skills, alirezarezvani/claude-skills, wshobson/agents, addyosmani/agent-skills, obra/superpowers, mattpocock/skills, neondatabase/agent-skills, supabase/agent-skills, tradermonty and agiprolabs trading skills, anthropics/skills (2), openai/skills (1). All MIT or Apache-2.0.
- **6 custom skills** for Jay: `agriloop-growth`, `buildflow-growth`, `fashion-launch`, `trading-lab` (with `go-no-go-checklist.md`), `investing-plan` (with CSV tracking templates), `hormozi-lens`.
- `docs/skills-registry.md` (every skill: category, goal, purpose, trigger, source, licence), `CLAUDE.md` (Skills section and safety rules), `docs/skills-vetting.md` (method, honest limits, findings).
- Allocation deviations from the brief, on purpose: Engineering 15 (+1) and SaaS 19 (+1) because no permissive DOCX/XLSX/PPTX skill exists (the Documents slots were not padded); Sales 7 (-1) and Fashion 9 (-1) because the Shopify skill was rejected and no fashion/inventory skill exists upstream.

**Rejected** (reasons in `docs/skills-vetting.md`):
- Licence: `docx`, `pdf`, `pptx`, `xlsx` (Anthropic: proprietary), `doc-coauthoring` (no licence), `vercel-react-best-practices` and the Vercel repo (no LICENSE file), ComposioHQ/awesome-claude-skills (no LICENSE file).
- Security / suitability: `shopify` (usage telemetry to shopify.dev, minified code, 94 binaries), `slippage-modeling` (live Jupiter/Solana calls), `ohlcv-processing` (Birdeye API key), `portfolio-manager` (Alpaca brokerage connection), `drawdown-circuit-breaker`, `pre-trade-discipline-gate`, `trade-performance-coach` (depend on a sibling skill and US-market calendar; the drawdown rule lives in `trading-lab` instead).
- Not used as sources: sickn33/antigravity-awesome-skills (unverifiable re-hosted aggregate), K-Dense scientific skills (off-topic), alpacahq/skills (not reachable).

**Honest limits of the vetting:** pattern scan of every file, AST audit of all 65 Python scripts, manual read of every flagged line and the process/server code. I did not read every line of every Markdown reference. Nothing was executed. `mt5-robot-tester`, `skill-creator`, `ad-creative`, `social` and `video` carry caution notes in the registry.

### How to add, update or remove a skill
1. Clone the upstream repo shallow into a scratch folder (never inside this repo): `git clone --depth 1 https://github.com/OWNER/REPO /tmp/REPO`.
2. Licence gate: MIT / Apache-2.0 / BSD / CC-BY, and a licence file must exist. Otherwise stop.
3. `python3 scripts/skills/vet_skill.py /tmp/REPO/path/to/skill --detail`, then **read** `SKILL.md` and every script, and every flagged line. Reject on exfiltration, unknown URLs, telemetry, obfuscation, key requests, hidden characters, or (trading) any live-order capability.
4. `python3 scripts/skills/install_skill.py --clone /tmp/REPO --owner-repo OWNER/REPO --path path/to/skill --category saas|eng|fashion|trading|invest|sales|docs [--notes "caution"]` (copies intact, adds LICENSE if missing, pins the commit).
5. Add a one-line purpose and trigger for it in `scripts/skills/skills_meta.py`; update the expected counts in `verify_skills.py` if the total changes.
6. `python3 scripts/skills/build_docs.py && python3 scripts/skills/verify_skills.py`, commit.
- **Update** = repeat steps 1-6 for the same skill (it overwrites the folder and moves the pinned commit). Re-vet: upstream can change after you vetted it. **Remove** = delete the folder and its manifest entry, then rebuild docs.
- To make a new custom skill, use the `skill-creator` skill's guidance; keep `name` equal to the folder name (lowercase, hyphens) and quote or fold YAML descriptions that contain colons.

### What each goal group gives you
- **SaaS growth (Agriloop + BuildFlow), 19**: the sales-and-product toolkit. Customer interviews and research (find out what people really pay for), beachhead choice (who to sell to first), pricing, onboarding and churn (keep them after they sign), cold outreach and demos, metrics (MRR, churn, CAC, LTV) and partner/revenue-share modelling for the health-professional deal.
- **Engineering, 15**: guard rails for your stack. Next.js App Router, Neon/Supabase Postgres, SQL tuning, Tailwind, auth, API design, test-first, debugging, code and security review, CI, performance. They stop avoidable mistakes before they reach real users.
- **Fashion/e-commerce, 9**: the marketing engine (ads, ad creative and hooks, email, SMS/WhatsApp, social, short video, influencers, competitor research). It does not include store operations or inventory maths; `fashion-launch` fills that gap and enforces "prove demand before you buy stock".
- **Trading, 10**: the proof toolkit, not a profit machine. Backtest quality, walk-forward and out-of-sample tests, risk statistics, sizing, journal, strategy template, MT5 Strategy Tester batching. `trading-lab` adds the hard drawdown rule, minimum paper period and go/no-go checklist.
- **Investing, 4**: portfolio metrics, financial modelling and runway maths; `investing-plan` adds the profit waterfall, rebalancing rules and tracking sheets. Educational, not advice.
- **Sales/offers/copy, 7**: offer design, copywriting and editing, persuasion, lead magnets, proposals, expert-panel review. `hormozi-lens` is the quick scorecard to run on any offer or pitch.
- **Documents/ops, 6**: PDF, research and summaries, project management, SEO audit, and `skill-creator` (how you add skills).

### Gaps and cautions
- **Sessions started in another repo (agriloop, agriloopmain, buildflow, Kadeform-, mq5) will not see these skills**: they live only in this repo. Decide later whether to copy `.claude/skills/` (about 4 MB) into those repos; if so, copy only the groups each venture needs.
- Agriloop/BuildFlow skills quote repo docs dated 25-28 Oct; they tell Claude to re-read them first.
- Missing upstream: DOCX/XLSX/PPTX, spreadsheet tracking (CSV templates provided), fashion store ops, Deriv/MQL5-specific testing.
- Branch: the environment assigned `claude/skills-library-phase-ylmbxk`, so the work is committed there rather than on a branch literally named `skills-library`.

### Recommended next phase
1. Run the first item of "Next steps" below (CURRENT_STATE_AUDIT.md + MASTER_PLAN.md, docs only) but with `buildflow-growth` loaded, so the 30-day plan is built around **BuildFlow's first 10 founding contractors** (unblock the P0 list: Storage, billing decision, legal pages, Pro hosting). That is the shortest path to revenue.
2. Then the venture docs, then the Phase 1 build.
3. Smoke-test the library once: ask for "a pricing test plan for BuildFlow" and confirm the reply names the skills used and lists claims needing verification.

### Ask Jay once (do not guess)
Which e-commerce repo is "the brand" and the fashion concept/budget; the partner and terms for the BuildFlow health-professional edition; Agriloop live data-source setting and current user counts; monthly personal expenses and risk tolerance for `investing-plan`; whether to copy skills into the venture repos.

## Next steps (one chat each)
1. docs/master/CURRENT_STATE_AUDIT.md + MASTER_PLAN.md (use the evidence above, do not re-gather).
2. docs/master/ventures/{BUILDFLOW,AGRILOOP,TRADING,ECOMMERCE}.md with: report, audit, risks, MVP scope, roadmap, growth plan, metrics, acceptance criteria.
3. Phase 1 build: `ventures`, `tasks`, `decisions`, `experiments`, `metrics` tables (reversible migration 007), venture-scoped views, weekly-allocation page. Keep Python/Neon/Vercel stack.
4. Then the BuildFlow sidekick work from the earlier brief (needs ANTHROPIC_API_KEY).
Open decisions: which e-commerce repo is the brand; Gmail token expires ~2 Nov; Agriloop live data source.
