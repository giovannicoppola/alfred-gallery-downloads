#!/usr/bin/env python3
"""Merge a pasted Alfred Gallery stats dump into downloads.json (dated history).

Usage:
    pbpaste | ./update_gallery_downloads.py            # date = today
    ./update_gallery_downloads.py dump.txt             # date = file mtime
    ./update_gallery_downloads.py --date 2026-05-31    # explicit override (e.g. late upload)

Dump format (one workflow per line; dot/space leaders are fine):
    convert.............5163
    michelin-guide......951
"""
import argparse, datetime, json, re, sys
from pathlib import Path

DATA = Path(__file__).with_name("downloads.json")
LINE = re.compile(r"^([A-Za-z0-9-]+)[.·\s]+(\d+)\s*$")             # slug <leaders> count
DATELINE = re.compile(r"^\s*#?\s*(?:date:\s*)?(\d{4}-\d{2}-\d{2})\s*$")  # 2026-04-14 / # 2026-04-14


def parse_dump(text):
    counts, found_date = {}, None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        d = DATELINE.match(s)
        if d:
            found_date = d.group(1)            # optional date line embedded in the dump
            continue
        m = LINE.match(s)
        if m:
            counts[m.group(1)] = int(m.group(2))
        else:
            print(f"skipped (no match): {s!r}", file=sys.stderr)
    return counts, found_date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile", nargs="?", help="dump file; omit to read stdin")
    ap.add_argument("--date", help="explicit YYYY-MM-DD; overrides everything")
    args = ap.parse_args()

    text = Path(args.infile).read_text() if args.infile else sys.stdin.read()
    counts, dump_date = parse_dump(text)

    # precedence: --date  >  date line in dump  >  file mtime  >  today
    if args.date:
        date = args.date
    elif dump_date:
        date = dump_date
    elif args.infile:
        date = datetime.date.fromtimestamp(Path(args.infile).stat().st_mtime).isoformat()
    else:
        date = datetime.date.today().isoformat()

    data = json.loads(DATA.read_text()) if DATA.exists() else {}
    changed = 0
    for slug, count in counts.items():
        hist = data.setdefault(slug, [])       # new workflow -> fresh history
        entry = {"date": date, "count": count, "display": f"{count:,}"}
        existing = next((e for e in hist if e.get("date") == date), None)
        if existing:
            existing.update(entry)             # one snapshot per date -> update in place
        else:
            hist.append(entry)
        changed += 1

    for hist in data.values():                 # keep every history newest-first,
        hist.sort(key=lambda e: e["date"], reverse=True)  # so backfill order never matters

    DATA.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"date={date}: parsed {len(counts)} workflows, recorded {changed} -> {DATA}")


if __name__ == "__main__":
    main()
