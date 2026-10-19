"""The 30s Brief renderer: 9:16 reel + 9:16 cover + 4:5 image post.

Template = the Oct 17 "press secretary out after 5 days" reel (Abdullah's favourite):
white header bar (round 30s logo, THE 30s BRIEF, date, red progress line under it),
light grey grid background, a new visual beat every 2-4 seconds built from REAL photos
(photo cards with a red name pill + subtitle, date pills, counting badges, quote cards,
a tilted stamp, bar charts with photo thumbnails), each element popping in as the voice
reaches it, big bold UPPERCASE captions underneath, and a FOLLOW end card.

Usage:
    python3 brief/render.py story.json OUT_DIR

story.json (all text in plain words; no em dashes):
{
  "slug": "press-sec-out-1210",
  "date": "OCT 17, 2026",                       # header date (default: today, New York)
  "tag": "BREAKING • WHITE HOUSE",              # cover/post pill
  "headline": "Press secretary out after 5 days",
  "head_top": "PRESS SECRETARY", "head_red": "OUT AFTER 5 DAYS",     # cover/post headline
  "stats": [{"value": "OCT 9", "label": "HIRED", "color": "blue"},    # cover/post, exactly 3
            {"value": "14 MIN", "label": "1ST BRIEFING", "color": "navy"},
            {"value": "OCT 16", "label": "OUT", "color": "red"}],
  "cover_label": "KATIE ZACHARIA",              # name pill on cover (default: first scene name)
  "voice_mp3": "/abs/voice.mp3",                # ONE file = all scene "text" joined with spaces
  "scenes": [ ... see SCENE TYPES ... ]
}

Every scene has "text" (the words spoken during it; may hold [audio tags]).
Elements appear one after another; set "at" on a scene key to the WORD NUMBER (0-based,
inside that scene's text) where it should pop in, e.g. "big_red_at": 6.

SCENE TYPES
  hero    {"tag", "image", "file_photo", "name", "sub", "big_top", "big_red", "big_red_at"}
          Tag pill, portrait photo card, red name pill, grey subtitle, big navy + red text.
          If big_red starts with a number it counts up ("5 DAYS").
  cards   {"title", "cards": [{"image", "file_photo", "pill", "color": "blue|navy|red",
           "badge": "14 MIN", "badge_sub": "total length", "at": 3}, ...]}   (1 or 2 cards)
  person  {"image", "file_photo", "name", "sub", "quote_label", "quote", "quote_at"}
  stamp   {"image", "file_photo", "pill", "stamp": "TRANSITIONING OUT", "stamp_at",
           "note_label": "TRUMP:", "note": "media was \"brutal\" to her", "note_at"}
  bars    {"title", "sub", "bars": [{"label", "value", "color": "red|amber|blue|navy",
           "image", "at"}, ...]}   (2-4 bars, grow one by one)
  number  {"title", "value": 16000, "prefix": "~", "suffix": "", "label",
           "dots": {"filled": 8, "total": 10}}    (optional people-icon grid)
  icons   {"title", "icon": "house|person|flame", "count": 6, "total": 6, "label",
           "badge": "2 FIREFIGHTERS HOSPITALIZED", "badge_at"}
  status  {"icon": "check|search|alert|none", "top", "bottom", "color": "green|red|navy", "sub"}
  time    {"label": "FRIDAY", "time": "11:30 AM", "image", "file_photo", "pill"}
  question{"title"}            (skip on tragic news)
  cta     {}                   (always last: "Follow The 30s Brief, for your daily news in thirty seconds.")
Old types still work: photo -> hero, stat -> number, text -> status.
Any photo not from the actual event: "file_photo": true (draws a FILE PHOTO tag).
"""
import json, math, os, re, subprocess, sys, datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

W, H, FPS = 1080, 1920, 30
NAVY = (15, 23, 42)
RED = (230, 40, 40)
BLUE = (37, 99, 235)
AMBER = (234, 150, 12)
GREEN = (22, 163, 74)
GREY = (100, 108, 122)
LGREY = (203, 208, 216)
WHITE = (255, 255, 255)
BORDER = (228, 231, 237)
BG_TOP, BG_BOT = (248, 249, 251), (236, 239, 244)
COL = {"blue": BLUE, "navy": NAVY, "red": RED, "amber": AMBER, "green": GREEN, "grey": GREY}
FD = "/usr/share/fonts/opentype/inter/"
HEADER_H = 112
CAP_Y = 1222


