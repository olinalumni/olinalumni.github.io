# Working in this repo

This is the static site for olinalumni.org, served by GitHub Pages from
`master`. There is no build step.

## Frontend changes need screenshots

Any PR that changes a rendered file (`index.html`, `resources/`, `css/`,
`tags/`, `img/`, `_data/`) must include before/after/diff screenshots for
each affected page. Generate them on the branch with:

```
python3 .github/scripts/screenshot_trio.py --page / [--page /other/page/]
```

Commit the images it writes under `.github/screenshots/<branch>/`, push, then
put the Markdown table it prints in the PR's **Screenshots** section with
`<sha>` replaced by the commit that added the images. Look at the diff image
before opening the PR and confirm the red region matches the intended change.

Full rules are in `CONTRIBUTING.md`. The PR template in `.github/` has the
section layout.
