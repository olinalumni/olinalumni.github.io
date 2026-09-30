#!/usr/bin/env python3
"""Generate before/after/diff screenshots for a frontend change.

Serves the base ref and the working tree on local HTTP servers, screenshots
each page with headless Chrome, and writes a pixel diff. Output lands in
.github/screenshots/<branch>/<page>-{before,after,diff}.png and a Markdown
table is printed for pasting into the PR description.

Usage:
  python3 .github/scripts/screenshot_trio.py [--base master] [--page /]... [--width 1280]

Requires Google Chrome (or set CHROME=/path/to/chrome), Pillow, and numpy
(`python3 -m pip install pillow numpy`).
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
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    sys.exit("Pillow and numpy are required: python3 -m pip install pillow numpy")

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


PIXEL_THRESHOLD = 60  # per-channel difference, after a light blur, that counts as changed
RED = (220, 30, 30)


def row_hashes(im):
    data, stride = im.tobytes(), im.width * 3
    return [hashlib.md5(data[i * stride:(i + 1) * stride]).digest() for i in range(im.height)]


def neighbor_offsets(spans, length):
    """For each row, the offset of the nearest matched span above and below it."""
    if not spans:
        z = np.zeros(length, dtype=np.int64)
        return z, z
    sentinel = np.iinfo(np.int64).min
    known = np.full(length, sentinel, dtype=np.int64)
    for start, n, off in spans:
        known[start:start + n] = off
    has = known != sentinel
    idx = np.arange(length)
    up = np.maximum.accumulate(np.where(has, idx, -1))
    down = np.minimum.accumulate(np.where(has, idx, length)[::-1])[::-1]
    prev = np.where(up >= 0, known[np.maximum(up, 0)], spans[0][2])
    nxt = np.where(down < length, known[np.minimum(down, length - 1)], spans[-1][2])
    return prev, nxt


def unmatched_pixels(src, dst, prev, nxt):
    """Per-pixel change mask for src rows against the best nearby dst row.

    Each src row is compared with dst rows at the offset of the matched span
    above it and the one below it. Within an offset, each pixel may match the
    dst row one above or below, which absorbs sub-pixel layout shifts. The
    offset with the fewest differing pixels wins for the whole row, so pixels
    cannot pick unrelated matches independently.
    """
    h = src.shape[0]
    ys = np.arange(h)
    best_mask, best_count = None, None
    for off in (prev, nxt):
        diff = None
        for d in (-1, 0, 1):
            rows = ys + off + d
            valid = (rows >= 0) & (rows < dst.shape[0])
            dd = np.abs(src - dst[np.clip(rows, 0, dst.shape[0] - 1)]).max(axis=2)
            dd[~valid] = 255
            diff = dd if diff is None else np.minimum(diff, dd)
        mask = diff > PIXEL_THRESHOLD
        count = mask.sum(axis=1)
        if best_mask is None:
            best_mask, best_count = mask, count
        else:
            better = count < best_count
            best_mask[better] = mask[better]
            best_count = np.minimum(best_count, count)
    return best_mask


def row_ranges(rows, gap=12):
    ranges = []
    for y in np.flatnonzero(rows):
        if ranges and y - ranges[-1][1] <= gap:
            ranges[-1][1] = y
        else:
            ranges.append([y, y])
    return ranges


def make_diff(before, after, out):
    """Highlight changed content in `after`, ignoring vertical shifts.

    Rows are aligned by exact match first to find how far each part of the
    page moved. Every row is then compared against its aligned counterpart
    with a small tolerance, so content that only moved, even by a fraction of
    a pixel, is left alone. Changed pixels are painted red, and a red bar marks
    where content from `before` was removed.
    """
    width = max(before.width, after.width)
    b_img, a_img = pad_to(before, (width, before.height)), pad_to(after, (width, after.height))
    blocks = difflib.SequenceMatcher(None, row_hashes(b_img), row_hashes(a_img), autojunk=False).get_matching_blocks()
    blocks = [blk for blk in blocks if blk.size]

    soften = lambda im: np.asarray(im.filter(ImageFilter.GaussianBlur(1)), dtype=np.int16)
    b, a = soften(b_img), soften(a_img)
    a_prev, a_next = neighbor_offsets(sorted((j, n, i - j) for i, j, n in blocks), a.shape[0])
    b_prev, b_next = neighbor_offsets(sorted((i, n, j - i) for i, j, n in blocks), b.shape[0])
    a_mask = unmatched_pixels(a, b, a_prev, a_next)
    b_mask = unmatched_pixels(b, a, b_prev, b_next)

    a_rows = a_mask.any(axis=1)
    bars = []
    for y0, y1 in row_ranges(b_mask.any(axis=1)):
        y = int(np.clip(y0 + b_prev[y0], 0, a.shape[0] - 1))
        if not a_rows[max(0, y - 8):y + 9].any():
            bars.append(y)

    changed = int(a_mask.sum() + b_mask.sum())
    faded = Image.blend(a_img.convert("L").convert("RGB"), Image.new("RGB", a_img.size, "white"), 0.55)
    if changed == 0:
        faded.save(out)
        return 0.0
    halo = Image.fromarray((a_mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))
    diff = Image.composite(Image.new("RGB", a_img.size, RED), faded, halo)
    draw = ImageDraw.Draw(diff)
    for y0, y1 in row_ranges(a_rows):
        xs = np.flatnonzero(a_mask[y0:y1 + 1].any(axis=0))
        draw.rectangle((max(0, xs[0] - 12), max(0, y0 - 12), min(width - 1, xs[-1] + 12),
                        min(a.shape[0] - 1, y1 + 12)), outline=RED, width=4)
    for y in bars:
        draw.rectangle((0, max(0, y - 3), width - 1, min(a.shape[0] - 1, y + 3)), fill=RED)
    diff.save(out)
    return 100.0 * changed / (a.shape[0] * width)


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
            print(f"{page}: {pct:.2f}% of pixels changed or removed -> {out_dir}/{name}-{{before,after,diff}}.png", file=sys.stderr)
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
