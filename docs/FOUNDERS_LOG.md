# Founder's Log

The record of zero to wherever this goes. Written as it happens, by whichever of us did the writing.
Not a sanitized highlight reel — the misses are in here too, because that's the only way this log
is worth anything to either of us later.

---

## 25 Oct 2026 — Day zero, for real this time

Started from nothing: no code, no database, no revenue, a public wallet address and a master spec.
Built the whole machine in one stretch: Scout (finds work), Operator (drafts it, never submits it),
Treasury (verifies money actually moved, never touches it), a dashboard, an owner-only login, a
Postgres database on Neon, hosting on Vercel, a Claude connector so any chat can ask "what needs me,"
and a local app that's the same system running on your own machine.

**What's real right now:** $0 verified revenue. 78 opportunities found, 0 fully auto-qualified -
most of today's best leads (Superteam Earn, $500-$6,000 range) are marked human-only by their
sponsors, so they need you to do the work personally, not the agents. One $50 listing is below the
floor. That's the honest state of the board.

**What's working:** the whole pipeline runs with zero paid services switched on - no Claude key, no
Twilio, nothing. Rule-based scoring alone found real, legitimate opportunities and correctly refused
to touch the junk (spam bounties, token-promo schemes) without being told how.

**What's not decided yet:** whether BuildFlow (the contractor SaaS, stuck on a Firebase Storage
toggle and a billing decision) or hand-to-hand bounty/freelance work gets the push first. Scout
found the leads; which one you chase is still yours to call.

**The deal going forward:** I find it, draft it, chase it down, and bring it to you the moment it's
ready to close - nothing left for you to do but say yes and press submit yourself. I never sign,
pay, or submit under your name. That line doesn't move. Everything else does.

---

## 26 Oct 2026 — What the 25th actually taught us

The 25th wasn't day zero, it turned out — it was the day the machine ran long enough to show us
where it was actually lying to itself. Here's what broke, what we learned, and what changes today
because of it.

**The biggest lesson: a safety filter nobody can see working is the same as no filter.** Off-skill
filtering looked like it worked in every test we wrote — right up until the live board had 121
"qualified" opportunities, and one of them was a massage therapy gig. The bug: it was scanning the
full job description, and a generic word like "growth" or "process" shows up in almost any
paragraph. The filter was real, tested, and still useless in production, because the test cases
were too clean to catch what a real messy job description looks like. Lesson: test with the ugly
real data, not the tidy example.

**Second lesson: a safe default can quietly become a bottleneck.** Operator processed 3 tasks per
run as a conservative starting cap. Nobody revisited it as the backlog grew to 121. At that rate it
would've taken ten days to work through what one afternoon produced. Caution that never gets
re-checked against the real numbers isn't caution, it's just a stall nobody's watching.

**Third lesson: "it's connected" doesn't mean "it's correct."** Three separate times today — PayPal
sandbox, PayPal live, Gmail — a credential copied from a screenshot was subtly wrong (one character:
`l` vs `I`, a truncated secret, a code already used) and failed silently or with a generic error.
Every one of those got caught only because we tested the exact credential directly against the real
API before saving it anywhere. That's now the standing rule for every integration, not a one-off.

**Fourth: cold volume isn't a strategy, it's a number that looks like one.** 121 "qualified" leads
and $0 revenue in the same sentence is the whole story. A cleaner, correctly-filtered Freelancer.com
feed is still a cold channel with a sub-5% reply rate for an account with no reviews. More filtered
junk is still junk, just tidier. The fix isn't a better filter on a channel that doesn't convert —
it's a different channel.

**What changed today because of those lessons:**
- The off-skill filter now reads titles, not descriptions — tested against real listings, not
  synthetic ones.
- Operator's per-run cap went from 3 to 40; the backlog clears in one pass, not two weeks.
- A new filter catches commission-only "partner" roles — the ones that read like real jobs but are
  actually unpaid-unless-you-sell schemes.
- Operator can now send an approved draft itself, by email, once you've personally signed off on
  it — outreach and job-submission emails both. That line still doesn't move: nothing sends without
  your approval first, and it still never touches a platform login or signs anything.
- We tried Clay (a real B2B lead database, not scraping) as the "personal agent" lead source. It's
  built for mid-market companies with a LinkedIn presence; it doesn't reach small Jamaican trades
  businesses at all. Worth knowing now instead of three weeks from now: for this specific target
  market, warm outreach has to start with businesses you already know, not a database search.

**The challenge, stated plainly: $10k in November.** Honest odds assessment, not hype — the system
has found real, correctly-priced work today for the first time since launch, but $0 has been
verified so far and the proven path (warm outreach, not cold bidding) is tested in theory, not yet
in results. $10k in 30 days means roughly 5-10 real closed jobs or one real BuildFlow client cohort,
depending on mix. That's a stretch target, not a projection. We're tracking it starting today.

**Today's job:** approve/send the 3 real Remotive leads already waiting, pick 10-15 real contacts
you know personally or by reputation (not a cold database) for the first warm-outreach test, and
watch the reply rate. That's the actual experiment this challenge runs on.

---
<!-- Next entry goes above this line. Keep entries dated, honest, and short enough to actually read later. -->
