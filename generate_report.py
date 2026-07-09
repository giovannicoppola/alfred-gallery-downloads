#!/usr/bin/env python3
"""Generate markdown reports with download stats and growth rates.

Usage:
    ./generate_report.py                    # generate report for latest data
    ./generate_report.py --date 2026-07-09  # generate report for specific date
"""
import argparse
import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DATA = Path(__file__).with_name("downloads.json")
REPORTS_DIR = Path(__file__).with_name("reports")


def calculate_growth(current: int, previous: int) -> Tuple[int, float]:
    """Calculate absolute and percentage growth."""
    delta = current - previous
    pct = (delta / previous * 100) if previous > 0 else 0.0
    return delta, pct


def get_workflow_stats(slug: str, history: List[Dict], target_date: str) -> Optional[Dict]:
    """Extract stats for a workflow at a specific date."""
    # Find the entry for target_date
    current = next((e for e in history if e["date"] == target_date), None)
    if not current:
        return None

    current_count = current["count"]

    # Find previous entry (next in list since sorted newest-first)
    current_idx = next((i for i, e in enumerate(history) if e["date"] == target_date), None)
    if current_idx is None or current_idx + 1 >= len(history):
        # No previous data
        return {
            "slug": slug,
            "current_count": current_count,
            "current_date": target_date,
            "previous_count": None,
            "previous_date": None,
            "delta": None,
            "growth_pct": None,
        }

    previous = history[current_idx + 1]
    previous_count = previous["count"]
    delta, growth_pct = calculate_growth(current_count, previous_count)

    # Calculate days between measurements
    current_dt = datetime.date.fromisoformat(target_date)
    previous_dt = datetime.date.fromisoformat(previous["date"])
    days_elapsed = (current_dt - previous_dt).days

    # Calculate CAGR using earliest available data point
    earliest = history[-1]  # Last entry (oldest date)
    earliest_count = earliest["count"]
    earliest_dt = datetime.date.fromisoformat(earliest["date"])
    total_days = (current_dt - earliest_dt).days

    if total_days > 0 and earliest_count > 0 and current_count > 0:
        years = total_days / 365.25
        cagr = (pow(current_count / earliest_count, 1 / years) - 1) * 100
    else:
        cagr = None

    return {
        "slug": slug,
        "current_count": current_count,
        "current_date": target_date,
        "previous_count": previous_count,
        "previous_date": previous["date"],
        "delta": delta,
        "growth_pct": growth_pct,
        "days_elapsed": days_elapsed,
        "cagr": cagr,
        "earliest_count": earliest_count,
        "earliest_date": earliest["date"],
        "total_days": total_days,
    }


def format_number(n: Optional[int]) -> str:
    """Format number with thousands separator."""
    return f"{n:,}" if n is not None else "N/A"


def format_growth(delta: Optional[int], pct: Optional[float]) -> str:
    """Format growth with +/- and percentage."""
    if delta is None or pct is None:
        return "N/A"
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:,} ({sign}{pct:.1f}%)"


