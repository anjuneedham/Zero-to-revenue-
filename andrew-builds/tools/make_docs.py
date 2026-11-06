#!/usr/bin/env python3
"""Generates the Episode 001 documents from the same JSON the video engine reads (single source of truth):
EPISODE_001_MASTER_SCRIPT.md, scripts/VOICEOVER_RECORDING_GUIDE.md, scripts/SHORTS_001_SCRIPTS.md, EPISODE_001_SHOT_LIST.md,
EPISODE_001_EDITING_PLAN.md, EPISODE_001_ASSET_REGISTER.md. Re-run after editing the JSON."""
import json
import re
import subprocess
from pathlib import Path

import os
EP = Path(os.environ.get("EPISODE_DIR", Path(__file__).resolve().parents[1] / "episode-001"))
N = re.search(r"(\d+)$", EP.name).group(1)
ED = EP / "editing-project"
ep = json.loads((ED / f"episode_{N}.json").read_text())
shorts = json.loads((ED / f"shorts_{N}.json").read_text())
shots = json.loads((ED / "shots.json").read_text())["shots"]
cfg = json.loads((ED / "video_style_config.json").read_text())
PH = re.compile(r"\[(?:FILL|RECORD|CONFIRM)[^\]]*\]")
manifest = {}
for m in (EP / "screen-recordings").rglob("manifest.json"):
    manifest.update(json.loads(m.read_text()))


def words(t):
    return len(PH.sub("", t).split()), len(PH.findall(t))


def est(t, wps, pp, phw):
    w, p = words(t)
    return (w + p * phw) / wps + pp * len([x for x in t.split("\n") if x.strip()])


def mmss(s):
    return f"{int(s // 60)}:{int(s % 60):02}"


def scratch_len(fn):
    p = EP / "voiceover" / "_scratch" / (Path(fn).stem + "_scratch.wav")
    if not p.exists():
        return None
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True).stdout)


def write(path, text):
    path = Path(str(path).replace("_001", f"_{N}"))
    if N != "001":  # the claims table is specific to Episode 001; other episodes build their own from templates/
        text = re.sub(r"## Claims check.*?\n---\n", "## Claims check\nBuild this table from `research/` for this episode: every factual statement and where it comes from.\n\n---\n", text, flags=re.S)
        text = text.replace("EPISODE_001", f"EPISODE_{N}").replace("EP001", f"EP{N}").replace("Episode 001", f"Episode {N}").replace("episode_001", f"episode_{N}").replace("shorts_001", f"shorts_{N}").replace("SHORTS_001", f"SHORTS_{N}")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text)
    print("wrote", Path(path).relative_to(EP))


