#!/usr/bin/env python3
"""Reproducible assembly for Andrew Builds episodes (FFmpeg only; no custom editor).

  produce.py scratch-vo [--episode-dir D]          make labelled robot guide tracks (espeak-ng) so timing/captions can be tested
  produce.py episode    [--scratch-vo] [...]       build the long-form episode
  produce.py short S1   [--scratch-vo] [...]       build one short (S1, S2, S3)
  produce.py all        [--scratch-vo]             episode + all shorts

Inputs (all under episode-001/): editing-project/{episode_001.json, shorts_001.json, shots.json, video_style_config.json},
voiceover/VO_*.wav, screen-recordings/**/EP001_<shot>_*.{webm,mp4,mov,mkv}. Nothing in screen-recordings/ or voiceover/ is modified.

Honesty rules baked in: a missing clip becomes a visible FOOTAGE NEEDED slate (never a fake); a missing narration file is silence of the
estimated length; any build with a gap, a scratch voice, or unconfirmed overlays is watermarked ASSEMBLY PROOF and reported as NOT FINAL.
Scenes are cached by content hash, so replacing one VO or clip re-renders only that scene."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTS = (".webm", ".mp4", ".mov", ".mkv", ".m4v")
PLACEHOLDER = re.compile(r"\[(?:FILL|RECORD|CONFIRM)[^\]]*\]")


def run(cmd, **kw):
    """Runs a command. If the last argument is an .mp4/.wav output path, it is written to a temp name and renamed only on success,
    so an interrupted or concurrent run can never leave a half-written file that the cache would mistake for a finished one."""
    cmd = list(cmd)
    final = None
    if str(cmd[0]) in ("ffmpeg", "espeak-ng") and isinstance(cmd[-1], Path) and cmd[-1].suffix in (".mp4", ".wav"):
        final = cmd[-1]
        cmd[-1] = final.with_name(f"{final.stem}.part{os.getpid()}{final.suffix}")
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        if final and cmd[-1].exists():
            cmd[-1].unlink()
        sys.exit("FFMPEG FAILED:\n" + " ".join(str(c) for c in cmd)[:400] + "\n" + "\n".join(r.stderr.strip().splitlines()[-12:]))
    if final:
        os.replace(cmd[-1], final)
    return r


def probe(path, entry="format=duration"):
    r = run(["ffprobe", "-v", "error", "-show_entries", entry, "-of", "default=nw=1:nk=1", path])
    return r.stdout.strip().splitlines()


def duration(path) -> float:
    return float(probe(path)[0])


def hexcol(h, alpha=None):
    h = h.lstrip("#")
    return f"0x{h}" + (f"{int(alpha * 255):02X}" if alpha is not None else "")


class Project:
    def __init__(self, ep_dir: Path, fmt: str):
        self.ep = ep_dir
        self.n = re.search(r"(\d+)$", ep_dir.name).group(1)
        self.edit = ep_dir / "editing-project"
        self.cfg = json.loads((self.edit / "video_style_config.json").read_text())
        self.shots = {s["id"]: s for s in json.loads((self.edit / "shots.json").read_text())["shots"]}
        self.fmt = fmt
        v = self.cfg["video"]
        self.W, self.H, self.fps = v[fmt]["width"], v[fmt]["height"], v["fps"]
        self.work = ep_dir / "_work"
        self.work.mkdir(exist_ok=True)
        self.manifests = {}
        for m in (ep_dir / "screen-recordings").rglob("manifest.json"):
            self.manifests.update(json.loads(m.read_text()))
        self.c = self.cfg["brand"]["colors"]

    def size(self, key):
        return self.cfg["text"][key][self.fmt]

    def font(self, primary=True):
        return self.cfg["brand"]["primary_font_file" if primary else "secondary_font_file"]

    def find_clip(self, shot):
        pats = []
        for base in (self.ep / "screen-recordings", self.ep / "raw-footage"):
            for p in sorted(base.rglob(f"EP{self.n}_{shot}_*")):
                if p.suffix.lower() in EXTS and "_work" not in p.parts:
                    pats.append(p)
        return pats[-1] if pats else None


def clean_text(t):
    return re.sub(r"\s+", " ", PLACEHOLDER.sub("", t)).strip()


def est_seconds(text, words_per_s, para_pause, ph_words):
    ph = len(PLACEHOLDER.findall(text))
    words = len(clean_text(text).split()) + ph * ph_words
    return words / words_per_s + para_pause * len([p for p in re.split(r"\n+", text) if p.strip()])


def textfile(pr: Project, name, text):
    p = pr.work / f"txt_{hashlib.sha1((name + text).encode()).hexdigest()[:10]}.txt"
    p.write_text(text)
    return p


def dt(pr, text, size, color, x, y, enable=None, box=None, primary=True, name="t", align=None, spacing=10):
    f = f"drawtext=fontfile={pr.font(primary)}:textfile={textfile(pr, name, text)}:expansion=none:fontsize={size}:fontcolor={color}:x={x}:y={y}:line_spacing={spacing}"
    if box:
        f += f":box=1:boxcolor={box}:boxborderw={max(14, size // 2)}"
    if align:
        f += f":text_align={align}"
    if enable:
        f += f":enable='between(t,{enable[0]:.3f},{enable[1]:.3f})'"
    return f


def sha(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:12]


def stamp(p: Path):
    return [p.name, p.stat().st_size, int(p.stat().st_mtime)] if p and p.exists() else None


# ------------------------------------------------------------------ clips --------------------------------------------

def render_clip(pr: Project, shot, src, dur, optional_label=None):
    """One shot -> a video-only mp4 of exactly `dur` seconds at the project size. Missing source -> a labelled slate."""
    W, H, fps = pr.W, pr.H, pr.fps
    info = pr.manifests.get(shot, {})
    start = float(info.get("start_offset_s", 0) or 0)
    label = info.get("label")
    key = sha(shot, stamp(src), start, round(dur, 2), pr.fmt, W, H, fps, label, pr.cfg["brand"], pr.cfg["text"])
    out = pr.work / f"clip_{shot}_{key}.mp4"
    if out.exists():
        return out, ("clip" if src else "slate")
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(fps), "-an", "-t", f"{dur:.3f}"]
    bg = hexcol(pr.c["slate"])
    if src is None:
        sh = pr.shots.get(shot, {})
        lines = [f"FOOTAGE NEEDED: {shot}", ""] + textwrap.wrap(sh.get("purpose", ""), 44 if pr.fmt == "horizontal" else 26) + [""] + \
                textwrap.wrap(f"Capture: {sh.get('slug', '')}  ({'you' if sh.get('cat') in 'BC' else 'automated'})", 44 if pr.fmt == "horizontal" else 26)
        vf = dt(pr, "\n".join(lines), pr.size("lower_third_size"), pr.c["text"], "(w-text_w)/2", "(h-text_h)/2", name="slate", primary=False, spacing=14)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={bg}:s={W}x{H}:r={fps}", "-vf", vf, *enc, out])
        return out, "slate"
    tag = ""
    if label:
        tag = "," + dt(pr, label, max(20, pr.size("lower_third_size") // 2 + 2), pr.c["highlight"], "24", "h-th-24", box=hexcol(pr.c["background"], 0.8), name="lbl")
    pre = ["-ss", f"{start:.2f}"] if start else []
    if pr.fmt == "horizontal":
        vf = f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg},setsar=1,tpad=stop_mode=clone:stop_duration={dur:.2f}{tag}"
        run(["ffmpeg", "-v", "error", "-y", *pre, "-i", src, "-vf", vf, *enc, out])
    else:  # vertical: blurred fill behind, the real screen recording kept intact in front
        fc = (f"[0:v]fps={fps},tpad=stop_mode=clone:stop_duration={dur:.2f},split[a][b];"
              f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:6,eq=brightness=-0.12[bg];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1{tag}[v]")
        run(["ffmpeg", "-v", "error", "-y", *pre, "-i", src, "-filter_complex", fc, "-map", "[v]", *enc, out])
    return out, "clip"


# ------------------------------------------------------------------ captions ----------------------------------------

def chunk_words(text, max_chars, max_lines):
    """Split narration into caption cards: break at sentence ends first, then at commas, then by length."""
    words, cards, cur = text.split(), [], []
    limit = max_chars * max_lines
    for w in words:
        cur.append(w)
        s = " ".join(cur)
        if re.search(r"[.!?]$", w) or (len(s) > limit * 0.6 and re.search(r"[,;:]$", w)) or len(s) >= limit - 6:
            cards.append(s)
            cur = []
    if cur:
        cards.append(" ".join(cur))
    return cards


def wrap_card(card, max_chars, max_lines):
    lines = textwrap.wrap(card, max_chars) or [card]
    return lines[:max_lines] if len(lines) <= max_lines else textwrap.wrap(card, max(max_chars, len(card) // max_lines + 4))[:max_lines]


def srt_time(t):
    t = max(0, t)
    return f"{int(t // 3600):02}:{int(t % 3600 // 60):02}:{int(t % 60):02},{int(round((t % 1) * 1000)) % 1000:03}"


def ass_time(t):
    t = max(0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02}:{int(t % 60):02}.{int((t % 1) * 100):02}"


def caption_cues(pr, scene_text, t0, vo_len, lead, tail, placeholder_gap_s):
    """Cue timing is PROPORTIONAL (by character count) across the narration. It is an estimate, not forced alignment:
    for exact sync, replace captions/*.srt with a transcription of your real recording (e.g. Descript or Whisper)."""
    cfg = pr.cfg["text"]
    mc, ml = cfg["caption_max_chars_per_line"][pr.fmt], cfg["caption_max_lines"]
    # split around placeholders: each placeholder is a silent gap (its words are not captioned)
    segs = re.split(r"(" + PLACEHOLDER.pattern + ")", scene_text)
    items = []
    for s in segs:
        if PLACEHOLDER.fullmatch(s or ""):
            items.append(("gap", placeholder_gap_s))
        else:
            for card in chunk_words(re.sub(r"\s+", " ", s).strip(), mc, ml):
                items.append(("card", card))
    weights = [max(8, len(v)) if k == "card" else placeholder_gap_s * 14 for k, v in items]
    span = max(0.1, vo_len - lead - tail)
    cues, t, total = [], t0 + lead, sum(weights) or 1
    for (k, v), w in zip(items, weights):
        d = span * w / total
        if k == "card":
            cues.append((t, t + d * 0.97, wrap_card(v, mc, ml)))
        t += d
    return cues


def write_captions(pr, cues, base: Path):
    cfg = pr.cfg["text"]
    base.with_suffix(".srt").write_text("".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n" + "\n".join(l) + "\n\n" for i, (a, b, l) in enumerate(cues, 1)))
    hl = {w.lower() for w in cfg["caption_highlight_words"]}
    hcol = pr.c["highlight"].lstrip("#")
    bgr = lambda h: h[4:6] + h[2:4] + h[0:2]
    size, mv = pr.size("caption_size"), pr.size("caption_margin_v")
    op = int((1 - cfg["caption_background_opacity"]) * 255)
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {pr.W}\nPlayResY: {pr.H}\nWrapStyle: 2\n\n[V4+ Styles]\n"
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
            f"Style: Cap,{pr.cfg['brand']['caption_font_name']},{size},&H00FFFFFF,&H00FFFFFF,&H{op:02X}{bgr('0A0F1A')},&H{op:02X}{bgr('0A0F1A')},1,0,0,0,100,100,0,0,3,14,0,2,60,60,{mv},1\n\n"
            "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n")

    def mark(line):
        return " ".join((r"{\c&H" + bgr(hcol) + r"&}" + w + r"{\c&HFFFFFF&}") if re.sub(r"\W", "", w).lower() in hl else w for w in line.split(" "))
    body = "".join(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Cap,,0,0,0,," + r"\N".join(mark(x) for x in l) + "\n" for a, b, l in cues)
    base.with_suffix(".ass").write_text(head + body)


# ------------------------------------------------------------------ scenes -------------------------------------------

def scene_overlays(pr, ov_list, D, include_unconfirmed, skipped):
    fs = []
    hs, ls, tg = pr.size("heading_size"), pr.size("lower_third_size"), pr.size("lower_third_size")
    for ov in ov_list:
        if ov.get("needs_confirm") and not include_unconfirmed:
            skipped.append(ov["text"])
            continue
        a, b = ov["at"] * D, min(D, (ov["at"] + ov["dur"]) * D)
        k = ov.get("kind", "lower")
        en = (a, b)
        if k == "full":
            fs.append(f"drawbox=x=0:y=0:w=iw:h=ih:color={hexcol(pr.c['background'], 0.94)}:t=fill:enable='between(t,{a:.3f},{b:.3f})'")
            fs.append(dt(pr, ov["text"], hs, pr.c["text"], "(w-text_w)/2", "(h-text_h)/2-%d" % (60 if ov.get("sub") else 0), en, name="full", align="center", spacing=18))
            if ov.get("sub"):
                fs.append(dt(pr, ov["sub"], ls, pr.c["highlight"], "(w-text_w)/2", "(h+text_h)/2+%d" % (hs // 2), en, name="sub", primary=False))
        elif k == "hook":
            fs.append(dt(pr, ov["text"], hs, pr.c["text"], "(w-text_w)/2", "h*0.10", en, box=hexcol(pr.c["background"], 0.78), name="hook", align="center", spacing=12))
        elif k == "tag":
            fs.append(dt(pr, ov["text"], max(20, tg // 2), pr.c["highlight"], "w-text_w-28", "28", en, box=hexcol(pr.c["background"], 0.8), name="tag", primary=False))
        else:
            fs.append(dt(pr, ov["text"], ls, pr.c["text"], "w*0.05" if pr.fmt == "horizontal" else "(w-text_w)/2", "h*0.70" if pr.fmt == "horizontal" else "h*0.16", en, box=hexcol(pr.c["background"], 0.78), name="lower", primary=False))
    return fs


def build_scene(pr, scene, vo_dir, args, rep, params):
    sid = scene["id"]
    a = pr.cfg["audio"]
    vo_real = vo_dir / scene["file"]
    vo_scr = vo_dir / "_scratch" / (Path(scene["file"]).stem + "_scratch.wav")
    if vo_real.exists():
        vo, vsrc = vo_real, "real"
    elif args.scratch_vo and vo_scr.exists():
        vo, vsrc = vo_scr, "scratch"
    else:
        vo, vsrc = None, "missing"
    if vo:
        vo_len = duration(vo)
        D = vo_len + a["lead_in_s"] + a["tail_s"]
    else:
        D = est_seconds(scene["voiceover"], params["wps"], params["pp"], params["phw"]) + a["lead_in_s"] + a["tail_s"]
        vo_len = D - a["lead_in_s"] - a["tail_s"]
    weights = [c.get("weight", 1) for c in scene["clips"]]
    parts, used, total_w = [], [], sum(weights)
    for c, w in zip(scene["clips"], weights):
        src = pr.find_clip(c["shot"])
        if src is None and c.get("optional"):
            total_w -= w
            rep["optional_skipped"].append(c["shot"])
            continue
        used.append((c, src, w))
    total_w = sum(w for _, _, w in used) or 1
    for c, src, w in used:
        d = D * w / total_w
        p, kind = render_clip(pr, c["shot"], src, d)
        parts.append(p)
        rep["clips"].append(dict(scene=sid, shot=c["shot"], kind=kind, seconds=round(d, 2), source=src.name if src else None))
        if kind == "slate":
            rep["missing_clips"].append(c["shot"])
    skipped = []
    key = sha(scene, vsrc, stamp(vo), [stamp(p) for p in parts], args.include_unconfirmed, pr.cfg, pr.fmt, rep["proof_text"])
    out = pr.work / f"scene_{sid}_{key}.mp4"
    aud = pr.work / f"scene_{sid}_{key}.wav"
    if not out.exists():
        lst = pr.work / f"list_{sid}.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        raw = pr.work / f"raw_{sid}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", raw])
        fs = scene_overlays(pr, scene.get("overlays", []), D, args.include_unconfirmed, skipped)
        if rep["proof_text"]:
            fs.append(dt(pr, rep["proof_text"], max(18, pr.size("lower_third_size") // 2), "white", "24", "24", box=hexcol("#B3261E", 0.85), name="proof", primary=False))
        t = pr.cfg["motion"]["transition_s"] if pr.cfg["motion"]["transition"] == "dip" else 0
        if t:
            fs += [f"fade=t=in:st=0:d={t}", f"fade=t=out:st={D - t:.3f}:d={t}"]
        vf = ",".join(fs) if fs else "null"
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(pr.fps), "-an", out])
        # audio: lead-in silence + narration + tail, exactly D long
        if vo:
            run(["ffmpeg", "-v", "error", "-y", "-i", vo, "-af", f"aresample=48000,aformat=channel_layouts=stereo,adelay={int(a['lead_in_s'] * 1000)}:all=1,apad=whole_dur={D:.3f},afade=t=in:d=0.02,atrim=0:{D:.3f}", aud])
        else:
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", f"{D:.3f}", aud])
    else:
        fs = scene_overlays(pr, scene.get("overlays", []), D, args.include_unconfirmed, skipped)
    rep["overlays_skipped_unconfirmed"] += skipped
    rep["scenes"].append(dict(id=sid, seconds=round(D, 2), narration=vsrc, clips=len(parts)))
    if vsrc != "real":
        rep["narration_not_final"].append(f"{sid} ({vsrc})")
    return out, aud, D, vo_len, vsrc


def assemble(pr, name, scenes, vo_dir, args, params, outname, burn, label):
    rep = dict(name=name, format=pr.fmt, scenes=[], clips=[], missing_clips=[], optional_skipped=[], narration_not_final=[], overlays_skipped_unconfirmed=[], proof_text="")
    placeholders = sum(len(PLACEHOLDER.findall(s["voiceover"])) for s in scenes)
    pre_missing = [c["shot"] for s in scenes for c in s["clips"] if pr.find_clip(c["shot"]) is None and not c.get("optional")]
    reasons = []
    if pre_missing:
        reasons.append(f"{len(set(pre_missing))} footage gap(s)")
    if any(not (vo_dir / s["file"]).exists() for s in scenes):
        reasons.append("narration not recorded" if not args.scratch_vo else "scratch narration")
    if placeholders:
        reasons.append(f"{placeholders} script placeholder(s)")
    proof = bool(reasons)
    if proof and pr.cfg["proof"]["watermark"]:
        rep["proof_text"] = pr.cfg["proof"]["watermark_text"] + "\n" + "\n".join(textwrap.wrap("; ".join(reasons), 62 if pr.fmt == "horizontal" else 40))
    vids, auds, t0, cues = [], [], 0.0, []
    a = pr.cfg["audio"]
    gap_s = params["phw"] / params["wps"]
    for s in scenes:
        v, au, D, vo_len, vsrc = build_scene(pr, s, vo_dir, args, rep, params)
        vids.append(v)
        auds.append(au)
        cues += caption_cues(pr, s["voiceover"], t0, D, a["lead_in_s"], a["tail_s"], gap_s)
        rep["scenes"][-1]["starts_at"] = round(t0, 2)
        t0 += D
    caps = pr.ep / "captions" / (outname + ("_scratch" if args.scratch_vo and any(x["narration"] == "scratch" for x in rep["scenes"]) else ""))
    write_captions(pr, cues, caps)
    lv, la = pr.work / f"{outname}_v.txt", pr.work / f"{outname}_a.txt"
    lv.write_text("".join(f"file '{p}'\n" for p in vids))
    la.write_text("".join(f"file '{p}'\n" for p in auds))
    vcat, acat = pr.work / f"{outname}_v.mp4", pr.work / f"{outname}_a.wav"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lv, "-c", "copy", vcat])
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", la, "-c", "copy", acat])
    # audio finishing: optional music bed (ducked under narration), then loudness normalisation
    music = a.get("music_file")
    music_path = (pr.ep / music) if music else None
    lufs, tp = a["narration_target_lufs"], a["true_peak_db"]
    if music_path and music_path.exists():
        af = (f"[1:a]aresample=48000,aloop=loop=-1:size=2e9,atrim=0:{t0:.2f},volume={a['music_db']}dB[m];[0:a]asplit[n1][n2];"
              f"[m][n1]sidechaincompress=threshold=0.04:ratio=8:attack=20:release=400:makeup=1[d];[n2][d]amix=inputs=2:normalize=0,loudnorm=I={lufs}:TP={tp}:LRA=11[a]")
        run(["ffmpeg", "-v", "error", "-y", "-i", acat, "-i", music_path, "-filter_complex", af, "-map", "[a]", pr.work / f"{outname}_mix.wav"])
        rep["music"] = music
    else:
        run(["ffmpeg", "-v", "error", "-y", "-i", acat, "-af", f"loudnorm=I={lufs}:TP={tp}:LRA=11", "-ar", "48000", pr.work / f"{outname}_mix.wav"])
        rep["music"] = None
    mix = pr.work / f"{outname}_mix.wav"
    out = pr.ep / "exports" / (outname + ("_PROOF" if proof else "") + ".mp4")
    out.parent.mkdir(exist_ok=True)
    v = pr.cfg["video"]
    vf = []
    if burn:
        shutil.copy(caps.with_suffix(".ass"), pr.work / "burn.ass")
        vf = ["-vf", f"subtitles=burn.ass:fontsdir={pr.cfg['brand']['fonts_dir']}"]
    run(["ffmpeg", "-v", "error", "-y", "-i", vcat, "-i", mix, *vf, "-c:v", "libx264", "-preset", v["preset"], "-crf", str(v["crf"]), "-maxrate", v["maxrate"], "-bufsize", v["bufsize"],
         "-pix_fmt", "yuv420p", "-r", str(pr.fps), "-c:a", "aac", "-b:a", v["audio_bitrate"], "-ar", "48000", "-movflags", "+faststart", "-shortest", out], cwd=pr.work)
    rep.update(output=str(out.relative_to(pr.ep)), status="NOT FINAL (assembly proof)" if proof else "ASSEMBLED (needs QA + human review)", reasons=reasons,
               total_seconds=round(t0, 2), captions=str(caps.with_suffix(".srt").relative_to(pr.ep)), captions_timing="estimated from text length, not forced-aligned",
               burned_captions=burn, placeholders_in_script=placeholders, missing_clips=sorted(set(rep["missing_clips"])), proof_text=None)
    (pr.ep / "production-reports").mkdir(exist_ok=True)
    (pr.ep / "production-reports" / f"build_{outname}.json").write_text(json.dumps(rep, indent=1))
    print(f"{rep['status']}: {out.name}  {t0:.1f}s  missing clips={rep['missing_clips']}  reasons={reasons}")
    return rep


# ------------------------------------------------------------------ scratch voice ------------------------------------

def scratch_vo(ep: Path, content):
    if not shutil.which("espeak-ng"):
        sys.exit("espeak-ng not installed (only needed for scratch guide tracks)")
    out = ep / "voiceover" / "_scratch"
    out.mkdir(parents=True, exist_ok=True)
    items = [(s["file"], s["voiceover"]) for s in content["episode"]["scenes"]] + [(s["file"], s["voiceover"]) for s in content["shorts"]["shorts"]]
    for fn, text in items:
        t = PLACEHOLDER.sub(" . . . . . . ", text)
        tf = out / "_t.txt"
        tf.write_text(t)
        wav = out / (Path(fn).stem + "_scratch.wav")
        run(["espeak-ng", "-v", "en-us", "-s", "155", "-p", "42", "-f", tf, "-w", wav])
        print("scratch", wav.name, round(duration(wav), 1), "s")
    (out / "_t.txt").unlink(missing_ok=True)
    (out / "README.txt").write_text("ROBOT GUIDE TRACKS, NOT NARRATION. Generated with espeak-ng only to test timing, captions and audio handling.\nNever publish these. Record the real VO_*.wav files in ../ and they take priority automatically.\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["scratch-vo", "episode", "short", "all"])
    ap.add_argument("which", nargs="?", help="short id (S1..S3) for 'short'")
    ap.add_argument("--episode-dir", default=str(HERE.parent / "episode-001"))
    ap.add_argument("--scratch-vo", action="store_true", help="use robot guide tracks where real narration is missing")
    ap.add_argument("--include-unconfirmed", action="store_true", help="draw overlays flagged needs_confirm")
    ap.add_argument("--no-burn", action="store_true", help="do not burn captions into the video")
    args = ap.parse_args()
    ep = Path(args.episode_dir)
    ed = ep / "editing-project"
    n = re.search(r"(\d+)$", ep.name).group(1)
    content = dict(episode=json.loads((ed / f"episode_{n}.json").read_text()), shorts=json.loads((ed / f"shorts_{n}.json").read_text()))
    if args.cmd == "scratch-vo":
        return scratch_vo(ep, content)
    cfg_burn = json.loads((ed / "video_style_config.json").read_text())["captions"]
    todo = []
    if args.cmd in ("episode", "all"):
        todo.append(("episode", None))
    if args.cmd == "all":
        todo += [("short", s["id"]) for s in content["shorts"]["shorts"]]
    if args.cmd == "short":
        todo.append(("short", args.which))
    for kind, which in todo:
        if kind == "episode":
            e = content["episode"]
            pr = Project(ep, "horizontal")
            params = dict(wps=e["words_per_second"], pp=e["paragraph_pause_s"], phw=e["placeholder_words"])
            assemble(pr, f"episode_{n}", e["scenes"], ep / "voiceover", args, params, f"EPISODE_{n}_long", cfg_burn["burn_in_long"] and not args.no_burn, "long")
        else:
            sh = next((s for s in content["shorts"]["shorts"] if s["id"] == which), None)
            if not sh:
                sys.exit(f"no such short: {which}")
            pr = Project(ep, "vertical")
            scene = dict(id=sh["id"], file=sh["file"], voiceover=sh["voiceover"], clips=sh["clips"], overlays=sh["overlays"])
            params = dict(wps=content["shorts"]["words_per_second"], pp=0.4, phw=content["shorts"]["placeholder_words"])
            assemble(pr, f"short_{sh['id']}", [scene], ep / "voiceover", args, params, f"SHORT_{sh['id']}_{sh['slug']}", cfg_burn["burn_in_short"] and not args.no_burn, "short")


if __name__ == "__main__":
    main()
