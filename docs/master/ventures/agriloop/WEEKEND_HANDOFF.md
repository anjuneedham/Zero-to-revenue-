# Agriloop weekend handoff (30 Oct 2026)

Read this first in any new session. It holds the decisions made so far so they are not re-asked.

## Facts and decisions
- **Focus:** Agriloop is 100% of the founder's time from 1 Nov. BuildFlow is on the back burner until the end of November (supporting existing users only).
- **Product:** marketplace connecting Jamaican farmers and buyers, filtered by parish and neighbouring parishes. Island-wide from launch; the creator is based in St. Mary and is the face.
- **Partner (one person, the creator):** sells her own seeds, 1k+ TikTok followers, strong audio and content style. Handles education and community. Founder does onboarding and demo/sales calls. Deal: **30% profit share + 10% ownership** (vesting proposed 24 months, 6-month cliff; profit share basis proposed as Net Revenue = platform fees received minus processor fees, refunds, chargebacks). The earlier "50/50" meant the founder's time split between ventures, NOT ownership. There is no 50% partner. Any "50%" on the Agriloop website is a mistake to find and remove.
- **Payments:** launch is invite-only, free for 60 days, cash/invoice orders only. No card processing, no fees, and no held funds until a legal review is done (target end of November). Stripe is unavailable in Jamaica; PayPal cannot split marketplace payouts there as far as is known. Later options to verify: WiPay, Fygaro, Lynk. Fee only on card payments; cash with an Agriloop invoice is fee-free.
- **Legal:** the founder cannot afford a full legal review now; the lawyer contacted said policies don't need a formal review. Drafts are in `legal/` and must be marked as drafts. Plan: sign the founder agreement in writing before launch; lawyer review of payments, terms and structure by end of November, before anyone pays.
- **Company:** not yet registered. Recommended: private limited company in Jamaica. See `COMPANY_REGISTRATION_PLAN.md`.
- **Known technical blocker:** the `agriloopmain` repo uses an in-memory data source (`AGRILOOP_DATA_SOURCE=memory`), not production-safe; there are no automated tests. The live Vercel env value is unverified. Stack: Next.js 16, Supabase Auth + RLS migrations, Capacitor Android, live at agriloopmain.vercel.app.
- **Costs:** Supabase free tier to build, Pro (~$25/month) before real farmers; Vercel Pro (~$20/month) before the first paid transaction (Hobby is non-commercial). Verify current prices.
- **Pages already published (private):** Legal Pack https://claude.ai/artifact/DrCd3fSeKchYNL9kqW8Ebw, Week One https://claude.ai/artifact/8siNYUyDAKkjmMrVxXb2vs. Sources: `legal/*.md`, `docs/visual/*.html`; rebuild the legal pack with `python3 scripts/visual_pack.py docs/master/ventures/agriloop/legal docs/visual/agriloop_legal_pack.html`.
- **Founder style:** visual learner; prefers plain language and pages/flows over long text. Use the `visual-model` skill for visuals.

## Weekend plan (Fri 30 Oct - Sun 1 Nov)
**Friday: make data real**
1. Attach `agriloopmain`; work on a new branch, never main.
2. Read the repo, check the Vercel env for the data source (do not print secrets), inspect the Supabase schema.
3. Replace the in-memory source with Supabase Postgres (existing Auth + RLS), via a reversible migration. Skip Prisma unless it is already working.
4. Add the minimum tests: signup, create listing, browse by parish, place order, invoice.

**Saturday: the full flow on a phone**
5. Signup with the terms checkbox (see `legal/TERMS_OF_USE.md`, "Acceptance at signup"), storing terms version, privacy version and timestamp; sellers accept the Seller Agreement before a first listing.
6. Farmer lists produce (photo, price, unit, parish); buyer browses by parish and neighbouring parishes (neighbour table for all 14 parishes); buyer orders; farmer confirms; invoice generated. Cash/invoice only.
7. Link Terms and Privacy pages (from `legal/`, clearly labelled draft until reviewed).
8. Find and remove any "50%" wording about ownership on the website.
9. Deploy a preview, give the founder a phone checklist, fix what breaks.

**Sunday: ready for Monday's call**
10. Seed 5 realistic sample listings (marked as samples).
11. Fill in the Legal Pack with the founder; update the Week One page if plans changed.
12. Final smoke test; list what is not done.

## Monday 2 Nov: call with the creator (60 min)
Vision 10, agreement 15, app demo 10, content plan 10, first 10 farmers 10, next actions 5. Details on the Week One page.

## Not to do
- No card payments, no fees, no held funds, no public launch.
- Do not email or message anyone unless the founder asks; creator agreement goes out from the founder only after the brackets are filled or it is labelled a draft.
- Do not touch BuildFlow.
- Do not push to main or open a pull request unless asked.

## Open items needing the founder
Supabase project name; creator's email and other socials; the new name for the OS repo; company name shortlist.
