#!/usr/bin/env python3
"""Merge a pasted Alfred Gallery stats dump into downloads.json (dated history).

Usage:
    pbpaste | ./update_gallery_downloads.py            # date = today
    ./update_gallery_downloads.py dump.txt             # date = file mtime
    ./update_gallery_downloads.py --date 2026-05-31    # explicit override (e.g. late upload)
    pbpaste | ./update_gallery_downloads.py --report   # update, print growth table, write markdown report
    ./update_gallery_downloads.py --report             # (no dump) print growth table; refresh per_day
    ./update_gallery_downloads.py --report-only        # print growth table; refresh per_day, no dump

Dump format (one workflow per line; dot/space leaders are fine):
    convert.............5163
    michelin-guide......951

Growth attribute:
    After sorting newest-first, each workflow's latest snapshot gets `per_day`:
    downloads/day over the most recent interval (latest − previous) / days.
    That is the preferred growth measure vs % / CAGR (which inflate small bases).
"""
import argparse, datetime, json, re, subprocess, sys
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


def parse_date(s: str) -> datetime.date:
    return datetime.date.fromisoformat(s)


def growth_metrics(hist: list) -> dict | None:
    """Return growth metrics for a newest-first history, or None if <2 snapshots."""
    if len(hist) < 2:
        return None
    latest, prev = hist[0], hist[1]
    days = max((parse_date(latest["date"]) - parse_date(prev["date"])).days, 1)
    delta = latest["count"] - prev["count"]
    per_day = round(delta / days, 2)
    pct = round(100.0 * delta / prev["count"], 1) if prev["count"] else None
    first = hist[-1]
    days_all = max((parse_date(latest["date"]) - parse_date(first["date"])).days, 1)
    delta_all = latest["count"] - first["count"]
    per_day_all = round(delta_all / days_all, 2)
    years = days_all / 365.25
    cagr = None
    if first["count"] > 0 and years > 0:
        cagr = round(((latest["count"] / first["count"]) ** (1 / years) - 1) * 100, 1)
    return {
        "slug": None,  # filled by caller
        "count": latest["count"],
        "date": latest["date"],
        "prev_date": prev["date"],
        "days": days,
        "delta": delta,
        "per_day": per_day,
        "pct": pct,
        "per_day_all": per_day_all,
        "cagr": cagr,
    }


def annotate_per_day(data: dict) -> None:
    """Set `per_day` on each workflow's latest snapshot; strip it from older ones."""
    for hist in data.values():
        hist.sort(key=lambda e: e["date"], reverse=True)
        for entry in hist:
            entry.pop("per_day", None)
        metrics = growth_metrics(hist)
        if metrics:
            hist[0]["per_day"] = metrics["per_day"]


def print_report(data: dict) -> None:
    rows = []
    for slug, hist in data.items():
        m = growth_metrics(hist)
        if not m:
            continue
        m["slug"] = slug
        rows.append(m)

    if not rows:
        print("No workflows with ≥2 snapshots — nothing to report.")
        return

    print("Growth report (latest interval)")
    print(
        f"{'slug':20} {'count':>6} {'Δ':>5} {'days':>4} "
        f"{'per_day':>7} {'pct':>7} {'per_day_all':>11} {'CAGR%':>7}"
    )
    print("-" * 78)
    for r in sorted(rows, key=lambda x: -x["per_day"]):
        pct = f"{r['pct']:.1f}%" if r["pct"] is not None else "—"
        cagr = f"{r['cagr']:.1f}" if r["cagr"] is not None else "—"
        print(
            f"{r['slug']:20} {r['count']:6d} {r['delta']:+5d} {r['days']:4d} "
            f"{r['per_day']:7.2f} {pct:>7} {r['per_day_all']:11.2f} {cagr:>7}"
        )
    print()
    print(
        "Best measure for comparing workflows: per_day "
        "(downloads/day over the latest interval)."
    )
    print("% growth and CAGR inflate newer/smaller bases; prefer per_day for ranking.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile", nargs="?", help="dump file; omit to read stdin")
    ap.add_argument("--date", help="explicit YYYY-MM-DD; overrides everything")
    ap.add_argument(
        "--report",
        action="store_true",
        help="after updating, print growth table and write a markdown report "
        "(or just print the table if no dump on stdin/file)",
    )
    ap.add_argument(
        "--report-only",
        action="store_true",
        help="print growth table and refresh per_day without ingesting a dump",
    )
    args = ap.parse_args()

    data = json.loads(DATA.read_text()) if DATA.exists() else {}

    if args.report_only:
        annotate_per_day(data)
        DATA.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        print_report(data)
        print(f"refreshed per_day -> {DATA}")
        return

    # If --report with no infile and stdin is a tty, just report.
    reading_dump = bool(args.infile) or not sys.stdin.isatty()
    if args.report and not reading_dump and not args.date:
        annotate_per_day(data)
        DATA.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        print_report(data)
        print(f"refreshed per_day -> {DATA}")
        return

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

    annotate_per_day(data)
    DATA.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"date={date}: parsed {len(counts)} workflows, recorded {changed} -> {DATA}")
    if args.report:
        print()
        print_report(data)
        report_script = Path(__file__).with_name("generate_report.py")
        if report_script.exists():
            subprocess.run([sys.executable, str(report_script), "--date", date], check=True)
        else:
            print(f"Warning: {report_script} not found, skipping report generation", file=sys.stderr)


if __name__ == "__main__":
    main()
