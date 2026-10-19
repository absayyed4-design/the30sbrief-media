"""The 30s Brief renderer: white-theme 9:16 reel + cover + 4:5 image post.

Usage:
    python3 brief/render.py story.json OUT_DIR

story.json:
{
  "slug": "gator-attack-florida",
  "tag": "BREAKING",                       # small red label at the top
  "headline": "12-foot gator kills fisherman in Florida",
  "voice_mp3": "/abs/path/voice.mp3",      # ONE file = all scene texts read in order
  "post_facts": ["...", "..."],            # 2-3 short lines for the image post
  "scenes": [
    {"type": "photo", "image": "/abs/a.jpg", "label": "Winter Garden, Florida",
     "file_photo": true, "text": "[serious] A nearly twelve-foot alligator killed ..."},
    {"type": "stat", "value": 32, "prefix": "", "suffix": "", "label": "deaths since 1948",
     "text": "Florida has recorded ... thirty-two deaths."},
    {"type": "text", "title": "What happens next", "text": "..."},
    {"type": "question", "title": "Would you still fish there?", "text": "[curious] Would you ..."},
    {"type": "cta", "text": "[warmly] Follow The 30s Brief, for your daily news in thirty seconds."}
  ]
}
Scene length is proportional to the spoken words in its "text"; the voiceover must be
generated from the scene texts joined with spaces, in order.
"""
import json, math, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

W, H, FPS = 1080, 1920, 30
WHITE, INK, RED, GREY, LIGHT = (255, 255, 255), (17, 17, 17), (229, 57, 53), (110, 110, 110), (242, 242, 242)
FD = "/usr/share/fonts/opentype/inter/"


def font(weight, size):
    for p in (f"{FD}Inter-{weight}.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def spoken(text):
    return re.sub(r"\[[^\]]*\]", " ", text).replace("...", " ").strip()


def words(text):
    return [w for w in spoken(text).split() if w]


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, weight, max_w, max_h, start=110, min_size=40, spacing=1.12):
    size = start
    while size >= min_size:
        f = font(weight, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) * size * spacing <= max_h:
            return f, lines, size
        size -= 4
    f = font(weight, min_size)
    return f, wrap(draw, text, f, max_w), min_size


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def cover_crop(img, w, h):
    return ImageOps.fit(img.convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.4))


def logo(size=60):
    """Wordmark: red square with '30s' + 'THE 30s BRIEF'."""
    f1, f2 = font("Black", int(size * 0.40)), font("ExtraBold", int(size * 0.62))
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    tw = tmp.textlength("THE 30s BRIEF", font=f2)
    im = Image.new("RGBA", (int(size + 18 + tw), size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, size, size], radius=int(size * 0.18), fill=RED)
    d.text((size / 2, size / 2), "30s", font=f1, fill=WHITE, anchor="mm")
    d.text((size + 18, size / 2), "THE 30s BRIEF", font=f2, fill=INK, anchor="lm")
    return im


def top_bar(canvas, tag):
    d = ImageDraw.Draw(canvas)
    lg = logo(64)
    canvas.paste(lg, (60, 70), lg)
    if tag:
        f = font("ExtraBold", 34)
        tw = d.textlength(tag, font=f)
        x1 = W - 60
        d.rounded_rectangle([x1 - tw - 40, 76, x1, 128], radius=26, fill=RED)
        d.text((x1 - tw / 2 - 20, 102), tag, font=f, fill=WHITE, anchor="mm")


def caption(canvas, text, prog):
    """Subtitle pill near the bottom; small pop-in."""
    if not text:
        return
    d = ImageDraw.Draw(canvas)
    f = font("ExtraBold", 58)
    lines = wrap(d, text, f, W - 200)[:2]
    lh = 72
    box_h = lh * len(lines) + 50
    y0 = 1560
    scale = 0.92 + 0.08 * ease(prog * 6)
    bw = max(d.textlength(l, font=f) for l in lines) + 80
    x0 = (W - bw * scale) / 2
    d.rounded_rectangle([x0, y0, x0 + bw * scale, y0 + box_h], radius=28, fill=INK)
    for i, l in enumerate(lines):
        d.text((W / 2, y0 + 25 + lh * i + lh / 2), l, font=f, fill=(255, 214, 0) if i == 0 else WHITE, anchor="mm")


