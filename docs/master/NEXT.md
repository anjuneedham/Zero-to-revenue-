# NEXT: live pointer for the next chat

Rule: one task per chat. When a task is done, update THIS file (status + next task), commit, push, then start a new chat with:
"Read docs/master/NEXT.md in anjuneedham/Zero-to-revenue- and do the task listed."
Never reuse a chat across days. Read HANDOFF.md only if NEXT.md points you to it.

## Weekly rhythm (each day's chat touches ONLY that venture's folder)
| Day | Focus | Default task type |
|---|---|---|
| Mon | BuildFlow | Fix launch blockers |
| Tue | Agriloop | Pre-launch build (persistence, tests) |
| Wed | Trading | Backtest / paper-journal evidence only |
| Thu | E-commerce | Brand decision, then storefront/offer work |
| Fri | BuildFlow growth | Acquisition, onboarding, metrics |
| Sat | Agriloop growth | Supplier/buyer outreach (pre-launch: waitlist) |
| Sun | OS review | Review week, update plan, set next week |

Today: Wed 28 Oct 2026 (OS planning day; overrides the rhythm).

## Status
- [x] Step 1: CURRENT_STATE_AUDIT.md + MASTER_PLAN.md
- [~] Step 2 (half done): ventures/{BUILDFLOW,AGRILOOP,TRADING,ECOMMERCE}.md (report, audit, risks, MVP scope, roadmap, growth plan, metrics, acceptance criteria). Use evidence in HANDOFF.md; do not re-gather. Facts: Agriloop NOT live (pre-launch); NO fashion brand repo yet (e-commerce docs must say brand is undecided: Kadeform- / NF-Fragrance- are existing non-fashion storefronts).
- [ ] Step 3: Phase 1 build: ventures, tasks, decisions, experiments, metrics tables (reversible migration 007), venture-scoped views, weekly-allocation page. Python/Neon/Vercel. Tests once at end.
- [ ] Step 4: BuildFlow sidekick (needs ANTHROPIC_API_KEY).

## Progress log
- 28 Oct: Step 2a done: ventures/BUILDFLOW.md and ventures/AGRILOOP.md written (evidence only, unverified items marked).

## NEXT TASK (do this one)
Step 2b: write ventures/TRADING.md + ventures/ECOMMERCE.md using the same section layout as BUILDFLOW.md (report, audit, risks, MVP scope, roadmap, growth plan, metrics, acceptance criteria). Trading: gate is backtest + >=4 weeks paper results, no live capital. E-commerce: brand undecided. Then tick Step 2, set next task to Step 3, update the progress log, commit, push.

## Open decisions (founder)
1. E-commerce: no fashion brand repo yet; create one or choose Kadeform-/NF-Fragrance-.
2. Gmail token expires ~2 Nov.
3. Agriloop: not live; decide target launch date and which data source (Prisma/Postgres vs Supabase).