# ---------------------------------------------------------------- master script ---------------------------------------
def master():
    wps, pp, phw = ep["words_per_second"], ep["paragraph_pause_s"], ep["placeholder_words"]
    tot_own = tot_ph = 0
    rows, secs = [], []
    t_est = 0
    for s in ep["scenes"]:
        w, p = words(s["voiceover"])
        e = est(s["voiceover"], wps, pp, phw)
        t_est += e
        tot_own += w
        tot_ph += p
        rows.append(f"| {s['id']} | {s['plan']} | {w} | {p} | {mmss(e)} |")
        sec = f"""### {s['scene']}

**SCENE:** {s['scene']}  (file `{s['file']}`)

**PURPOSE:** {s['purpose']}

**ESTIMATED DURATION:** plan {s['plan']} · estimated from the text: {mmss(e)} ({w} own words + {p} placeholder(s)). The real length is whatever you record; the edit adapts to it.

**VOICEOVER:**

{chr(10).join('> ' + ln if ln.strip() else '>' for ln in s['voiceover'].split(chr(10)))}

**VISUALS:** {s['visuals']}

**SCREEN RECORDING:** {s['screen_recording']}

**EDITING NOTES:** {s['editing_notes']}

**TRANSITION TO NEXT SCENE:** {s['transition']}
"""
        secs.append(sec)
    write(EP / "EPISODE_001_MASTER_SCRIPT.md", f"""# EPISODE 001: MASTER SCRIPT

**Title:** {ep['title']}
**Alternative:** {ep['alt_title']}
**Channel:** Andrew Builds · **Format:** long-form documentary, voiceover over real screen recordings and desk footage.

*Generated from `editing-project/episode_001.json` by `tools/make_docs.py`. Edit the JSON, not this file.*

## Status: DRAFT, WAITING FOR YOUR INPUT
Every spoken word is written. Anything I could not verify is a **bracketed placeholder**, never an invented fact:

| Marker | Meaning |
|---|---|
| `[FILL: ...]` | A fact only you know (a number, your reason, your offer). Replace the whole bracket with what you will say. |
| `[RECORD: ...]` | A moment only you can describe, in your own words, and only if it really happened. |

Until the placeholders are filled, any render is an **assembly proof** and is watermarked as such.

## Length
| Section | Plan | Own words | Placeholders | Est. read time |
|---|---|---|---|---|
{chr(10).join(rows)}
| **Total** | 0:00-11:30 | **{tot_own}** | **{tot_ph}** | **{mmss(t_est)}** |

**Runtime, honestly:** the script has {tot_own} words of its own. At a relaxed 150 words per minute that is about {mmss(tot_own / 150 * 60 + 0.6 * 40)} before your placeholders; each filled placeholder adds
roughly 10-30 spoken words. So the finished voiceover should land near **{mmss(t_est)}**. That is an **estimate**: a fast reader (160+ wpm) who answers each placeholder in one short phrase could finish
just under 10:00. If that happens, add a real example or detail to one of the placeholders (Scene 3 or Scene 5 are the best places); do not pad. The actual length is confirmed only after you record.
The robot guide track for the whole script measured {mmss(sum(filter(None, [scratch_len(s['file']) for s in ep['scenes']])))} with every placeholder spoken as a short pause.

## Claims check (what each factual statement rests on)
| Statement in the script | Source |
|---|---|
| Years of sales and customer service; ran own businesses, helped others run theirs; uses AI to build websites, funnels, apps | `docs/strategy/OWNER_PROFILE.md` (owner-provided 25 Oct 2026) |
| An earlier system found "over a hundred" qualified opportunities; verified revenue "at the time: zero" | `docs/FOUNDERS_LOG.md` 26 Oct 2026 (121 qualified, $0 verified). **Confirm it is still zero when you record.** |
| A business-contact database does not cover small local trades | `docs/FOUNDERS_LOG.md` 26 Oct 2026 (Clay) |
| Ten or fifteen real contacts as the first test | `docs/FOUNDERS_LOG.md` 26 Oct 2026 |
| Twelve editable playbooks; Today screen; pipeline; step-through history; counts instead of percentages; no AI; does not send messages | The shipped product; see `project-documentation/PRODUCT_TEST_REPORT.md` |
| "Tested the whole journey in a browser on made-up businesses" | `tests/e2e/journey.js`: 25 checks run and passed on 6 Nov 2026 |
| "Exactly one user: me. Zero customers for the software." | True as far as any repo shows. **Confirm.** |

Deliberately **not** claimed: any revenue, any number of replies or customers, product-market fit, any AI capability, any price.

---

{chr(10).join(secs)}
""")


