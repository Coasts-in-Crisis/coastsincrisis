NOTE: This README was created by Sonnet 5.

# Coasts in Crisis — rebuild notes

A record of rebuilding [coastsincrisis.net](https://web.archive.org/web/20240826215207/https://coastsincrisis.net/) — a Drupal 9 digital art exhibit about Caribbean arts and cultures after the 2017 hurricane season — as a static [11ty](https://www.11ty.dev/) site, from a Drupal backup and Wayback Machine snapshots.

## Starting materials

- `backup-coastsincrisis.net-6-12-2022.tar.gz` — the site's Drupal codebase, theme, and uploaded images
- `rebecc25_drup1.sql` — a full mysqldump of the site's database
- Wayback Machine snapshots of the live site, used as a visual/structural reference and for double-checking exact layout details

The database turned out to be the more valuable source: the real page content, titles, and text lived there as rows, not in the theme files, and it was higher-fidelity than anything scraped from Wayback would have been.

## What got built

**Homepage** — the interactive hurricane-path map: a base image of three colored storm tracks (María, José, Irma) with hover-triggered pathway buttons and three rotating decorative icons, each positioned precisely on its line by sampling the actual image pixel data rather than eyeballing it.

**Info pages** — About, Resources, People (artist bios, event team, dev team — including the site's own original developer).

**Three pathways**, each a landing page plus several linked artist/artwork pages chained together with "Spiral Back / Spiral Forward" navigation that loops back to the homepage at the end:

- *Entangled Ecologies* — landing page, Ode to the Fallen Trees, Groundscapes Displaced, Slave Trees
- *Creative Resistance* — landing page, After the Hurricane (Creating Art Was Healing), Reclamation, Welcome to Paradise, Against Disposability
- *Predictable Precarity* — landing page, Age of Abandonment, Shelter in Place, Deafening Silence, Foretelling a Catastrophic Future

18 pages total, all generated statically.

## Key decisions

- **11ty over anything more complex** — the site is small (18 nodes) and doesn't need a CMS; a static generator with plain Nunjucks templates was the right amount of tooling.
- **Vanilla CSS instead of Bootstrap** — the original ran on Bootstrap 3.4.1 (2019-era, jQuery-dependent, long past end of life). The real visual identity lived in the theme's own custom CSS layered on top, not in Bootstrap itself, so it wasn't worth carrying forward.
- **Content pulled from the database, not scraped from Wayback** — higher fidelity, and it meant the site could be rebuilt even where Wayback's capture was incomplete or visually mangled.

## Notable bugs found along the way

A few of these were genuinely subtle and worth remembering if this project gets touched again:

- **mysqldump splits large tables across multiple `INSERT` statements.** The People page came up completely empty on the first extraction pass because its content happened to land in the *second* `INSERT INTO node__body` statement, and the extraction script was only reading the first.
- **The site's hurricane-name labels didn't match their actual rendered colors.** Files and CSS classes named after "María" were actually the green path; "Irma" was magenta; only "José" (yellow) matched its name. This was true consistently across the homepage icons, the hover-overlay images, and each pathway's background art — confirmed by sampling actual pixel colors rather than trusting file names.
- **CSS animations silently override static transforms on the same element.** The rotating hurricane icons all originally used `transform: rotate()` (via the `.rotate` animation) and `transform: translate(-50%, -50%)` (for centering) on the *same* element — the animation always won, breaking the centering. Fixed by splitting each icon into a positioning wrapper and a separately-rotating child.
- **`object-fit: cover` crops unpredictably when a background image sits behind content of unknown height.** The pathway background art (the colored line drawings behind each pathway's landing page) needs to scale by width and let height follow naturally, not "cover" the full content area — otherwise a page with a lot of text would zoom and crop the artwork differently than a short one.
- **A single CSS specificity mistake silently defeated three different attempted fixes** for one bug (floated images being forced to a fixed 45% width instead of their real size) before it was actually solved — worth remembering that `.class img` and `figure.class img` have different specificity even though they look similar, and that `width: revert` doesn't reliably restore an HTML `width=""` attribute across browsers the way you'd expect.
- **Emergent float-stacking order doesn't always match source order.** On one page, two right-floated elements (a video and a text box) rendered in the *wrong* visual order relative to the original site, even though the DOM order matched — root-caused by comparing exact pixel measurements against the live Wayback page via JS, not by guessing from CSS theory.

## Tools written along the way

Both are in `scripts/` and documented in their own headers:

- **`drupal_extract.py`** — pulls node content, titles, and URL aliases straight out of the raw `.sql` dump, no database required. Handles the multi-`INSERT`-statement gotcha above.
- **`find_line_position.py`** — samples actual pixel colors in the line-art images to find precise, verifiable placement coordinates (with real clearance from other colors, not just "the nearest pixel") — used for every icon and background-art placement across the homepage and all three pathways.

## If you're doing this by hand

A few things that would trip up a manual reproduction and weren't obvious going in:

- **Environment**: Node.js + npm for 11ty; Python 3 with Pillow (`pip install pillow`) for the image-analysis script. No database server required — both scripts work directly on the raw backup files.
- **Filenames in the tar have spaces** (e.g. `Regrowth I_DavidBerg_0.jpg`) — quote paths in `tar` commands. Image `src` values in the database are also URL-encoded (`%20` for spaces), so decode those before matching them against the tar's actual file listing.
- **Targeted extraction is much faster than unpacking everything.** The backup is 117MB; `tar -xzf archive.tar.gz path/to/one/file.jpg` pulls a single file out directly without extracting the rest.
- **Don't trust an extracted image's own resolution as its intended display size.** The files in the backup are the full-resolution originals — much larger than what Drupal actually displayed via its resized "medium" image style. The real intended size is in the `width=""`/`height=""` attributes on each `<img>` tag in the database content (or in a Wayback snapshot's rendered HTML), not the file's own pixel dimensions. Using the file's real resolution instead is what caused the "images too small/too large" bugs during this build.
- **The Wayback Machine's CDX API will rate-limit you** (`429 Too Many Requests`) if queried too quickly — space requests out. It's also worth querying the CDX API (`http://web.archive.org/cdx/search/cdx?url=...`) to find a timestamp that was actually captured for a given sub-page, rather than assuming one global snapshot date covers the whole site — not every page was crawled on every date.
- **The SQL dump's text fields are escape-encoded, not raw HTML** — literal `\'`, `\"`, and `\r\n` sequences need unescaping before the content is usable. The lower-effort alternative is restoring the dump into a local MySQL/MariaDB and browsing it with a GUI (TablePlus, Sequel Ace, phpMyAdmin) instead of parsing the text by hand — see the note at the bottom of `drupal_extract.py`.

## Where this leaves things

The 11ty site itself is functionally complete: all 18 pages, three pathways, full nav, and content matching the original database. Deployment (gh-pages or otherwise) wasn't something I set up as part of this conversation — check the git history for anything done separately there.
