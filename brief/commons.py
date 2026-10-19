"""Find and download free-license photos from Wikimedia Commons.

    python3 brief/commons.py search "Lake Apopka Florida" [limit]
        -> prints candidates: index | title | WxH | license | artist
    python3 brief/commons.py get "File:Some photo.jpg" OUT.jpg
        -> downloads a 1600px version and prints the credit line as JSON

Only licenses safe for reuse are accepted (public domain, CC0, CC BY, CC BY-SA).
Credit line goes in the Facebook caption: "Photo: <artist> / Wikimedia Commons (<license>)".
"""
import json, re, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "the30sbrief-bot/1.0 (https://github.com/absayyed4-design/the30sbrief-media; absayyed4-design@users.noreply.github.com) python-urllib"}
OK = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? ?\d|cc-by|cc by-sa|cc-by-sa)", re.I)


def fetch(url, timeout=60):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(int(e.headers.get("Retry-After") or 0) or 3 * (attempt + 1))


def call(params):
    return json.loads(fetch(API + "?" + urllib.parse.urlencode({**params, "format": "json"}), 30))


def clean(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


def info(pages):
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        m = ii.get("extmetadata", {})
        lic = clean(m.get("LicenseShortName", {}).get("value"))
        out.append({"title": p["title"], "w": ii.get("width"), "h": ii.get("height"),
                    "license": lic, "artist": clean(m.get("Artist", {}).get("value"))[:80],
                    "url": ii.get("url"), "ok": bool(OK.match(lic))})
    return out


def search(q, limit=8):
    r = call({"action": "query", "generator": "search", "gsrnamespace": 6, "gsrlimit": limit,
              "gsrsearch": f"{q} filetype:bitmap", "prop": "imageinfo",
              "iiprop": "url|size|extmetadata", "iiurlwidth": 1600,
              "iiextmetadatafilter": "LicenseShortName|Artist"})
    pages = sorted(r.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    return info(pages)


def get(title, out):
    r = call({"action": "query", "titles": title, "prop": "imageinfo",
              "iiprop": "url|size|extmetadata", "iiurlwidth": 1600,
              "iiextmetadatafilter": "LicenseShortName|Artist"})
    item = info(r["query"]["pages"].values())[0]
    if not item["ok"]:
        raise SystemExit(f"License not allowed: {item['license']}")
    open(out, "wb").write(fetch(item["url"], 120))
    try:  # originals can be huge; shrink to max 2000px
        from PIL import Image
        im = Image.open(out); im.thumbnail((2000, 2000)); im.convert("RGB").save(out, "JPEG", quality=90)
    except Exception as e:
        raise SystemExit(f"Not a usable image: {e}")
    item["credit"] = f"Photo: {item['artist'] or 'Unknown'} / Wikimedia Commons ({item['license']})"
    print(json.dumps(item))


if __name__ == "__main__":
    if sys.argv[1] == "search":
        for i, c in enumerate(search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)):
            print(i, "|", c["title"], "|", f"{c['w']}x{c['h']}", "|", c["license"], "|", c["artist"], "|", "OK" if c["ok"] else "SKIP")
    elif sys.argv[1] == "get":
        get(sys.argv[2], sys.argv[3])
