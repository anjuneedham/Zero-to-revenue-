# BUILDFlow Content Engine: reference notes (v1.0, 28 Oct 2026)

Condensed from the owner's master prompt. Full week-1 batch (14 storyboards) is in `docs/buildflow-content/engine-data.json`. The partner-facing page is `docs/buildflow-content/partner-playbook.html`.

## Goal
Organic user acquisition and product research. Platforms: YouTube Shorts, TikTok, Instagram Reels, Facebook Reels. 2 videos a day: 1 Builder, 1 Consumer. Every video targets ONE audience. Success is repeatable content-market fit, not 14 videos.

## Hierarchy
Audience problem, curiosity, value, BUILDFlow connection, CTA. Do not lead with the product (except build-in-public videos).

## Video formula
0-3s hook, 3-8s problem, 8-15s curiosity loop, 15-30s payoff, 30-40s BUILDFlow, 40-45s CTA. Lengths: 15-25s insight, 25-40s education, 40-60s story/demo. Curiosity must be real and relevant.

## Hook types
Direct target, problem, warning, curiosity, contrarian, specific scenario (most valuable). Examples in the JSON.

## Pillars
Builder: project management, customer management, getting more work, business operations, trust, education, build-in-public.
Consumer: finding trustworthy contractors, project management, avoiding bad contractors, construction education, empowerment, contractor discovery, build-in-public.

## 7-day loop
1 Project management, 2 Trust, 3 Discovery, 4 Communication, 5 Money/delays, 6 Checklist, 7 Build in public. Each day has a Builder and a Consumer video.

## Testing
One variable at a time: hook, opening visual, length, topic, CTA, presentation, curiosity mechanism, product placement. Rank metrics: retention, avg watch %, shares, saves, comments, profile visits, follows. Winner becomes a content family (5+ variations). Failure ladder: new hook, stronger first visual, shorter cut, new presentation, stronger curiosity loop, then deprioritise.

## Weekly process
20-30 topics scored /10 on audience relevance, pain, curiosity, visual, BUILDFlow relevance, shareability. Pick 14. Storyboard, film, publish on all four, collect analytics, find winners, make variations. Weekly report fields are in the JSON.

## Never
Fake testimonials, users, revenue or statistics. Invented features. Every video an ad. Logo-first intros. Generic motivation. Non-construction content. Overusing "AI".

## Product accuracy (as of 25 Oct 2026, see BUILDFLOW_LAUNCH_PLAN.md)
Exists in beta: customer and project management; public contractor profile. Everything else is "we're building / testing / working on". Billing is a stub. Not yet validated with real contractors. Each video carries a `check` field to verify against the live app before filming.

## Dashboard redo (later)
Use `engine-data.json` as the seed. Needed tables: videos (id, audience, day, pillar, hook, variable, hypothesis), posts (video_id, platform, posted_at, and the 14 tracking columns in `trackingColumns`), weekly_reports, families (winner_id, variations). Views: Week board with per-platform posted state (currently localStorage in the page), retention-first leaderboard, winner to family generator, weekly report. Shared state across the partners needs a real store, not localStorage.

## Open items for the owner
Partner terms (split, roles, account ownership) are deliberately left blank in the page. Agree them with both cousins before Day 1.