def generate_markdown_report(data: Dict, target_date: str) -> str:
    """Generate a markdown report for all workflows."""
    stats_list = []

    for slug, history in data.items():
        stats = get_workflow_stats(slug, history, target_date)
        if stats:
            stats_list.append(stats)

    # Sort by current count descending
    stats_list.sort(key=lambda x: x["current_count"], reverse=True)

    # Calculate totals
    total_current = sum(s["current_count"] for s in stats_list)
    total_previous = sum(s["previous_count"] for s in stats_list if s["previous_count"] is not None)
    total_delta = total_current - total_previous if total_previous > 0 else None
    total_growth_pct = (total_delta / total_previous * 100) if total_previous > 0 and total_delta is not None else None

    # Build markdown
    lines = [
        f"# Alfred Gallery Download Report",
        f"",
        f"**Report Date:** {target_date}",
        f"",
        f"## Summary",
        f"",
        f"- **Total Downloads:** {format_number(total_current)}",
        f"- **Previous Total:** {format_number(total_previous)}",
        f"- **Growth:** {format_growth(total_delta, total_growth_pct)}",
        f"- **Workflows Tracked:** {len(stats_list)}",
        f"",
        f"## Workflow Details (by Downloads)",
        f"",
        f"| Rank | Workflow | Downloads | Previous | Growth | Period | CAGR |",
        f"|------|----------|-----------|----------|--------|--------|------|",
    ]

    for rank, stats in enumerate(stats_list, 1):
        period = f"{stats['days_elapsed']}d" if stats.get('days_elapsed') else "N/A"
        cagr_str = f"{stats['cagr']:+.1f}%" if stats.get('cagr') is not None else "N/A"

        lines.append(
            f"| {rank} | `{stats['slug']}` | "
            f"{format_number(stats['current_count'])} | "
            f"{format_number(stats['previous_count'])} | "
            f"{format_growth(stats['delta'], stats['growth_pct'])} | "
            f"{period} | "
            f"{cagr_str} |"
        )

    # Add second table sorted by CAGR
    stats_by_cagr = [s for s in stats_list if s.get('cagr') is not None]
    stats_by_cagr.sort(key=lambda x: x['cagr'], reverse=True)

    lines.extend([
        f"",
        f"## Workflow Details (by CAGR)",
        f"",
        f"| Rank | Workflow | CAGR | Downloads | Growth | Period |",
        f"|------|----------|------|-----------|--------|--------|",
    ])

    for rank, stats in enumerate(stats_by_cagr, 1):
        period = f"{stats['days_elapsed']}d" if stats.get('days_elapsed') else "N/A"
        cagr_str = f"{stats['cagr']:+.1f}%" if stats.get('cagr') is not None else "N/A"

        lines.append(
            f"| {rank} | `{stats['slug']}` | "
            f"{cagr_str} | "
            f"{format_number(stats['current_count'])} | "
            f"{format_growth(stats['delta'], stats['growth_pct'])} | "
            f"{period} |"
        )

    # Top performers section
    lines.extend([
        f"",
        f"## Top Performers",
        f"",
    ])

    # Filter workflows with growth data
    with_growth = [s for s in stats_list if s.get('growth_pct') is not None]

    if with_growth:
        # Top by absolute growth
        top_absolute = sorted(with_growth, key=lambda x: x['delta'], reverse=True)[:5]
        lines.extend([
            f"### By Absolute Growth (Last Period)",
            f"",
        ])
        for s in top_absolute:
            lines.append(f"- **{s['slug']}**: {format_growth(s['delta'], s['growth_pct'])} in {s['days_elapsed']} days")

        lines.append(f"")

        # Top by percentage growth (last period)
        top_percentage = sorted(with_growth, key=lambda x: x['growth_pct'], reverse=True)[:5]
        lines.extend([
            f"### By Percentage Growth (Last Period)",
            f"",
        ])
        for s in top_percentage:
            lines.append(f"- **{s['slug']}**: {format_growth(s['delta'], s['growth_pct'])} in {s['days_elapsed']} days")

        lines.append(f"")

        # Top by CAGR
        with_cagr = [s for s in stats_list if s.get('cagr') is not None]
        top_cagr = sorted(with_cagr, key=lambda x: x['cagr'], reverse=True)[:5]
        lines.extend([
            f"### By CAGR (All-Time)",
            f"",
        ])
        for s in top_cagr:
            cagr_str = f"{s['cagr']:+.1f}%"
            lines.append(f"- **{s['slug']}**: {cagr_str} CAGR ({format_number(s['earliest_count'])} → {format_number(s['current_count'])} over {s['total_days']} days)")

    lines.extend([
        f"",
        f"---",
        f"*Generated on {datetime.date.today().isoformat()}*",
    ])

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Generate download stats report")
    ap.add_argument("--date", help="Target date (YYYY-MM-DD); defaults to latest")
    args = ap.parse_args()

    if not DATA.exists():
        print(f"Error: {DATA} not found")
        return 1

    data = json.loads(DATA.read_text())

    # Determine target date
    if args.date:
        target_date = args.date
    else:
        # Find most recent date across all workflows
        all_dates = set()
        for history in data.values():
            for entry in history:
                all_dates.add(entry["date"])
        target_date = max(all_dates) if all_dates else datetime.date.today().isoformat()

    # Generate report
    report = generate_markdown_report(data, target_date)

    # Create reports directory
    REPORTS_DIR.mkdir(exist_ok=True)

    # Save report
    report_path = REPORTS_DIR / f"report-{target_date}.md"
    report_path.write_text(report)

    print(f"Report generated: {report_path}")

    # Also create/update a "latest" symlink or copy
    latest_path = REPORTS_DIR / "latest.md"
    latest_path.write_text(report)
    print(f"Latest report: {latest_path}")

    return 0


if __name__ == "__main__":
    exit(main())
