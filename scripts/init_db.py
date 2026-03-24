#!/usr/bin/env python3
"""Database schema initialization for the twitter-gig-hunter skill.

Creates the scored_tweets and agent_actions tables (with indexes) in
ZeroClaw's memory.db. Safe to run multiple times -- all statements use
CREATE ... IF NOT EXISTS.
"""

import os
import sqlite3
import sys

from common import MEMORY_DB, output_success, output_error


def init_schema():
    """Create all tables and indexes in memory.db."""
    # Ensure the memory directory exists
    os.makedirs(os.path.dirname(MEMORY_DB), exist_ok=True)

    conn = sqlite3.connect(MEMORY_DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")

    # ── scored_tweets table ──────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scored_tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT UNIQUE NOT NULL,
            text TEXT NOT NULL,
            username TEXT NOT NULL,
            bio TEXT,
            follower_count INTEGER DEFAULT 0,
            verified INTEGER DEFAULT 0,
            score INTEGER NOT NULL,
            category TEXT NOT NULL,
            reason TEXT,
            should_reply INTEGER DEFAULT 0,
            opportunity_summary TEXT,
            found_at REAL NOT NULL,
            query_used TEXT,
            replied INTEGER DEFAULT 0,
            reply_text TEXT,
            replied_at REAL
        )
    """)

    # ── scored_tweets indexes ────────────────────────────────────────
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scored_tweets_score "
        "ON scored_tweets(score)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scored_tweets_category "
        "ON scored_tweets(category)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scored_tweets_found_at "
        "ON scored_tweets(found_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scored_tweets_username "
        "ON scored_tweets(username)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_scored_tweets_tweet_id "
        "ON scored_tweets(tweet_id)"
    )

    # ── agent_actions table ──────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            timestamp REAL NOT NULL,
            success INTEGER NOT NULL,
            error_code TEXT,
            tokens_used INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            details TEXT
        )
    """)

    # ── agent_actions indexes ────────────────────────────────────────
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_actions_type "
        "ON agent_actions(action_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_actions_timestamp "
        "ON agent_actions(timestamp)"
    )

    conn.commit()
    conn.close()


def main():
    try:
        init_schema()
        output_success({
            "success": True,
            "tables": ["scored_tweets", "agent_actions"],
        })
    except Exception as e:
        output_error("DB_INIT_FAILED", str(e))


if __name__ == "__main__":
    main()
