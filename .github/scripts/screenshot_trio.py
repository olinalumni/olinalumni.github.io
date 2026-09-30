#!/usr/bin/env python3
"""Generate before/after/diff screenshots for a frontend change.

Serves the base ref and the working tree on local HTTP servers, screenshots
each page with headless Chrome, and writes a pixel diff. Output lands in
.github/screenshots/<branch>/<page>-{before,after,diff}.png and a Markdown
table is printed for pasting into the PR description.

Usage:
  python3 .github/scripts/screenshot_trio.py [--base master] [--page /]... [--width 1280]

Requires Google Chrome (or set CHROME=/path/to/chrome) and Pillow
(`python3 -m pip install pillow`).
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
except ImportError:
    sys.exit("Pillow is required: python3 -m pip install pillow")

CHROME_CANDIDATES = [
    os.environ.get("CHROME"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    shutil.which("google-chrome"),
    shutil.which("google-chrome-stable"),
    shutil.which("chromium"),
    shutil.which("chromium-browser"),
]
CAPTURE_HEIGHT = 8000  # tall enough for every page on this site; trimmed later
BOTTOM_PAD = 40
# Third-party embeds that load asynchronously and change layout when they land
# (Twitter follow buttons, Facebook SDK, analytics). Blocking them keeps two
# captures of the same tree pixel-identical, at the cost of the embeds
# rendering as their plain-link fallbacks.
BLOCKED_HOSTS = [
    "platform.twitter.com", "syndication.twitter.com", "connect.facebook.net",
    "www.google-analytics.com", "ssl.google-analytics.com", "www.googletagmanager.com",
]


def find_chrome():
    for c in CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    sys.exit("Chrome not found. Set CHROME=/path/to/chrome.")


def git(*args, **kw):
    return subprocess.check_output(["git", *args], text=True, **kw).strip()


def serve(directory, port):
    return subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", directory],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def screenshot(chrome, url, out, width):
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--window-size={width},{CAPTURE_HEIGHT}", "--virtual-time-budget=8000",
         "--host-resolver-rules=" + ", ".join(f"MAP {h} ~NOTFOUND" for h in BLOCKED_HOSTS),
         f"--screenshot={out}", url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )


def trim_bottom(path):
    """Cut the empty area below the page content, keeping a small margin."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    bg = im.getpixel((w - 1, h - 1))
    px = im.load()
    last = h - 1
    while last > 0 and all(px[x, last] == bg for x in range(0, w, 8)):
        last -= 1
    im = im.crop((0, 0, w, min(h, last + 1 + BOTTOM_PAD)))
    im.save(path)
    return im


def pad_to(im, size):
    if im.size == size:
        return im
    out = Image.new("RGB", size, "white")
    out.paste(im, (0, 0))
    return out


def make_diff(before, after, out):
    size = (max(before.width, after.width), max(before.height, after.height))
    b, a = pad_to(before, size), pad_to(after, size)
    mask = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v > 16 else 0)
    changed = sum(1 for v in mask.getdata() if v)
    total = size[0] * size[1]
    if changed == 0:
        base = a.convert("L").convert("RGB")
        base.save(out)
        return 0.0
    halo = mask.filter(ImageFilter.MaxFilter(9))
    faded = Image.blend(a.convert("L").convert("RGB"), Image.new("RGB", size, "white"), 0.55)
    red = Image.new("RGB", size, (220, 30, 30))
    diff = Image.composite(red, faded, halo)
    box = halo.getbbox()
    ImageDraw.Draw(diff).rectangle(
        (max(0, box[0] - 12), max(0, box[1] - 12), min(size[0] - 1, box[2] + 12), min(size[1] - 1, box[3] + 12)),
        outline=(220, 30, 30), width=4,
    )
    diff.save(out)
    return 100.0 * changed / total


def slug(page):
    s = page.strip("/").replace("/", "-")
    return s or "home"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="master", help="git ref to screenshot as 'before' (default: master)")
    ap.add_argument("--page", action="append", default=[], help="page path to capture, repeatable (default: /)")
    ap.add_argument("--width", type=int, default=1280, help="viewport width in px (default: 1280)")
    ap.add_argument("--out", default=None, help="output dir (default: .github/screenshots/<branch>)")
    args = ap.parse_args()
    pages = args.page or ["/"]

    root = git("rev-parse", "--show-toplevel")
    os.chdir(root)
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    out_dir = args.out or os.path.join(".github", "screenshots", branch.replace("/", "-"))
    os.makedirs(out_dir, exist_ok=True)
    out_dir = os.path.relpath(out_dir, root) if os.path.isabs(out_dir) and out_dir.startswith(root) else out_dir
    chrome = find_chrome()

    base_dir = tempfile.mkdtemp(prefix="screenshot-base-")
    procs = []
    try:
        git("worktree", "add", "--detach", "--quiet", base_dir, args.base)
        procs.append(serve(base_dir, 8781))
        procs.append(serve(root, 8782))
        time.sleep(1)
        rows = []
        for page in pages:
            name = slug(page)
            before_p = os.path.join(out_dir, f"{name}-before.png")
            after_p = os.path.join(out_dir, f"{name}-after.png")
            diff_p = os.path.join(out_dir, f"{name}-diff.png")
            screenshot(chrome, f"http://127.0.0.1:8781{page}", before_p, args.width)
            screenshot(chrome, f"http://127.0.0.1:8782{page}", after_p, args.width)
            before = trim_bottom(before_p)
            after = trim_bottom(after_p)
            pct = make_diff(before, after, diff_p)
            rows.append((page, before_p, after_p, diff_p, pct))
            print(f"{page}: {pct:.2f}% of pixels changed -> {out_dir}/{name}-{{before,after,diff}}.png", file=sys.stderr)
    finally:
        for p in procs:
            p.terminate()
        subprocess.run(["git", "worktree", "remove", "--force", base_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("\nCommit the images, then paste this into the PR (replace <sha> with that commit):\n")
    raw = "https://raw.githubusercontent.com/olinalumni/olinalumni.github.io/<sha>/"
    for page, b, a, d, pct in rows:
        print(f"### `{page}`\n")
        print("| Before | After | Diff |")
        print("| --- | --- | --- |")
        print(f"| ![before]({raw}{b}) | ![after]({raw}{a}) | ![diff]({raw}{d}) |\n")


if __name__ == "__main__":
    main()
