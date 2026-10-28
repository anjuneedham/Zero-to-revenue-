# Agriloop (venture doc)
Repo `agriloopmain` (private; same commit as public `farm-market-place`; `agriloop` is the older predecessor) · live https://agriloopmain.vercel.app · stage: BUILD · priority 2.

## Report
Farm marketplace. Next.js 16, Supabase Auth + RLS migrations, Capacitor Android. *(handoff)*

## Audit / risks
Marketplace data uses an in-memory source (`AGRILOOP_DATA_SOURCE=memory`, "NOT production-safe"): data vanishes on restart. Prisma adapter is the largest remaining item. No automated tests. UNVERIFIED: what the live Vercel env sets for the data source. Two-sided marketplace cold-start risk. No payments or logistics defined.

## MVP scope
Listings + inquiries persisted in a real database, auth, basic moderation. Payment and delivery stay manual (WhatsApp/phone) for the pilot.

## Roadmap
- [ ] Check live env data source via Vercel MCP `filter_project_envs` (no decrypt) and record it
- [ ] Choose persistence: Supabase tables (already used for auth) vs Prisma; log decision
- [ ] Implement persistent data adapter + migration; add tests for it
- [ ] Add smoke tests for auth + listing create/read
- [ ] Recruit pilot: 5 farmers + 5 buyers in one parish
- [ ] Growth: farmer WhatsApp groups, co-ops, extension officers

## Metrics
farmers_onboarded, listings_live, buyer_inquiries, completed_deals (self-reported), repeat_buyers.

## Acceptance criteria
Listings survive a redeploy; 5 farmers + 5 buyers active; 3 inquiries convert to a real transaction.
**Kill/pivot criterion:** pilot yields 0 completed deals in 8 weeks after persistence ships → pause, log decision.
