---
name: agriloop-growth
description: Customer discovery, pricing tests and outreach plans for AgriLoop (Jamaican agricultural marketplace connecting farmers, buyers and businesses). Use when Jay wants Agriloop's first users, a field pilot plan, farmer or buyer interview scripts, premium/pricing decisions, WhatsApp outreach scripts, or a go/no-go on charging real customers.
---

# Agriloop growth

Goal: **first real farmers and buyers using Agriloop, then first paying premium members.** Do the work *and* teach Jay why, in plain language.

## Ground truth (read before advising)

Check these files in the Agriloop repo (`agriloopmain`) before relying on this summary; they may have changed:
`docs/PRODUCT_ARCHITECTURE.md`, `docs/PREMIUM_STRATEGY.md`, `docs/MVP_ROADMAP.md`, `docs/USER_FLOWS.md`.

What the docs say today (as of the 2026-10-30 library build):
- Four layers: **Marketplace**, **Buyer Requests** (demand posted before supply exists), **Community**, **Academy**. Community and core Academy are free forever by design.
- Premium sells outcomes ("be seen first in your parish", "save on every bulk order"). Prices live in the database (`SubscriptionPlan`), never in code, and savings figures must be real data.
- Planned field pilot: **50 farmers (Manchester, St Elizabeth) + 15 Kingston buyers**. Metrics: listings per farmer, requests per buyer, response rate, first-contact time.
- Payment is off-platform in the MVP (discover -> contact -> negotiate -> arrange payment -> complete).

**Blockers to verify before real users or money** (from `docs/master/HANDOFF.md`): marketplace data uses an in-memory data source (`AGRILOOP_DATA_SOURCE=memory`, "NOT production-safe"); what the live Vercel environment actually sets is UNVERIFIED; there are no automated tests. Never invite real users to create data that a redeploy could erase. If the data-source question is still open, say so first and make that the first task.

## The cold-start logic (teach this)

A marketplace is empty until both sides show up, so start with the **side that is easiest to find and has the most urgent pain** and give them value *without* the other side. For Agriloop that is **Buyer Requests**: a restaurant, hotel, supermarket or processor posts "I need 200 kg of tomatoes weekly in Kingston" and farmers respond. A few buyers with real, recurring demand will pull farmers in. Recruit 15 buyers first, then use their requests to recruit farmers ("a buyer in Kingston asked for scallion this week").

## Workflow

1. **Pick one beachhead** (use `beachhead-segment`): one crop group + one parish + one buyer type. Example hypothesis: *Kingston restaurants/hotels that currently buy by phone from several farmers.* Mark it as a hypothesis until interviews support it.
2. **Customer discovery** (use `interview-script`, `customer-research`, `summarize-interview`): 10 buyer and 10 farmer conversations before building more. Ask about the *last time* they bought/sold: how they found each other, price discussion, payment, no-shows, what went wrong. Do not pitch Agriloop in the first 10 minutes. Record verbatim quotes.
3. **Offer** (use `hormozi-lens`, `offers`): for buyers, "reliable supply from verified farms, post a request in 2 minutes"; for farmers, "reach buyers who actually want your crop, free". Remove effort: Jay or a helper can post the first listings/requests *for* them (done-for-you) via WhatsApp.
4. **Outreach** (use `prospecting`, `cold-email`; adapt to WhatsApp/phone/in person): warm network first, then farmer groups, agricultural extension contacts, market associations, restaurant owners. Script template below.
5. **Pilot metrics** (use `startup-metrics-framework`): weekly review of the four pilot metrics plus *requests that received a response within 24 h*. A marketplace lives or dies on the response rate.
6. **Pricing test** (use `pricing`, `partnerships-architect` for supplier discounts): do not set prices from imagination. Interview buyers about willingness to pay for (a) priority supply, (b) bulk discounts, (c) saved lists; interview farmers about (d) featured listings, (e) request alerts. Test with 5-10 real people before enabling any `SubscriptionPlan`. Payment from Jamaica: Stripe is not available there (see the BuildFlow notes); confirm a payment rail (bank transfer, PayPal, local processor) before charging.
7. **Retention** (use `onboarding`, `churn-prevention`): first win = a farmer receives a response to a listing, or a buyer gets a quote, within 48 h of signing up.

## WhatsApp outreach templates (edit, never send without Jay approving)

Buyer: "Hi [Name], it's Jay from AgriLoop in Jamaica. We're helping [restaurants/hotels] in [Kingston] find reliable local farms. Do you buy [crop] regularly? I'd love 10 minutes to hear how you source it now, not selling anything. Could I call you [day]?"

Farmer: "Hi [Name], Jay here. I'm building a free app that connects farmers in [parish] directly with buyers who post what they need. Is it OK if I ask how you sell your [crop] today? I can also list your farm for you at no cost."

## Output format

- **Where we are** (evidence only) and **the constraint** (one sentence).
- **This week's plan**: numbered actions with a number target (e.g. 20 messages, 5 calls).
- **What to measure** and how.
- **Needs verification**: market sizes ("roughly 200,000 farmers" in the docs is unverified), prices, regulations, buyer behaviour.

## Don'ts

- Don't present demo data as real traction (the docs mark seeded content `isDemoData`).
- Don't promise features marked "Architected" or "not available yet" in the roadmap.
- Don't gate the free tiers; the premium strategy forbids it.
- Ask Jay once (at the end of the session) for anything missing: current user counts, who the first buyers are, the live data-source setting.
