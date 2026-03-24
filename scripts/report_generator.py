#!/usr/bin/env python3
"""Lead digest generation -- daily/weekly reports from scored_tweets.

Usage:
    python3 report_generator.py --type daily
    python3 report_generator.py --type weekly --days 7

Output (stdout): {"report_type": "...", "period_days": N, "total_leads": N, "report_text": "..."}
Errors (stdout): {"error": true, "code": "...", "message": "...", "retryable": ...}
Debug/warnings go to stderr only.
"""

import argparse
import json
import sqlite3
import sys
import time
from collections import defaultdict

from common import (
    MEMORY_DB,
    classify_error,
    log_action,
    output_error,
    output_success,
)


def fetch_leads(days: int, min_score: int = 70) -> list:
    """Fetch scored tweets from the last N days with score >= min_score."""
    cutoff = time.time() - (days * 86400)

    try:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT tweet_id, text, username, bio, follower_count, verified,
                      score, category, reason, should_reply, opportunity_summary,
                      found_at, query_used, replied, reply_text, replied_at
               FROM scored_tweets
               WHERE found_at > ? AND score >= ?
               ORDER BY score DESC""",
            (cutoff, min_score),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Warning: failed to fetch leads: {e}", file=sys.stderr)
        return []


def generate_daily_report(leads: list, days: int) -> str:
    """Generate a daily text report grouped by category."""
    if not leads:
        return f"No leads found (score >= 70) in the last {days} day(s)."

    # Group by category
    by_category = defaultdict(list)
    for lead in leads:
        by_category[lead["category"]].append(lead)

    lines = [
        f"=== Daily Lead Digest ({days} day{'s' if days != 1 else ''}) ===",
        f"Total leads: {len(leads)}",
        "",
    ]

    for category, cat_leads in sorted(
        by_category.items(), key=lambda x: -len(x[1])
    ):
        lines.append(f"--- {category.replace('_', ' ').title()} ({len(cat_leads)}) ---")
        for lead in sorted(cat_leads, key=lambda x: -x["score"]):
            tweet_url = f"https://twitter.com/{lead['username']}/status/{lead['tweet_id']}"
            replied_mark = " [REPLIED]" if lead.get("replied") else ""
            lines.append(
                f"  Score: {lead['score']} | @{lead['username']}{replied_mark}"
            )
            lines.append(f"  Summary: {lead.get('opportunity_summary', 'N/A')}")
            lines.append(f"  Link: {tweet_url}")
            lines.append("")

    return "\n".join(lines)


def generate_weekly_report(leads: list, days: int) -> str:
    """Generate a weekly report with aggregate stats and top leads."""
    daily_text = generate_daily_report(leads, days)

    if not leads:
        return daily_text

    # Aggregate stats
    by_category = defaultdict(list)
    for lead in leads:
        by_category[lead["category"]].append(lead)

    total = len(leads)
    avg_score = sum(l["score"] for l in leads) / total if total else 0
    replied_count = sum(1 for l in leads if l.get("replied"))

    stats_lines = [
        "",
        "=== Weekly Aggregate Stats ===",
        f"Total leads found: {total}",
        f"Average score: {avg_score:.1f}",
        f"Replies sent: {replied_count}",
        "",
        "By category:",
    ]
    for category, cat_leads in sorted(
        by_category.items(), key=lambda x: -len(x[1])
    ):
        stats_lines.append(
            f"  {category.replace('_', ' ').title()}: {len(cat_leads)}"
        )

    # Top 5 leads
    top_5 = sorted(leads, key=lambda x: -x["score"])[:5]
    stats_lines.append("")
    stats_lines.append("Top 5 leads:")
    for i, lead in enumerate(top_5, 1):
        tweet_url = f"https://twitter.com/{lead['username']}/status/{lead['tweet_id']}"
        stats_lines.append(
            f"  {i}. Score {lead['score']} | @{lead['username']} | {lead.get('opportunity_summary', 'N/A')}"
        )
        stats_lines.append(f"     {tweet_url}")

    return daily_text + "\n" + "\n".join(stats_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate daily or weekly lead digest."
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["daily", "weekly"],
        help="Report type: 'daily' or 'weekly'.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Number of days to include (default: 1 for daily, 7 for weekly).",
    )
    args = parser.parse_args()

    # Default days based on report type
    if args.days is None:
        days = 1 if args.type == "daily" else 7
    else:
        days = args.days

    try:
        leads = fetch_leads(days)

        if args.type == "daily":
            report_text = generate_daily_report(leads, days)
        else:
            report_text = generate_weekly_report(leads, days)

        result = {
            "report_type": args.type,
            "period_days": days,
            "total_leads": len(leads),
            "report_text": report_text,
        }

        log_action(
            action_type="report_generator",
            success=True,
            details=f"type={args.type} days={days} leads={len(leads)}",
        )
        output_success(result)

    except Exception as e:
        code, retryable = classify_error(e)
        log_action(
            action_type="report_generator",
            success=False,
            error_code=code,
            details=f"type={args.type} error={str(e)[:200]}",
        )
        output_error(code, str(e)[:500], retryable=retryable)


if __name__ == "__main__":
    main()
