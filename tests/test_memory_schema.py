"""Tests for the memory schema (scored_tweets and agent_actions tables).

Validates that:
- scored_tweets table exists with 17 columns and correct column names
- agent_actions table exists with 8 columns
- scored_tweets enforces UNIQUE constraint on tweet_id
- init_db creates the memory directory if it does not exist
"""

import os
import sqlite3
import time

import pytest


EXPECTED_SCORED_TWEETS_COLUMNS = [
    "id",
    "tweet_id",
    "text",
    "username",
    "bio",
    "follower_count",
    "verified",
    "score",
    "category",
    "reason",
    "should_reply",
    "opportunity_summary",
    "found_at",
    "query_used",
    "replied",
    "reply_text",
    "replied_at",
]


class TestScoredTweetsTable:
    """Tests for the scored_tweets table schema."""

    def test_scored_tweets_table_exists(self, initialized_db):
        """scored_tweets table should exist in the database."""
        conn = sqlite3.connect(initialized_db)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scored_tweets'"
        ).fetchall()
        conn.close()
        assert len(tables) == 1

    def test_scored_tweets_has_17_columns(self, initialized_db):
        """scored_tweets table should have exactly 17 columns."""
        conn = sqlite3.connect(initialized_db)
        columns = conn.execute("PRAGMA table_info(scored_tweets)").fetchall()
        conn.close()
        assert len(columns) == 17

    def test_scored_tweets_column_names(self, initialized_db):
        """scored_tweets table should have the exact expected column names."""
        conn = sqlite3.connect(initialized_db)
        columns = conn.execute("PRAGMA table_info(scored_tweets)").fetchall()
        conn.close()
        column_names = [col[1] for col in columns]
        assert column_names == EXPECTED_SCORED_TWEETS_COLUMNS

    def test_scored_tweets_unique_tweet_id(self, initialized_db):
        """Inserting a duplicate tweet_id should raise IntegrityError."""
        conn = sqlite3.connect(initialized_db)
        now = time.time()
        conn.execute(
            "INSERT INTO scored_tweets (tweet_id, text, username, score, category, found_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("tweet_123", "Hello world", "testuser", 80, "freelance", now),
        )
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO scored_tweets (tweet_id, text, username, score, category, found_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("tweet_123", "Duplicate", "testuser2", 50, "job", now),
            )
        conn.close()


class TestAgentActionsTable:
    """Tests for the agent_actions table schema."""

    def test_agent_actions_table_exists(self, initialized_db):
        """agent_actions table should exist in the database."""
        conn = sqlite3.connect(initialized_db)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_actions'"
        ).fetchall()
        conn.close()
        assert len(tables) == 1

    def test_agent_actions_has_8_columns(self, initialized_db):
        """agent_actions table should have exactly 8 columns."""
        conn = sqlite3.connect(initialized_db)
        columns = conn.execute("PRAGMA table_info(agent_actions)").fetchall()
        conn.close()
        assert len(columns) == 8


class TestInitDb:
    """Tests for the init_db function."""

    def test_init_db_creates_directory(self, tmp_path, scripts_dir, monkeypatch):
        """init_db should create the memory directory if it does not exist."""
        nested_dir = tmp_path / "nested" / "memory"
        db_path = str(nested_dir / "memory.db")

        try:
            import common

            monkeypatch.setattr(common, "MEMORY_DB", db_path)
            from common import init_db

            init_db()
            assert os.path.isdir(str(nested_dir))
        except (ImportError, AttributeError):
            pytest.skip("common.py or init_db not yet available")