# ---------------------------------------------------------------- voiceover guide -------------------------------------
def vo_guide():
    wps, pp, phw = ep["words_per_second"], ep["paragraph_pause_s"], ep["placeholder_words"]
    blocks = []
    for i, s in enumerate(ep["scenes"], 1):
        e = est(s["voiceover"], wps, pp, phw)
        sl = scratch_len(s["file"])
        dur = mmss(e) + (f" (robot guide track measured {mmss(sl)})" if sl else "")
        blocks.append(f"""## {i}. `{s['file']}`  ({s['scene']})

- **Approx. duration:** {dur}
- **Tone:** {s['tone']}
- **Pace:** {s['pace']}
- **Emphasis:** {s['emphasis']}
- **Pauses:** {s['pauses']}

**Script:**

{chr(10).join('> ' + ln if ln.strip() else '>' for ln in s['voiceover'].split(chr(10)))}
""")
    sc = []
    for s in shorts["shorts"]:
        sc.append(f"- `{s['file']}`: {s['title']} (see `SHORTS_001_SCRIPTS.md`)")
    write(EP / "scripts" / "VOICEOVER_RECORDING_GUIDE.md", f"""# Voiceover Recording Guide (Episode 001)

You record the narration. This file is the session plan. One file per section, so any section can be re-recorded and swapped without rebuilding the episode.

## Before you start
1. Record in a quiet room. Switch off fans, air conditioning, notifications and phones. Soft furnishings help; a wardrobe of clothes works well.
2. Use the same microphone at the same distance (a hand's width from your mouth, slightly off-axis) for every section and every session.
3. Record a 10-second test first. Play it back with headphones. Fix hiss, echo or popping before you continue.
4. Keep peaks around -12 dB. If the meter touches red, move back or lower the gain. **Clipped audio cannot be repaired.**
5. Record each section more than once if you stumble. Keep every take.
6. Leave about one second of silence before and after each section. The edit trims it.
7. Keep the original recordings untouched. Do not add EQ, compression, noise reduction or effects. The pipeline normalises loudness only.
8. Save as **WAV**, any sample rate 44.1 or 48 kHz, mono or stereo, with the exact file names below, into `episode-001/voiceover/`.

## Fill the placeholders first
Open `EPISODE_001_MASTER_SCRIPT.md` and decide what you will really say at each `[FILL]` / `[RECORD]`. Then put the same words into
`editing-project/episode_001.json` (replace the bracket) so the captions match what you recorded. If you would rather speak freely, record first and
replace the captions with a transcript of your recording (see EPISODE_001_EDITING_PLAN.md, "Captions").

## Replacing one section later
Record a new `VO_00X_NAME.wav` with the same name, then run `python3 andrew-builds/tools/produce.py episode`. Only the changed scene is re-rendered (scenes are cached by content).

## Robot guide tracks
`voiceover/_scratch/` holds robot (text-to-speech) tracks made only to test timing and captions. They are **not** narration and are never used unless you pass `--scratch-vo`. Your real files always take priority.

{chr(10).join(blocks)}

## Short-form narration files
{chr(10).join(sc)}
""")


# ---------------------------------------------------------------- shorts ----------------------------------------------
def shorts_doc():
    out = ["""# Short-form scripts: three Shorts from Episode 001

Each Short stands alone, has its own hook in the first 1-2 seconds, and makes one complete point. They are **not** clips of the documentary.
Brand: Andrew Builds. Format 9:16 (1080x1920), 20-45 seconds. Generated from `editing-project/shorts_001.json`.
"""]
    wps = shorts["words_per_second"]
    for s in shorts["shorts"]:
        w, p = words(s["voiceover"])
        out.append(f"""
---

## {s['id']}: {s['title'].upper()}

**1. Short title:** {s['title']}
**Angle:** {s['angle']}
**Audio file:** `{s['file']}` · estimated {w + 10 * p} words ≈ {int((w + 10 * p) / wps)}-{int((w + 10 * p) / wps) + 6} seconds

**2. Hook (first 1-2 seconds):** "{s['hook']}"  · on screen: **{s['overlays'][0]['text'].replace(chr(10), ' ')}**

**3. Full narration:**

{chr(10).join('> ' + ln for ln in s['voiceover'].split(chr(10)))}

**4. Shot-by-shot storyboard**

| Time | Visual | Shot | On-screen text |
|---|---|---|---|
{chr(10).join(f"| {b['t']}s | {b['visual']} | {b['shot'] or '(text card)'} | {b['text']} |" for b in s['beats'])}

**5. On-screen text:** {' · '.join(s['on_screen_text'])}

**6. Screen recording requirements:** {s['screen_recording_requirements']}

**7. Captions:** {s['captions']}

**8. Editing instructions:** {s['editing']}

**9. Closing CTA:** {s['cta']}

**10. TikTok description:** {s['tiktok_description']}

**11. YouTube Shorts title:** {s['yt_title']}

**12. Suggested cover text:** {s['cover_text'].replace(chr(10), ' / ')}
""")
    write(EP / "scripts" / "SHORTS_001_SCRIPTS.md", "\n".join(out))


