"""On This Day USA renderer: vintage 9:16 reel + cover + 4:5 image post, plus page branding.

    python3 history/render.py story.json OUT_DIR
    python3 history/render.py --branding OUT_DIR

story.json:
{
  "slug": "yorktown-surrender-1781",
  "date": "October 19",            # month + day shown on the intro card
  "year": 1781,
  "headline": "The British surrender at Yorktown",
  "voice_mp3": "/abs/voice.mp3",   # ONE file = all scene texts read in order
  "post_facts": ["...", "..."],
  "scenes": [
    {"type": "intro", "text": "[dramatic] October 19th, 1781. ..."},
    {"type": "photo", "image": "/abs/a.jpg", "label": "Yorktown, Virginia", "caption": "Painting by John Trumbull, 1820", "text": "..."},
    {"type": "stat", "value": 8000, "suffix": "", "label": "British soldiers laid down their arms", "text": "..."},
    {"type": "text", "title": "The war was effectively over", "image": "/abs/b.jpg", "text": "..."},
    {"type": "question", "title": "Did you learn this in school?", "text": "..."},
    {"type": "cta", "text": "[warmly] Follow On This Day USA for a new story from history, every day."}
  ]
}
"""
import json, os, random, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance, ImageChops

W, H, FPS = 1080, 1920, 30
PAPER = (239, 228, 204)
PAPER_DARK = (222, 206, 175)
INK = (42, 31, 23)
RED = (155, 44, 31)
NAVY = (47, 62, 85)
GOLD = (176, 141, 87)
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "brief", "fonts")


def font(name, size, var=None):
    paths = {
        "display": "AbrilFatface-Regular.ttf",
        "serif": "PlayfairDisplay[wght].ttf",
        "old": "OldStandard-Bold.ttf",
        "oldr": "OldStandard-Regular.ttf",
        "type": "SpecialElite-Regular.ttf",
        "cond": "Oswald[wght].ttf",
    }
    try:
        f = ImageFont.truetype(os.path.join(FD, paths[name]), size)
        if var:
            f.set_variation_by_name(var)
        return f
    except Exception:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", size)


def spoken(t):
    return re.sub(r"\[[^\]]*\]", " ", t).replace("...", " ").strip()


