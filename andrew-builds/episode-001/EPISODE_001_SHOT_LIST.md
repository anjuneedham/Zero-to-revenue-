# EPISODE 001: SHOT LIST

*Generated from `editing-project/shots.json`.* Shot IDs match the clips used in `episode_001.json` and `shorts_001.json`.

| Group | Meaning | Count |
|---|---|---|
| **A** | I (Claude) capture this, from the real app, on clearly fictional DEMO data. **Already captured** (see Asset Register) | 12 |
| **B** | **You** must capture this (your real data, your camera, your own apps) | 9 |
| **C** | Needs a real-world event. Never stage it | 3 |

Naming: `EP001_<shot>_<slug>_<YYYYMMDD>_v<nn>.<ext>`. Put B/C files in `screen-recordings/` (screen) or `raw-footage/` (camera). The engine finds them by the `EP001_<shot>_` prefix, so no config change is needed. If a clip is missing it renders as a visible FOOTAGE NEEDED slate.

## Recording checklist: Samsung Galaxy Tab S9 FE+ (follow in order)
1. Charge the tablet above 50% and plug it in if you will record for more than 10 minutes.
2. Open **Settings > Notifications > Do not disturb** and switch it on. Close every app except the one you are recording.
3. Turn off **Edge panels** and any floating bubbles. Hide the keyboard until you need it.
4. Swipe down twice to open the Quick panel and tap **Screen recorder**. Open its settings: set **Sound** to *No sound* (your voice-over is recorded separately), pick the **highest video quality offered** (usually 1080p), and switch on **Show taps and touches** so viewers can follow your actions.
5. Landscape footage (the documentary): hold the tablet sideways and **lock rotation** in Quick panel. Portrait footage (Shorts): hold it upright and lock rotation.
6. Open the app page for the shot *before* starting the recorder. Check the screen for anything private (names, numbers, emails, handles). If something private must stay on screen, use the app's Search view or crop it in the edit.
7. Tap Record, wait for the 3-2-1 countdown, then **do nothing for two seconds**. This gives the edit a clean start.
8. Perform the actions listed for that shot slowly and on purpose. One action at a time. Do not scroll back and forth. Hold still for 3 seconds on anything the viewer must read.
9. Stop with the red button or the status-bar chip. Wait two seconds first.
10. Play it back immediately. If a name or number slipped in, delete it and record again.
11. Rename it exactly as the shot list says and copy it to `screen-recordings/`. Never edit or overwrite the original.
12. Camera footage (B06, B07): film in daylight, phone held steady or propped, 1080p or 4K at 30 fps, 10-15 seconds per take. Keep mail, documents and other screens out of frame.
13. Never record anyone's face, voice, message or business without their permission.
14. If a shot needs real data that is not entered yet, enter it first. Back-filling earlier outreach is supported (see `project-documentation/OUTREACH_STATUS.md`).

---

## A. Footage I capture (done)

### Shot 1 · `A01` · today-empty

| | |
|---|---|
| **Scene** | VO_004_SOFTWARE |
| **Narrative purpose** | Show the starting point: an empty Today screen and the add-prospect form. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #today (empty database) |
| **Actions to perform** | 1. Let the page settle for 2s; 2. Move the pointer to the 'Add a prospect' card; 3. Type a fictional business name; 4. Click 'Add prospect' |
| **Must be visible** | Empty states with guidance text; Add-prospect form; Daily targets |
| **Must be hidden** | Nothing personal exists in the database |
| **Orientation / size** | landscape 1600x1000 |
| **Recommended length** | 25-35s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A01_today-empty_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 4, opening of the software section |

### Shot 2 · `A02` · prospect-create-edit

| | |
|---|---|
| **Scene** | VO_004_SOFTWARE / Short 1 |
| **Narrative purpose** | A prospect can be created with only a name and filled in later. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #pipeline then #prospect/<id> |
| **Actions to perform** | 1. Add a fictional business; 2. Open Details; 3. Enter industry, location, source, a deal value; 4. Save |
| **Must be visible** | Prospect header chips; Details form; Timeline entry 'Details updated' |
| **Must be hidden** | No real data; DEMO DATA label burned in |
| **Orientation / size** | landscape 1600x1000 |
| **Recommended length** | 40-55s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A02_prospect-create-edit_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Short 1 beat 3 |

