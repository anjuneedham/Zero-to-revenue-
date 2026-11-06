# HANDOFF REPORT: Bootstrapper Experiment, Episode 001

Written 6 Nov 2026. Everything below was run or inspected in this session; anything not done is said plainly.
Nothing was published, sent, or contacted. No outreach was made. No production system was touched or deployed.

## Read this first: three things only you can resolve
1. **Which offer is "the business"?** The brief does not say. The repos point to **BuildFlow** (contractor SaaS, Jamaica) and service tiers. I wrote the script around "[FILL: the offer]" instead of guessing.
2. **I cannot see your real outreach.** The prospect records live in your production database, which this session cannot reach. `project-documentation/OUTREACH_STATUS.md` separates confirmed, recorded, missing and assumed. I did not read your mailbox.
3. **No rendered file is final**, and none can be yet: they need your narration, your B footage, and your answers to 12 `[FILL]` placeholders.

---

## SECTION 1: SOFTWARE
**Audited:** four repos attached; only `Zero-to-revenue-` (Python + Postgres + vanilla-JS PWA, "Zero to Hero OS") is the outreach/revenue system. The others (YardScale site, Agriloop x2) were not used for the product. Full audit: `project-documentation/CURRENT_STATE_AUDIT.md`, `TECHNICAL_ARCHITECTURE.md`, `PRODUCT_GAP_ANALYSIS.md`, `IMPLEMENTATION_PLAN.md`.

**Built (additive; existing features untouched):**
- Prospect pipeline on the existing `leads` table: 11 active stages, 6 closed outcomes, 2 parked; only a name is required.
- Outreach execution: prepare, record sent (channel + approach label), follow-up scheduling, response, meeting, proposal, won/lost, with backdating support.
- **12 editable playbooks** (all required fields), duplicate/edit/add/remove/reorder steps, archive, run on a prospect with saved progress, past runs reviewable; runs snapshot their steps.
- **Today** command centre: configurable daily targets, follow-ups, tasks, attention list, opportunities, meetings, recent activity, rule-based next actions, recorded daily review, timezone-aware.
- **Append-only activity log** (database-enforced) with per-prospect timeline, a **playback stepper** (a review of records, labelled as such, not a video), and a business-wide feed.
- **Insights:** all requested counts, conversion shown as counts (percentages only at n >= 30), time between stages, recorded revenue labelled *owner-recorded, not verified*, and a Learning section that keeps **facts / hypotheses / rule-based suggestions** visibly separate (no AI claims; none exists).
- Fix to an existing bug: request bodies were read up to 4 KB even where a route allows 200 KB (the CSV import).

**Tested (executed):** 25 new unit/API tests (real Postgres, real auth), 25-check browser journey covering all 15 required steps, migration on a populated database, whole suite 261 run / 260 pass. **1 failure is pre-existing** (a Scout test fixture whose listing deadline, 5 Nov 2026, has passed; unrelated). Details, incl. defects found and fixed along the way, in `project-documentation/PRODUCT_TEST_REPORT.md`.

**Incomplete / not done:** not deployed (needs your go-ahead; migration 007 runs on first start); not tested on Neon, Vercel, a real Samsung tablet, Firefox/Safari, screen readers, or with large data; no bulk import for back-filling earlier outreach; sales data not in the MCP connector.

## SECTION 2: DOCUMENTARY
- **Title:** *I'm Building a Business From Scratch (And Building the Software to Run It)* (alt: *Can I Build a Business Using Software I'm Building Myself?*)
- **Script:** `episode-001/EPISODE_001_MASTER_SCRIPT.md`: every spoken word, 7 scenes, 1,497 own words + 12 placeholders. Every factual line is traced to a source in the claims table; no revenue, customer, reply or result is claimed.
- **Runtime (honest):** estimated ~10:20 on own words alone and ~11:20 with your placeholders answered. **The robot proof measures 9:30**, which **fails the 10:00 gate** because each placeholder is only a short pause in it. Whether the real recording clears 10:00 is unknown until you record; the QA gate will tell you. Do not pad if short: add a real example (Scene 3 or 5).
- **Voiceover sections:** `episode-001/scripts/VOICEOVER_RECORDING_GUIDE.md`: `VO_001_HOOK` … `VO_007_CLOSING` (+ `VO_S1_START`, `VO_S2_TOOL`, `VO_S3_TWO`), with tone, pace, emphasis, pauses and the recording rules.
- **Screen recordings:** `EPISODE_001_SHOT_LIST.md` (30 shots): **18 captured by me** from the real app on DEMO data (landscape + portrait, DEMO DATA label burned in); **9 you must capture**; **3 need a real event**.
- **Editing:** a config-driven, cached, non-destructive FFmpeg pipeline (`andrew-builds/tools/produce.py`) with a central style config. Full-length proof assembled and checked (see Section 5). Music not chosen (none available, I did not synthesise any).