def font(weight, size):
    size = max(8, int(size))
    for p in (f"{FD}InterDisplay-{weight}.otf", f"{FD}Inter-{weight}.otf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


_D = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def tlen(text, f):
    return _D.textlength(text, font=f)


def fit(text, weight, max_w, start, min_size=20):
    s = start
    while s > min_size and tlen(text, font(weight, s)) > max_w:
        s -= 2
    return font(weight, s)


def wrap(text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if tlen(t, f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def spoken(text):
    return re.sub(r"\[[^\]]*\]", " ", text).replace("...", " ").strip()


def words(text):
    return [w for w in spoken(text).split() if w]


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def back(t):
    t = max(0.0, min(1.0, t))
    c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def cover_crop(img, w, h, cy=0.3):
    return ImageOps.fit(img.convert("RGB"), (int(w), int(h)), Image.LANCZOS, centering=(0.5, cy))


def load(path):
    return Image.open(path).convert("RGB") if path and os.path.exists(path) else None


def rmask(w, h, r):
    m = Image.new("L", (int(w), int(h)), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, int(w) - 1, int(h) - 1], radius=int(r), fill=255)
    return m


class Sprite:
    """RGBA layer with padding for shadows. (ox, oy) = where the content box's top-left sits."""

    def __init__(self, w, h, pad=40):
        self.pad = pad
        self.im = Image.new("RGBA", (int(w + 2 * pad), int(h + 2 * pad)), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def shadow(self, box, r, blur=16, alpha=50, dy=10):
        x0, y0, x1, y1 = [int(v + self.pad) for v in box]
        m = Image.new("L", self.im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([x0, y0 + dy, x1, y1 + dy], radius=r, fill=alpha)
        m = m.filter(ImageFilter.GaussianBlur(blur))
        sh = Image.new("RGBA", self.im.size, (25, 35, 65, 0))
        sh.putalpha(m)
        self.im = Image.alpha_composite(sh, self.im)
        self.d = ImageDraw.Draw(self.im)

    def box(self, b):
        return [v + self.pad for v in b]

    def paste(self, img, xy, mask=None):
        self.im.paste(img, (int(xy[0] + self.pad), int(xy[1] + self.pad)), mask)

    def text(self, xy, s, f, fill, anchor="la"):
        self.d.text((xy[0] + self.pad, xy[1] + self.pad), s, font=f, fill=fill, anchor=anchor)


# ---------- brand ----------
def round_logo(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=WHITE, outline=RED, width=max(3, size // 24))
    d.text((size / 2, size * 0.43), "30s", font=font("Black", size * 0.36), fill=NAVY, anchor="mm")
    bw, bh = size * 0.44, size * 0.11
    d.rectangle([size / 2 - bw / 2, size * 0.62, size / 2 + bw / 2, size * 0.62 + bh], fill=RED)
    d.text((size / 2, size * 0.62 + bh / 2), "BRIEF", font=font("Black", max(7, size * 0.075)), fill=WHITE, anchor="mm")
    return im


def grid_bg(w, h, grid=True):
    g = Image.new("RGB", (1, h))
    for y in range(h):
        k = y / max(h - 1, 1)
        g.putpixel((0, y), tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * k) for i in range(3)))
    bg = g.resize((w, h))
    if grid:
        d = ImageDraw.Draw(bg)
        for x in range(0, w, 72):
            d.line([(x, 0), (x, h)], fill=(232, 235, 240), width=1)
        for y in range(0, h, 72):
            d.line([(0, y), (w, y)], fill=(232, 235, 240), width=1)
    return bg


def header(canvas, date):
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W, HEADER_H], fill=WHITE)
    d.line([(0, HEADER_H), (W, HEADER_H)], fill=BORDER, width=2)
    lg = round_logo(64)
    canvas.paste(lg, (32, 24), lg)
    d.text((112, 56), "THE 30s BRIEF", font=font("Black", 32), fill=NAVY, anchor="lm")
    d.text((W - 36, 56), date, font=font("SemiBold", 25), fill=GREY, anchor="rm")


# ---------- building blocks (return Sprite + content top-left in frame coords) ----------
def pill_sprite(text, f, fill, color=WHITE, padx=30, h=None):
    h = h or int(f.size * 1.85)
    w = tlen(text, f) + 2 * padx
    s = Sprite(w, h, pad=20)
    s.d.rounded_rectangle(s.box([0, 0, w, h]), radius=h // 2, fill=fill)
    s.text((w / 2, h / 2), text, f, color, "mm")
    return s, w, h


def card_sprite(img, w, h, pill=None, pill_color=RED, sub=None, file_photo=False, border=8, r=30, cy=0.28):
    extra = 0
    if pill:
        extra += 30
    if sub:
        extra += 52
    s = Sprite(w, h + extra, pad=44)
    s.shadow([0, 0, w, h], r, blur=18, alpha=60, dy=12)
    s.d.rounded_rectangle(s.box([0, 0, w, h]), radius=r, fill=WHITE)
    iw, ih = w - 2 * border, h - 2 * border
    if img is not None:
        s.paste(cover_crop(img, iw, ih, cy), (border, border), rmask(iw, ih, r - border))
    if file_photo:
        f = font("Bold", 22)
        tw = tlen("FILE PHOTO", f)
        s.d.rounded_rectangle(s.box([border + 14, border + 14, border + 40 + tw, border + 52]), radius=8, fill=(0, 0, 0))
        s.text((border + 27, border + 33), "FILE PHOTO", f, WHITE, "lm")
    y = h
    if pill:
        f = fit(pill.upper(), "Black", w - 40, 34, 20)
        ph = int(f.size * 1.7)
        pw = tlen(pill.upper(), f) + 56
        s.d.rounded_rectangle(s.box([w / 2 - pw / 2, h - ph * 0.55, w / 2 + pw / 2, h + ph * 0.45]), radius=ph // 2, fill=pill_color)
        s.text((w / 2, h - ph * 0.05), pill.upper(), f, WHITE, "mm")
        y = h + ph * 0.45
    if sub:
        f = fit(sub, "SemiBold", w + 120, 28, 18)
        s.text((w / 2, y + 30), sub, f, GREY, "mm")
    return s


def quote_sprite(label, quote, w, quote_color=RED):
    fl = font("SemiBold", 24)
    fq = fit(quote, "Black", w - 60, 60, 26)
    lines = wrap(quote, fq, w - 60)[:2]
    h = 70 + len(lines) * fq.size * 1.1 + 24
    s = Sprite(w, h, pad=30)
    s.shadow([0, 0, w, h], 16, blur=12, alpha=35, dy=6)
    s.d.rounded_rectangle(s.box([0, 0, w, h]), radius=16, fill=WHITE, outline=BORDER, width=2)
    s.text((w / 2, 40), label.upper(), fl, GREY, "mm")
    for i, l in enumerate(lines):
        s.text((w / 2, 70 + i * fq.size * 1.1), l, fq, quote_color, "ma")
    return s, h


def stamp_sprite(text, max_w=700):
    t = f"“{text.upper()}”"
    f = fit(t, "Black", max_w - 80, 56, 26)
    w, h = tlen(t, f) + 80, f.size * 2.1
    s = Sprite(w, h, pad=60)
    s.d.rounded_rectangle(s.box([0, 0, w, h]), radius=12, outline=RED, width=7, fill=(255, 255, 255, 120))
    s.text((w / 2, h / 2), t, f, RED, "mm")
    s.im = s.im.rotate(-5, resample=Image.BICUBIC, expand=False)
    return s, w, h


def icon_img(kind, size, color):
    im = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S = size * 4
    if kind == "house":
        d.polygon([(S * .5, S * .08), (S * .95, S * .48), (S * .82, S * .48), (S * .82, S * .92),
                   (S * .18, S * .92), (S * .18, S * .48), (S * .05, S * .48)], fill=color)
        d.rectangle([S * .42, S * .62, S * .58, S * .92], fill=(255, 255, 255, 0))
    elif kind == "person":
        d.ellipse([S * .33, S * .04, S * .67, S * .38], fill=color)
        d.rounded_rectangle([S * .2, S * .44, S * .8, S * .98], radius=int(S * .2), fill=color)
    elif kind == "flame":
        d.ellipse([S * .2, S * .38, S * .8, S * .96], fill=color)
        d.polygon([(S * .5, S * .02), (S * .8, S * .62), (S * .2, S * .62)], fill=color)
        d.ellipse([S * .36, S * .62, S * .64, S * .92], fill=(255, 200, 60))
    elif kind == "check":
        d.ellipse([0, 0, S - 1, S - 1], fill=GREEN)
        d.line([(S * .28, S * .52), (S * .44, S * .68), (S * .74, S * .34)], fill=WHITE, width=int(S * .1), joint="curve")
    elif kind == "search":
        d.ellipse([S * .08, S * .08, S * .68, S * .68], outline=NAVY, width=int(S * .09))
        d.line([(S * .6, S * .6), (S * .92, S * .92)], fill=NAVY, width=int(S * .12))
        d.text((S * .38, S * .39), "?", font=font("Black", S * .38), fill=RED, anchor="mm")
    elif kind == "alert":
        d.polygon([(S * .5, S * .06), (S * .96, S * .9), (S * .04, S * .9)], fill=RED)
        d.text((S * .5, S * .6), "!", font=font("Black", S * .5), fill=WHITE, anchor="mm")
    return im.resize((size, size), Image.LANCZOS)


# ---------- timeline element ----------
class El:
    """A sprite placed at (x, y) (content top-left), appearing at time t0 with an animation.
    dyn: optional callable(local_t) -> Sprite for animated content (counters, bars)."""

    def __init__(self, sprite, x, y, t0, anim="up", dyn=None):
        self.sp, self.x, self.y, self.t0, self.anim, self.dyn = sprite, x, y, t0, anim, dyn

    def draw(self, canvas, t, fade):
        lt = t - self.t0
        if lt < 0:
            return
        sp = self.dyn(lt) if self.dyn else self.sp
        im = sp.im
        a = ease(lt / 0.35) * fade
        dx = dy = 0
        sc = 1.0
        if self.anim == "up":
            dy = (1 - ease(lt / 0.4)) * 50
        elif self.anim == "pop":
            sc = 0.82 + 0.18 * back(lt / 0.45)
        elif self.anim == "stamp":
            sc = 1.6 - 0.6 * ease(lt / 0.3)
            a = min(1.0, lt / 0.15) * fade
        elif self.anim == "left":
            dx = (1 - ease(lt / 0.4)) * -120
        if a <= 0:
            return
        if sc != 1.0:
            nw, nh = max(1, int(im.width * sc)), max(1, int(im.height * sc))
            im2 = im.resize((nw, nh), Image.BILINEAR)
            px = self.x - sp.pad - (nw - im.width) / 2
            py = self.y - sp.pad - (nh - im.height) / 2
            im = im2
        else:
            px, py = self.x - sp.pad, self.y - sp.pad
        if a < 0.999:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        canvas.alpha_composite(im, (int(px + dx), int(py + dy)))


def word_time(scene, n, default):
    """Time (scene-local word index n) -> absolute seconds; falls back to default."""
    if n is None:
        return default
    wt = scene["_wt"]
    n = max(0, min(int(n), len(wt) - 1))
    return wt[n]


# ---------- scene builders ----------
def count_text(s, k):
    m = re.match(r"^([^\d]*)([\d,\.]+)(.*)$", s)
    if not m:
        return s
    pre, num, post = m.groups()
    val = float(num.replace(",", ""))
    dec = len(num.split(".")[1]) if "." in num else 0
    cur = val * ease(k)
    out = f"{cur:,.{dec}f}" if "," in num else f"{cur:.{dec}f}"
    return pre + out + post


def text_sprite(s, f, color, w=W):
    sp = Sprite(w, f.size * 1.2, pad=10)
    sp.text((w / 2, 0), s, f, color, "ma")
    return sp


def build_scene(sc, story):
    t0, t1 = sc["_t0"], sc["_t1"]
    typ = sc["type"]
    if typ == "photo":
        typ = "hero"
        sc.setdefault("name", sc.get("label"))
        sc.setdefault("big_top", sc.get("title"))
    if typ == "stat":
        typ = "number"
        sc.setdefault("title", "")
    if typ == "text":
        typ = "status"
        sc.setdefault("top", sc.get("title", ""))
        sc.setdefault("icon", "none")
    els = []
    stg = lambda i: t0 + 0.05 + 0.35 * i
    img = load(sc.get("image"))
    fp = bool(sc.get("file_photo"))

    if typ == "hero":
        y = 140
        if sc.get("tag"):
            p, pw, ph = pill_sprite(sc["tag"].upper(), font("Black", 28), RED)
            els.append(El(p, W / 2 - pw / 2, y, stg(0), "pop"))
        y = 250
        cw, ch = 450, 505
        els.append(El(card_sprite(img, cw, ch, sc.get("name"), RED, sc.get("sub"), fp), W / 2 - cw / 2, y, stg(1), "pop"))
        yb = y + ch + (100 if sc.get("sub") else 60)
        if sc.get("big_top"):
            f = fit(sc["big_top"].upper(), "Black", W - 120, 88, 40)
            els.append(El(text_sprite(sc["big_top"].upper(), f, NAVY), 0, yb, word_time(sc, sc.get("big_top_at"), stg(2)), "up"))
        if sc.get("big_red"):
            txt = sc["big_red"].upper()
            f = fit(txt, "Black", W - 100, 138, 50)
            ta = word_time(sc, sc.get("big_red_at"), stg(3))
            els.append(El(None, 0, yb + 100, ta, "up",
                          dyn=lambda lt, txt=txt, f=f: text_sprite(count_text(txt, lt / 0.7), f, RED)))

    elif typ == "cards":
        y = 160
        if sc.get("title"):
            f = fit(sc["title"].upper(), "Black", W - 120, 50, 28)
            els.append(El(text_sprite(sc["title"].upper(), f, NAVY), 0, y, stg(0), "up"))
        cards = sc.get("cards", [])[:2]
        cw, ch = (640, 350) if len(cards) == 2 else (720, 560)
        y = 240
        for i, c in enumerate(cards):
            ci = load(c.get("image"))
            ta = word_time(sc, c.get("at"), stg(1 + 2 * i))
            els.append(El(card_sprite(ci, cw, ch, c.get("pill"), COL.get(c.get("color", "blue"), BLUE), None,
                                      bool(c.get("file_photo")), cy=0.35), W / 2 - cw / 2, y, ta, "pop"))
            if c.get("badge"):
                bt = word_time(sc, c.get("badge_at"), ta + 0.6)
                bx, by = W / 2 + cw / 2 - 30 - 170, y + 22
                sub = c.get("badge_sub", "")

                def badge(lt, txt=c["badge"].upper(), sub=sub):
                    sp = Sprite(170, 96, pad=24)
                    sp.shadow([0, 0, 170, 96], 14, blur=8, alpha=40, dy=4)
                    sp.d.rounded_rectangle(sp.box([0, 0, 170, 96]), radius=14, fill=WHITE)
                    f = fit(txt, "Black", 150, 44, 20)
                    sp.text((85, 42 if sub else 48), count_text(txt, lt / 0.8), f, RED, "mm")
                    if sub:
                        sp.text((85, 76), sub, font("SemiBold", 17), GREY, "mm")
                    return sp
                els.append(El(None, bx, by, bt, "pop", dyn=badge))
            y += ch + 88

    elif typ == "person":
        cw, ch = 450, 535
        y = 180
        els.append(El(card_sprite(img, cw, ch, sc.get("name"), RED, sc.get("sub"), fp), W / 2 - cw / 2, y, stg(0), "pop"))
        if sc.get("quote"):
            q, qh = quote_sprite(sc.get("quote_label", ""), sc["quote"].upper(), 680)
            els.append(El(q, W / 2 - 340, y + ch + 120, word_time(sc, sc.get("quote_at"), stg(2)), "pop"))

    elif typ == "stamp":
        cw, ch = 670, 390
        y = 220
        els.append(El(card_sprite(img, cw, ch, sc.get("pill"), NAVY, None, fp, cy=0.4), W / 2 - cw / 2, y, stg(0), "pop"))
        if sc.get("stamp"):
            st, sw, sh = stamp_sprite(sc["stamp"])
            els.append(El(st, W / 2 - sw / 2, 700, word_time(sc, sc.get("stamp_at"), stg(2)), "stamp"))
        if sc.get("note"):
            q, qh = quote_sprite(sc.get("note_label", ""), sc["note"], 460, NAVY)
            els.append(El(q, W / 2 - 230, 900, word_time(sc, sc.get("note_at"), stg(4)), "up"))

    elif typ == "bars":
        f = fit(sc.get("title", "").upper(), "Black", W - 100, 48, 26)
        els.append(El(text_sprite(sc.get("title", "").upper(), f, NAVY), 0, 160, stg(0), "up"))
        if sc.get("sub"):
            els.append(El(text_sprite(sc["sub"], font("SemiBold", 26), GREY), 0, 222, stg(0), "up"))
        bars = sc.get("bars", [])[:4]
        n = len(bars)
        base_y, maxh, bw, gap = 866, 440, 150, 208
        vmax = max(float(b["value"]) for b in bars) or 1
        x_first = W / 2 - gap * (n - 1) / 2
        line = Sprite(gap * n + 40, 4, pad=4)
        line.d.rectangle(line.box([0, 0, gap * n + 40, 3]), fill=LGREY)
        els.append(El(line, x_first - gap / 2 - 20, base_y, stg(0), "up"))
        for i, b in enumerate(bars):
            cx = x_first + gap * i
            ta = word_time(sc, b.get("at"), stg(1 + 2 * i))
            col = COL.get(b.get("color", "blue"), BLUE)
            v = float(b["value"])
            hgt = max(6, maxh * v / vmax)

            dec = int(b.get("decimals", 0 if v.is_integer() else 2))
            pre = b.get("prefix", "")

            def bar(lt, v=v, hgt=hgt, col=col, dec=dec, pre=pre):
                k = ease(lt / 0.8)
                sp = Sprite(bw + 80, maxh + 70, pad=10)
                hh = hgt * k
                top = maxh + 70 - hh
                sp.d.rounded_rectangle(sp.box([40, top, 40 + bw, maxh + 70]), radius=6, fill=col)
                val = v * k
                sp.text((40 + bw / 2, top - 10), f"{pre}{val:,.{dec}f}", font("Black", 44), col if col == RED else NAVY, "md")
                return sp
            els.append(El(None, cx - bw / 2 - 40, base_y - maxh - 70, ta, "none", dyn=bar))
            lab = text_sprite(b.get("label", "").upper(), fit(b.get("label", "").upper(), "Bold", gap - 10, 28, 16), GREY, gap)
            els.append(El(lab, cx - gap / 2, base_y + 20, ta, "up"))
            bi = load(b.get("image"))
            if bi is not None:
                th = Sprite(128, 128, pad=20)
                th.shadow([0, 0, 128, 128], 22, blur=8, alpha=50, dy=4)
                th.d.rounded_rectangle(th.box([0, 0, 128, 128]), radius=22, fill=WHITE)
                th.paste(cover_crop(bi, 116, 116, 0.25), (6, 6), rmask(116, 116, 18))
                els.append(El(th, cx - 64, base_y + 66, ta, "pop"))

    elif typ == "number":
        y = 170
        if sc.get("title"):
            f = fit(sc["title"].upper(), "Black", W - 100, 54, 28)
            els.append(El(text_sprite(sc["title"].upper(), f, NAVY), 0, y, stg(0), "up"))
        val = float(sc.get("value", 0))
        dec = int(sc.get("decimals", 0 if val.is_integer() else 1))
        full = f"{sc.get('prefix', '')}{val:,.{dec}f}{sc.get('suffix', '')}"
        fn = fit(full, "Black", W - 100, 170, 70)

        def num(lt):
            k = ease(lt / 1.2)
            return text_sprite(f"{sc.get('prefix', '')}{val * k:,.{dec}f}{sc.get('suffix', '')}", fn, RED)
        els.append(El(None, 0, 250, stg(1), "pop", dyn=num))
        if sc.get("label"):
            els.append(El(text_sprite(sc["label"], fit(sc["label"], "SemiBold", W - 120, 36, 20), GREY), 0, 260 + fn.size * 1.15, stg(2), "up"))
        dots = sc.get("dots")
        if dots:
            tot, fil = int(dots.get("total", 10)), int(dots.get("filled", 0))
            cols = min(8, tot)
            rows = math.ceil(tot / cols)
            sz = 74
            gx = 98
            x0 = W / 2 - gx * (cols - 1) / 2 - sz / 2
            y0 = 520 + fn.size * 0.6
            for i in range(tot):
                r, c = divmod(i, cols)
                ic = Sprite(sz, sz, pad=4)
                ic.paste(icon_img("person", sz, RED if i < fil else LGREY), (0, 0), icon_img("person", sz, RED if i < fil else LGREY))
                els.append(El(ic, x0 + c * gx, y0 + r * (sz + 22), stg(2) + 0.04 * i, "pop"))

    elif typ == "icons":
        y = 190
        if sc.get("title"):
            f = fit(sc["title"].upper(), "Black", W - 100, 56, 28)
            els.append(El(text_sprite(sc["title"].upper(), f, NAVY), 0, y, stg(0), "up"))
        tot, cnt = int(sc.get("total", sc.get("count", 6))), int(sc.get("count", 6))
        cols = 3 if tot <= 6 else 4
        sz = 170 if tot <= 6 else 140
        gx = sz + 40
        x0 = W / 2 - gx * (cols - 1) / 2 - sz / 2
        ic_kind = sc.get("icon", "house")
        rows = math.ceil(tot / cols)
        for i in range(tot):
            r, c = divmod(i, cols)
            col = (240, 82, 30) if i < cnt else LGREY
            ic = Sprite(sz, sz, pad=4)
            im = icon_img(ic_kind, sz, col)
            ic.paste(im, (0, 0), im)
            if i < cnt and ic_kind == "house":
                fl = icon_img("flame", int(sz * 0.42), (255, 170, 30))
                ic.paste(fl, (sz * 0.58, -sz * 0.05), fl)
            els.append(El(ic, x0 + c * gx, 300 + r * (sz + 30), stg(1) + 0.12 * i, "pop"))
        ly = 300 + rows * (sz + 30) + 20
        if sc.get("label"):
            els.append(El(text_sprite(sc["label"].upper(), fit(sc["label"].upper(), "Black", W - 120, 58, 28), (240, 82, 30)), 0, ly, stg(2), "up"))
        if sc.get("badge"):
            p, pw, ph = pill_sprite(sc["badge"].upper(), font("Black", 30), AMBER, padx=34)
            els.append(El(p, W / 2 - pw / 2, ly + 100, word_time(sc, sc.get("badge_at"), stg(4)), "pop"))

    elif typ in ("status", "question"):
        y = 300
        icon = sc.get("icon", "none")
        if typ == "question":
            p, pw, ph = pill_sprite("TELL US IN THE COMMENTS", font("Black", 32), RED)
            els.append(El(p, W / 2 - pw / 2, 260, stg(0), "pop"))
            sc.setdefault("top", sc.get("title", ""))
            y = 400
        elif icon != "none":
            ic = Sprite(220, 220, pad=4)
            im = icon_img(icon, 220, NAVY)
            ic.paste(im, (0, 0), im)
            els.append(El(ic, W / 2 - 110, 240, stg(0), "pop"))
            y = 520
        col = COL.get(sc.get("color", "red"), RED)
        top, bot = sc.get("top", "").upper(), sc.get("bottom", "").upper()
        lines = [(l, NAVY) for l in wrap(top, font("Black", 80), W - 120)] + [(l, col) for l in wrap(bot, font("Black", 80), W - 120)]
        if typ == "question":
            lines = [(l, NAVY) for l in wrap(top, font("Black", 92), W - 120)]
        f = font("Black", 92 if typ == "question" else 80)
        for i, (l, c) in enumerate(lines[:5]):
            els.append(El(text_sprite(l, fit(l, "Black", W - 100, f.size, 30), c), 0, y + i * f.size * 1.08, stg(1 + i), "up"))
        if sc.get("sub"):
            els.append(El(text_sprite(sc["sub"], font("SemiBold", 34), GREY), 0, y + len(lines[:5]) * f.size * 1.08 + 20, stg(2 + len(lines)), "up"))

    elif typ == "time":
        tc = Sprite(330, 160, pad=30)
        tc.shadow([0, 0, 330, 160], 18, blur=10, alpha=35, dy=5)
        tc.d.rounded_rectangle(tc.box([0, 0, 330, 160]), radius=18, fill=WHITE, outline=BORDER, width=2)
        tc.text((165, 42), sc.get("label", "").upper(), font("SemiBold", 26), GREY, "mm")
        tc.text((165, 105), sc.get("time", "").upper(), fit(sc.get("time", "").upper(), "Black", 300, 66, 30), NAVY, "mm")
        els.append(El(tc, W / 2 - 165, 150, stg(0), "pop"))
        if img is not None:
            cw, ch = 760, 560
            els.append(El(card_sprite(img, cw, ch, sc.get("pill"), NAVY, None, fp, cy=0.4), W / 2 - cw / 2, 380, stg(1), "pop"))

    elif typ == "cta":
        def logo(lt):
            k = back(lt / 0.5)
            sz = max(10, int(230 * (0.6 + 0.4 * k)))
            sp = Sprite(230, 230, pad=0)
            lg = round_logo(sz)
            sp.paste(lg, ((230 - sz) / 2, (230 - sz) / 2), lg)
            return sp
        els.append(El(None, W / 2 - 115, 380, t0, "none", dyn=logo))
        els.append(El(text_sprite("FOLLOW", font("Black", 104), NAVY), 0, 650, t0 + 0.3, "up"))
        els.append(El(text_sprite("THE 30s BRIEF", font("Black", 70), RED), 0, 770, t0 + 0.6, "up"))
        els.append(El(text_sprite("Daily news in 30 seconds", font("SemiBold", 36), GREY), 0, 865, t0 + 0.9, "up"))
        p, pw, ph = pill_sprite("FOLLOW  +", font("Black", 40), RED, padx=60)
        els.append(El(p, W / 2 - pw / 2, 940, t0 + 1.2, "pop"))
    return els


# ---------- timing ----------
def audio_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True).stdout
    return float(out.strip())


def silence_edges(path):
    """Leading / trailing silence (seconds) of the voice file."""
    out = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=n=-40dB:d=0.25", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d\.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d\.]+)", out)]
    lead = ends[0] if starts and starts[0] < 0.05 and ends else 0.0
    return lead, starts, ends


def word_timeline(scenes, path):
    """Estimate when each word is spoken: weight by length, add pauses at punctuation."""
    dur = audio_duration(path)
    lead, _, _ = silence_edges(path)
    speech_end = dur - 0.25
    allw = []
    for si, s in enumerate(scenes):
        for w in words(s.get("text", "")):
            allw.append((si, w))
    weights = []
    for _, w in allw:
        wt = len(re.sub(r"[^\w]", "", w)) + 2.2
        if w[-1:] in ".?!":
            wt += 5
        elif w[-1:] in ",;:":
            wt += 2.5
        weights.append(wt)
    tot = sum(weights) or 1
    t = lead
    span = max(1.0, speech_end - lead)
    times = []
    for wt in weights:
        times.append(t)
        t += span * wt / tot
    for s in scenes:
        s["_wt"] = []
    for (si, w), tt in zip(allw, times):
        scenes[si]["_wt"].append(tt)
    return allw, times, dur


def render_reel(story, out_dir):
    scenes = story["scenes"]
    allw, times, adur = word_timeline(scenes, story["voice_mp3"])
    dur = adur + 0.5
    for i, s in enumerate(scenes):
        s["_t0"] = 0.0 if i == 0 else (s["_wt"][0] - 0.12 if s["_wt"] else scenes[i - 1]["_t1"])
    for i, s in enumerate(scenes):
        s["_t1"] = scenes[i + 1]["_t0"] if i + 1 < len(scenes) else dur
    els = [build_scene(s, story) for s in scenes]
    # captions: 3-word groups
    caps = []
    i = 0
    while i < len(allw):
        si = allw[i][0]
        grp = [allw[i]]
        j = i + 1
        while j < len(allw) and len(grp) < 3 and allw[j][0] == si and allw[j - 1][1][-1:] not in ".?!,":
            grp.append(allw[j])
            j += 1
        end = times[j] if j < len(times) else dur
        if scenes[si]["type"] != "cta" or True:
            caps.append((times[i], end, " ".join(w for _, w in grp).upper()))
        i = j
    date = story.get("date") or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-4))).strftime("%b %d, %Y").upper()
    base = grid_bg(W, H)
    header(base, date)
    base = base.convert("RGBA")
    out = os.path.join(out_dir, f"{story['slug']}.mp4")
    n = int(dur * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-i", story["voice_mp3"], "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-af", "apad", "-c:a", "aac", "-b:a", "192k", "-t", f"{n / FPS:.3f}",
        "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    fcap = font("Black", 54)
    for fi in range(n):
        t = fi / FPS
        k = max(j for j in range(len(scenes)) if scenes[j]["_t0"] <= t)
        s = scenes[k]
        canvas = base.copy()
        fade = 1.0
        if k + 1 < len(scenes):
            fade = min(1.0, max(0.0, (s["_t1"] - t) / 0.22))
        for e in els[k]:
            e.draw(canvas, t, fade)
        d = ImageDraw.Draw(canvas)
        d.rectangle([0, HEADER_H - 4, int(W * min(1, t / dur)), HEADER_H + 4], fill=RED)
        for a, b, txt in caps:
            if a <= t < b:
                f = fit(txt, "Black", W - 80, 54, 28)
                d.text((W / 2, CAP_Y), txt, font=f, fill=NAVY, anchor="mm")
                break
        ff.stdin.write(canvas.convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    if ff.returncode != 0:
        raise SystemExit("ffmpeg failed")
    return out


# ---------- cover + image post (same look as the Oct 17 cover) ----------
def first_photo(story):
    for s in story["scenes"]:
        if s.get("image") and os.path.exists(s["image"]):
            return load(s["image"]), bool(s.get("file_photo")), s.get("name") or s.get("label")
        for c in s.get("cards", []):
            if c.get("image") and os.path.exists(c["image"]):
                return load(c["image"]), bool(c.get("file_photo")), None
    return None, False, None


def headline_block(canvas, story, y, max_h):
    d = ImageDraw.Draw(canvas)
    top = (story.get("head_top") or "").upper().strip()
    red = (story.get("head_red") or "").upper().strip()
    if not top and not red:
        ws = story["headline"].upper().split()
        k = max(1, len(ws) // 2)
        top, red = " ".join(ws[:k]), " ".join(ws[k:])
    size = 120
    while size > 40:
        ft, fr = font("Black", size * 0.86), font("Black", size)
        lt, lr = wrap(top, ft, W - 80) if top else [], wrap(red, fr, W - 60) if red else []
        hgt = len(lt) * ft.size * 1.02 + len(lr) * fr.size * 1.02
        if len(lt) + len(lr) <= 4 and hgt <= max_h and all(tlen(l, ft) <= W - 80 for l in lt) \
                and all(tlen(l, fr) <= W - 60 for l in lr):
            break
        size -= 3
    yy = y + (max_h - hgt) / 2
    for l in lt:
        d.text((W / 2, yy), l, font=ft, fill=NAVY, anchor="ma")
        yy += ft.size * 1.02
    for l in lr:
        d.text((W / 2, yy), l, font=fr, fill=RED, anchor="ma")
        yy += fr.size * 1.02


def stat_row(canvas, stats, y, h=168):
    if not stats:
        return
    n = min(3, len(stats))
    gap, margin = 32, 60
    cw = (W - 2 * margin - gap * (n - 1)) / n
    for i, s in enumerate(stats[:n]):
        x0 = margin + i * (cw + gap)
        sp = Sprite(cw, h, pad=24)
        sp.shadow([0, 0, cw, h], 26, blur=10, alpha=30, dy=5)
        sp.d.rounded_rectangle(sp.box([0, 0, cw, h]), radius=26, fill=WHITE, outline=BORDER, width=3)
        v, l = str(s.get("value", "")).upper(), str(s.get("label", "")).upper()
        sp.text((cw / 2, h * 0.40), v, fit(v, "Black", cw - 36, 74, 30), COL.get(s.get("color", "navy"), NAVY), "mm")
        sp.text((cw / 2, h * 0.76), l, fit(l, "Bold", cw - 30, 32, 18), GREY, "mm")
        canvas.alpha_composite(sp.im, (int(x0 - sp.pad), int(y - sp.pad)))


def render_cover(story, out_dir):
    c = grid_bg(W, H, grid=False).convert("RGBA")
    d = ImageDraw.Draw(c)
    lg = round_logo(100)
    f = font("Black", 56)
    tw = tlen("THE 30s BRIEF", f)
    x = (W - 100 - 44 - tw) / 2
    c.alpha_composite(lg, (int(x), 135))
    d.text((x + 144, 185), "THE 30s BRIEF", font=f, fill=NAVY, anchor="lm")
    if story.get("tag"):
        p, pw, ph = pill_sprite(story["tag"].upper(), font("Black", 44), RED, padx=38, h=86)
        c.alpha_composite(p.im, (int(W / 2 - pw / 2 - p.pad), 288 - p.pad))
    headline_block(c, story, 410, 230)
    img, fp, label = first_photo(story)
    if img is not None:
        cs = card_sprite(img, 780, 715, story.get("cover_label", label), NAVY, None, fp, border=10, r=44)
        c.alpha_composite(cs.im, (150 - cs.pad, 670 - cs.pad))
    stat_row(c, story.get("stats"), 1478)
    p, pw, ph = pill_sprite("WATCH IN 30 SECONDS  ▶", font("Black", 48), RED, padx=52, h=92)
    c.alpha_composite(p.im, (int(W / 2 - pw / 2 - p.pad), 1715 - p.pad))
    out = os.path.join(out_dir, f"{story['slug']}-cover.jpg")
    c.convert("RGB").save(out, quality=93)
    return out


def render_post(story, out_dir):
    PH = 1350
    c = grid_bg(W, PH, grid=False).convert("RGBA")
    d = ImageDraw.Draw(c)
    lg = round_logo(80)
    f = font("Black", 46)
    tw = tlen("THE 30s BRIEF", f)
    x = (W - 80 - 36 - tw) / 2
    c.alpha_composite(lg, (int(x), 44))
    d.text((x + 116, 84), "THE 30s BRIEF", font=f, fill=NAVY, anchor="lm")
    if story.get("tag"):
        p, pw, ph = pill_sprite(story["tag"].upper(), font("Black", 36), RED, padx=32, h=70)
        c.alpha_composite(p.im, (int(W / 2 - pw / 2 - p.pad), 150 - p.pad))
    headline_block(c, story, 238, 200)
    img, fp, label = first_photo(story)
    if img is not None:
        cs = card_sprite(img, 640, 560, story.get("cover_label", label), NAVY, None, fp, border=10, r=40)
        c.alpha_composite(cs.im, (220 - cs.pad, 470 - cs.pad))
    stat_row(c, story.get("stats"), 1110, h=150)
    out = os.path.join(out_dir, f"{story['slug']}-post.jpg")
    c.convert("RGB").save(out, quality=93)
    return out


if __name__ == "__main__":
    story = json.load(open(sys.argv[1]))
    od = sys.argv[2]
    os.makedirs(od, exist_ok=True)
    print(render_reel(story, od))
    print(render_cover(story, od))
    print(render_post(story, od))
