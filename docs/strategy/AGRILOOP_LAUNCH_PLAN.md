# Agriloop: path to launch with a creator (written 29 Oct 2026)

A creator with an engaged following and an algorithm already pointed at the right people could start **Tuesday 3 Nov**. That makes Agriloop the focal venture. BuildFlow is parked, not dropped. The same list is live in the dashboard under Game plan > Agriloop launch.

Everything below was checked on 29 Oct in `agriloopmain` (commit 03eba34) and the Vercel project `agriloopmain`. Env var *names* were read, never values.

## The Firebase question: it isn't Agriloop's problem

- **Agriloop has no Firebase anywhere.** Auth is Supabase Auth with Postgres RLS. The Firebase Storage / Blaze-plan blocker belongs to **BuildFlow** only.
- **Agriloop's real blocker is the data layer.** Marketplace data (listings, requests, community posts) runs on `MemoryDataSource`, a process-local store. Its own code says it is "NOT production-safe". The live Vercel project has only three env vars: the Supabase URL, the publishable key, and `ALLOW_SEED_IN_PRODUCTION=true`. There is no `DATABASE_URL` and no `AGRILOOP_DATA_SOURCE`, so production is on the memory store.
- **What that means on Tuesday:** accounts survive (Supabase). Listings and posts do not; they live on one serverless instance and can vanish on a cold start. Anyone the creator sends will post something and then lose it.
- **`ALLOW_SEED_IN_PRODUCTION=true`** also means the live site shows demo listings and farmers as if they were real. Fine for a demo, misleading for a real audience.

## Hosting: Vercel vs Hostinger

**Recommendation: do not migrate before Tuesday.** Hosting is not what blocks launch, and moving it adds a second operations surface in the week that matters.

