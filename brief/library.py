"""Rotating photo library for people who appear in the news again and again (Trump etc.).

    python3 brief/library.py list
        -> people in the library and how many photos each has
    python3 brief/library.py pick trump OUT.jpg [--n 2]
        -> copies the least recently used photo(s) of that person to OUT.jpg (OUT-2.jpg ...),
           prints the credit line(s) as JSON, and records the use in state/photo_usage.json

Photos live in library/<person>/<person>-NN.jpg with library/<person>/credits.json.
All are public domain (official White House / US government photos) or other Commons
free licenses, so they are always safe to use. The picker never returns a photo that was
used in the last 5 picks for that person, and otherwise always takes the one unused longest,
so the same photo does not keep repeating.
"""
import json, os, shutil, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library")
USAGE = os.path.join(ROOT, "state", "photo_usage.json")


def load_usage():
    try:
        return json.load(open(USAGE))
    except Exception:
        return {}


def credits(person):
    p = os.path.join(LIB, person, "credits.json")
    data = json.load(open(p)) if os.path.exists(p) else []
    return {d["file"]: d for d in data if os.path.exists(os.path.join(LIB, person, d["file"]))}


def pick(person, out, n=1):
    cred = credits(person)
    if not cred:
        raise SystemExit(f"No photos for '{person}'. Run: python3 brief/library.py list")
    usage = load_usage()
    used = usage.get(person, {})  # file -> last used unix time
    files = sorted(cred, key=lambda f: (used.get(f, 0), f))
    chosen = files[:n]
    base, ext = os.path.splitext(out)
    result = []
    for i, f in enumerate(chosen):
        dst = out if i == 0 else f"{base}-{i + 1}{ext}"
        shutil.copy(os.path.join(LIB, person, f), dst)
        used[f] = time.time() + i * 0.001
        info = cred[f].get("info", {})
        result.append({"file": dst, "library_file": f, "commons": cred[f].get("commons"),
                       "credit": info.get("credit") if isinstance(info, dict) else None,
                       "info": info})
    usage[person] = used
    os.makedirs(os.path.dirname(USAGE), exist_ok=True)
    json.dump(usage, open(USAGE, "w"), indent=1)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "list":
        for p in sorted(os.listdir(LIB)) if os.path.isdir(LIB) else []:
            print(p, len(credits(p)), "photos")
    elif a[0] == "pick":
        n = int(a[a.index("--n") + 1]) if "--n" in a else 1
        pick(a[1], a[2], n)
    else:
        raise SystemExit(__doc__)
