# Where to look for $500+ work, and what to do about each (25 Oct 2026)

Scout enforces a **$500 floor** (`MIN_EXPECTED_PAYMENT_USD`, default 500) - except for a job that
reads as genuinely small and quick (title mentions fix/typo/small/config/etc, no more than 2 named
skills, nothing complex-sounding): those qualify under the floor too, since they cost almost no time.
A job that reads as hard (full rebuild, migration, "end to end", architecture, or 3+ named skills) must
clear the floor to qualify at all. Below the bar and not clearly a quick win goes to REVIEW_REQUIRED,
not auto-queued, so it still shows up for you to glance at.

## Wired into Scout (automatic, read-only)
| Source | What it is | Status |
|---|---|---|
| **Freelancer.com** | Public project-search API, no login. Real client-set budgets, bid counts. Fixed-price, $500+ only. | Added 25 Oct |
| **Remotive** | Public jobs API; filtered to its `contract`/`freelance` listings only (not the full-time roles). | Added 25 Oct |
| **Superteam Earn** | Vetted Web3 bounty listings, sponsor + deadline + entry count. | Built earlier; most listings are prize pools or human-only |
| **GitHub "bounty" label** | Open issues. Mostly spam; repo-reputation checked. | Built earlier; low yield |

**Checked and skipped:** OpenStreetMap Overpass (blocked in this sandbox), Nominatim (refuses automated
bulk use - its own anti-scraping policy), WeWorkRemotely RSS (almost entirely full-time salaried roles
with no structured pay field, a poor match for one-off paid work).

## Needs an account; Scout cannot read these (public API is closed or login-gated)
Pursue these yourself; I can draft proposals and track them once you're in.

| Marketplace | What it's for | What you do |
|---|---|---|
| **Upwork** | Largest general freelance market, fixed-price $500+ projects common | Create a profile, apply with proposals. Its public job feed/API was closed in 2024 |
| **Contra** | No-fee freelance marketplace, portfolio-first | Create a profile, list your BuildFlow/AI-automation work |
| **Braintrust** | Vetted network, client-paid fees (freelancer keeps 100%) | Apply, get vetted |
| **Toptal** | Vetted network, large projects | Apply; screening is extensive |
| **Codeable** | WordPress-specific, no platform fee to freelancers | Apply; favors experienced devs |
| **Gun.io** | Vetted developer network | Apply |
| **Arc.dev** | Remote developer marketplace | Apply |
| **PeoplePerHour** | UK-leaning general freelance market | Create a profile |
| **Webflow Experts / Partner directories** (Webflow, Framer) | Matches your website/funnel-building skill directly | Apply as an Expert/Partner |

## For BuildFlow-style local clients (not a job board — direct outreach)
- **Local contractors/trades** via the "Never Miss a Job" plan already in the Game plan page.
- **ClickAway** (Jamaican competitor) — study its listings for demand signals, not as a source to scrape.

## What I need from you to widen Scout automatically
1. **Confirm the $500 floor is right**, or tell me a different number.
2. **A GitHub token** (read-only, no scopes) raises the GitHub rate limit so more real search can run.
3. If you create a Freelancer.com account, a **logged-in session isn't needed** for discovery (the public
   API already works); but applying/bidding is manual and goes through the Operator's draft-and-approve flow.
4. Say which of the login-gated marketplaces above you actually want to join — I'll write the application
   profile text and proposal templates once you tell me.

## Outreach to businesses you find yourself (25 Oct update)
I tried to find an automated, public, bulk-safe source of contractor emails/phones for Jamaica.
None exists that is both reachable and consent-safe: OpenStreetMap's Overpass API is blocked in this
sandbox, and Nominatim refused the request (its own policy against unauthorized bulk/automated use -
exactly the kind of guardrail that exists for a reason). Scraping directory sites' HTML in bulk risks
their terms and gets domains blacklisted, so this system does not do it.

**What's built instead (Operator page, "Leads" panel):**
1. You paste a CSV of businesses you found yourself (`name,business,email,phone,notes`). Nothing is
   scraped; only this owner-supplied import writes to the leads table.
2. **Draft outreach** generates one personalized email per lead, with every specific claim (why you're
   reaching out, any example link, your contact details) left as `[OWNER TO FILL]` - it never invents one.
3. Each draft becomes a decision in your queue, same as a bounty submission: **Approve**, then **I sent
   it** once you've actually sent it yourself. Nothing sends automatically - this matches the policy rule
   that outreach always needs owner approval (`core/policy/policy.py`, `Action.SEND_OUTREACH`).

This is the structure; actual sending (SMTP/Gmail integration) isn't wired up yet, so "I sent it" means
you send it from your own email client using the draft. If you want one-click send from the dashboard,
that needs a connected email account and is a separate, larger piece of work.

## Payment calculator (25 Oct)
Treasury now has a general-purpose calculator - any amount, any asset you were actually paid in
(crypto or fiat), converted to USD or JMD. It is not tied to a specific job. Rates come from two
free, no-key public APIs (CoinGecko for crypto, open.er-api.com for fiat), fetched server-side and
cached for 5 minutes. This is reference only - it never counts as verified revenue on its own; that
still requires Treasury's on-chain verification (or an owner-confirmed stablecoin contract) as before.

## Off-ramping crypto to JMD cash (researched, not wired into the system)
No source gave a confirmed, current answer for "sell USDC, get JMD in a Jamaican bank" - worth
testing with a small amount before relying on any route:
- **Binance** is the most commonly cited exchange for Jamaican users (reported 0.10% maker/taker fees,
  bank transfer or card funding) but JMD P2P / direct Jamaican bank withdrawal isn't confirmed current.
- **Common route:** sell crypto for USD on an exchange, withdraw to a bank or Wise, then convert
  USD -> JMD locally (banks, or Wise's own conversion). A Jamaican user has reported this working via
  Wise for PayPal funds; the same likely applies to exchange withdrawals.
- **Yellow Card** (a common African off-ramp) does not support Jamaica/JMD - ruled out.
- **Not confirmed:** whether WiPay (your local card gateway) accepts crypto at all; it is a card
  gateway, not an exchange, so probably not a fit for this.

## Scout cleanup (25 Oct)
Every Scout run now removes opportunities that are clearly junk (a scam-level risk score, or a
gift-card/token-promotion/duplicated-title flag) and that nothing has touched yet (no task, no
payment). This runs automatically on every refresh - "Run Scout now" both finds new work and tidies
up the old junk in one click. Anything the Operator drafted or you approved is never deleted.
