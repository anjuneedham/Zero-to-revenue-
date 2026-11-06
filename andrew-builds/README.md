# Andrew Builds: production system

A repeatable, scriptable pipeline for the Bootstrapper Experiment series. Text, config and scripts are tracked in git; large media (recordings, narration, exports) is git-ignored.

```
andrew-builds/
  episode-001/            the first episode (script, shot list, plans, footage, proofs, reports)
  episode-002/            scaffolded framework for the next one (see its PLAN)
  templates/              planning, story, voiceover, shots, short extraction, editing config, export report, performance
  tools/
    produce.py            FFmpeg assembly for episodes and shorts (config-driven, cached, non-destructive)
    qa.py                 automated checks on videos and on the project (secret/personal-email scan)
    make_docs.py          generates script/VO guide/shot list/editing plan/asset register from the JSON
    make_thumbnails.py    thumbnail drafts from real product frames
    make_export_report.py EXPORT_REPORT from the QA and build JSON
    capture_demo.js       captures the "A" screen recordings from the real app on DEMO data
    new_episode.py        scaffold Episode N
    suggest_content.py    short-form ideas from real recorded activity only
  DAILY_SHORTS_SYSTEM.md
```

## Make Episode 003 (or 002) without rebuilding anything
```
python3 andrew-builds/tools/new_episode.py 3 "Working title"
# fill episode-003/EPISODE_003_PLAN.md, editing-project/episode_003.json, shots.json, shorts_003.json
EPISODE_DIR=andrew-builds/episode-003 python3 andrew-builds/tools/make_docs.py
python3 andrew-builds/tools/produce.py episode --episode-dir andrew-builds/episode-003
EPISODE_DIR=andrew-builds/episode-003 python3 andrew-builds/tools/qa.py video <export> --kind long --srt <srt>
```

## Requirements
FFmpeg with libx264, libass and drawtext; Python 3.10+ with Pillow; Node + Playwright only for `capture_demo.js`; `espeak-ng` only for robot guide tracks (timing tests; never publish).
