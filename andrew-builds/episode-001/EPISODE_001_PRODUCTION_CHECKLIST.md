# EPISODE 001: PRODUCTION CHECKLIST

Statuses are literal: `NOT STARTED` · `IN PROGRESS` · `WAITING FOR MY INPUT` · `READY FOR REVIEW` · `COMPLETED AND VERIFIED` · `BLOCKED`.
Nothing is marked COMPLETED AND VERIFIED unless it was actually done and checked. Last updated 6 Nov 2026.

## Pipeline
| # | Stage | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Idea | COMPLETED AND VERIFIED | Premise fixed by your brief |
| 2 | Story research | COMPLETED AND VERIFIED | `research/RESEARCH_NOTES.md`: facts drawn from the repos, each with its source |
| 3 | Fact collection | WAITING FOR MY INPUT | 12 `[FILL]/[RECORD]` placeholders; outreach records not accessible (OUTREACH_STATUS.md) |
| 4 | Story structure | COMPLETED AND VERIFIED | 7 scenes in `editing-project/episode_001.json` |
| 5 | Script | READY FOR REVIEW | All words written; 1,497 own words; placeholders remain by design |
| 6 | Recording plan | READY FOR REVIEW | EPISODE_001_SHOT_LIST.md, scripts/VOICEOVER_RECORDING_GUIDE.md |
| 7 | Voiceover | WAITING FOR MY INPUT | 7 episode files + 3 short files to record (names in the guide). Robot guide tracks exist for timing tests only |
| 8 | Footage | IN PROGRESS | A (12 clips): captured · B (9 clips): WAITING FOR MY INPUT · C (3): WAITING FOR A REAL EVENT |
| 9 | Assembly | IN PROGRESS | Proof builds work end to end (see EXPORT_REPORT). Final needs your VO + B footage |
| 10 | Editing | IN PROGRESS | Style config, overlays, transitions done; music not chosen |
| 11 | Captions | IN PROGRESS | SRT/ASS generated with estimated timing; replace with a transcript of your real recording |
| 12 | Shorts | IN PROGRESS | 3 proofs built; each needs your VO and its B clips |
| 13 | Quality review | IN PROGRESS | Automated checks run on proofs; human review of the final cut still to do |
| 14 | Export | BLOCKED | Waiting on VO + footage + confirmed facts. Only `_PROOF` files exist |
| 15 | Publishing package | READY FOR REVIEW | YOUTUBE_PACKAGE.md, TIKTOK_LAUNCH_PACKAGE.md, thumbnails/THUMBNAIL_BRIEF.md |
| 16 | Performance review | NOT STARTED | After publishing; template in `../templates/` |

## Your actions, in order
1. **Confirm the offer and audience** (OUTREACH_STATUS.md, assumptions 1-4). It decides Scene 3 and the shorts.
2. **Back-fill your real prospects** into the app (or tell me to start tracking from today) so B01/B03/B05 show real numbers.
3. **Decide the placeholders.** Write what you will say for each `[FILL]`/`[RECORD]` in `editing-project/episode_001.json` (or record freely and caption from a transcript).
4. **Record the voiceover**, following `scripts/VOICEOVER_RECORDING_GUIDE.md`. Seven episode files, three short files. Save as WAV with the exact names.
5. **Capture the B footage** following the Recording checklist in EPISODE_001_SHOT_LIST.md (blur/hide all names).
6. **Choose a licensed music track** (optional) and set it in the style config.
7. **Run** `python3 andrew-builds/tools/produce.py episode` then `tools/qa.py`, and watch the result with sound.
8. **Take your photo** for the thumbnail PHOTO SLOT.
9. **Review the first cut** and send me notes. Then publish yourself. I will not publish, send outreach or contact anyone.

## Hard rules
- No publishing, outreach or contact without your explicit say-so.
- Original recordings are never overwritten (the pipeline only reads them).
- No real name, email, phone, handle or credential in any footage or file. `tools/qa.py project` scans the text files for secrets and personal emails.
- No revenue, customer, reply or result is stated unless you have verified it.
