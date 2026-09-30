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
import difflib
import hashlib
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


def row_hashes(im):
    data, stride = im.tobytes(), im.width * 3
    return [hashlib.md5(data[i * stride:(i + 1) * stride]).digest() for i in range(im.height)]


def make_diff(before, after, out):
    """Highlight changed content in `after`, ignoring vertical shifts.

    Rows are aligned with a sequence match on per-row hashes, so content that
    only moved because something above it grew or shrank is left alone.
    Inserted rows get a red tint, replaced rows get a per-pixel diff, and a
    removed block is marked with a thin red bar at the point it was removed.
    """
    width = max(before.width, after.width)
    b, a = pad_to(before, (width, before.height)), pad_to(after, (width, after.height))
    ops = difflib.SequenceMatcher(None, row_hashes(b), row_hashes(a), autojunk=False).get_opcodes()

    mask = Image.new("L", a.size, 0)          # per-pixel changes
    tint = Image.new("L", a.size, 0)          # inserted rows
    bars = []                                 # y positions of removed blocks
    boxes = []
    changed = 0
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        if tag == "replace" and (i2 - i1) == (j2 - j1):
            region = ImageChops.difference(a.crop((0, j1, width, j2)), b.crop((0, i1, width, i2)))
            region = region.convert("L").point(lambda v: 255 if v > 16 else 0)
            mask.paste(region, (0, j1))
            changed += sum(1 for v in region.getdata() if v)
            boxes.append((0, j1, width - 1, j2 - 1))
            continue
        if j2 > j1:                           # rows only in after (insert, or uneven replace)
            tint.paste(255, (0, j1, width, j2))
            changed += (j2 - j1) * width
            boxes.append((0, j1, width - 1, j2 - 1))
        if i2 > i1:                           # rows only in before
            bars.append(j1)
            boxes.append((0, max(0, j1 - 3), width - 1, min(a.height - 1, j1 + 3)))

    faded = Image.blend(a.convert("L").convert("RGB"), Image.new("RGB", a.size, "white"), 0.55)
    if changed == 0 and not bars:
        faded.save(out)
        return 0.0
    red = Image.new("RGB", a.size, (220, 30, 30))
    diff = Image.composite(Image.blend(faded, red, 0.35), faded, tint)
    diff = Image.composite(red, diff, mask.filter(ImageFilter.MaxFilter(9)))
    draw = ImageDraw.Draw(diff)
    for y in bars:
        draw.rectangle((0, max(0, y - 3), width - 1, min(a.height - 1, y + 3)), fill=(220, 30, 30))
    for x0, y0, x1, y1 in boxes:
        draw.rectangle((x0, max(0, y0 - 10), x1, min(a.height - 1, y1 + 10)), outline=(220, 30, 30), width=4)
    diff.save(out)
    return 100.0 * changed / (a.width * a.height)


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
