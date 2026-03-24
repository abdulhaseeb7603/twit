"""Tests for operational logging to the agent_actions table.

Validates that log_action():
- Inserts rows with correct action_type and success values
- Records error_code when provided
- Records tokens_used and cost_usd when provided
- Does not crash when the database path is invalid
"""

import sqlite3

import pytest


class TestLogAction:
    """Tests for the log_action() function in common.py."""

    def test_log_action_inserts_row(self, initialized_db, scripts_dir):
        """log_action() should insert a row into agent_actions with correct values."""
        from common import log_action

        log_action("test_action", True)

        conn = sqlite3.connect(initialized_db)
        rows = conn.execute(
            "SELECT action_type, success FROM agent_actions"
        ).fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "test_action"
        assert rows[0][1] == 1  # True stored as 1

    def test_log_action_records_error_code(self, initialized_db, scripts_dir):
        """log_action() should record error_code when provided."""
        from common import log_action

        log_action("test_fail", False, error_code="TEST_ERR")

        conn = sqlite3.connect(initialized_db)
        row = conn.execute(
            "SELECT error_code FROM agent_actions WHERE action_type = 'test_fail'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "TEST_ERR"

    def test_log_action_records_cost(self, initialized_db, scripts_dir):
        """log_action() should record tokens_used and cost_usd when provided."""
        from common import log_action

        log_action("test_cost", True, tokens_used=100, cost_usd=0.001)

        conn = sqlite3.connect(initialized_db)
        row = conn.execute(
            "SELECT tokens_used, cost_usd FROM agent_actions WHERE action_type = 'test_cost'"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == 100
        assert abs(row[1] - 0.001) < 1e-6

    def test_log_action_does_not_crash_on_db_error(self, scripts_dir, monkeypatch):
        """log_action() should not raise when MEMORY_DB points to an invalid path."""
        try:
            import common

            monkeypatch.setattr(common, "MEMORY_DB", "/nonexistent/path/db.sqlite")
            # Should not raise -- errors are logged to stderr
            common.log_action("test_broken", False)
        except ImportError:
            pytest.skip("common.py not yet available")
