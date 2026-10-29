# The 60-day challenge (1 Nov - 31 Dec 2026): $10,000 verified cash

**Offer:** annual plan, first two months free to try, personal one-on-one onboarding, for **BuildFlow** and **AgriLoop**.
**Rule:** only cash Treasury has verified counts. An open deal is pipeline, never revenue.

## The math (editable in the app: Challenge > Edit target & prices)
- BuildFlow annual = 12 x $50 = **$600** up front, plus 2 free months added on top (assumption: change it if you meant
  "two months free" differently, e.g. 10 months billed). $10,000 = **17 BuildFlow deals** (about 2 a week for 61 days).
- AgriLoop has **no price anywhere in its repo** (admin-set per country). Set one before the first AgriLoop call, or the
  draft carries an "[OWNER TO FILL] (annual price)" hole and deals need a typed amount.
- Mixed example: 10 BuildFlow ($6,000) + 8 AgriLoop at $500 ($4,000).

## Daily loop (15 min of system, the rest is selling)
1. Open **Challenge**. "Do these today" is ordered: replies, booked onboardings, follow-ups due, fresh leads.
2. Tap a lead > pick the channel > edit the draft (fill every `[OWNER TO FILL]`) > send it yourself (WhatsApp, Instagram,
   call) or send email through Overview > press **I sent it - log it**. Follow-up is scheduled for +3 days.
3. They reply: **They replied**. They book a call: **Onboarding booked**.
4. They say yes: **They paid / close the deal** creates the payment. On the deal card press **Request PayPal payment**,
   send them the link, then verify. The cash number moves only after verification. Set onboarding to scheduled / done.
5. "What's working" shows replies and paid by channel; double down on whatever converts.
- Opt-outs: **Not interested / opt-out** marks the lead lost and the system will never draft or send to it again.

## Before you sell (from each product's own readiness report)
- **BuildFlow:** Firebase Storage not provisioned (uploads fail), no billing, legal pages are placeholders, never run on a real
  phone. Take the first payments by PayPal or bank transfer. Do not promise photo uploads until Storage is on (31 Oct reminder).
- **AgriLoop:** marketplace data is in-memory demo data, not safe for real customers. Do not take annual money for a
  marketplace that would lose their listings; ship the Prisma/Supabase data layer first or sell as a founding-member waitlist.

## Known limits
- Gmail refresh token (OAuth app in Testing mode) expires about 2 Nov: re-issue it or publish the OAuth app. Until then
  email sends fail with a clear error; WhatsApp/Instagram drafts need no integration.
- No AI is running (`ANTHROPIC_API_KEY` unset). Drafts are deterministic templates with explicit fill-ins. Nothing is sent
  without your approval or your own hands.
- Vercel Cron runs once a day (daily report now includes the challenge status); everything else is on-demand.
