# alfred-gallery-downloads

Single source of truth for [Alfred Gallery](https://alfred.app/) download counts of my
workflows, with dated history. Powers `shields.io` "Gallery Downloads" badges in each
workflow's README.

> ⚠️ This repo must stay **public** — shields.io fetches `downloads.json` anonymously.

## Updating

When a new periodic stats dump arrives, copy the block and run:

```sh
pbpaste | ./update_gallery_downloads.py                 # dated today
pbpaste | ./update_gallery_downloads.py --date 2026-05-31  # override if uploading late
./update_gallery_downloads.py dump.txt                  # from a file (uses file mtime)
```

Then `git commit && git push`. The script:

- parses the raw dump format (`slug······count`),
- stores one dated snapshot per workflow, newest-first,
- adds new workflows automatically,
- keeps every history sorted by date, so out-of-order/backfilled dumps self-correct.

## Badge snippet

In each workflow README, replace `SLUG` with that workflow's **Gallery slug**
(the key in `downloads.json`, which may differ from the repo name):

```html
<a href="https://alfred.app/workflows/giovannicoppola/SLUG/">
<img alt="Gallery Downloads"
src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fgiovannicoppola%2Falfred-gallery-downloads%2Fmain%2Fdownloads.json&query=%24.SLUG%5B0%5D.count&label=Gallery%20Downloads&color=5C1F87&logo=alfred"><br/>
</a>
```

`query=$.SLUG[0].count` reads the latest (newest-first) count for that workflow.