### Shot 3 · `A03` · playbook-run

| | |
|---|---|
| **Scene** | VO_001_HOOK / VO_004_SOFTWARE / VO_005_EXECUTION |
| **Narrative purpose** | A playbook is an executable, step-by-step process with saved progress. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #prospect/<id> (Playbook card) |
| **Actions to perform** | 1. Choose 'D. Initial outreach'; 2. Start playbook; 3. Tick step 1, then 2; 4. Open 'Playbook guide' |
| **Must be visible** | Step list with notes; Progress '1 of 4 steps'; Example messages in the guide |
| **Must be hidden** | No real data |
| **Orientation / size** | landscape 1600x1000 |
| **Recommended length** | 40-55s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A03_playbook-run_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 5 and scene 4 |

### Shot 4 · `A04` · log-outreach-followup

| | |
|---|---|
| **Scene** | VO_005_EXECUTION / Short 1 |
| **Narrative purpose** | Recording a message and scheduling its follow-up in one step. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #prospect/<id> (Log message sent) |
| **Actions to perform** | 1. Click 'Log message sent'; 2. Choose channel, name the approach, paste fictional text; 3. Leave 'Follow up in (days)' at 3; 4. Record sent |
| **Must be visible** | Channel/approach fields; Timeline: message sent + follow-up scheduled |
| **Must be hidden** | Fictional text only |
| **Orientation / size** | landscape 1600x1000 |
| **Recommended length** | 40-55s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A04_log-outreach-followup_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 5, around 'set a follow-up date' |

### Shot 5 · `A05` · today-populated

| | |
|---|---|
| **Scene** | VO_001_HOOK / VO_004_SOFTWARE / VO_007_CLOSING |
| **Narrative purpose** | The Today command centre with real-looking structure: targets, follow-ups, attention list, recent activity. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #today (demo data loaded) |
| **Actions to perform** | 1. Slow scroll from targets to follow-ups due; 2. Pause on 'Needs attention'; 3. Pause on recent activity |
| **Must be visible** | Targets with progress; Follow-ups due and overdue; Rule-based recommendations |
| **Must be hidden** | All businesses are fictional 'DEMO' names |
| **Orientation / size** | landscape 1600x1000 |
| **Recommended length** | 35-50s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A05_today-populated_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 1 cold open; scene 4 |

### Shot 6 · `A06` · timeline-playback

| | |
|---|---|
| **Scene** | VO_004_SOFTWARE / VO_006_OPPORTUNITY / Short 2 |
| **Narrative purpose** | Reconstruct one prospect's journey event by event. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #prospect/<id> (Playback card) |
| **Actions to perform** | 1. Open a prospect with a full history; 2. Click Next four times; 3. Press Play and let it run; 4. Drag the slider back to the start |
| **Must be visible** | Stage track highlighting the current stage; Event details with 'Happened' and 'recorded' times |
| **Must be hidden** | Fictional names only |
| **Orientation / size** | landscape 1600x1000 |
| **Recommended length** | 35-50s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A06_timeline-playback_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 4 ('step through its history') |

### Shot 7 · `A07` · insights

| | |
|---|---|
| **Scene** | VO_001_HOOK / VO_004_SOFTWARE / VO_006_OPPORTUNITY / Short 2 |
| **Narrative purpose** | Honest reporting: counts first, no percentages from tiny samples, facts vs hypotheses. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #insights |
| **Actions to perform** | 1. Scroll from the counts to the Conversion table; 2. Pause on 'too few to read'; 3. Scroll to 'What you've learned' |
| **Must be visible** | Counts; 'too few to read' notes; Fact / Hypothesis / Suggestion badges |
| **Must be hidden** | Demo numbers only (labelled) |
| **Orientation / size** | landscape 1600x1000 |
| **Recommended length** | 35-50s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A07_insights_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 4 ('one of six, not seventeen percent') |

### Shot 8 · `A08` · playbook-editor

| | |
|---|---|
| **Scene** | VO_004_SOFTWARE / VO_006_OPPORTUNITY / Short 3 |
| **Narrative purpose** | Playbooks are editable and duplicable for different offers. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #playbooks then #playbook/<id> |
| **Actions to perform** | 1. Open 'E. Follow-up'; 2. Duplicate; 3. Add a step; 4. Move a step down; 5. Save new version |
| **Must be visible** | Step editor with Up/Down/Remove; 'Version 2' after saving |
| **Must be hidden** | No real data |
| **Orientation / size** | landscape 1600x1000 |
| **Recommended length** | 40-55s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A08_playbook-editor_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 4 and scene 6 |

