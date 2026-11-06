# Product Test Report

Executed 6 Nov 2026 against a **local** server and a **throwaway local Postgres 16** (not Neon, not Vercel). All records used were
clearly labelled test data. Nothing was run against production. Each result below was observed in this session.

## Summary
| | Count |
|---|---|
| Unit/API tests (new, `tests/unit/test_sales.py`) | 25 run, 25 passed |
| Whole repo suite | 261 run, 260 passed, **1 failed (pre-existing, unrelated)** (baseline before this work: 236 run, 235 passed, same 1 failure) |
| Browser journey (`tests/e2e/journey.js`, Chromium via Playwright) | 25 run, 25 passed |
| Migration 007 on a database already holding leads | passed, idempotent (applied once, second run applied nothing) |

## PASSED (executed)
**Browser journey, run on a fresh database:**

| ID | Check | Result |
|---|---|---|
| E00 | Today page loads with a clear empty state | PASSED |
| E00b | Add form validates: empty submit shows an error | PASSED |
| E01 | 1. Create a prospect (name only) | PASSED |
| E02 | 2. Edit prospect details (and validation) | PASSED |
| E03 | 3. Research then qualify the prospect | PASSED |
| E04 | 4+5. Assign a playbook and complete a step | PASSED |
| E05 | 6+7. Record outreach and schedule a follow-up | PASSED |
| E06 | 8. Complete the follow-up from Today | PASSED |
| E07 | 9. Record a positive response | PASSED |
| E08 | 10. Move through the pipeline manually | PASSED |
| E09 | 11. Record a meeting | PASSED |
| E10 | 12. Record a proposal | PASSED |
| E11 | 13. Mark the prospect won | PASSED |
| E12 | 14. Timeline lists the whole journey; playback steps through it | PASSED |
| E13 | 15. Insights show performance with counts, no false precision | PASSED |
| E14 | Persistence after refresh | PASSED |
| E15 | Playbooks: duplicate, edit steps, reorder, archive | PASSED |
| E16 | Targets are configurable | PASSED |
| E17 | Deleting a prospect keeps its history | PASSED |
| E18 | Unknown prospect id shows a recovery path, not a crash | PASSED |
| L_tablet-landscape | Layout tablet-landscape 1280x800: no horizontal overflow on any page | PASSED |
| L_tablet-portrait | Layout tablet-portrait 800x1280: no horizontal overflow on any page | PASSED |
| L_phone | Layout phone 390x844: no horizontal overflow on any page | PASSED |
| A11Y | Accessibility basics: every field labelled, buttons named, one h1, focus visible | PASSED |
| ERR | No JavaScript errors or server 5xx during the whole run | PASSED |

**Unit/API tests (through the real HTTP handler with real owner auth):** full 15-step journey; auth required on every route (401 with no/bad
token); oversize body rejected; validation messages (empty prospect, bad email, negative value, duplicate email, bad stage, bad channel, bad/impossible
dates, empty research, outcome needing a date, future `occurred_at`); closing outcomes and reopen; not-qualified cleans up tasks; history cannot be
updated, deleted or truncated (database triggers); edits create events and never rewrite old ones; personal data not copied into the log; back-fill
keeps recorded and occurred times separate; earlier-stage work never moves a prospect backwards; deleting a prospect keeps history; seed idempotent and
never overwrites edits; all 12 built-in playbooks have every required field; duplicate/edit/reorder/add/remove steps, archive; run snapshot survives
playbook edits; progress persists; completing all steps completes the run and suggests the next; completing a task completes its step; abandon records
progress; empty states; due/overdue; configurable targets (0 = off, bad values rejected); back-filled work does not count toward today; daily review is a
recorded event; **no percentages below n=30 and no hypotheses below 5 prospects**; timezone setting.
A mutation check was run: loosening the sample threshold made the relevant test fail, then the code was restored.

**Defects found by testing and fixed during this work:** (1) recording a meeting as *held* left its *booked* task open and overdue (found while seeding demo data; fixed, test added); (2) legacy leads with status SENT would have appeared as stage "identified" (migration now maps legacy status to a stage and logs a labelled system event, no contact date claimed); (3) empty form-error rows added dead space and half-width tables clipped (CSS fixed).

**A caveat on my own process:** the first browser run and the first demo-footage capture ran against a server process that had not picked up the latest code (my reset script's `pkill` pattern did not match). Both were rerun after the script was fixed, and all results in this report are from the rerun on current code.

**Persistence after refresh:** passed (E14). **Mobile/tablet layout:** passed for no horizontal overflow on Today, Pipeline, Playbooks, a playbook
editor and Insights at 1280x800, 800x1280 and 390x844 **in emulated Chromium viewports**.
**Accessibility basics (automated):** every visible form field has a label, every button has a name, exactly one visible `h1`, `lang` set (A11Y).
**Console/network:** no JavaScript errors and no HTTP 5xx during the run (ERR).
**Visual review:** screenshots of Today (tablet portrait), a won prospect, timeline playback and Insights were opened and read. One layout problem
was found and fixed (an empty error row adding a gap in forms; tables clipped in half-width cards).

## FAILED
| What | Detail |
|---|---|
| `tests.unit.test_scout...test_verified_sponsor_with_ai_allowed_qualifies_but_token_promo_and_unverified_do_not` | **Pre-existing**, fails identically on the untouched checkout. Cause confirmed: the fixture listing's deadline is 2026-11-05 and today is 2026-11-06, so it is now expired. Scout code is not modified by this work. |

## BLOCKED
| What | Why |
|---|---|
| Test against the real Neon database and the deployed Vercel app | No `DATABASE_URL` in this session, and deploying needs your authorization. |
| Real-device tablet check (Samsung Tab S9 FE+) | No device. Only emulated viewports were tested. |
| Back-fill/verification of real prospect records | The real records are not accessible (see OUTREACH_STATUS.md). |

## NOT TESTED
- Firefox and Safari (only Chromium).
- Screen reader behaviour (only automated label/name checks); keyboard-only operation beyond the playback and form controls exercised by the script.
- Colour-contrast measurement (visual review only; the existing theme was reused).
- Offline/service-worker behaviour of the new pages; installing the PWA.
- Performance with large data (hundreds of prospects, 20,000 events).
- Concurrent use from two devices.
- Dark theme of the new components (CSS uses existing variables; not looked at).
- The `/mcp` connector (sales data is not exposed there).
- Playwright `journey.js` is not part of the existing CI (the repo has no CI config); run it by hand (header of the file explains how).
