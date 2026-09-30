# Contributing

## Frontend changes should include screenshots

A pull request that changes something a visitor can see should include a
**before / after / diff** screenshot trio for each affected page. That covers
edits to `index.html`, anything under `resources/`, `css/`, `tags/`, `img/`,
and `_data/`. Changes to only `README.md`, `CONTRIBUTING.md`, `CNAME`, or
files under `.github/` do not need them.

The trio is:

- **Before**: the page as rendered from `master`.
- **After**: the page as rendered from your branch.
- **Diff**: the after screenshot with changed content highlighted in red.
  The two captures are aligned first, so content that only moved because
  something above it grew or shrank is not flagged, even when the move is a
  fraction of a pixel. A thin red bar marks where content was removed.

Reviewers use the diff to confirm the change touched only what the PR says it
touched.

### Generating the trio

Run the script from the repo root on your branch. It needs Google Chrome and
the Pillow and numpy Python packages (`python3 -m pip install pillow numpy`).

```
python3 .github/scripts/screenshot_trio.py [--publish]
```

By default it captures `/` against `master`. Pass `--page` once per affected
page and `--base` to compare against something other than `master`:

```
python3 .github/scripts/screenshot_trio.py --page / --page /resources/banter/
```

Images are written to `.github/screenshots/<branch>/`, which is gitignored.
Look them over, especially the diff. Screenshots never go in the PR itself.

The script blocks a few asynchronous third-party embeds (Twitter follow
buttons, the Facebook SDK, analytics) so two captures of the same tree are
pixel-identical. Those embeds appear as their plain-link fallbacks in the
screenshots.

### Adding the trio to the PR

Screenshots live on a separate evidence branch, `evidence/<your-branch>`, so
the PR diff stays limited to the actual change. Publish them with:

```
python3 .github/scripts/screenshot_trio.py --no-capture --publish
```

That commits every image in `.github/screenshots/<branch>/` to the evidence
branch and pushes it, without touching your working tree or PR branch. It
prints Markdown with links pinned to the evidence commit. Paste that into the
**Screenshots** section of the PR description. Any extra images you put in the
folder, such as phone-width captures, are published and linked too.

Rerunning publish adds a new commit to the evidence branch, so links in older
PR descriptions keep working. Don't delete evidence branches after merging.

If you'd rather not push a branch, drag the three files into the PR
description on GitHub instead. Either way, aim to show all three.

## Branches

Create a branch off `master` and open a PR against `master`. See the README
for how the card lists on the homepage are built.
