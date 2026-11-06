#!/usr/bin/env python3
"""Builds the thumbnail concepts (1280x720) from real frames of the captured product footage.
No photo of the presenter exists yet, so each concept reserves a PHOTO SLOT and the files in thumbnails/ are DRAFTS until a real photo is composited."""
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

EP = Path(__file__).resolve().parents[1] / "episode-001"
FONT_X = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_M = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
BG, TXT, ACC = (10, 15, 26), (245, 247, 250), (242, 176, 30)
W, H = 1280, 720


def frame(clip_glob, t, out):
    src = next((EP / "screen-recordings" / "product-demo").glob(clip_glob), None)
    if not src:
        sys.exit(f"missing footage {clip_glob}; run the capture first")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(src), "-frames:v", "1", str(out)], check=True)
    return Image.open(out).convert("RGB")


def rounded(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, *im.size], r, fill=255)
    im = im.convert("RGBA")
    im.putalpha(m)
    return im


def shadowed(base, im, xy, blur=26, off=18):
    sh = Image.new("RGBA", (im.width + 120, im.height + 120), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([60, 60 + off, 60 + im.width, 60 + im.height + off], 26, fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(sh, (xy[0] - 60, xy[1] - 60))
    base.alpha_composite(im, xy)


def text(d, xy, s, size, fill, font=FONT_X, anchor="la", stroke=0):
    d.text(xy, s, font=ImageFont.truetype(font, size), fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))


def photo_slot(d, box):
    x0, y0, x1, y1 = box
    for i in range(x0, x1, 22):  # dashed outline: obviously a placeholder
        d.line([(i, y0), (min(i + 11, x1), y0)], fill=(138, 151, 173), width=3)
        d.line([(i, y1), (min(i + 11, x1), y1)], fill=(138, 151, 173), width=3)
    for j in range(y0, y1, 22):
        d.line([(x0, j), (x0, min(j + 11, y1))], fill=(138, 151, 173), width=3)
        d.line([(x1, j), (x1, min(j + 11, y1))], fill=(138, 151, 173), width=3)
    text(d, ((x0 + x1) // 2, (y0 + y1) // 2), "PHOTO SLOT\n(your photo)", 30, (138, 151, 173), FONT_M, "mm")


def vignette(im):
    v = Image.new("L", (W, H), 0)
    ImageDraw.Draw(v).ellipse([-W * 0.2, -H * 0.4, W * 1.2, H * 1.4], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(150))
    dark = Image.new("RGBA", (W, H), (*BG, 255))
    return Image.composite(im, dark, v)


def t1(shot):
    im = Image.new("RGBA", (W, H), (*BG, 255))
    ui = rounded(shot.resize((640, 400)), 24)
    bg = shot.resize((W, H)).filter(ImageFilter.GaussianBlur(22)).convert("RGBA")
    bg = Image.blend(bg, Image.new("RGBA", (W, H), (*BG, 255)), 0.82)
    im = vignette(bg)
    shadowed(im, ui, (600, 300))
    d = ImageDraw.Draw(im)
    text(d, (56, 56), "BUILDING", 138, TXT)
    text(d, (56, 190), "FROM ZERO", 138, ACC)
    text(d, (60, 372), "EPISODE 001", 34, (138, 151, 173), FONT_M)
    photo_slot(d, (40, 440, 420, 690))
    return im.convert("RGB")


def t2(shot):
    bg = shot.resize((W, H)).filter(ImageFilter.GaussianBlur(10)).convert("RGBA")
    im = vignette(Image.blend(bg, Image.new("RGBA", (W, H), (*BG, 255)), 0.72))
    d = ImageDraw.Draw(im)
    text(d, (W // 2, 210), "THE BOOTSTRAPPER", 118, TXT, anchor="mm")
    text(d, (W // 2, 350), "EXPERIMENT", 160, ACC, anchor="mm")
    text(d, (W // 2, 520), "A business + the software to run it", 44, (200, 208, 222), FONT_M, "mm")
    d.rounded_rectangle([W // 2 - 130, 600, W // 2 + 130, 664], 32, fill=ACC)
    text(d, (W // 2, 632), "EP 001", 40, BG, anchor="mm")
    return im.convert("RGB")


def t3(a, b):
    im = Image.new("RGBA", (W, H), (*BG, 255))
    d = ImageDraw.Draw(im)
    for i, (shot, x) in enumerate(((a, 40), (b, 660))):
        shadowed(im, rounded(shot.resize((580, 362)), 20), (x, 250))
    d = ImageDraw.Draw(im)
    text(d, (40, 40), "TWO BUSINESSES.", 92, TXT)
    text(d, (40, 138), "ONE EXPERIMENT.", 92, ACC)
    text(d, (330, 640), "1  Win customers", 34, TXT, FONT_M, "mm")
    text(d, (950, 640), "2  Build the tool", 34, TXT, FONT_M, "mm")
    return im.convert("RGB")


def main():
    g = EP / "graphics"
    g.mkdir(exist_ok=True)
    today = frame("EP001_A05_*", 6, g / "frame_today.png")
    pipe = frame("EP001_A09_*", 5, g / "frame_pipeline.png")
    play = frame("EP001_A08_*", 22, g / "frame_playbook.png")
    out = EP / "thumbnails"
    out.mkdir(exist_ok=True)
    items = [("T1_building-from-zero_DRAFT.jpg", t1(today)), ("T2_bootstrapper-experiment_DRAFT.jpg", t2(pipe)), ("T3_two-businesses_DRAFT.jpg", t3(today, play))]
    for name, im in items:
        im.save(out / name, quality=90)
        im.resize((168, 94)).save(g / ("small_" + name.split("_")[0] + ".png"))
    sheet = Image.new("RGB", (W, H + 140), BG)
    for i, (n, im) in enumerate(items[:1]):
        sheet.paste(im, (0, 0))
    row = Image.new("RGB", (3 * 170 + 40, 100), BG)
    for i, (n, _) in enumerate(items):
        row.paste(Image.open(g / ("small_" + n.split("_")[0] + ".png")), (i * 190, 3))
    row.save(g / "small_size_check.png")
    print("thumbnails:", [n for n, _ in items])


if __name__ == "__main__":
    main()
