# The 60-day challenge (1 Nov - 31 Dec 2026): $10,000 verified cash

**Offer:** annual plan, first two months free to try, personal one-on-one onboarding, for **BuildFlow** and **AgriLoop**.
**Rule:** only cash Treasury has verified counts. An open deal is pipeline, never revenue.

## The math (editable in the app: Challenge > Edit target & prices)
"Two months free" = **12 months of service for the price of 10**: annual price = monthly x 10 (owner, 29 Oct).
| Plan | Monthly | Annual (cash up front) | Deals for $10,000 |
|---|---|---|---|
| BuildFlow | $50 | **$500** | 20 |
| AgriLoop Farmer Premium | $20 | **$200** | 50 |
| AgriLoop Buyer Basic | $10 | **$100** | 100 |
Mixed example: 12 BuildFlow ($6,000) + 20 Farmer Premium ($4,000). BuildFlow carries the target; AgriLoop is volume.
Roughly 3 BuildFlow deals a week for 61 days, or fewer if you mix in farmers.

## Daily loop (15 min of system, the rest is selling)
1. Open **Challenge**. "Do these today" is ordered: replies, booked onboardings, follow-ups due, fresh leads.
2. Tap a lead > pick the channel > edit the draft (fill every `[OWNER TO FILL]`) > send it yourself (WhatsApp, Instagram,
   call) or send email through Overview > press **I sent it - log it**. Follow-up is scheduled for +3 days.
3. They reply: **They replied**. They book a call: **Onboarding booked**.
4. They say yes: **They said yes - create the deal** creates the payment. On the deal card press **Copy PayPal message**
   (creates the PayPal order the first time, reuses it after), paste it to them yourself, then press **Check if paid**.
   The cash number moves only after verification. Set onboarding to scheduled / done. For AgriLoop it asks you to confirm
   the database is live first.
5. "What's working" shows replies and paid by channel; double down on whatever converts.
- Adding leads fast: **From screenshot / paste** reads pasted text (and screenshots once the AI key is set), shows what it
  found, and only creates a lead when you press **Add lead** on a row you checked. Treat every extracted field as unverified.
- **Weekly report** (Challenge page; also recorded as a notification every Sunday - it reaches WhatsApp only if Twilio is configured, which it is not today, so open the page to read it): messages -> replies -> onboardings booked -> paid, by
  channel and by plan, with next-week actions from fixed rules. "Paid by channel" uses the channel you first reached the lead
  on. Counts need you to log every message and reply; if you do not, the report says so.
- **Ventures** page: per-venture tasks, open decisions and experiments (BuildFlow, AgriLoop, Trading, E-commerce).
- Opt-outs: **Not interested / opt-out** marks the lead lost and the system will never draft or send to it again.

## Before you sell (from each product's own readiness report)
- **BuildFlow:** Firebase Storage not provisioned (uploads fail), no billing, legal pages are placeholders, never run on a real
  phone. Take the first payments by PayPal or bank transfer. Do not promise photo uploads until Storage is on (31 Oct reminder).
- **AgriLoop:** the database is being set up fully this weekend (owner). Until the live app runs on it, marketplace data is
  in-memory demo data. Book calls and onboarding now, but take no payment until it is confirmed live, and make the in-app
  plans match $10 Buyer Basic / $20 Farmer Premium (prices live in AgriLoop's admin screen, not code).

## Known limits
- Gmail refresh token (OAuth app in Testing mode) expires about 2 Nov: re-issue it or publish the OAuth app. Until then
  email sends fail with a clear error; WhatsApp/Instagram drafts need no integration.
- No AI is running (`ANTHROPIC_API_KEY` unset). Drafts are deterministic templates with explicit fill-ins; screenshot reading
  is off until the key plus `LLM_MONTHLY_BUDGET_USD`, `LLM_PRICE_IN_PER_MTOK`, `LLM_PRICE_OUT_PER_MTOK` are set. Nothing is
  sent without your approval or your own hands.
- Vercel Cron runs once a day (daily report includes the challenge status; Sundays also record the weekly report); everything else is on-demand.
