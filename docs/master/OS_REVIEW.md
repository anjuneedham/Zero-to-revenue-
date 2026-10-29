# Review of the OS, 29 Oct 2026 (the day the challenge OS starts)

Written after the finish pass. "Verified" means I ran it; "not verified" means I could not.

## What it is today
A single-owner revenue cockpit on Python / Neon / Vercel: a prospect pipeline for BuildFlow and AgriLoop, copy-ready drafts
per channel, deals tied to PayPal orders, cash that counts only after Treasury verifies it, a pace tracker against $10,000 by
31 Dec, a weekly channel/plan report, and a Ventures page for tasks, decisions and experiments. Approval gates, owner login
(password + authenticator), audit log and kill switch all remain.

**It does not sell for you.** It removes admin and tells you whom to message next. Revenue still depends on how many real
conversations you start each day.

## Verified
- 284 tests pass against real Postgres, including the new PayPal message, ingestion, weekly report, Sunday tick and the
  migration-008 rollback and re-apply.
- The new pages load in Chromium against a real database with no JS or API errors; ingestion, weekly and ventures routes
  return correct data.
- Production deployment of the Phase 10 build is live; migrations ran (the API answers 401 rather than 503).

## Not verified
- Logged-in smoke test of production (no owner credentials in my sandbox) and the `/api/challenge` config payload.
- The deployed copy of the work from this chat (steps 2, 4, 5, 6) until the deploy below is done and checked.
- Live PayPal order from the new button (you said PayPal works; the button calls the same functions).
- Claude vision extraction (no key). Gmail send after ~2 Nov (token expires; skipped by you).
- Neon backup / point-in-time recovery settings.

## What it still needs to be very effective, in order of impact
1. **Leads in, every day.** The system is empty until you feed it. Nothing else matters if fewer than ~20 new people a day are
   messaged. Until the first week of data exists, no conversion rate is known, so do not plan on a guessed one.
2. **Products that can honour a sale.** BuildFlow: Storage off (uploads fail), no billing, placeholder legal pages, never run
   on a real phone. AgriLoop: in-memory demo data until the database is live. Selling annual plans on these risks refunds and
   a bad reputation locally. This is the biggest real risk to the $10k, ahead of any software gap.
3. **Reach you cannot lose.** Gmail token expires ~2 Nov, so email sends fail; Twilio is record-only, so reports and
   reminders do not reach your phone. You must open the page each day. A daily push is the cheapest big upgrade.
4. **Honest measurement.** The report is only as good as your logging. If messages and replies are not logged the numbers are
   zero, not "bad". Replies and bookings are manual buttons, not read from WhatsApp/Instagram.
5. **Customer record.** Paid deals anchor to a synthetic opportunity row (known workaround). There is no customers table, so
   onboarding delivery, renewals in Nov 2027 and referrals are not tracked.
6. **Old, off-target features still present.** Scout's gig/bounty feeds, the job-proposal templates and the Game plan tabs
   belong to the earlier crypto/zero-capital product. They add noise and a daily cron cost. I left them because Treasury and
   Operator share their plumbing and deleting working code on an ambiguous instruction is not reversible in effect. See the
   decision below.
7. **Operational safety.** Secrets were pasted into chats (PayPal live secret, Gmail secret and refresh token, sandbox keys):
   rotate them. Vercel runtime logs on this plan keep about 1 hour, so a failure overnight leaves no trace. No CI runs the
   tests. No browser end-to-end test exists (I ran a one-off smoke).

## How to get there
**This week (before 1 Nov)**
- Do the logged-in smoke test of production once: Challenge loads, add a lead, draft, log, create a test deal, press Copy
  PayPal message. Delete the test lead.
- Decide the one question that blocks cleanup: remove Scout's gig feeds and job templates now, or keep them as a side feed?
  (Record it on the Ventures page as a decision.)
- Re-issue the Gmail token or accept WhatsApp/Instagram/calls only for now.
- Add ANTHROPIC_API_KEY plus the three LLM budget/price settings when ready, then test one real screenshot.
- BuildFlow: provision Firebase Storage (31 Oct reminder). AgriLoop: confirm the database is live before any payment.

**Weeks 1-2 (1-14 Nov)**
- Log every message and reply. On the first Sunday read the weekly report and keep only the channel that produced replies.
- Run exactly one experiment at a time from the Ventures page (one change, one metric).
- Add a push for the daily "Do these today" list (Twilio WhatsApp or email) so the cockpit comes to you.

**Weeks 3-5 (15 Nov - 5 Dec)**
- Build a customers table and anchor payments to it; track onboarding delivery and a 2-week check-in.
- Add CI that runs the suite on every push, and a short browser smoke test.
- Verify Neon backups; set an error alert for failed cron runs.

**Weeks 6-9 (6 Dec - 31 Dec)**
- Use the data: double down on the best channel and plan, cut the rest. Only now consider automating drafts further.
- Remove the dead Scout/Operator job features if the decision above says so, plus the stale docs (`MASTER_SYSTEM.md`,
  `docs/architecture/*`).

## Measures that mean it is working
- Verified cash against the pace line on the Challenge page (not pipeline).
- Messages logged per day, reply rate per channel, replies to booked onboardings, booked to paid.
- Time from "they said yes" to cash verified.