### Shot 9 · `A09` · pipeline-populated

| | |
|---|---|
| **Scene** | VO_001_HOOK / VO_003_BUSINESS / VO_004_SOFTWARE / VO_006_OPPORTUNITY / Shorts |
| **Narrative purpose** | Every prospect sits at a clear stage. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #pipeline (demo data) |
| **Actions to perform** | 1. Pause on the stage chips; 2. Click 'Contacted'; 3. Click 'Closed'; 4. Open one prospect |
| **Must be visible** | Stage chips with counts; Prospect rows with follow-up pills |
| **Must be hidden** | Fictional names only |
| **Orientation / size** | landscape 1600x1000 |
| **Recommended length** | 30-45s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A09_pipeline-populated_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 1, 3, 4 |

### Shot 10 · `A10` · tablet-portrait-today

| | |
|---|---|
| **Scene** | Short 2 |
| **Narrative purpose** | The Today screen at tablet-portrait width for vertical video. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #today (demo data), viewport 810x1440 |
| **Actions to perform** | 1. Slow scroll from targets to follow-ups due; 2. Pause on 'Needs attention' |
| **Must be visible** | Targets, follow-ups, attention list |
| **Must be hidden** | Fictional names only |
| **Orientation / size** | portrait 810x1440 |
| **Recommended length** | 30-40s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A10_tablet-portrait-today_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Short 2 beats 1-2 |

### Shot 11 · `A11` · e2e-test-run

| | |
|---|---|
| **Scene** | VO_004_SOFTWARE |
| **Narrative purpose** | Proof that the journey was tested: the automated browser test driving the real app. |
| **Application** | Automated Playwright test against the local app |
| **Page** | whole app |
| **Actions to perform** | 1. (automatic) The 25-check journey runs |
| **Must be visible** | The app being driven through the full journey |
| **Must be hidden** | Fictional names only (prefix TEST) |
| **Orientation / size** | landscape 1280x800 |
| **Recommended length** | ~90s, use 6-10s excerpts |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A11_e2e-test-run_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 4 ('tested the whole journey') |

### Shot 12 · `A12` · portrait-empty-then-add

| | |
|---|---|
| **Scene** | Short 1 |
| **Narrative purpose** | Portrait hook: an empty Today screen, then the first prospect gets added. |
| **Application** | Zero-to-Revenue web app (Sales: Today / Pipeline / Playbooks / Insights), run locally |
| **Page** | #today (empty), viewport 810x1440 |
| **Actions to perform** | 1. Show empty state; 2. Type a fictional name into the add form; 3. Add prospect |
| **Must be visible** | Empty state; Add form |
| **Must be hidden** | Nothing personal |
| **Orientation / size** | portrait 810x1440 |
| **Recommended length** | 20-30s |
| **Can Claude capture it?** | yes, captured |
| **File name** | `EP001_A12_portrait-empty-then-add_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Short 1 opening |


## B. Footage you must capture

### Shot 13 · `B01` · real-pipeline

| | |
|---|---|
| **Scene** | VO_003_BUSINESS |
| **Narrative purpose** | Your real pipeline: the evidence behind 'I've started reaching out'. |
| **Application** | Zero-to-Revenue (your deployed or local app, real data) |
| **Page** | #pipeline |
| **Actions to perform** | 1. Back-fill your real prospects first (see OUTREACH_STATUS.md); 2. Open Pipeline, tap 'Active'; 3. Tap 'Contacted' to show who has been messaged; 4. Hold still 3s on each view |
| **Must be visible** | Stage chips and counts |
| **Must be hidden** | BLUR OR HIDE every business name, contact name, email, phone, handle (use 'Search' to avoid scrolling past names) |
| **Orientation / size** | landscape (tablet sideways) |
| **Recommended length** | 20-30s |
| **Can Claude capture it?** | NO. You must capture this |
| **File name** | `EP001_B01_real-pipeline_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 3 |

### Shot 14 · `B02` · real-outreach-compose

