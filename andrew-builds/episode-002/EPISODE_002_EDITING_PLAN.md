# EPISODE 001: EDITING PLAN

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
| `editing-project/episode_002.json` | scenes: narration text, which clips (with weights), overlays |
| `editing-project/shorts_002.json` | the three Shorts, same structure |
| `editing-project/shots.json` | the shot database (shot list and asset register are generated from it) |
| `editing-project/video_style_config.json` | **VIDEO_STYLE_CONFIG**: fonts, colours, sizes, caption look/position, transition, zoom, loudness, music level, resolution, fps, bitrate |

### VIDEO_STYLE_CONFIG (current values)
| Setting | Value |
|---|---|
| Primary / secondary font | Inter Display Bold / Inter Medium |
| Brand colours | background `#0A0F1A`, text `#F5F7FA`, highlight `#F2B01E`, muted `#8A97AD` (placeholders, see note) |
| Heading / lower third / caption size (long, short) | 84/96, 40/46, 46/58 px |
| Caption position / background | bottom (long), lower-middle (short) / 62% dark box |
| Highlight colour | #F2B01E on key words |
| Transition | dip (dip to black), 0.22 s each side |
| Zoom intensity | 0.0 (no zoom: screen recordings stay readable) |
| Narration / music / duck / SFX | -16 LUFS / -22 dB / -12 dB / -18 dB |
| Intro / outro | 0 s / 0 s (the closing title card is an overlay in the last scene) |
| Aspect / resolution / fps | 16:9 1920x1080 and 9:16 1080x1920 / 30 fps |
| Export | H.264 CRF 20, max 12M, AAC 192k, `+faststart` |

**Brand note:** no Andrew Builds brand assets exist in any attached repository. The values above are a restrained placeholder (dark navy, off-white, amber). Replace them with your real brand colours and fonts in that one file.

## Per-scene visual plan
| Scene | Plan | Primary visual | Secondary visual | Overlay(s) | Transition |
|---|---|---|---|---|---|
| Scene 1 - Hook | 0:00-0:40 | A01 | - | - | TODO |

Clip lengths come from **weights** (relative share of the scene), so when the real narration length differs from the estimate every shot rescales automatically. A source clip shorter than its slot holds its last frame; longer ones are trimmed from the recorded start offset.
Footage you still owe appears as a **FOOTAGE NEEDED** slate. Event-dependent clips marked optional (C01) are skipped if they do not exist. Overlays marked `needs_confirm` are skipped until you confirm the fact they state (`--include-unconfirmed` draws them).

## Retention principles applied
Real footage first; first sentence over action, not a logo; no cut faster than the sentence; no generic stock; one highlight per demo shot; full-screen text only for the three lines worth stopping on; music (when you choose it) ducks 12 dB under the voice; pauses are kept, not trimmed away; the DEMO DATA label is burned into every captured product clip.

## Captions
Generated as `.srt` (for YouTube upload) and `.ass` (burned in). **Timing is proportional to text length, not forced-aligned** because no speech-to-text tool is available here. It is close enough for review, but for publishing, replace `captions/EPISODE_002_long.srt` with a transcript of your real narration (the Descript connector or YouTube's auto-sync can do this), then re-run with `--no-burn` and upload the SRT, or burn the corrected ass.

## Music
No music library exists here and I will not synthesise music. Choose a royalty-free instrumental you have the licence to use, drop it in `music/`, set `audio.music_file` in the config (path relative to `episode-001/`). It is mixed under the narration with sidechain ducking. Until then the proof has no music. Record the licence in the Asset Register.

## Quality gates (automated by `tools/qa.py`, then human)
duration ≥ 10:00 (long) or 20-45 s (shorts) · 1920x1080 / 1080x1920 · 30 fps · H.264 + AAC 48 kHz stereo · integrated loudness -16 ±2 LUFS · true peak ≤ -1 dBFS · silence ≤ 35% · no black segment ≥ 1 s · caption file valid, ordered, readable · contact sheet for visual review · build report must show no gaps, no scratch narration and no placeholders before a video is called READY FOR REVIEW.
