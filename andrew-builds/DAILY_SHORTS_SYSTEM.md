# Daily short-form system (3 per day across TikTok and YouTube Shorts)

Goal: three short videos a day without depending on the weekly documentary, **and without inventing activity to hit the number.**
If only one thing really happened today, publish one (or none). A consistent *honest* feed beats a full one with filler.

## Where ideas come from (all real)
| Source | What it gives | How |
|---|---|---|
| The app's activity log | messages sent, replies, lost-deal reasons, follow-ups cleared, meetings, proposals, playbook runs | `DATABASE_URL=... python3 andrew-builds/tools/suggest_content.py --days 1 --repo <repo>` lists up to 3 ideas, each with its evidence. With no activity it prints "none" |
| Git history | what you changed in the tool and why | the same command with `--repo` |
| Your own notes | a mistake, a reflection, a question from a comment | you decide; keep it true |

## The three daily slots
1. **Work** (what I did): outreach/lesson/result from the activity log.
2. **Build** (what I changed in the tool): a feature working on screen, with the problem it solves.
3. **Reflect or teach** (one useful idea): a mistake, a small tutorial (e.g. how a follow-up date changes behaviour), or a founder reflection.
If a slot has no real material today, skip it.

## 25-minute routine
1. Run the suggester (1 min). Pick the best idea or ignore it.
2. Record a 15-30 s screen capture of the real thing (names hidden) and a one-take voiceover (10 min).
3. Add it to `editing-project/shorts_<N>.json` (copy a short, change title/narration/clips) and run `tools/produce.py short <id>` (5 min).
4. Run `tools/qa.py`, watch it once with sound, publish yourself (9 min).

## Templates and rules
- Template: `templates/SHORT_EXTRACTION_TEMPLATE.md`. One idea per short; hook in 1-2 s; 20-45 s; captions on.
- Demo data is always labelled; real footage always hides names; nothing from a private conversation without permission.
- Never show revenue that Treasury has not verified.
- Track results in `templates/PERFORMANCE_TRACKING_TEMPLATE.md`. Change one thing at a time.
