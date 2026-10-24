"""Gentle Little Reminders: 6-second seamless loop reel renderer.

    python3 quotes/render_loop.py STORY.json OUT_DIR

STORY.json:
{
  "slug": "be-gentle-cloud",
  "art": "/path/art.png",          # ElevenLabs illustration on a plain white background
  "lines": ["Be gentle with yourself.", "You are doing the best", "you can, and that is enough."],
  "highlight": "gentle",           # optional: one word drawn in coral
  "motion": "float",               # float | swing | sway | breathe | spin
  "music": "quotes/music/musicbox.mp3",
  "music_start": 0                 # optional: seconds into the track
}

Output: OUT_DIR/<slug>.mp4 (1080x1920, 30fps, exactly 6 s) and OUT_DIR/<slug>-cover.jpg.
The loop is seamless: every motion, the line boil and the paper are periodic in exactly 6 s,
the text is static from frame 0 (no fade), and the music tail is crossfaded into its head,
so viewers do not notice where the video restarts.
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 6.0
N = int(FPS * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
INK = (44, 42, 46)
CORAL = (226, 110, 96)
GREY = (150, 146, 140)


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


def paper(seed=7):
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    for scale, amp in [(4, 10), (16, 5), (64, 2.5), (256, 1.2)]:
        small = rng.standard_normal((H // scale + 2, W // scale + 2)).astype(np.float32)
        img = Image.fromarray(small).resize((W + scale * 2, H + scale * 2), Image.BICUBIC)
        acc += np.asarray(img)[:H, :W] * amp
    yy, xx = np.mgrid[0:H, 0:W]
    shade = -6 * ((xx / W - 0.5) ** 2 + (yy / H - 0.45) ** 2)
    base = 239 + acc * 0.5 + shade
    rgb = np.stack([base + 1, base, base - 4], -1)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def prep_art(path, box=820):
    art = Image.open(path).convert("RGB")
    # trim white margins
    g = np.asarray(art.convert("L"))
    ys, xs = np.where(g < 235)
    if len(xs):
        pad = 20
        art = art.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0),
                        min(xs.max() + pad, art.width), min(ys.max() + pad, art.height)))
    s = box / max(art.size)
    art = art.resize((int(art.width * s), int(art.height * s)), Image.LANCZOS)
    # push near-white to pure white so multiply shows the paper
    a = np.asarray(art).astype(np.float32)
    lum = a.mean(-1, keepdims=True)
    a = np.where(lum > 228, 255, a)
    return Image.fromarray(a.astype(np.uint8))


def boil_frames(art, n=12, seed=3):
    """n slightly wobbled copies; cycled through so the wobble repeats inside the loop."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        dx, dy = rng.uniform(-1.6, 1.6, 2)
        ang = rng.uniform(-0.35, 0.35)
        im = art.rotate(ang, resample=Image.BICUBIC, translate=(dx, dy), fillcolor=(255, 255, 255))
        out.append(im)
    return out


def motion(kind, t):
    """Returns (dx, dy, angle_deg, scale) at time t; every term is periodic in DUR."""
    p = 2 * math.pi * t / DUR
    if kind == "swing":
        return 0, 0, 6 * math.sin(p), 1.0
    if kind == "sway":
        return 14 * math.sin(p), 0, 2.5 * math.sin(p + 0.6), 1.0
    if kind == "breathe":
        return 0, 6 * math.sin(p), 0, 1.0 + 0.035 * math.sin(p)
    if kind == "spin":
        return 0, 0, -360 * t / DUR, 1.0
    # float (default): two gentle bobs and one side drift per loop
    return 10 * math.sin(p), 24 * math.sin(2 * p), 1.5 * math.sin(p), 1.0


def draw_text(img, lines, highlight=None, top=1330):
    d = ImageDraw.Draw(img)
    f = font("Caveat-Regular.ttf", 82)
    fh = font("Caveat-SemiBold.ttf", 82)
    lh = 96
    y = top
    for line in lines:
        words = line.split(" ")
        widths = []
        for w in words:
            ff = fh if highlight and w.strip(".,!?").lower() == highlight.lower() else f
            widths.append((w, ff, d.textlength(w, font=ff)))
        space = d.textlength(" ", font=f)
        total = sum(x[2] for x in widths) + space * (len(words) - 1)
        x = (W - total) / 2
        for w, ff, wd in widths:
            col = CORAL if ff is fh else INK
            d.text((x, y), w, font=ff, fill=col)
            x += wd + space
        y += lh
    wm = font("Caveat-Regular.ttf", 40)
    t = "Gentle Little Reminders"
    d.text(((W - d.textlength(t, font=wm)) / 2, 1790), t, font=wm, fill=GREY)


def render(story, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    slug = story["slug"]
    bg = paper()
    draw_text(bg, story["lines"], story.get("highlight"))
    if story.get("top_line"):
        d = ImageDraw.Draw(bg)
        f = font("Caveat-SemiBold.ttf", 70)
        t = story["top_line"]
        d.text(((W - d.textlength(t, font=f)) / 2, 230), t, font=f, fill=INK)
    art = prep_art(story["art"], story.get("art_size", 820))
    boils = boil_frames(art)
    cx, cy = W // 2, story.get("art_y", 820)
    kind = story.get("motion", "float")

    tmp = os.path.join(out_dir, slug + "-silent.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                           "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium", tmp],
                          stdin=subprocess.PIPE)
    cover = None
    for i in range(N):
        t = i / FPS
        dx, dy, ang, sc = motion(kind, t)
        a = boils[(i // 3) % len(boils)]  # 60 boil steps / 12 frames = 5 full cycles per loop
        if sc != 1.0:
            a = a.resize((int(a.width * sc), int(a.height * sc)), Image.BICUBIC)
        if ang:
            a = a.rotate(ang, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
        layer = Image.new("RGB", (W, H), (255, 255, 255))
        layer.paste(a, (int(cx - a.width / 2 + dx), int(cy - a.height / 2 + dy)))
        frame = ImageChops.multiply(bg, layer)
        if i == 0:
            cover = frame
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()

    out = os.path.join(out_dir, slug + ".mp4")
    music = story.get("music")
    if music:
        if not os.path.isabs(music):
            music = os.path.join(os.path.dirname(HERE), music)
        ss = story.get("music_start", 0)
        x = 1.0  # crossfade seconds: the clip's tail fades into its own head
        fc = (f"[1:a]atrim={ss}:{ss + DUR + x},asetpts=PTS-STARTPTS,loudnorm=I=-18:TP=-2,"
              f"asplit[a][b];"
              f"[a]atrim=0:{DUR},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={x}[head];"
              f"[b]atrim={DUR}:{DUR + x},asetpts=PTS-STARTPTS,afade=t=out:st=0:d={x}[tail];"
              f"[head][tail]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.9[m]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", music, "-filter_complex", fc,
                        "-map", "0:v", "-map", "[m]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-t", str(DUR), "-movflags", "+faststart", out], check=True)
        os.remove(tmp)
    else:
        os.replace(tmp, out)
    cover.convert("RGB").save(os.path.join(out_dir, slug + "-cover.jpg"), quality=90)
    print(out)


if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2])
