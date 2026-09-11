olinalumni
==========

A website for Olin Alumni using [GitHub Pages](http://pages.github.com/)

Making changes
--------------
Please feel free to suggest new content or fix errors with this site. You can either "Open an Issue" on this GitHub Project to request changes to the site, or directly submit a pull request yourself.


Adding content to cards
-----------------------
The 'card' elements on the page are set up to use a riot template for ease of modification. The template is contained in the tags/card-list.tag file. It reads more or less like html with javascript inserted items. The content for each card-list itself is in a javascript object below each card-list tag. Social media fields in the content objects will only display if the field is included in the object (ie. a youtube link will only be displayed if the youtubeURL field is included in the object).

Running locally
---------------
Since it's just a static app, you can serve the files really easily

- `python3 -m http.server 8000` (the old `python -m SimpleHTTPServer` is Python 2, which no longer ships with macOS)

Some pages (`resources/banter/`) load ES modules and fetch from Supabase, which requires serving over `http://`, not opening the file directly — run the command above from the repo root and visit `http://localhost:8000/`.

Submitting changes
------------------
Fork this repo. Create a new branch off of master using your initials and the feature added (e.g. `tcr-socialmedia`). Submit that branch as a PR.

License
-------

MIT (code) and CC0 (resources)
