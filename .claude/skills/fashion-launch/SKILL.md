---
name: fashion-launch
description: >-
  Takes a fashion e-commerce brand from research to first sale on a near-zero budget: niche and
  product research, demand validation before buying stock, brand identity, Shopify store, product
  pages, short-form content and UGC scripts, small paid-ad tests, email/SMS/WhatsApp retention, and
  margin and inventory maths. Use when Jay starts, plans or troubleshoots the fashion brand.
---

# Fashion launch (research to first sale, near-zero budget)

Goal (priority 2): a fashion brand with real sales. Do the work and teach Jay why, in plain language.

## Ground truth and open questions

From `docs/master/HANDOFF.md` (2026-10-28): **no fashion repo exists yet.** The two storefronts found are not fashion: `Kadeform-` (a Shopify/Dawn theme for the single hero product FlexBack Pro, with a reusable `kadeform-*` section library) and `NF-Fragrance-` (static site, five colognes). Jay has not yet said which one is "the brand" or what the fashion concept is. **Ask Jay once, at the end**: niche, target customer, budget in USD, who fulfils (self, supplier, print-on-demand), and whether to reuse the Kadeform theme sections. Until answered, treat everything below as a template, not a plan.

## The principle (teach this)

**Sell first, stock later.** The biggest cash trap in fashion is buying inventory (sizes x colours x styles) for a guess. With little cash, prove demand with something cheap, then spend. Order of spend: attention (free) -> pre-orders/waitlist (free) -> sample (small) -> small batch or print-on-demand (medium) -> ads (only when organic proves a product converts).

## Gated stages (do not skip a gate)

| # | Stage | Do | Gate to pass |
|---|---|---|---|
| 0 | Customer + niche | Choose one customer (age, place, style, occasion) and one problem ("nothing fits / nothing suits Caribbean weather / nothing for this subculture"). Use `beachhead-segment`, `customer-research`. | You can name 20 real people who fit and where they hang out |
| 1 | Research | Profile 10 competitors (`competitor-profiling`): price points, hero products, reviews, ad angles. Look for repeated complaints in reviews (the gap). Check trend durability, not just virality. | One clear gap and one hero product idea, with a target price |
| 2 | Unit economics on paper | Landed cost (product + shipping + duties + packaging) vs price; see margin maths below. | Gross margin after payment fees and a returns allowance is healthy enough to fund ads |
| 3 | Brand | Name, voice, 3 colours, logo-lite, one-line promise (`product-marketing`, `frontend-design`; check name/handle/domain availability and any trademark conflict yourself). | Brand page + voice guide in one document |
| 4 | Demand test | Mockups or samples; a waitlist/pre-order page, a WhatsApp catalogue, or an Instagram/TikTok post series. Use `social`, `video`, `influencer-marketing` (UGC, micro-creators, gifting). | Target (set it first): e.g. 100 waitlist sign-ups or 10 pre-orders from organic reach |
| 5 | Store | Shopify (a paid platform; use the trial wisely), reuse proven sections from `Kadeform-`, product pages via `copywriting` + `cro`. Cheaper pre-launch alternative: payment links + WhatsApp catalogue. | Checkout tested end to end with a real small payment |
| 6 | First sales | Sell the first 10 to people you reach personally, collect photos/reviews (UGC). | 10 paid orders and 3 customer photos/reviews |
| 7 | Paid test | Only now: small daily-budget tests with 3-5 hooks (`ads`, `ad-creative`). | Pre-decided kill/scale rule below |
| 8 | Retention | Welcome + abandoned-cart + post-purchase flows (`emails`, `sms` for WhatsApp/SMS), plus a simple "share with a friend" ask in the post-purchase email. | Repeat purchase rate tracked from order 1 |

## Margin and inventory maths (write the numbers down; mark unknowns UNKNOWN)

- **Landed cost** = unit cost + inbound shipping + customs/duties + packaging + (sample/QC share).
- **Contribution margin per order** = price - landed cost - payment fees - outbound shipping - returns allowance - ad cost per order (CAC).
- **Break-even ROAS** = price / contribution margin before ads. If your blended ROAS is below this, ads lose money.
- A common rule of thumb is pricing at roughly 2.5-3x landed cost; it is a *heuristic to test* against your actual fees, returns and CAC, not a law.
- **Inventory**: start with the fewest SKUs, order the minimum quantity that gets an acceptable unit price, track sell-through weekly, never reorder until a style sells through at full price.
- Cash cycle: note supplier lead time and time-to-payout so you do not fund growth with money you do not have.

## Short-form content (the free engine)

Hooks to test (3 per product): problem-first ("Tired of X?"), result-first (outfit transformation), social-proof, behind-the-scenes (making/sourcing), trend-remix. A script = Hook (0-3 s) -> Proof/Demo -> Offer + one CTA ("comment SIZE / tap the link"). Batch-shoot 10 clips in one session; post daily; keep a log of hook, views, 3-second hold, saves, link clicks, sales. UGC: gift to micro-creators for content rights; get written permission to reuse.

## Paid ads: rules before spending

Decide in advance: test budget cap, number of creatives, how many days, **kill rule** (e.g. spend of 2x break-even CPA with no purchase), **scale rule** (consistent ROAS above break-even over several days). Never move money out of rent/food/tax money into ads. Tracking must work before any spend (`ads` skill's audit guardrails).

## Jamaica-specific items to verify (don't assume)

Payment options and payout availability for a Jamaica-based Shopify store (Stripe is unavailable per the BuildFlow notes; check Shopify Payments, PayPal and local gateways), shipping and customs costs, JMD vs USD pricing, delivery coverage, and sole-trader/GCT/registration obligations. Mark each "verify with provider/accountant".

## Output format

Current stage and which gate is next; this week's 5 actions; numbers (unit economics table with UNKNOWNs); what to measure; **needs verification** list.