# ---------------------------------------------------------------- shot list -------------------------------------------
def shot_list():
    def block(s):
        got = "yes, captured" if s["cat"] == "A" and s["id"] in manifest else ("yes, automated, see `tools/capture_demo.js`" if s["cat"] == "A" else "NO. You must capture this" if s["cat"] == "B" else "NO. Needs a real event")
        return f"""### Shot {s['n']} · `{s['id']}` · {s['slug']}

| | |
|---|---|
| **Scene** | {s['scene']} |
| **Narrative purpose** | {s['purpose']} |
| **Application** | {s['app']} |
| **Page** | {s['page']} |
| **Actions to perform** | {'; '.join(f'{i}. {a}' for i, a in enumerate(s['actions'], 1))} |
| **Must be visible** | {'; '.join(s['visible'])} |
| **Must be hidden** | {'; '.join(s['hidden'])} |
| **Orientation / size** | {s['orientation']} |
| **Recommended length** | {s['length']} |
| **Can Claude capture it?** | {got} |
| **File name** | `{s['file_pattern']}` |
| **Timeline position** | {s['timeline']} |
"""
    A = [s for s in shots if s["cat"] == "A"]
    B = [s for s in shots if s["cat"] == "B"]
    C = [s for s in shots if s["cat"] == "C"]
    write(EP / "EPISODE_001_SHOT_LIST.md", f"""# EPISODE 001: SHOT LIST

*Generated from `editing-project/shots.json`.* Shot IDs match the clips used in `episode_001.json` and `shorts_001.json`.

| Group | Meaning | Count |
|---|---|---|
| **A** | I (Claude) capture this, from the real app, on clearly fictional DEMO data. **Already captured** (see Asset Register) | {len(A)} |
| **B** | **You** must capture this (your real data, your camera, your own apps) | {len(B)} |
| **C** | Needs a real-world event. Never stage it | {len(C)} |

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

{chr(10).join(block(s) for s in A)}

## B. Footage you must capture

{chr(10).join(block(s) for s in B)}

## C. Footage that needs a real-world event

{chr(10).join(block(s) for s in C)}
""")


