# STATE: single source of truth (update every session)
Last updated: 2026-10-28 by the token/continuity audit session.

## Owner and ventures
- Owner: anjuneedham (Jamaica; Stripe unavailable there). Background: sales and customer service, has run businesses, builds sites, funnels and apps with AI. See docs/strategy/OWNER_PROFILE.md.
- Venture 1, BuildFlow: live beta SaaS for construction pros. Repo `buildflow`. Plan: docs/strategy/BUILDFLOW_LAUNCH_PLAN.md.
- Venture 2, Agriloop: repo `agriloopmain`. Marketplace data is in-memory, not production-safe.
- Venture 3, Trading: repo `mq5`. No evidence of an edge yet.
- Venture 4, Fashion / clothing brand: **UNKNOWN: brand name, plan and repo.** The owner told a previous chat this and it was never written to a file, so it was lost. Owner to re-supply ONCE; then record it here and never ask again.
- Weekly rhythm: Mon BuildFlow, Tue Agriloop, Wed trading, Thu e-commerce/fashion, Fri BuildFlow growth, Sat Agriloop growth, Sun OS review.

## Decisions made
- Keep the Python / Neon / Vercel stack for the OS.
- Sessions start from the repo, not from chat history. CLAUDE.md plus this file are the memory.
- The earlier handoff said "founder must confirm which e-commerce repo is the brand". The owner has since said it is a fashion/clothing brand, and no repo matched. Treat that as unresolved until the owner gives the name and repo (or says none exists yet).

## Done (newest first)
- 2026-10-28: Diagnosed lost-context cause; added CLAUDE.md and this STATE.md.
- 2026-10-28: HANDOFF.md and IMPLEMENTATION_AUDIT.md written (1b1c990, de0ad30).

## Next (exactly one)
Owner supplies the fashion brand name, plan and repo, which gets recorded above. Then: docs/master/CURRENT_STATE_AUDIT.md and MASTER_PLAN.md from the evidence in HANDOFF.md.

## Open questions
- Fashion brand: name, plan, repo, current state.
- Agriloop live data source (memory or database) on Vercel.
- Gmail token expires about 2 Nov.
- Neon backup/PITR settings unverified.
