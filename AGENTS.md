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

Commit the images it writes under `.github/screenshots/<branch>/`, push, then
put the Markdown table it prints in the PR's **Screenshots** section with
`<sha>` replaced by the commit that added the images. Look at the diff image
before opening the PR and confirm the red region matches the intended change.

The diff only highlights content that changed, not content that merely moved
up or down because something above it grew or shrank.

Details are in `CONTRIBUTING.md`. The PR template in `.github/` has the
section layout.