| | Vercel (now) | Hostinger |
|---|---|---|
| Status | Live, `/market` returns 200 | Not set up |
| Fit | Native Next.js | Node.js apps run on **Business web hosting or Cloud plans** (VPS is manual). GitHub deploy, private repos, Node 20/22/24 supported ([Hostinger Next.js hosting](https://www.hostinger.com/ca/web-apps-hosting/nextjs-hosting), [Node.js support list](https://www.hostinger.com/support/?p=8903)). |
| Cost | Hobby is free but **non-commercial** | Paid plan from day one |
| Unknown | n/a | Whether Next.js 16 runs cleanly on their managed Node host. Test it, don't assume. |

- **Vercel Hobby is acceptable for Agriloop until money flows.** `PAYMENT_PROVIDER=none` and marketplace deals happen off-platform. The Hobby/Pro question arrives when Premium checkout goes live, and that is the honest moment to compare Vercel Pro against Hostinger on cost.
- **The test you asked for is worth running, as a staging mirror after Tuesday.** Put a copy on a Hostinger subdomain with the same env vars, with Vercel staying the live site. Pass criteria: builds from GitHub, env vars set, signup and a listing round-trip work, SSL is fine, and you can read logs without help. A day of work, not a migration.
- **BuildFlow stays on Vercel**, as you proposed. Note it is the one that must reach Pro before charging.

## What has to be true before Tuesday

| Priority | Who | Item | Why |
|---|---|---|---|
| P0 | Agent | **Build the Prisma data source** against the existing Supabase Postgres | Largest item in Agriloop's own roadmap. Nothing above the repository layer changes. No new vendor, no card. |
| P0 | You | **Add `DATABASE_URL` (Supabase connection string) as a Vercel secret and set `AGRILOOP_DATA_SOURCE=prisma`** | I never see the value. Do this only after the adapter is merged and tested. |
| P0 | You | **Set `ALLOW_SEED_IN_PRODUCTION=false` once real data exists** | Stops demo farmers showing as real. Keep a few genuine listings first so the site is not empty. |
| P0 | Both | **Listing photos on Supabase Storage** (the Firebase Storage alternative) | `STORAGE_PROVIDER=local` writes to `public/uploads`, which does not persist on Vercel. Supabase Storage is in the project you already have, with no Blaze plan or card. Check current free-tier limits. |
| P0 | Both | **Real signup emails** | `EMAIL_PROVIDER=console` logs to stdout, and email verification is "modelled but not enforced" in Agriloop's own security doc. Supabase's built-in auth mailer is rate-limited; set a custom SMTP (Resend is already the intended provider) so a spike of signups from the creator's audience can confirm. |
| P0 | You | **Settle the creator ask** | One action for her audience (sign up + post a listing or request), one link, one UTM tag per video, so you can see what her audience does. |
| P1 | Agent | **Privacy and Terms pages** | None exist under `src/app` (only About and Guidelines). Marketplace collects personal data; draft, then a human reviews. |
| P1 | You | **Seed 20-30 real listings** before the first post | A marketplace with nothing in it wastes her first spike of attention. |
| P1 | Agent | **Instrument the pilot metrics** | Listings per farmer, requests per buyer, response rate, first-contact time (from the repo's own MVP roadmap). |
| P2 | You | Android build for Play Store | Web first. The creator's audience will arrive on phones via a link. |

## Status update, 29 Oct (evening): what the fix session did

Work is on branch `feat/prisma-data-source` in `agriloopmain` (not merged, no PR). "Verified"
below means tested against a real Postgres or the live Supabase project; "in code" means written
but not exercised live.

| Item | Status |
|---|---|
| Supabase project | Was **paused**; restored and now ACTIVE_HEALTHY. Verified. |
| Marketplace tables (Listing, PriceTier, BuyerRequest, RequestResponse, Category, Product) with RLS | Applied to the live project. Verified. |
| Product catalogue | Production had **0 categories and 0 products**, so nobody could have posted a listing. Seeded 47 + 69. Verified. |
| Prisma data source for users, profiles, parishes, catalogue, listings, requests | Written; 30 tests pass against a throwaway Postgres built from the migrations (includes ownership checks, and the tests were shown to fail when a guard is removed). **Not run against the live database**: that needs `DATABASE_URL`, which only you add. |
| Photo uploads | The listing form never sent photos at all (`storageService` was unused). Built: `listing-photos` bucket (public read, 5 MB, image types, owner-folder write policies; applied live and verified), upload route, form field. **Not tested end to end with a signed-in user.** |
| Real signup emails | App code never sent any: all emails are Supabase Auth's. Needs Resend SMTP in the Supabase dashboard (**you**; steps in `agriloopmain/docs/GO_LIVE_RUNBOOK.md`). |
| Keep-alive | Daily Vercel cron + `/api/health` (in code). Pro plan still recommended: free projects have no backups. |
| Vercel env + production promotion | **Not done.** Waiting on you for `DATABASE_URL`, then a preview check. |

**Gap this session found that the plan did not list:** only listings, requests, people and
reference data move to Postgres. **Messages, notifications, favourites, community posts, farm
updates, orders and reviews stay in memory** and are lost on a cold start. Messaging is how a
buyer currently contacts a farmer, so either migrate it next or lead with WhatsApp for the
launch week. If neither happens by Tuesday, the fallback above applies: hold the start.

**Still blocked on a Supabase confirmation prompt (needs you):** two small migrations that
contain a `drop` (PriceTier policy split; viewCount no longer touching updatedAt). Neither
blocks launch.

## Firebase options for BuildFlow (parked, for later)

1. **Keep Firebase, do the Blaze upgrade.** Usage within the free quota costs nothing; the hurdle is the card. A virtual USD card may be accepted where a prepaid card is not. Add the budget alert.
2. **Swap the storage layer** (Supabase Storage, Vercel Blob or Cloudflare R2). It removes the card dependency but is a code change in the BuildFlow repo (upload paths, `storage.rules`, tests), roughly a day.
3. **Do nothing this week.** BuildFlow's own reminder is set for 31 Oct. Decide after Agriloop's first week.

## Risks

- **The pilot is only as good as the data layer.** If the adapter slips, the fallback is to hold the creator's start a few days, not launch on memory storage.
- **One-person bandwidth.** Agriloop gets the main push; BuildFlow gets only the founding-contractor conversations you were already having.
- **Unverified:** whether the Vercel team is on Hobby or Pro; Neon/Supabase backup settings; Hostinger plan pricing in your region.