def words(t):
    return [w for w in spoken(t).split() if w]


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, fname, max_w, max_h, start=110, min_size=40, lh=1.12, var=None):
    s = start
    while s >= min_size:
        f = font(fname, s, var)
        ls = wrap(d, text, f, max_w)
        if len(ls) * s * lh <= max_h:
            return f, ls, s
        s -= 4
    f = font(fname, min_size, var)
    return f, wrap(d, text, f, max_w), min_size


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# ---------- textures ----------
def paper(w, h, seed=7):
    rnd = random.Random(seed)
    base = Image.new("RGB", (w, h), PAPER)
    noise = Image.effect_noise((w // 2, h // 2), 18).resize((w, h), Image.BILINEAR)
    base = Image.composite(Image.new("RGB", (w, h), PAPER_DARK), base, noise.point(lambda v: int(v * 0.35)))
    # soft blotches
    blot = Image.new("L", (w, h), 0)
    bd = ImageDraw.Draw(blot)
    for _ in range(14):
        x, y, r = rnd.randint(0, w), rnd.randint(0, h), rnd.randint(80, 260)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=rnd.randint(10, 28))
    blot = blot.filter(ImageFilter.GaussianBlur(60))
    base = Image.composite(Image.new("RGB", (w, h), (205, 186, 150)), base, blot)
    # vignette
    vig = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vig).ellipse([-w * 0.25, -h * 0.15, w * 1.25, h * 1.15], fill=255)
    vig = ImageOps.invert(vig.filter(ImageFilter.GaussianBlur(min(w, h) // 5))).point(lambda v: int(v * 0.55))
    return Image.composite(Image.new("RGB", (w, h), (150, 120, 85)), base, vig)


def sepia(img):
    g = ImageOps.grayscale(img.convert("RGB"))
    g = ImageEnhance.Contrast(g).enhance(1.08)
    s = ImageOps.colorize(g, black=(38, 26, 16), mid=(150, 118, 82), white=(245, 232, 205))
    grain = Image.effect_noise(s.size, 22).convert("RGB")
    return Image.blend(s, ImageChops.multiply(s, ImageOps.autocontrast(grain).point(lambda v: 200 + v // 5)), 0.6)


def cover_crop(img, w, h):
    return ImageOps.fit(img.convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.42))


def print_frame(img, w, h, border=26):
    """Old photo print: sepia image inside a cream border with a thin dark keyline."""
    card = Image.new("RGB", (w + border * 2, h + border * 2), (246, 238, 220))
    card.paste(sepia(cover_crop(img, w, h)), (border, border))
    ImageDraw.Draw(card).rectangle([border - 3, border - 3, border + w + 2, border + h + 2], outline=(90, 70, 50), width=2)
    return card


def paste_rot(canvas, im, xy, angle):
    im = im.convert("RGBA").rotate(angle, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.paste((40, 25, 10, 110), (0, 0), im.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    x, y = xy
    canvas.paste(sh, (x + 10, y + 16), sh)
    canvas.paste(im, (x, y), im)


def star(d, cx, cy, r, fill):
    import math
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = math.radians(-90 + i * 36)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def stars(d, cx, cy, r, fill, gap=None, n=3):
    gap = gap or r * 3.2
    for i in range(n):
        star(d, cx + (i - (n - 1) / 2) * gap, cy, r, fill)


# ---------- brand ----------
def badge(size=300):
    """Round vintage stamp logo."""
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, s - 1, s - 1], fill=RED)
    d.ellipse([s * 0.05, s * 0.05, s * 0.95, s * 0.95], outline=(246, 236, 214), width=int(s * 0.018))
    d.ellipse([s * 0.2, s * 0.2, s * 0.8, s * 0.8], fill=(246, 236, 214))
    # ring text spread evenly around the full circle, with drawn stars as separators
    import math
    ring = font("cond", int(s * 0.088), "Bold")
    r = s * 0.375
    parts = ["ON THIS DAY", "*", "USA", "*", "SINCE 1776", "*"]
    seq = []
    for p in parts:
        seq += [p] if p == "*" else list(p)
    widths = [s * 0.07 if c == "*" else d.textlength(c, font=ring) for c in seq]
    circ = 2 * math.pi * r * 0.97
    extra = (circ - sum(widths)) / len(seq)
    cur = -90.0 - (widths[0] / 2) / r * 180 / math.pi
    cream = (246, 236, 214)
    for c, cw in zip(seq, widths):
        a = cur + (cw / 2) / r * 180 / math.pi
        x = s / 2 + r * math.cos(math.radians(a))
        y = s / 2 + r * math.sin(math.radians(a))
        if c == "*":
            star(d, x, y, s * 0.028, cream)
        else:
            ch = Image.new("RGBA", (int(s * 0.12), int(s * 0.12)), (0, 0, 0, 0))
            ImageDraw.Draw(ch).text((ch.width / 2, ch.height / 2), c, font=ring, fill=cream, anchor="mm")
            ch = ch.rotate(-a - 90, resample=Image.BICUBIC)
            im.paste(ch, (int(x - ch.width / 2), int(y - ch.height / 2)), ch)
        cur += (cw + extra) / r * 180 / math.pi
    # center calendar page
    f1 = font("cond", int(s * 0.07), "Bold")
    f2 = font("display", int(s * 0.25))
    d.text((s / 2, s * 0.34), "TODAY IN", font=f1, fill=RED, anchor="mm")
    d.text((s / 2, s * 0.53), "1776", font=font("display", int(s * 0.16)), fill=INK, anchor="mm")
    d.line([s * 0.32, s * 0.65, s * 0.68, s * 0.65], fill=INK, width=int(s * 0.008))
    d.text((s / 2, s * 0.71), "HISTORY", font=f1, fill=INK, anchor="mm")
    return im.resize((size, size), Image.LANCZOS)


def wordmark(height=70, color=INK):
    f = font("display", height)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    t = "On This Day USA"
    w = int(tmp.textlength(t, font=f)) + 10
    im = Image.new("RGBA", (w, int(height * 1.35)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, height * 0.65), t, font=f, fill=color, anchor="lm")
    return im


def branding(out):
    os.makedirs(out, exist_ok=True)
    # profile picture
    pp = paper(1080, 1080, 3)
    b = badge(940)
    pp.paste(b, (70, 70), b)
    pp.save(os.path.join(out, "profile.jpg"), quality=94)
    # cover 1640x624 (keep text in the centre safe area)
    cw, ch = 1640, 624
    cv = paper(cw, ch, 11)
    d = ImageDraw.Draw(cv)
    for y in (40, ch - 40):
        d.line([60, y, cw - 60, y], fill=INK, width=3)
        d.line([60, y + (8 if y < 100 else -8), cw - 60, y + (8 if y < 100 else -8)], fill=INK, width=1)
    d.text((cw / 2, 110), "EST. EVERY DAY  •  AMERICAN HISTORY IN 30 SECONDS", font=font("type", 34), fill=RED, anchor="mm")
    d.text((cw / 2, 270), "On This Day USA", font=font("display", 150), fill=INK, anchor="mm")
    d.text((cw / 2, 410), "The stories that shaped America, one date at a time", font=font("serif", 50, "Bold"), fill=NAVY, anchor="mm")
    stars(d, cw / 2, 515, 18, GOLD, gap=360)
    cv.save(os.path.join(out, "cover.jpg"), quality=94)
    return out


# ---------- reel ----------
def topbar(c, story):
    d = ImageDraw.Draw(c)
    b = badge(96)
    c.paste(b, (56, 56), b)
    d.text((170, 80), "ON THIS DAY USA", font=font("cond", 40, "Bold"), fill=INK, anchor="lm")
    d.text((170, 124), f"{story['date'].upper()}, {story['year']}", font=font("type", 32), fill=RED, anchor="lm")
    d.line([56, 172, W - 56, 172], fill=INK, width=3)
    d.line([56, 180, W - 56, 180], fill=INK, width=1)


def caption(c, text, prog):
    if not text:
        return
    d = ImageDraw.Draw(c)
    f = font("type", 54)
    ls = wrap(d, text, f, W - 220)[:2]
    lh = 66
    bw = max(d.textlength(l, font=f) for l in ls) + 80
    bh = lh * len(ls) + 46
    x0, y0 = (W - bw) / 2, 1585
    a = ease(prog * 6)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=(246, 238, 220), outline=INK, width=3)
    d.rectangle([x0 + 8, y0 + 8, x0 + bw - 8, y0 + bh - 8], outline=(150, 120, 90), width=1)
    for i, l in enumerate(ls):
        d.text((W / 2, y0 + 23 + lh * i + lh / 2 + (1 - a) * 6), l, font=f, fill=INK, anchor="mm")


class Scene:
    def __init__(self, s, story, idx):
        self.s, self.story, self.idx = s, story, idx
        self.img = Image.open(s["image"]).convert("RGB") if s.get("image") and os.path.exists(s["image"]) else None
        self.angle = [-2.2, 1.8, -1.4, 2.4][idx % 4]
        if self.img is not None:
            self.frame_big = print_frame(self.img, 900, 760)
            self.frame_small = print_frame(self.img, 760, 470, 20)

    def draw(self, c, t, dur):
        d = ImageDraw.Draw(c)
        p = t / max(dur, 0.01)
        typ = self.s["type"]
        if typ == "intro":
            a = ease(t * 1.6)
            d.text((W / 2, 520), "ON THIS DAY", font=font("type", 64), fill=RED, anchor="mm")
            d.line([W / 2 - 260, 580, W / 2 + 260, 580], fill=INK, width=3)
            d.text((W / 2, 720 + (1 - a) * 40), self.story["date"].upper(), font=font("display", 130), fill=INK, anchor="mm")
            yr = str(int(int(self.story["year"]) * ease(t * 0.9 + 0.1))) if t < 1.2 else str(self.story["year"])
            d.text((W / 2, 930), yr, font=font("display", 260), fill=RED, anchor="mm")
            f, ls, sz = fit(d, self.story["headline"], "serif", W - 180, 300, 80, 46, var="Black")
            for i, l in enumerate(ls[:3]):
                b = ease((t - 0.5 - 0.15 * i) * 3)
                d.text((W / 2, 1150 + i * sz * 1.12 + (1 - b) * 30), l, font=f, fill=INK, anchor="ma")
        elif typ == "photo" and self.img is not None:
            fr = self.frame_big
            z = 1.0 + 0.04 * p
            fr2 = fr.resize((int(fr.width * z), int(fr.height * z)), Image.BILINEAR)
            paste_rot(c, fr2, (int((W - fr2.width) / 2) - 20, 230 - int((fr2.height - fr.height) / 2)), self.angle)
            if self.s.get("label"):
                a = ease((t - 0.3) * 3)
                f = font("type", 44)
                lb = self.s["label"]
                tw = d.textlength(lb, font=f)
                x = W - 80 - tw - 50 + (1 - a) * 400
                d.rectangle([x, 1010, x + tw + 50, 1080], fill=RED)
                d.text((x + 25, 1045), lb, font=f, fill=(246, 236, 214), anchor="lm")
            cap = self.s.get("caption")
            if cap:
                d.text((W / 2, 1125), cap, font=font("oldr", 34), fill=(95, 75, 55), anchor="mm")
            title = self.s.get("title") or self.story["headline"]
            f, ls, sz = fit(d, title, "serif", W - 160, 300, 74, 46, var="Black")
            for i, l in enumerate(ls[:3]):
                b = ease((t - 0.15 * i) * 3)
                d.text((W / 2, 1190 + i * sz * 1.12 + (1 - b) * 26), l, font=f, fill=INK, anchor="ma")
        elif typ == "stat":
            val = float(self.s.get("value", 0))
            cur = val * ease(p * 1.6)
            dec = int(self.s.get("decimals", 0 if val.is_integer() else 1))
            num = f"{self.s.get('prefix','')}{cur:,.{dec}f}{self.s.get('suffix','')}"
            if self.img is not None:
                paste_rot(c, self.frame_small, ((W - self.frame_small.width) // 2, 250), self.angle)
                y = 1010
            else:
                y = 760
            f, _, _ = fit(d, num, "display", W - 140, 260, 230, 100)
            d.text((W / 2, y), num, font=f, fill=RED, anchor="mm")
            stars(d, W / 2, y + 140, 16, GOLD, gap=60)
            f2, ls, sz = fit(d, self.s.get("label", ""), "old", W - 180, 240, 64, 40)
            for i, l in enumerate(ls):
                d.text((W / 2, y + 200 + i * sz * 1.15), l, font=f2, fill=INK, anchor="ma")
        elif typ in ("text", "question"):
            title = self.s.get("title", "")
            if typ == "question":
                d.rectangle([90, 420, W - 90, 1340], outline=INK, width=6)
                d.rectangle([110, 440, W - 110, 1320], outline=RED, width=2)
                d.text((W / 2, 540), "YOUR TURN", font=font("type", 58), fill=RED, anchor="mm")
                f, ls, sz = fit(d, title, "serif", W - 300, 560, 100, 54, var="Black")
                y = 880 - len(ls) * sz * 1.12 / 2
                for i, l in enumerate(ls):
                    b = ease((t - 0.12 * i) * 3)
                    d.text((W / 2, y + i * sz * 1.12 + (1 - b) * 30), l, font=f, fill=INK, anchor="ma")
                d.text((W / 2, 1230), "Tell us in the comments", font=font("oldr", 44), fill=NAVY, anchor="mm")
            else:
                y0 = 300
                if self.img is not None:
                    paste_rot(c, self.frame_small, ((W - self.frame_small.width) // 2, 240), self.angle)
                    y0 = 860
                d.line([W / 2 - 150, y0 + 10, W / 2 - 40, y0 + 10], fill=GOLD, width=3)
                d.line([W / 2 + 40, y0 + 10, W / 2 + 150, y0 + 10], fill=GOLD, width=3)
                star(d, W / 2, y0 + 10, 18, GOLD)
                f, ls, sz = fit(d, title, "serif", W - 180, 560, 92, 50, var="Black")
                for i, l in enumerate(ls):
                    b = ease((t - 0.12 * i) * 3)
                    d.text((W / 2, y0 + 80 + i * sz * 1.12 + (1 - b) * 30), l, font=f, fill=INK, anchor="ma")
        elif typ == "cta":
            s = 0.85 + 0.15 * ease(p * 3)
            b = badge(int(520 * s))
            c.paste(b, ((W - b.width) // 2, 420 + (520 - b.height) // 2), b)
            d.text((W / 2, 1060), "On This Day USA", font=font("display", 96), fill=INK, anchor="mm")
            d.text((W / 2, 1160), "A new story from American history", font=font("oldr", 46), fill=NAVY, anchor="mm")
            d.text((W / 2, 1218), "every single day", font=font("oldr", 46), fill=NAVY, anchor="mm")
            d.rectangle([W / 2 - 210, 1300, W / 2 + 210, 1400], fill=RED)
            d.text((W / 2, 1350), "FOLLOW", font=font("cond", 60, "Bold"), fill=(246, 236, 214), anchor="mm")


def audio_duration(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                 "default=nw=1:nk=1", p], capture_output=True, text=True).stdout.strip())


def render_reel(story, out_dir):
    scenes = story["scenes"]
    dur = audio_duration(story["voice_mp3"]) + 0.6
    wc = [max(1, len(words(s.get("text", "")))) for s in scenes]
    lens = [dur * c / sum(wc) for c in wc]
    starts = [sum(lens[:i]) for i in range(len(lens))]
    objs = [Scene(s, story, i) for i, s in enumerate(scenes)]
    chunks = []
    for s, st, ln in zip(scenes, starts, lens):
        if s["type"] == "cta":
            continue
        ws = words(s.get("text", ""))
        g = [" ".join(ws[i:i + 4]) for i in range(0, len(ws), 4)]
        for gi, txt in enumerate(g):
            chunks.append((st + ln * gi / len(g), st + ln * (gi + 1) / len(g), txt))
    bg = paper(W, H, 5)
    n = int(dur * FPS)
    out = os.path.join(out_dir, f"{story['slug']}.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", story["voice_mp3"], "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "21", "-pix_fmt", "yuv420p", "-af", "apad", "-c:a", "aac", "-b:a", "160k",
                           "-t", f"{n / FPS:.3f}", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    flick = random.Random(1)
    for i in range(n):
        t = i / FPS
        k = max(j for j in range(len(starts)) if starts[j] <= t)
        c = bg.copy()
        objs[k].draw(c, t - starts[k], lens[k])
        if scenes[k]["type"] != "cta":
            topbar(c, story)
            for a, b, txt in chunks:
                if a <= t < b:
                    caption(c, txt, (t - a) / max(b - a, 0.01))
                    break
        lt = t - starts[k]
        if lt < 0.18 and k > 0:
            c = Image.blend(bg, c, lt / 0.18)
        # subtle old-film flicker
        if i % 3 == 0:
            c = ImageEnhance.Brightness(c).enhance(1 + flick.uniform(-0.025, 0.02))
        ImageDraw.Draw(c).rectangle([0, H - 12, int(W * t / dur), H], fill=RED)
        ff.stdin.write(c.tobytes())
    ff.stdin.close()
    ff.wait()
    if ff.returncode:
        raise SystemExit("ffmpeg failed")
    return out


def first_image(story):
    for s in story["scenes"]:
        if s.get("image") and os.path.exists(s["image"]):
            return Image.open(s["image"]).convert("RGB")
    return None


def render_cover(story, out_dir):
    c = paper(W, H, 9)
    d = ImageDraw.Draw(c)
    topbar(c, story)
    img = first_image(story)
    if img is not None:
        paste_rot(c, print_frame(img, 900, 820), (60, 240), -1.8)
    d.text((W / 2, 1180), f"{story['date'].upper()}, {story['year']}", font=font("type", 62), fill=RED, anchor="mm")
    f, ls, sz = fit(d, story["headline"], "display", W - 140, 470, 120, 64)
    for i, l in enumerate(ls[:4]):
        d.text((W / 2, 1260 + i * sz * 1.1), l, font=f, fill=INK, anchor="ma")
    out = os.path.join(out_dir, f"{story['slug']}-cover.jpg")
    c.save(out, quality=92)
    return out


def render_post(story, out_dir):
    PW, PH = 1080, 1350
    c = paper(PW, PH, 13)
    d = ImageDraw.Draw(c)
    d.text((PW / 2, 70), f"ON THIS DAY  •  {story['date'].upper()}, {story['year']}", font=font("type", 40), fill=RED, anchor="mm")
    d.line([60, 110, PW - 60, 110], fill=INK, width=3)
    img = first_image(story)
    y = 140
    if img is not None:
        fr = print_frame(img, 860, 560, 22)
        paste_rot(c, fr, ((PW - fr.width) // 2 - 10, 140), -1.2)
        y = 780
    f, ls, sz = fit(d, story["headline"], "display", PW - 120, 230, 84, 50)
    for l in ls[:3]:
        d.text((PW / 2, y), l, font=f, fill=INK, anchor="ma")
        y += sz * 1.08
    y += 22
    fb = font("old", 36)
    for fact in story.get("post_facts", [])[:3]:
        fl = wrap(d, fact, fb, PW - 170)
        if y + len(fl) * 46 > PH - 120:
            break
        star(d, 82, y + 22, 14, RED)
        for l in fl:
            d.text((110, y), l, font=fb, fill=(55, 42, 32))
            y += 46
        y += 10
    b = badge(80)
    c.paste(b, (60, PH - 110), b)
    d.text((160, PH - 70), "On This Day USA", font=font("display", 46), fill=INK, anchor="lm")
    out = os.path.join(out_dir, f"{story['slug']}-post.jpg")
    c.save(out, quality=92)
    return out


if __name__ == "__main__":
    if sys.argv[1] == "--branding":
        print(branding(sys.argv[2]))
    else:
        st = json.load(open(sys.argv[1]))
        od = sys.argv[2]
        os.makedirs(od, exist_ok=True)
        print(render_reel(st, od))
        print(render_cover(st, od))
        print(render_post(st, od))
