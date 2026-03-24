"""Shared pytest fixtures for the twitter-gig-hunter test suite.

Provides:
- scripts_dir: absolute path to bridge scripts with sys.path injection
- tmp_db: temporary SQLite database with MEMORY_DB monkeypatched
- mock_env: all 5 required environment variables set to dummy values
- initialized_db: tmp_db with schema tables already created
"""

import os
import sys
import sqlite3

import pytest


SCRIPTS_DIR = os.path.expanduser(
    "~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts"
)


@pytest.fixture
def scripts_dir():
    """Return absolute path to bridge scripts and add to sys.path."""
    abs_path = os.path.abspath(SCRIPTS_DIR)
    if abs_path not in sys.path:
        sys.path.insert(0, abs_path)
    return abs_path


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Create a temporary SQLite database and monkeypatch common.MEMORY_DB.

    Yields the path to the temporary database file.
    """
    db_path = str(tmp_path / "test_memory.db")
    # Create the database file
    conn = sqlite3.connect(db_path)
    conn.close()

    # Monkeypatch common.MEMORY_DB so all code under test uses the temp DB
    try:
        import common
        monkeypatch.setattr(common, "MEMORY_DB", db_path)
    except ImportError:
        # common.py not yet available (Wave 0 -- tests are RED)
        pass

    yield db_path


@pytest.fixture
def mock_env(monkeypatch):
    """Set all 5 required environment variables to dummy values.

    Restores original environment after test via monkeypatch auto-cleanup.
    """
    env_vars = {
        "MINIMAX_API_KEY": "test-key-minimax",
        "TWITTER_USERNAME": "test-user",
        "TWITTER_EMAIL": "test@example.com",
        "TWITTER_PASSWORD": "test-password-xxx",
        "OPENAI_API_KEY": "test-key-openai",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def initialized_db(tmp_db):
    """Create schema tables in the temporary database.

    Depends on tmp_db. Runs the init_db schema creation (scored_tweets
    and agent_actions tables) against the temp DB, then yields the path.
    """
    conn = sqlite3.connect(tmp_db)
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
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_scored_tweets_tweet_id "
        "ON scored_tweets(tweet_id)"
    )
    conn.commit()
    conn.close()
    yield tmp_db