# ---------------------------------------------------------------- editing plan ---------------------------------------
def editing_plan():
    rows = []
    for s in ep["scenes"]:
        cl = sorted(s["clips"], key=lambda c: -c.get("weight", 1))
        primary, secondary = cl[0]["shot"], (cl[1]["shot"] if len(cl) > 1 else "-")
        ov = "; ".join(("[needs confirm] " if o.get("needs_confirm") else "") + o["text"].replace("\n", " ") for o in s.get("overlays", [])) or "-"
        rows.append(f"| {s['scene']} | {s['plan']} | {primary} | {secondary} | {ov} | {s['transition']} |")
    write(EP / "EPISODE_001_EDITING_PLAN.md", f"""# EPISODE 001: EDITING PLAN

## Chosen workflow and why
I inspected the environment first (see `project-documentation/CURRENT_STATE_AUDIT.md`, item 17). Available: **FFmpeg 6.1.1** (libx264, AAC, libass `subtitles`, `drawtext`,
`loudnorm`, `ebur128`, `blackdetect`, `silencedetect`), `ffprobe`, Python 3.13 + Pillow, Chromium + Playwright, Inter and JetBrains fonts, `espeak-ng` (installed by me for robot guide
tracks only). Not available here: a GUI editor, a music library, forced-alignment/speech-to-text. A Descript connector exists but needs your uploaded media, so it is an option for you, not part of the pipeline.

**Selected: a config-driven FFmpeg pipeline** (`tools/produce.py`), because it is automated, repeatable and scriptable. A hand-edited timeline in a GUI editor would not be reproducible. I did **not** build a custom editor.
The existing `agriloopmain/video-production` pipeline is Agriloop-specific (its own database and brand), so it is deliberately not reused.

```
python3 andrew-builds/tools/produce.py scratch-vo          # robot guide tracks (timing tests only)
python3 andrew-builds/tools/produce.py episode             # long-form (uses your real VO_*.wav; add --scratch-vo to test without them)
python3 andrew-builds/tools/produce.py short S1            # or S2, S3  (or: all)
python3 andrew-builds/tools/qa.py video <file> --kind long|short --srt <captions.srt>
python3 andrew-builds/tools/qa.py project
python3 andrew-builds/tools/make_docs.py                   # regenerate these documents after editing the JSON
```

## Non-destructive by design
Source recordings and narration are only **read**. Everything generated lives in `_work/` (cache, git-ignored), `exports/`, `captions/` and `production-reports/`. Scenes are cached by content hash, so replacing one narration file or one clip re-renders only that scene.

## Files that control the edit
| File | Controls |
|---|---|
| `editing-project/episode_001.json` | scenes: narration text, which clips (with weights), overlays |
| `editing-project/shorts_001.json` | the three Shorts, same structure |
| `editing-project/shots.json` | the shot database (shot list and asset register are generated from it) |
| `editing-project/video_style_config.json` | **VIDEO_STYLE_CONFIG**: fonts, colours, sizes, caption look/position, transition, zoom, loudness, music level, resolution, fps, bitrate |

### VIDEO_STYLE_CONFIG (current values)
| Setting | Value |
|---|---|
| Primary / secondary font | Inter Display Bold / Inter Medium |
| Brand colours | background `{cfg['brand']['colors']['background']}`, text `{cfg['brand']['colors']['text']}`, highlight `{cfg['brand']['colors']['highlight']}`, muted `{cfg['brand']['colors']['muted']}` (placeholders, see note) |
| Heading / lower third / caption size (long, short) | {cfg['text']['heading_size']['horizontal']}/{cfg['text']['heading_size']['vertical']}, {cfg['text']['lower_third_size']['horizontal']}/{cfg['text']['lower_third_size']['vertical']}, {cfg['text']['caption_size']['horizontal']}/{cfg['text']['caption_size']['vertical']} px |
| Caption position / background | bottom (long), lower-middle (short) / {int(cfg['text']['caption_background_opacity'] * 100)}% dark box |
| Highlight colour | {cfg['brand']['colors']['highlight']} on key words |
| Transition | {cfg['motion']['transition']} (dip to black), {cfg['motion']['transition_s']} s each side |
| Zoom intensity | {cfg['motion']['zoom_intensity']} (no zoom: screen recordings stay readable) |
| Narration / music / duck / SFX | -16 LUFS / {cfg['audio']['music_db']} dB / {cfg['audio']['music_duck_db']} dB / {cfg['audio']['sound_effect_db']} dB |
| Intro / outro | {cfg['motion']['intro_s']} s / {cfg['motion']['outro_s']} s (the closing title card is an overlay in the last scene) |
| Aspect / resolution / fps | 16:9 1920x1080 and 9:16 1080x1920 / 30 fps |
| Export | H.264 CRF {cfg['video']['crf']}, max {cfg['video']['maxrate']}, AAC {cfg['video']['audio_bitrate']}, `+faststart` |

**Brand note:** no Andrew Builds brand assets exist in any attached repository. The values above are a restrained placeholder (dark navy, off-white, amber). Replace them with your real brand colours and fonts in that one file.

## Per-scene visual plan
| Scene | Plan | Primary visual | Secondary visual | Overlay(s) | Transition |
|---|---|---|---|---|---|
{chr(10).join(rows)}

Clip lengths come from **weights** (relative share of the scene), so when the real narration length differs from the estimate every shot rescales automatically. A source clip shorter than its slot holds its last frame; longer ones are trimmed from the recorded start offset.
Footage you still owe appears as a **FOOTAGE NEEDED** slate. Event-dependent clips marked optional (C01) are skipped if they do not exist. Overlays marked `needs_confirm` are skipped until you confirm the fact they state (`--include-unconfirmed` draws them).

## Retention principles applied
Real footage first; first sentence over action, not a logo; no cut faster than the sentence; no generic stock; one highlight per demo shot; full-screen text only for the three lines worth stopping on; music (when you choose it) ducks 12 dB under the voice; pauses are kept, not trimmed away; the DEMO DATA label is burned into every captured product clip.

## Captions
Generated as `.srt` (for YouTube upload) and `.ass` (burned in). **Timing is proportional to text length, not forced-aligned** because no speech-to-text tool is available here. It is close enough for review, but for publishing, replace `captions/EPISODE_001_long.srt` with a transcript of your real narration (the Descript connector or YouTube's auto-sync can do this), then re-run with `--no-burn` and upload the SRT, or burn the corrected ass.

## Music
No music library exists here and I will not synthesise music. Choose a royalty-free instrumental you have the licence to use, drop it in `music/`, set `audio.music_file` in the config (path relative to `episode-001/`). It is mixed under the narration with sidechain ducking. Until then the proof has no music. Record the licence in the Asset Register.

## Quality gates (automated by `tools/qa.py`, then human)
duration ≥ 10:00 (long) or 20-45 s (shorts) · 1920x1080 / 1080x1920 · 30 fps · H.264 + AAC 48 kHz stereo · integrated loudness -16 ±2 LUFS · true peak ≤ -1 dBFS · silence ≤ 35% · no black segment ≥ 1 s · caption file valid, ordered, readable · contact sheet for visual review · build report must show no gaps, no scratch narration and no placeholders before a video is called READY FOR REVIEW.
""")


