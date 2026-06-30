# Updating download counts

When a new periodic Alfred Gallery stats batch arrives, follow these steps.

## TL;DR

```sh
cd /Users/giovanni/github/alfred-gallery-downloads
pbpaste | ./update_gallery_downloads.py        # copy the stats block first
git commit -am "Update gallery downloads $(date +%F)"
git push
```

That's it — the badges in every workflow README update automatically once pushed.

---

## Step by step

### 1. Copy the stats block

Select and copy the raw batch, exactly as received, e.g.:

```
convert·············5163
outlook-suite·······4398
michelin-guide······951
```

The dot/space leaders and column alignment don't matter — the script parses
`slug <leaders> count` per line.

### 2. Run the updater

From inside this repo:

```sh
pbpaste | ./update_gallery_downloads.py
```

- Dates the snapshot **today** by default.
- Adds a new dated entry per workflow (newest-first) in `downloads.json`.
- **New workflows** in the batch are added automatically.
- A workflow that drops out of the batch keeps its old history untouched.

The script prints a summary, e.g.
`date=2026-06-29: parsed 15 workflows, recorded 15 -> downloads.json`.

### 3. Commit and push

```sh
git commit -am "Update gallery downloads $(date +%F)"
git push
```

The shields.io badges read the raw `downloads.json` from GitHub, so they refresh
within a few minutes of the push (shields caches briefly).

---

## Variations

### The batch is old / you forgot to upload for a while

Override the date (otherwise it records as today):

```sh
pbpaste | ./update_gallery_downloads.py --date 2026-05-31
```

Backfilling out-of-order is safe: each workflow's history is re-sorted
newest-first on every write, so the badge (which reads `[0]`) always shows the
most recent count regardless of the order you add batches.

### Read from a file instead of the clipboard

```sh
./update_gallery_downloads.py batch.txt            # date = file's modified time
./update_gallery_downloads.py --date 2026-05-31 batch.txt
```

### Embed the date in the dump

If you paste a `YYYY-MM-DD` line (optionally prefixed `#` or `date:`) anywhere in
the block, the script uses it automatically — no `--date` needed:

```
2026-05-31
convert·············5163
...
```

**Date precedence:** `--date` flag  >  date line in the dump  >  file mtime  >  today.

---

## Adding the badge to a NEW workflow

The script tracks the data for a new workflow automatically, but its README
needs the badge added once. Replace `SLUG` with the workflow's Gallery slug
(the key in `downloads.json`):

```html
<a href="https://alfred.app/workflows/giovannicoppola/SLUG/">
<img alt="Gallery Downloads"
src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fgiovannicoppola%2Falfred-gallery-downloads%2Fmain%2Fdownloads.json&query=%24.SLUG%5B0%5D.count&label=Gallery%20Downloads&color=5C1F87&logo=alfred"><br/>
</a>
```

## Notes

- This repo **must stay public** — shields.io fetches `downloads.json` anonymously.
- Badge URLs hardcode the `main` branch; keep the default branch named `main`.
- Gallery slugs are not always the repo name (e.g. `michelin-guide` →
  `alfred-michelin`); the slug is whatever the gallery stats use, and that's the
  key stored in `downloads.json`.
