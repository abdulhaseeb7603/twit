#!/usr/bin/env python3
"""Rate limit enforcement for Twitter posting.

Enforces a hard cap of 5 successful replies per hour by querying the
agent_actions table in memory.db.
"""

import argparse
import sqlite3
import sys
import time

from common import MEMORY_DB, output_success, output_error


# ── Constants ────────────────────────────────────────────────────────
MAX_POSTS_PER_HOUR = 5
WINDOW_SECONDS = 3600  # 1 hour


def check_rate_limit() -> dict:
    """Check whether posting is allowed under the 5/hour rate limit.

    Returns:
        dict with keys: allowed (bool), remaining (int), reset_in_seconds (int).
    """
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    try:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        rows = conn.execute(
            "SELECT timestamp FROM agent_actions "
            "WHERE action_type = 'twitter_post' "
            "AND success = 1 "
            "AND timestamp > ? "
            "ORDER BY timestamp ASC",
            (cutoff,),
        ).fetchall()
        conn.close()
    except Exception:
        # If the table doesn't exist yet, no posts have been made
        rows = []

    count = len(rows)
    remaining = max(0, MAX_POSTS_PER_HOUR - count)
    allowed = remaining > 0

    # Calculate when the oldest post in the window expires
    if rows and not allowed:
        oldest_ts = rows[0][0]
        reset_in = int((oldest_ts + WINDOW_SECONDS) - now)
        reset_in = max(0, reset_in)
    else:
        reset_in = 0

    return {
        "allowed": allowed,
        "remaining": remaining,
        "reset_in_seconds": reset_in,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Check Twitter posting rate limit (5/hour)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Output rate limit status as JSON.",
    )
    args = parser.parse_args()

    if args.check:
        result = check_rate_limit()
        output_success(result)
    else:
        print("Usage: rate_limiter.py --check", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