| | |
|---|---|
| **Scene** | VO_001_HOOK / VO_005_EXECUTION / Short 1 |
| **Narrative purpose** | The real moment of writing and sending a first message. |
| **Application** | Whichever app you really send from (WhatsApp, Instagram, email) |
| **Page** | Message composer |
| **Actions to perform** | 1. Start the recording before you open the app; 2. Write the real message at normal speed; 3. Send it; 4. Stop recording |
| **Must be visible** | Your typing, the send action |
| **Must be hidden** | Recipient name, number, handle and profile photo; hide notification shade; do not show the thread history |
| **Orientation / size** | portrait or landscape (portrait if it also feeds Shorts) |
| **Recommended length** | 20-40s |
| **Can Claude capture it?** | NO. You must capture this |
| **File name** | `EP001_B02_real-outreach-compose_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 1 and scene 5 ('pressing send') |

### Shot 15 · `B03` · real-today-morning

| | |
|---|---|
| **Scene** | VO_002_BACKGROUND / VO_005_EXECUTION / VO_007_CLOSING |
| **Narrative purpose** | Starting a real working day from the Today screen. |
| **Application** | Zero-to-Revenue (real data) |
| **Page** | #today |
| **Actions to perform** | 1. Open the app fresh; 2. Pause on targets and follow-ups due; 3. Tap one follow-up |
| **Must be visible** | Targets and what's due |
| **Must be hidden** | Business names (blur in edit or use the Search view) |
| **Orientation / size** | landscape |
| **Recommended length** | 25-40s |
| **Can Claude capture it?** | NO. You must capture this |
| **File name** | `EP001_B03_real-today-morning_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 5 and 7 |

### Shot 16 · `B04` · real-log-message

| | |
|---|---|
| **Scene** | VO_003_BUSINESS / VO_005_EXECUTION / Short 3 |
| **Narrative purpose** | Recording a real message and setting its follow-up date. |
| **Application** | Zero-to-Revenue (real data) |
| **Page** | #prospect/<id> > Log message sent |
| **Actions to perform** | 1. Open a real prospect; 2. Tap 'Log message sent'; 3. Pick channel and a short approach label; 4. Do not paste the full message on camera if it names anyone; 5. Leave follow-up at 3 days and record |
| **Must be visible** | Form fields, the follow-up being scheduled |
| **Must be hidden** | Business and contact names, message body if it names anyone |
| **Orientation / size** | landscape |
| **Recommended length** | 25-40s |
| **Can Claude capture it?** | NO. You must capture this |
| **File name** | `EP001_B04_real-log-message_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 5 |

### Shot 17 · `B05` · real-insights

| | |
|---|---|
| **Scene** | VO_003_BUSINESS / VO_005_EXECUTION |
| **Narrative purpose** | Your real numbers, whatever they are. |
| **Application** | Zero-to-Revenue (real data) |
| **Page** | #insights |
| **Actions to perform** | 1. Open Insights; 2. Pause on the counts for 4s; 3. Scroll to 'What you've learned' |
| **Must be visible** | Counts and honesty notes |
| **Must be hidden** | Nothing sensitive; names only appear in the business timeline at the bottom, so do not scroll there |
| **Orientation / size** | landscape |
| **Recommended length** | 20-30s |
| **Can Claude capture it?** | NO. You must capture this |
| **File name** | `EP001_B05_real-insights_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 3 status line |

### Shot 18 · `B06` · desk-broll

| | |
|---|---|
| **Scene** | VO_001_HOOK / VO_002_BACKGROUND / VO_007_CLOSING / Shorts |
| **Narrative purpose** | Who is building this and where. |
| **Application** | Camera (phone) |
| **Page** | n/a |
| **Actions to perform** | 1. Film your workspace in daylight; 2. Slow pan, 10s each: desk, hands on the tablet, screen in the background; 3. Optionally 10s to camera: 'I'm Andrew' |
| **Must be visible** | Your desk, the tablet |
| **Must be hidden** | Mail, documents, other screens, family, anything with addresses |
| **Orientation / size** | landscape 4K or 1080p, 30fps |
| **Recommended length** | 30-60s total |
| **Can Claude capture it?** | NO. You must capture this |
| **File name** | `EP001_B06_desk-broll_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scenes 1, 2, 7; Shorts 1 and 3 |

### Shot 19 · `B07` · tablet-hands

| | |
|---|---|
| **Scene** | VO_002_BACKGROUND / VO_006_OPPORTUNITY / VO_007_CLOSING |
| **Narrative purpose** | Hands-on-device texture for the product scenes. |
| **Application** | Camera (phone) |
| **Page** | n/a |
| **Actions to perform** | 1. Film your hands using the tablet, 15s; 2. Keep the screen angled away or showing only the app shell |
| **Must be visible** | Hands and device |
| **Must be hidden** | Screen content that shows names or messages |
| **Orientation / size** | landscape |
| **Recommended length** | 15-30s |
| **Can Claude capture it?** | NO. You must capture this |
| **File name** | `EP001_B07_tablet-hands_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scenes 2, 6, 7 |

