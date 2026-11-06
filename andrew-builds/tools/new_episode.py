#!/usr/bin/env python3
"""Scaffold a new episode folder (same layout as Episode 001) with skeleton JSON and a plan, reusing the shared style config.
  new_episode.py 2 "Working title"
Then: fill editing-project/episode_00N.json, record, capture, and run tools/produce.py --episode-dir andrew-builds/episode-00N."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRS = ["research", "scripts", "voiceover", "screen-recordings", "raw-footage", "music", "graphics", "editing-project", "captions", "exports", "thumbnails", "production-reports"]


def main():
    if len(sys.argv) < 3 or not sys.argv[1].isdigit():
        sys.exit(__doc__)
    n, title = f"{int(sys.argv[1]):03}", sys.argv[2]
    ep = ROOT / f"episode-{n}"
    if ep.exists():
        sys.exit(f"{ep} already exists; refusing to overwrite")
    for d in DIRS:
        (ep / d).mkdir(parents=True)
        (ep / d / ".gitkeep").touch()
    shutil.copy(ROOT / "episode-001" / "editing-project" / "video_style_config.json", ep / "editing-project" / "video_style_config.json")
    scene = dict(id="VO_001_HOOK", file="VO_001_HOOK.wav", scene="Scene 1 - Hook", plan="0:00-0:40", purpose="TODO", tone="TODO", pace="TODO", emphasis="TODO", pauses="TODO",
                 voiceover="[FILL: write the spoken words. Only state facts you can show.]", visuals="TODO", screen_recording="TODO", editing_notes="TODO", transition="TODO",
                 clips=[dict(shot="A01", weight=1)], overlays=[])
    (ep / "editing-project" / f"episode_{n}.json").write_text(json.dumps(dict(title=title, alt_title="", channel="Andrew Builds", episode=int(n), words_per_second=2.5, paragraph_pause_s=0.6, placeholder_words=10, scenes=[scene]), indent=1))
    (ep / "editing-project" / f"shorts_{n}.json").write_text(json.dumps(dict(shorts=[], words_per_second=2.6, placeholder_words=10), indent=1))
    shot = dict(id="A01", cat="A", slug="todo", scene="VO_001_HOOK", purpose="TODO", app="TODO", page="TODO", actions=["TODO"], visible=["TODO"], hidden=["TODO"], orientation="landscape", length="20-30s", timeline="TODO", n=1,
                file_pattern=f"EP{n}_A01_todo_<YYYYMMDD>_v<nn>.<ext>")
    (ep / "editing-project" / "shots.json").write_text(json.dumps(dict(naming=f"EP{n}_<shot>_<slug>_<YYYYMMDD>_v<nn>.<ext>", shots=[shot]), indent=1))
    tpl = (ROOT / "templates" / "EPISODE_PLAN_TEMPLATE.md").read_text().replace("<N>", n).replace("<TITLE>", title)
    (ep / f"EPISODE_{n}_PLAN.md").write_text(tpl)
    print(f"created {ep.relative_to(ROOT.parent)}; next: fill {ep.name}/EPISODE_{n}_PLAN.md and editing-project/episode_{n}.json")


if __name__ == "__main__":
    main()
