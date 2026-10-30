---
name: buildflow-growth
description: Go-to-market for BuildFlow, Jay's SaaS for contractors and construction professionals, plus the planned health-professional version built with an industry partner on revenue share. Use for signing the first founding customers, pricing tests, demos and objection handling, onboarding, retention, positioning against competitors, and writing or modelling the partnership / revenue-share pitch.
---

# BuildFlow growth

Goal: **first paying customers, then recurring revenue.** Do the work and teach Jay why, in plain language.

## Ground truth (verify, don't assume)

Read `docs/strategy/BUILDFLOW_LAUNCH_PLAN.md`, `docs/strategy/OWNER_PROFILE.md` and `docs/master/HANDOFF.md` in this repo first. As of 2026-10-30 they say:
- Live beta at buildflow-app-beta.vercel.app: customer and project management for contractors plus a public profile customers can discover. **$50/month incl. 1 user, +$20 per extra user, 14-day trial** (an *untested* price, not validated).
- Its own readiness report says **NOT READY**. P0 blockers: Firebase Storage not enabled (uploads fail), billing is a stub (Stripe is not available in Jamaica), legal pages are placeholders, Vercel must be on Pro before charging.
- Plan: sign **10 founding contractors** (free 60 days for feedback, job photos, a testimonial), bill manually by bank transfer or PayPal at first, then automate.
- Jay has **no warm contractor contacts to interview right now**, so lead generation is part of the job.
- Competitor to study: ClickAway (Jamaican matching app; "about 2,800 beta users" is a reported, unverified figure).
- Adjacent agency offer: "Never Miss a Job" (missed-call text-back, intake, quote follow-up, review request) at roughly $750-1,500 setup + $250-497/month. A **hypothesis to validate**, not a price list.

Do not tell Jay BuildFlow is ready to charge until the P0 items are done. Say which are open.

## Version A: BuildFlow for construction

**Customer:** a solo contractor or small crew (builders, electricians, plumbers, roofers, landscapers, renovators) who loses jobs because leads, quotes and follow-ups live in WhatsApp and memory.

**Core promise (test it):** "Your leads are yours. One flat monthly price. Works from WhatsApp, built for the field." Do not repeat this until contractors confirm it matters.

Steps:
1. **Find contractors without warm contacts** (`prospecting`, `cold-email`, adapt to WhatsApp/calls): hardware stores and supplier counters, Facebook/WhatsApp trade groups, Instagram contractor pages, job sites, church and community networks, existing YardScale clients. Target 20 conversations/week.
2. **Discovery before pitching** (`interview-script`): the last job they lost, how quotes are sent and followed up, how they get paid, what tools they use, what they pay for today. Capture quotes (`summarize-interview`).
3. **Founding offer** (`hormozi-lens`, `offers`): done-for-you setup (Jay enters their first customers and builds their profile), a first win within 3 days, free 60 days, honest ask in return (feedback call, photos, testimonial). Cap it at 10 so the scarcity is real.
4. **Demo** (`sales-enablement`): show *their* business in the app, not a feature tour. Use CLOSER from `hormozi-lens`.
5. **Price test** (`pricing`): after they have used it, ask "would you pay $50/month, in USD or JMD? Would a cheaper solo tier help?" Record answers; decide with 10 data points, not 2.
6. **Onboard and retain** (`onboarding`, `customer-success-manager`, `churn-prevention`): activation = first customer added + first quote sent in week 1. Weekly WhatsApp check-in for the first month.
7. **Metrics** (`startup-metrics-framework`, `saas-metrics-coach`): founding contractors signed, activated %, quotes sent per contractor, paid conversion at day 60, MRR, churn.

## Version B: health-professional edition (partnership, revenue share)

Facts we have: the plan is an industry partnership with revenue share. Facts we do **not** have: who the partner is, the terms discussed, which professions (clinics, physiotherapists, dentists, therapists?), what data the product would hold. **Ask Jay once, at the end of the session**; do not guess.

Design guardrails (teach the reasoning):
- **Do not store clinical records in v1.** Scheduling, client contact details, invoices and reminders are far lower risk than patient records. Patient data triggers privacy law and professional-confidentiality duties. *Verify* the current Jamaican data-protection requirements (the Data Protection Act) and any professional-body rules with a qualified Jamaican lawyer before launch.
- Reuse the BuildFlow core (customers, projects -> appointments/cases, public profile, quotes -> invoices); change vocabulary, templates and onboarding, not the architecture.
- Don't make health or outcome claims in marketing.

Partnership / revenue-share pitch (use `partnerships-architect` and `channel-economics`; `scripts/revshare_modeler.py` in `partnerships-architect` models direct vs partner margins; run it with `--help` first, it uses stdlib only):

1. **What the partner brings**: access to professionals (distribution), credibility, maybe domain input. Classify the contribution: *referral* (introductions only), *reseller* (sells and supports), or *strategic* (co-builds). The share % should follow the depth of the contribution.
2. **What Jay brings**: the product, hosting, support, roadmap.
3. **Model before you negotiate**: per-customer revenue, cost to serve, support load, payment fees, partner cost of sale, break-even number of customers for each side. Leave unknowns as UNKNOWN. The modeler quotes industry-typical bands (e.g. referral about 5-10%, reseller about 20-35%); treat these as *starting points to verify*, not facts for Jamaica.
4. **Term sheet checklist** (a lawyer drafts the contract): what revenue is shared (net collected, not billed), % and how long per customer, exclusivity and territory, who owns customer data and the relationship, who handles support, minimums/targets, payment timing, audit rights, termination and what happens to existing customers, IP ownership, branding.
5. **The one-page pitch**: problem for their professionals -> what the product does in 3 bullets -> proposed split and why it is fair -> a 90-day pilot with 5-10 professionals and clear success numbers -> what you need from them this week.
6. **Pilot first**: propose a small, time-boxed pilot with agreed metrics before any long-term exclusivity.

## Output format

- Where we stand (evidence + open P0s), the single constraint, this week's actions with numeric targets.
- For pitches: a draft Jay can edit, never sent automatically.
- **Needs verification**: price points, competitor figures, legal and regulatory claims, partner economics.