# ---------------------------------------------------------------- asset register -------------------------------------
def asset_register():
    rows = []
    for s in shots:
        info = manifest.get(s["id"])
        f = None
        for base in (EP / "screen-recordings", EP / "raw-footage"):
            c = sorted(base.rglob(f"EP001_{s['id']}_*"))
            c = [x for x in c if x.suffix != ".json"]
            if c:
                f = c[-1]
        status = "CAPTURED (demo data)" if f and s["cat"] == "A" else "RECEIVED" if f else ("NOT STARTED" if s["cat"] != "C" else "WAITING FOR A REAL EVENT")
        if s["cat"] == "B" and not f:
            status = "WAITING FOR MY INPUT"
        size = f"{f.stat().st_size / 1e6:.1f} MB" if f else "-"
        dur = f"{info['duration_s']}s" if info and info.get("duration_s") else "-"
        rows.append(f"| {s['id']} | {s['slug']} | {s['cat']} | {f.name if f else '-'} | {dur} | {size} | {status} |")
    vos = []
    for s in ep["scenes"] + shorts["shorts"]:
        real = (EP / "voiceover" / s["file"]).exists()
        vos.append(f"| {s['file']} | narration | {'RECEIVED' if real else 'WAITING FOR MY INPUT'} | robot guide track exists: {'yes' if scratch_len(s['file']) else 'no'} |")
    write(EP / "EPISODE_001_ASSET_REGISTER.md", f"""# EPISODE 001: ASSET REGISTER

Original media vs rendered outputs are kept apart: originals in `voiceover/`, `screen-recordings/`, `raw-footage/` (read-only to the pipeline); renders in `exports/`; cache in `_work/`.
Media files are **git-ignored** (large and regenerable). This register and the capture scripts are the record. *Generated by `tools/make_docs.py`.*

## Footage
| Shot | Name | Group | File | Length | Size | Status |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

A = captured by Claude from the real app on DEMO data · B = you capture · C = needs a real event. All A clips carry a burned-in DEMO DATA label (A11 is labelled AUTOMATED TEST RUN in the edit).

## Narration
| File | Type | Status | Note |
|---|---|---|---|
{chr(10).join(vos)}

## Music and sound effects
| Item | Status | Licence |
|---|---|---|
| Music bed | NOT STARTED: you choose a licensed track | record licence here |
| Sound effects | NOT USED | n/a |

## Graphics and thumbnails
| File | Type | Status |
|---|---|---|
| thumbnails/T1_building-from-zero_DRAFT.jpg | concept 1 (recommended) | DRAFT: needs your photo in the PHOTO SLOT |
| thumbnails/T2_bootstrapper-experiment_DRAFT.jpg | concept 2 | DRAFT |
| thumbnails/T3_two-businesses_DRAFT.jpg | concept 3 | DRAFT |
| graphics/frame_*.png | stills taken from captured demo footage (DEMO DATA visible) | READY |

## Rendered outputs (assembly proofs, all with robot guide narration)
See `EPISODE_001_EXPORT_REPORT.md` for what each one is and what it passed.
""")


if __name__ == "__main__":
    master()
    vo_guide()
    shorts_doc()
    shot_list()
    editing_plan()
    asset_register()