class Scene:
    def __init__(self, spec, story):
        self.s, self.story = spec, story
        self.img = None
        if spec.get("image") and os.path.exists(spec["image"]):
            self.img = Image.open(spec["image"]).convert("RGB")
            self.photo = cover_crop(self.img, 1180, 1030)  # extra margin for Ken Burns

    def draw(self, canvas, t, dur):
        typ = self.s["type"]
        d = ImageDraw.Draw(canvas)
        p = t / max(dur, 0.01)
        if typ == "photo" and self.img is not None:
            z = 1.0 + 0.08 * p
            pw, ph = int(1080 * z), int(950 * z)
            ph_img = self.photo.resize((int(1180 * z), int(1030 * z)), Image.BILINEAR)
            ox = (ph_img.width - 1080) // 2
            oy = (ph_img.height - 950) // 2
            crop = ph_img.crop((ox, oy, ox + 1080, oy + 950))
            mask = Image.new("L", (1080, 950), 0)
            ImageDraw.Draw(mask).rounded_rectangle([40, 0, 1040, 950], radius=36, fill=255)
            canvas.paste(crop, (0, 180), mask)
            if self.s.get("file_photo"):
                f = font("Bold", 26)
                d.rounded_rectangle([70, 200, 70 + d.textlength("FILE PHOTO", font=f) + 30, 244], radius=10, fill=(0, 0, 0))
                d.text((85, 222), "FILE PHOTO", font=f, fill=WHITE, anchor="lm")
            if self.s.get("label"):
                a = ease((t - 0.2) * 3)
                f = font("ExtraBold", 46)
                lbl = self.s["label"]
                tw = d.textlength(lbl, font=f)
                x = 70 - (1 - a) * 300
                d.rounded_rectangle([x, 1050, x + tw + 50, 1118], radius=14, fill=RED)
                d.text((x + 25, 1084), lbl, font=f, fill=WHITE, anchor="lm")
            hl = self.s.get("title") or self.story["headline"]
            f, lines, sz = fit_text(d, hl, "Black", W - 140, 330, start=78, min_size=48)
            for i, l in enumerate(lines[:4]):
                a = ease((t - 0.1 * i) * 4)
                d.text((70, 1170 + i * sz * 1.12 + (1 - a) * 30), l, font=f, fill=INK)
        elif typ == "stat":
            val = float(self.s.get("value", 0))
            cur = val * ease(p * 1.6)
            dec = int(self.s.get("decimals", 0 if float(val).is_integer() else 1))
            num = f"{self.s.get('prefix','')}{cur:,.{dec}f}{self.s.get('suffix','')}"
            f, _, _ = fit_text(d, num, "Black", W - 120, 300, start=240, min_size=100)
            d.text((W / 2, 720), num, font=f, fill=RED, anchor="mm")
            d.rectangle([W / 2 - 80, 900, W / 2 + 80, 912], fill=INK)
            f2, lines, sz = fit_text(d, self.s.get("label", ""), "ExtraBold", W - 160, 380, start=76, min_size=44)
            for i, l in enumerate(lines):
                d.text((W / 2, 990 + i * sz * 1.15), l, font=f2, fill=INK, anchor="ma")
            if self.img is not None:
                th = cover_crop(self.img, 300, 300)
                m = Image.new("L", (300, 300), 0)
                ImageDraw.Draw(m).ellipse([0, 0, 300, 300], fill=255)
                canvas.paste(th, (W // 2 - 150, 250), m)
        elif typ in ("text", "question"):
            title = self.s.get("title", "")
            if typ == "question":
                d.rounded_rectangle([60, 330, W - 60, 1380], radius=40, outline=RED, width=10, fill=WHITE)
                f = font("ExtraBold", 44)
                d.text((W / 2, 440), "TELL US IN THE COMMENTS", font=f, fill=RED, anchor="mm")
                f2, lines, sz = fit_text(d, title, "Black", W - 220, 700, start=104, min_size=56)
                y = 860 - len(lines) * sz * 1.12 / 2
                for i, l in enumerate(lines):
                    a = ease((t - 0.12 * i) * 3)
                    d.text((W / 2, y + i * sz * 1.12 + (1 - a) * 40), l, font=f2, fill=INK, anchor="ma")
            else:
                if self.img is not None:
                    th = cover_crop(self.img, 1000, 560)
                    m = Image.new("L", th.size, 0)
                    ImageDraw.Draw(m).rounded_rectangle([0, 0, th.width, th.height], radius=30, fill=255)
                    canvas.paste(th, (40, 200), m)
                    y0 = 820
                else:
                    y0 = 420
                d.rectangle([70, y0, 90, y0 + 120], fill=RED)
                f2, lines, sz = fit_text(d, title, "Black", W - 190, 650, start=96, min_size=52)
                for i, l in enumerate(lines):
                    a = ease((t - 0.12 * i) * 3)
                    d.text((120 + (1 - a) * 60, y0 + i * sz * 1.12), l, font=f2, fill=INK)
        elif typ == "cta":
            lg = logo(150)
            s = 0.85 + 0.15 * ease(p * 3)
            lg = lg.resize((int(lg.width * s), int(lg.height * s)), Image.LANCZOS)
            canvas.paste(lg, ((W - lg.width) // 2, 700), lg)
            f = font("ExtraBold", 64)
            for i, l in enumerate(["Follow for your daily", "news in 30 seconds"]):
                d.text((W / 2, 980 + i * 84), l, font=f, fill=INK, anchor="ma")
            d.rounded_rectangle([W / 2 - 200, 1220, W / 2 + 200, 1320], radius=50, fill=RED)
            d.text((W / 2, 1270), "FOLLOW", font=font("Black", 56), fill=WHITE, anchor="mm")


def audio_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True).stdout
    return float(out.strip())


def render_reel(story, out_dir):
    scenes = story["scenes"]
    dur = audio_duration(story["voice_mp3"]) + 0.6
    wc = [max(1, len(words(s.get("text", "")))) for s in scenes]
    total = sum(wc)
    lens = [dur * c / total for c in wc]
    starts = [sum(lens[:i]) for i in range(len(lens))]
    objs = [Scene(s, story) for s in scenes]
    # caption chunks (~4 words) per scene, time-proportional
    chunks = []
    for s, st, ln in zip(scenes, starts, lens):
        if s["type"] == "cta":
            continue
        ws = words(s.get("text", ""))
        groups = [" ".join(ws[i:i + 4]) for i in range(0, len(ws), 4)]
        for gi, g in enumerate(groups):
            chunks.append((st + ln * gi / len(groups), st + ln * (gi + 1) / len(groups), g))
    out = os.path.join(out_dir, f"{story['slug']}.mp4")
    n = int(dur * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", story["voice_mp3"], "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "21", "-pix_fmt", "yuv420p", "-af", "apad", "-c:a", "aac", "-b:a", "160k", "-t", f"{n / FPS:.3f}",
        "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS
        k = max(j for j in range(len(starts)) if starts[j] <= t)
        canvas = Image.new("RGB", (W, H), WHITE)
        lt = t - starts[k]
        objs[k].draw(canvas, lt, lens[k])
        if scenes[k]["type"] != "cta":
            top_bar(canvas, story.get("tag", ""))
            for a, b, txt in chunks:
                if a <= t < b:
                    caption(canvas, txt, (t - a) / max(b - a, 0.01))
                    break
        # quick fade between scenes
        if lt < 0.15 and k > 0:
            canvas = Image.blend(Image.new("RGB", (W, H), WHITE), canvas, lt / 0.15)
        # progress bar
        ImageDraw.Draw(canvas).rectangle([0, H - 14, int(W * t / dur), H], fill=RED)
        ff.stdin.write(canvas.tobytes())
    ff.stdin.close()
    ff.wait()
    if ff.returncode != 0:
        raise SystemExit("ffmpeg failed")
    return out


def first_image(story):
    for s in story["scenes"]:
        if s.get("image") and os.path.exists(s["image"]):
            return Image.open(s["image"]).convert("RGB"), s
    return None, None


def render_cover(story, out_dir):
    c = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(c)
    img, sc = first_image(story)
    if img is not None:
        c.paste(cover_crop(img, W, 1060), (0, 0))
        if sc.get("file_photo"):
            f = font("Bold", 28)
            d.rounded_rectangle([40, 1000, 40 + d.textlength("FILE PHOTO", font=f) + 30, 1044], radius=10, fill=(0, 0, 0))
            d.text((55, 1022), "FILE PHOTO", font=f, fill=WHITE, anchor="lm")
    d.rectangle([0, 1060, W, 1074], fill=RED)
    f, lines, sz = fit_text(d, story["headline"], "Black", W - 120, 560, start=104, min_size=60)
    for i, l in enumerate(lines[:5]):
        d.text((60, 1130 + i * sz * 1.1), l, font=f, fill=INK)
    lg = logo(70)
    c.paste(lg, (60, H - 150), lg)
    tag = story.get("tag", "")
    if tag:
        f2 = font("ExtraBold", 36)
        tw = d.textlength(tag, font=f2)
        d.rounded_rectangle([W - 60 - tw - 40, H - 145, W - 60, H - 85], radius=30, fill=RED)
        d.text((W - 80 - tw / 2, H - 115), tag, font=f2, fill=WHITE, anchor="mm")
    out = os.path.join(out_dir, f"{story['slug']}-cover.jpg")
    c.save(out, quality=92)
    return out


def render_post(story, out_dir):
    PW, PH = 1080, 1350
    c = Image.new("RGB", (PW, PH), WHITE)
    d = ImageDraw.Draw(c)
    img, sc = first_image(story)
    top = 0
    if img is not None:
        c.paste(cover_crop(img, PW, 640), (0, 0))
        top = 640
        if sc.get("file_photo"):
            f = font("Bold", 24)
            d.rounded_rectangle([30, 590, 30 + d.textlength("FILE PHOTO", font=f) + 26, 628], radius=8, fill=(0, 0, 0))
            d.text((43, 609), "FILE PHOTO", font=f, fill=WHITE, anchor="lm")
    d.rectangle([0, top, PW, top + 12], fill=RED)
    f, lines, sz = fit_text(d, story["headline"], "Black", PW - 110, 300, start=78, min_size=46)
    y = top + 45
    for l in lines[:4]:
        d.text((55, y), l, font=f, fill=INK)
        y += sz * 1.1
    y += 25
    fb = font("SemiBold", 38)
    for fact in story.get("post_facts", [])[:3]:
        fl = wrap(d, fact, fb, PW - 160)
        if y + len(fl) * 48 > PH - 130:
            break
        d.ellipse([60, y + 14, 78, y + 32], fill=RED)
        for l in fl:
            d.text((100, y), l, font=fb, fill=(40, 40, 40))
            y += 48
        y += 14
    lg = logo(56)
    c.paste(lg, (55, PH - 100), lg)
    out = os.path.join(out_dir, f"{story['slug']}-post.jpg")
    c.save(out, quality=92)
    return out


if __name__ == "__main__":
    story = json.load(open(sys.argv[1]))
    od = sys.argv[2]
    os.makedirs(od, exist_ok=True)
    print(render_reel(story, od))
    print(render_cover(story, od))
    print(render_post(story, od))
