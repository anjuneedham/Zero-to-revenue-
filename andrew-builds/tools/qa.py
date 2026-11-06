#!/usr/bin/env python3
"""Automated quality checks for rendered videos and for the production project.

  qa.py video <file> --kind long|short [--srt captions.srt]   duration, resolution/aspect, fps, codecs, audio presence, loudness,
                                                              silence, black frames, caption validity; writes a contact sheet to inspect by eye
  qa.py project                                               script/shot-list/asset consistency, leftover placeholders, secret scan

Automated checks cannot judge whether the video is *good*. Every report ends with the human-review items that remain. A video is only
reported READY FOR REVIEW when every automated check passes AND its build report says it has no gaps, no scratch narration and no placeholders."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os
EP = Path(os.environ.get("EPISODE_DIR", HERE.parent / "episode-001"))
N = re.search(r"(\d+)$", EP.name).group(1)


def sh(cmd):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True)


def probe(path):
    r = sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    return json.loads(r.stdout)


def loudness(path):
    r = sh(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"])
    t = r.stderr.split("Summary:")[-1]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", t)
    p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", t)
    lra = re.search(r"LRA:\s+([\d.]+) LU", t)
    return (float(i.group(1)) if i else None, float(p.group(1)) if p else None, float(lra.group(1)) if lra else None)


def silences(path, dur):
    r = sh(["ffmpeg", "-nostats", "-i", path, "-af", "silencedetect=noise=-45dB:d=2.0", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [(float(a), float(b)) for a, b in re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", r.stderr)]
    total = sum(d for _, d in ends)
    if len(starts) > len(ends):  # silent until the end
        total += dur - starts[-1]
    long = [round(d, 1) for _, d in ends if d >= 4.0]
    return total, long


def black_frames(path):
    r = sh(["ffmpeg", "-nostats", "-i", path, "-vf", "blackdetect=d=1.0:pic_th=0.98", "-an", "-f", "null", "-"])
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]


def parse_srt(p):
    cues = []
    for block in re.split(r"\n\s*\n", Path(p).read_text().strip()):
        lines = block.strip().splitlines()
        m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", lines[1]) if len(lines) >= 3 else None
        if not m:
            return None
        g = list(map(int, m.groups()))
        cues.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000, lines[2:]))
    return cues


def contact_sheet(path, dur, out, vertical):
    n = 24
    fps = n / max(dur, 1)
    w, h = (180, 320) if vertical else (320, 180)
    cols = 8 if vertical else 6
    sh(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", f"fps={fps:.5f},scale={w}:{h},tile={cols}x{-(-n // cols)}", "-frames:v", "1", out])


def check_video(a):
    p = Path(a.file)
    d = probe(p)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    dur = float(d["format"]["duration"])
    vertical = a.kind == "short"
    res = []

    def chk(name, ok, detail):
        res.append(dict(check=name, result="PASS" if ok else "FAIL", detail=detail))
    chk("video stream present, H.264, yuv420p", bool(v) and v["codec_name"] == "h264" and v.get("pix_fmt") == "yuv420p", f"{v and v['codec_name']} {v and v.get('pix_fmt')}")
    want = (1080, 1920) if vertical else (1920, 1080)
    chk("resolution/aspect ratio", bool(v) and (v["width"], v["height"]) == want, f"{v['width']}x{v['height']} (want {want[0]}x{want[1]}, {'9:16' if vertical else '16:9'})")
    fr = eval(v["r_frame_rate"]) if v else 0
    chk("frame rate 30", abs(fr - 30) < 0.01, f"{fr:.2f}")
    chk("audio stream present (AAC, 48 kHz, stereo)", bool(au) and au["codec_name"] == "aac" and au["sample_rate"] == "48000" and au["channels"] == 2, au and f"{au['codec_name']} {au['sample_rate']} {au['channels']}ch")
    lo, hi = (20, 45) if vertical else (600, 1e9)
    chk("duration " + ("20-45 s (short)" if vertical else ">= 10:00 (long-form)"), lo <= dur <= hi, f"{dur:.1f}s = {int(dur // 60)}:{int(dur % 60):02}")
    chk("faststart / container OK", sh(["ffmpeg", "-v", "error", "-i", p, "-f", "null", "-"]).stderr.strip() == "", "decoded end to end with no errors")
    i, tp, lra = loudness(p)
    chk("integrated loudness within -16 LUFS +/- 2", i is not None and abs(i + 16) <= 2, f"{i} LUFS, LRA {lra}")
    chk("true peak <= -1 dBFS (no clipping)", tp is not None and tp <= -1.0, f"{tp} dBFS")
    st, long_ = silences(p, dur)
    chk("silence <= 35% of runtime", st / dur <= 0.35, f"{st:.1f}s silent ({100 * st / dur:.0f}%), gaps >=4s: {long_}")
    bf = black_frames(p)
    chk("no black or blank segment >= 1 s", not bf, f"{bf}")
    srt = Path(a.srt) if a.srt else None
    if srt and srt.exists():
        cues = parse_srt(srt)
        ok = cues is not None and all(c[0] < c[1] for c in cues) and all(cues[k][1] <= cues[k + 1][0] + 0.001 for k in range(len(cues) - 1)) and cues[-1][1] <= dur + 0.2
        chk("captions: valid SRT, ordered, no overlaps, within runtime", bool(ok), f"{len(cues or [])} cues")
        if cues:
            cps = max(len(" ".join(c[2])) / max(0.2, c[1] - c[0]) for c in cues)
            maxline = max(len(l) for c in cues for l in c[2])
            chk("captions readable: <= 22 chars/s, <= %d chars/line" % (26 if vertical else 44), cps <= 22 and maxline <= (26 if vertical else 44), f"max {cps:.1f} chars/s, longest line {maxline}")
    else:
        chk("captions: SRT present", False, "no SRT given")
    name = p.stem
    sheet = EP / "production-reports" / f"contact_{name}.png"
    contact_sheet(p, dur, sheet, vertical)
    build = EP / "production-reports" / ("build_" + re.sub(r"_PROOF$", "", name) + ".json")
    reasons = []
    if build.exists():
        b = json.loads(build.read_text())
        reasons = b.get("reasons", [])
    else:
        reasons = ["no build report"]
    auto_fail = [r for r in res if r["result"] == "FAIL"]
    verdict = "READY FOR REVIEW" if not auto_fail and not reasons else "NOT FINAL"
    why = [f"automated check failed: {r['check']}" for r in auto_fail] + reasons
    human = ["Watch the whole video once with sound (automation cannot judge pacing, clarity or taste).", "Read every frame that contains a screen recording: no names, emails, phone numbers or credentials visible.",
             "Confirm every spoken claim is true on the day you publish (revenue, counts, status).", "Check captions against the real narration; timing is estimated until you replace the SRT with a transcript of your recording.",
             "Check the music (if any) never masks the voice."]
    out = dict(file=str(p.relative_to(EP)) if EP in p.parents else str(p), kind=a.kind, duration_s=round(dur, 1), checks=res, verdict=verdict, not_final_because=why, contact_sheet=str(sheet.relative_to(EP)), human_review_required=human)
    (EP / "production-reports").mkdir(exist_ok=True)
    (EP / "production-reports" / f"qa_{name}.json").write_text(json.dumps(out, indent=1))
    print(f"{p.name}: {verdict}")
    for r in res:
        print(f"  [{r['result']}] {r['check']}: {r['detail']}")
    for w in why:
        print("  NOT FINAL because:", w)
    return 0 if not auto_fail else 1


def check_project(a):
    ed = EP / "editing-project"
    ep = json.loads((ed / f"episode_{N}.json").read_text())
    sh_ = json.loads((ed / f"shorts_{N}.json").read_text())
    shots = {s["id"]: s for s in json.loads((ed / "shots.json").read_text())["shots"]}
    problems, info = [], []
    used = set()
    for sc in ep["scenes"]:
        for c in sc["clips"]:
            used.add(c["shot"])
            if c["shot"] not in shots:
                problems.append(f"{sc['id']}: clip {c['shot']} is not in shots.json")
    for s in sh_["shorts"]:
        for c in s["clips"]:
            used.add(c["shot"])
            if c["shot"] not in shots:
                problems.append(f"{s['id']}: clip {c['shot']} is not in shots.json")
    for sid in set(shots) - used:
        info.append(f"shot {sid} is defined but not used by any scene or short")
    ph = sum(len(re.findall(r"\[(?:FILL|RECORD|CONFIRM)[^\]]*\]", s["voiceover"])) for s in ep["scenes"] + sh_["shorts"])
    info.append(f"{ph} unresolved [FILL/RECORD] placeholders remain in the spoken text (expected until you fill them)")
    words = 0
    for s in ep["scenes"]:
        words += len(re.sub(r"\[(?:FILL|RECORD|CONFIRM)[^\]]*\]", "", s["voiceover"]).split())
    info.append(f"episode narration: {words} own words (+ placeholders)")
    pat = re.compile(r"(sk-[A-Za-z0-9]{20,}|postgres(ql)?://\S+:\S+@|Bearer [A-Za-z0-9._-]{20,}|AKIA[0-9A-Z]{16}|\b[\w.+-]+@(?!example\.)[\w-]+\.[a-z]{2,}\b)")
    for f in list(EP.rglob("*.md")) + list(EP.rglob("*.json")) + list((EP.parent / "tools").glob("*")):
        if "_work" in f.parts or f.is_dir():
            continue
        try:
            t = f.read_text()
        except Exception:
            continue
        for m in pat.finditer(t):
            problems.append(f"possible secret or personal email in {f.relative_to(EP.parent)}: {m.group(0)[:30]}...")
    for p in problems:
        print("PROBLEM:", p)
    for i in info:
        print("info:", i)
    print("PROJECT CHECK:", "PASS" if not problems else "FAIL")
    return 0 if not problems else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    v = sp.add_parser("video")
    v.add_argument("file")
    v.add_argument("--kind", choices=["long", "short"], required=True)
    v.add_argument("--srt")
    sp.add_parser("project")
    a = ap.parse_args()
    sys.exit(check_video(a) if a.cmd == "video" else check_project(a))
