# First 5 founding contractors: faceless short-video acquisition

Research note, 29 Oct 2026. This is the next main focus. The same content is live in the dashboard under Game plan > First 5 users, where the actions can be ticked off. Everything here is a hypothesis to test, not a forecast: no view or conversion numbers are known yet.

**Goal.** First 5 founding contractors using BuildFlow, free for 60 days in exchange for feedback, job photos and a testimonial (decided 29 Oct: free, not $10). Payment is a later step, so the success metric is five active contractors, not revenue. The engine is 2 faceless short videos a day that give value for a comment and ask for a short setup call.

**Thesis.** Every video does one job: trade something genuinely useful for a comment or DM, then move the person to a 15-minute setup call. No face, no phone camera: everything is built on a computer from screen recordings, text, stock or AI footage and a voiceover (or captions only).

## Decisions (29 Oct)
- **Offer:** Free for founding contractors (60 days), in return for feedback, job photos and a testimonial.
- **Platforms:** TikTok, YouTube Shorts, Facebook, Instagram. One edit exported to all four.
- **Audience:** Two sides: contractors and construction service professionals (the buyers), and consumers who want trustworthy people to hire (the demand that makes the profile worth having). Contractor-first: consumer videos point to contractors' public profiles, and each founding contractor shares their own link.
- **Editing:** Samsung Tab S9 FE only. Faceless formats need no camera: use the built-in screen recorder for demos, and stock or AI footage, text and captions for the rest, so camera quality does not matter.

## The 6-beat storyboard (every video)
| Beat | What goes on screen |
|---|---|
| 1 Hook (0-2s) | One line of on-screen text naming a contractor pain in their words, e.g. "You quoted 3 jobs this week. How many did you follow up?" |
| 2 Pain (2-6s) | Show the mess: a WhatsApp thread, a notebook, a lost invoice. Screenshot or stock b-roll. |
| 3 Turn (6-12s) | Show the fix: a screen recording of BuildFlow doing that exact task (quote, client list, job photos, profile link). |
| 4 Free thing (12-18s) | Name the giveaway: "I made a free quote follow-up script pack." Show it on screen. |
| 5 Ask (18-22s) | "Comment QUOTE and I'll send it." Keyword comment is the interaction that feeds the algorithm. |
| 6 Loop (last frame) | End on the first frame's text so it replays, which lifts watch time. |

## No-camera formats
| Format | How it works |
|---|---|
| Screen-record demo | BuildFlow on a laptop/emulator doing one job in under 15s. Fully camera-free. The proof format. |
| Text-on-screen story | Kinetic text over stock footage: "3 mistakes that cost contractors jobs". Quick to batch. |
| Before / after split | Left: paper and WhatsApp chaos. Right: the same job in BuildFlow. |
| Template reveal | Scroll through a free quote/invoice/checklist and offer it for a comment. |
| Myth or number | One stat or rule of thumb (how to price a job, deposit norms) as an animated slide. Mark any figure you cannot source as an estimate. |
| Customer-voice skit | Text-message style conversation: a customer asks for a quote at 9pm, contractor answers late. Two chat bubbles, no actor. |

## What we give away
| Offer | Why |
|---|---|
| Free quote follow-up script pack | WhatsApp message templates for quote follow-up, deposit and review requests. Cheapest to make, fits WhatsApp-first trade. |
| Free quote and invoice template | Simple PDF or sheet in JMD and USD. |
| Free job-photo checklist | What to photograph before, during and after a job. |
| Free profile setup | The call itself is the offer: "I'll set up your public profile and first quote with you in 15 minutes." |

## Funnel to track
| Stage | Action | Note |
|---|---|---|
| Views | Reach | Watch the 3-second hold and completion rate per format |
| Comments / DMs | Keyword comment or DM | Target and track per format; this is the real signal |
| Free thing sent | DM with the giveaway plus one question about their trade | Capture trade, parish, how they quote today |
| Call booked | 15-min setup call | Offer two time slots; use a booking link |
| Account set up | On the call, with them | Count only completed set-ups |


## The 10-day test
Run 10 days, 20 videos. Rotate the 6 formats evenly so each gets about 3 posts, hold the offer and CTA constant per 5-video block, and log views, comments, DMs and calls per video in one sheet. After day 10 keep the top 2 formats and drop the rest. Everything below is a planning assumption until the log says otherwise: expect most videos to do little, so judge on comments per 1,000 views and calls per 10 DMs, not on any single hit.

## Risks
- Free users still need a working app: Firebase Storage must be on before any setup call or photos fail. Billing does not block this.
- BuildFlow is not launch-ready (Storage, billing, legal are open). A call that ends in a broken upload loses the user. Fix Storage and decide billing first, or sell as a guided beta.
- Collecting names and numbers in DMs: have a one-line consent note and the legal pages in place.
- Platform rules on giveaways, automated DMs and AI footage differ; check each platform's current rules before using auto-reply tools.
- No view or conversion figures are known yet. Nothing here is a forecast.

## Open questions
- Which trade first (roofers, electricians, plumbers, general builders)? One trade makes the hooks sharper.
- Voiceover (your voice, no face) or captions only?
- Consumer-side giveaway: e.g. a free checklist for hiring a contractor safely. Worth doing once 2-3 contractor profiles are live.

## Actions
- [P0] (owner) **Turn on Firebase Storage**: The only blocker for free founding users. Billing is not needed yet.
- [P0] (agent) **Build the first free giveaway**: Quote follow-up WhatsApp script pack as a PDF in JMD/USD context. Agent drafts, you review.
- [P1] (agent) **Write 20 storyboards from the 6-beat template**: Scene by scene: on-screen text, visual source, voiceover line, CTA keyword. Rotated across the 6 formats for the 10-day test.
- [P1] (owner) **Pick the no-camera toolchain**: Tab S9 FE: built-in screen recorder for demos plus CapCut or Descript for editing. Stock footage and captions or voiceover. No camera needed.
- [P1] (owner) **Set up a 15-minute booking link and a keyword-to-DM flow**: Booking page with a buffer, and a saved DM reply that sends the giveaway and the link.
- [P1] (both) **Create the per-video log**: One row per video: format, hook, views, comments, DMs, calls booked, set-ups, paid. Can live in the dashboard later.
- [P2] (owner) **Post 2 a day for 10 days, then review**: Keep the top 2 formats, cut the rest, write what changed in the Founders Log.
- [P1] (both) **Make the founding trial 60 days**: BuildFlow currently creates a 14-day trial for every business (onboarding.ts). For founding contractors it needs 60, as a code change in the BuildFlow repo.
- [P1] (owner) **Pick the first trade to target**: One trade for the first 10 days so the hooks and DM script stay specific.