## SECTION 3: SHORTS
| | Concept | Script | Status |
|---|---|---|---|
| S1 | Start Before You're Ready | `scripts/SHORTS_001_SCRIPTS.md` | Proof built, all automated checks pass; waits for your VO + B02, B06 |
| S2 | Building the Tool I Need | same | Proof built, all automated checks pass; **no footage gaps**; waits for your VO |
| S3 | Two Businesses, One Experiment | same | Proof built, all automated checks pass; waits for your VO + B04, B06 |
All three: 9:16 1080x1920, 30 fps, 35-39 s, hooks in the first 1-2 s, captions burned in, ASSEMBLY PROOF watermark. Each has title, hook, narration, storyboard, on-screen text, recording requirements, captions, editing notes, CTA, TikTok description, YouTube Shorts title and cover text.

## SECTION 4: YOUR REQUIRED ACTIONS (in order)
1. Tell me the **offer and audience**, and whether to **back-fill** earlier outreach or treat tracking as starting today.
2. Decide what you will say at each of the **12 `[FILL]/[RECORD]`** spots (or record freely and caption from a transcript).
3. **Record the narration** (7 + 3 WAV files, exact names in the guide).
4. **Capture the 9 B clips** per the Samsung checklist (names, numbers, emails, handles hidden).
5. **Pick a licensed music track** (optional) and **take your thumbnail photo**.
6. Run `produce.py` then `qa.py`, **watch the result with sound**, and send me notes.
7. **Publish yourself.** Rotate the credentials that were pasted into chat in earlier sessions (listed in the 26 Oct audit).

## SECTION 5: PRODUCTION STATUS
| Item | Status |
|---|---|
| Software audit | COMPLETED AND VERIFIED |
| Sales system (build + tests) | COMPLETED AND VERIFIED (local; not deployed) |
| Deployment to Vercel/Neon | NOT STARTED (needs your authorization) |
| Outreach status | WAITING FOR MY INPUT |
| Script | READY FOR REVIEW (placeholders by design) |
| Shot list and recording guide | READY FOR REVIEW |
| Footage A (18) | COMPLETED AND VERIFIED (frames inspected; DEMO data) |
| Footage B (9) / C (3) | WAITING FOR MY INPUT / WAITING FOR A REAL EVENT |
| Voiceover | WAITING FOR MY INPUT |
| Long-form edit | IN PROGRESS: proof only, not final |
| Shorts edits | IN PROGRESS: proofs only, not final |
| Captions | IN PROGRESS (timing is estimated until you provide a transcript) |
| Thumbnails | WAITING FOR MY INPUT (drafts built; need your photo) |
| YouTube / TikTok packages | READY FOR REVIEW |
| Export | BLOCKED (VO, B footage, confirmed facts) |
| Episode 002 framework | READY FOR REVIEW (scaffold builds and passes the project check) |

## SECTION 6: NEXT EPISODE
`episode-002/EPISODE_002_PLAN.md` gives a decision rule tied to what actually happens: 10+ real messages logged → "I contacted N real people, here's what the pipeline says"; fewer → "My first week of real outreach"; none → an honest "why I haven't sent it yet" episode ending in a real send; a reply or call leads. A payment is only a story once Treasury verifies it. `tools/suggest_content.py` proposes daily Shorts from recorded activity only, and says "none" when nothing happened. Scaffold more with `tools/new_episode.py`.

## Where things are
`/home/user/Zero-to-revenue-/` on branch `ccr-e319a82c-wm4cgs`: `project-documentation/`, `core/sales/`, `dashboard/sales_api.py`, `dashboard/static/js/{sales,playbooks,insights}.js`, `database/migrations/007_sales_os.sql`, `tests/`, and `andrew-builds/` (media is git-ignored; re-create with the tools).
