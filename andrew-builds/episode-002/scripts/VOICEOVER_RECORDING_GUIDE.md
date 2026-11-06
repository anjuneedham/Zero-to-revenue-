# Voiceover Recording Guide (Episode 002)

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
Open `EPISODE_002_MASTER_SCRIPT.md` and decide what you will really say at each `[FILL]` / `[RECORD]`. Then put the same words into
`editing-project/episode_002.json` (replace the bracket) so the captions match what you recorded. If you would rather speak freely, record first and
replace the captions with a transcript of your recording (see EPISODE_002_EDITING_PLAN.md, "Captions").

## Replacing one section later
Record a new `VO_00X_NAME.wav` with the same name, then run `python3 andrew-builds/tools/produce.py episode`. Only the changed scene is re-rendered (scenes are cached by content).

## Robot guide tracks
`voiceover/_scratch/` holds robot (text-to-speech) tracks made only to test timing and captions. They are **not** narration and are never used unless you pass `--scratch-vo`. Your real files always take priority.

## 1. `VO_001_HOOK.wav`  (Scene 1 - Hook)

- **Approx. duration:** 0:04
- **Tone:** TODO
- **Pace:** TODO
- **Emphasis:** TODO
- **Pauses:** TODO

**Script:**

> [FILL: write the spoken words. Only state facts you can show.]


## Short-form narration files

