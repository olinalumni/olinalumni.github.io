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
  Rows are aligned between the two captures first, so content that only moved
  because something above it grew or shrank is not flagged. A thin red bar
  marks where content was removed.

Reviewers use the diff to confirm the change touched only what the PR says it
touched.

### Generating the trio

Run the script from the repo root on your branch. It needs Google Chrome and
the Pillow Python package (`python3 -m pip install pillow`).

```
python3 .github/scripts/screenshot_trio.py
```

By default it captures `/` against `master`. Pass `--page` once per affected
page and `--base` to compare against something other than `master`:

```
python3 .github/scripts/screenshot_trio.py --page / --page /resources/banter/
```

Images are written to `.github/screenshots/<branch>/`. Commit them on your
branch. They are not published to the site because GitHub Pages skips
directories that start with a dot.

The script blocks a few asynchronous third-party embeds (Twitter follow
buttons, the Facebook SDK, analytics) so two captures of the same tree are
pixel-identical. Those embeds appear as their plain-link fallbacks in the
screenshots.

### Adding the trio to the PR

The script prints a Markdown table. Paste it into the **Screenshots** section
of the PR description and replace `<sha>` with the hash of the commit that
added the images, so the links keep working after the branch is deleted.

If you would rather not commit images, drag the three files into the PR
description on GitHub instead. Either way, aim to show all three.

## Branches

Create a branch off `master` and open a PR against `master`. See the README
for how the card lists on the homepage are built.
