"""Publish finished files to the `media` branch so Facebook can fetch them by URL.

    python3 brief/host.py FILE [FILE ...]
        -> prints one public raw.githubusercontent.com URL per file

Each call replaces the `media` branch with a single fresh commit (force push), so the
repo never grows. Facebook downloads the files while the post is being created, so it
is fine that the next run replaces them. Use unique file names (slug + timestamp).
"""
import os, shutil, subprocess, sys, tempfile

REPO = "absayyed4-design/the30sbrief-media"
BRANCH = "media"


def run(*cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True)


def main(files):
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                          cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
    remote = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True,
                            cwd=root).stdout.strip()
    tmp = tempfile.mkdtemp(prefix="media-")
    try:
        run("git", "init", "-q", "-b", BRANCH, cwd=tmp)
        for f in files:
            shutil.copy(f, os.path.join(tmp, os.path.basename(f)))
        run("git", "add", "-A", cwd=tmp)
        run("git", "-c", "user.name=the30sbrief-bot", "-c", "user.email=absayyed4-design@users.noreply.github.com",
            "commit", "-q", "-m", "media", cwd=tmp)
        run("git", "push", "-q", "--force", remote, f"{BRANCH}:{BRANCH}", cwd=tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in files:
        print(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{os.path.basename(f)}")


if __name__ == "__main__":
    main(sys.argv[1:])
