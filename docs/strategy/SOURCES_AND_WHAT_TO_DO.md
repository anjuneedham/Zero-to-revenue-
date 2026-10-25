# Where to look for $500+ work, and what to do about each (25 Oct 2026)

Scout now enforces: **$500 floor** for ordinary jobs; jobs that read as complex (full rebuilds,
migrations, "end to end", architecture, or more than 2 named skills) need **$1,000+** instead of being
let in cheap. Set with `MIN_EXPECTED_PAYMENT_USD` (default 500). Below the bar and not clearly worth it
goes to REVIEW_REQUIRED, not auto-queued.

## Wired into Scout (automatic, read-only)
| Source | What it is | Status |
|---|---|---|
| **Freelancer.com** | Public project-search API, no login. Real client-set budgets, bid counts. Fixed-price, $500+ only. | Added 25 Oct |
| **Superteam Earn** | Vetted Web3 bounty listings, sponsor + deadline + entry count. | Built earlier; most listings are prize pools or human-only |
| **GitHub "bounty" label** | Open issues. Mostly spam; repo-reputation checked. | Built earlier; low yield |

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
