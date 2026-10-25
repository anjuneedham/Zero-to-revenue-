# Investor thesis: where Zero-to-Revenue should play

## Unfair advantage already in hand
The owner's Vercel account already holds builds for trades and local businesses: `needhams-construction`,
`yardscale-digital` + funnel, `buildflow-app`, `theos-restaurant-platform`, `agriloop`. The owner can ship
web funnels for small operators. The agent system adds automation on top. Few people have both.

## Market: trades and home-service contractors (construction, landscaping, renovation)
**Pain point (one, specific):** leads leak between the first call and the signed quote. Owners are on site,
miss calls, reply hours later and send quotes days later. Every slow reply goes to the competitor who answered first.

**Why demand is high and supply low (hypotheses to validate in weeks 1-4, not facts):**
- Demand: contractors spend on ads and directories but rarely measure what happens after the phone rings.
- Supply: AI agencies sell generic chatbots; few implementers understand both trades workflows and automation.

## The offer: "Never Miss a Job"
1. Missed-call text-back within 60 seconds (SMS via Twilio, which we're already integrating).
2. A 24/7 intake form/chat that captures job type, address, photos and timing.
3. Quote follow-up sequence: day 1, 3 and 7 reminders, drafted by AI and approved by the contractor.
4. A review request after job completion.
5. A weekly report for the owner: leads in, response time, quotes sent, jobs won.
Pricing hypothesis: $1,500 setup + $400/month. Validate with real conversations before fixing it.

## Path to $100k in 12 months (target, not forecast)
| Months | Milestone | Revenue engine |
|---|---|---|
| 1-2 | Bounties/freelance keep cash flowing; 15 contractor interviews; 1 pilot at cost | Bounties + pilot |
| 3-4 | 4 paying clients | Setup fees + first retainers |
| 5-6 | 10 clients; case study with real numbers from the pilot | Retainers compound |
| 7-9 | 20 clients; referral deal with a trades supplier or accountant | Referrals |
| 10-12 | 30+ clients; subcontract setups | ~$12k MRR + setups |
Rough maths: ~40 setups x $1.5k = $60k, plus retainers building to ~$12k/month ≈ $40k over the year.

## How the agent system serves this
- **Scout:** besides bounties, finds contractors with weak response paths (public info only, no scraping
  behind logins) and ranks them; the owner decides who to contact.
- **Operator:** drafts outreach, proposals and onboarding docs; the owner approves and sends.
- **Treasury:** tracks setup fees and retainers as verified revenue; MRR on the dashboard.
- **Notifications:** the same Twilio integration becomes part of the product.

## Kill criteria (the investor's discipline)
- Fewer than 5 of 15 interviews confirm the pain by week 4: pivot within trades (e.g. invoicing/payment chasing).
- Pilot doesn't measurably improve response time within 30 days: fix delivery before selling more.
- Rules: no cold-call spam, follow SMS consent laws (opt-in, STOP handling), no fake reviews.