### Shot 20 · `B08` · dev-environment

| | |
|---|---|
| **Scene** | VO_002_BACKGROUND |
| **Narrative purpose** | You actually building the software. |
| **Application** | Your editor / terminal / browser dev tools |
| **Page** | n/a |
| **Actions to perform** | 1. Record 30s of real work in the editor or terminal on the Zero-to-Revenue repo; 2. Run the tests once on camera |
| **Must be visible** | Code, test output |
| **Must be hidden** | ANY .env file, API keys, tokens, database URLs, secrets, private repo names you do not want public |
| **Orientation / size** | landscape |
| **Recommended length** | 30-60s |
| **Can Claude capture it?** | NO. You must capture this |
| **File name** | `EP001_B08_dev-environment_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 2 |

### Shot 21 · `B09` · real-today-portrait

| | |
|---|---|
| **Scene** | Shorts 1 and 2 (replaces A10 once real data exists) |
| **Narrative purpose** | Vertical footage of your real Today screen. |
| **Application** | Zero-to-Revenue (real data) |
| **Page** | #today, tablet portrait |
| **Actions to perform** | 1. Rotate the tablet to portrait; 2. Record the Today screen, slow scroll; 3. Blur names in the edit |
| **Must be visible** | Targets and follow-ups |
| **Must be hidden** | Business names |
| **Orientation / size** | portrait |
| **Recommended length** | 20-30s |
| **Can Claude capture it?** | NO. You must capture this |
| **File name** | `EP001_B09_real-today-portrait_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Shorts |


## C. Footage that needs a real-world event

### Shot 22 · `C01` · first-reply

| | |
|---|---|
| **Scene** | VO_005_EXECUTION (optional) |
| **Narrative purpose** | A real reply arriving. Only if it happens; never staged. |
| **Application** | Wherever the reply arrives |
| **Page** | Notification / thread |
| **Actions to perform** | 1. Screen-record when a real reply lands; 2. Then log it with 'Log response' on camera |
| **Must be visible** | The moment of notice; then the log form |
| **Must be hidden** | Sender identity, message content unless they agree |
| **Orientation / size** | portrait or landscape |
| **Recommended length** | 15-30s |
| **Can Claude capture it?** | NO. Needs a real event |
| **File name** | `EP001_C01_first-reply_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Scene 5 (optional) |

### Shot 23 · `C02` · first-call-or-meeting

| | |
|---|---|
| **Scene** | Future episode |
| **Narrative purpose** | A discovery call or meeting. Ask permission before recording anyone. |
| **Application** | Phone/Meet |
| **Page** | n/a |
| **Actions to perform** | 1. Get explicit consent first; 2. Record audio only if they agree |
| **Must be visible** | n/a |
| **Must be hidden** | Their face, name, business unless they approve |
| **Orientation / size** | n/a |
| **Recommended length** | n/a |
| **Can Claude capture it?** | NO. Needs a real event |
| **File name** | `EP001_C02_first-call-or-meeting_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Episode 002+ |

### Shot 24 · `C03` · first-payment

| | |
|---|---|
| **Scene** | Future episode |
| **Narrative purpose** | A real, verified payment. Do not stage; do not show until Treasury verifies it. |
| **Application** | Zero-to-Revenue Treasury page |
| **Page** | #treasury |
| **Actions to perform** | 1. Only after the payment is verified |
| **Must be visible** | Verified status |
| **Must be hidden** | Account numbers, payer details |
| **Orientation / size** | landscape |
| **Recommended length** | 15-30s |
| **Can Claude capture it?** | NO. Needs a real event |
| **File name** | `EP001_C03_first-payment_<YYYYMMDD>_v<nn>.<ext>` |
| **Timeline position** | Episode 002+ |

