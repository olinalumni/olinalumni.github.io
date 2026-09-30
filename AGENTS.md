# Working in this repo

This is the static site for olinalumni.org, served by GitHub Pages from
`master`. There is no build step.

## Frontend changes should include screenshots

A PR that changes a rendered file (`index.html`, `resources/`, `css/`,
`tags/`, `img/`, `_data/`) should include before/after/diff screenshots for
each affected page. Generate them on the branch with:

```
python3 .github/scripts/screenshot_trio.py --page / [--page /other/page/]
```

It writes the images to `.github/screenshots/<branch>/`, which is
gitignored. Look at the diff image and confirm the red region matches the
intended change. Then publish them to the evidence branch:

```
python3 .github/scripts/screenshot_trio.py --no-capture --publish
```

This pushes `evidence/<branch>` and prints Markdown with pinned links. Put
that in the PR's **Screenshots** section. Never commit screenshots to the PR
branch; they belong only on the evidence branch. Don't delete evidence
branches, since merged PR descriptions link to them.

The diff only highlights content that changed, not content that merely moved
up or down because something above it grew or shrank.

Details are in `CONTRIBUTING.md`. The PR template in `.github/` has the
section layout.
