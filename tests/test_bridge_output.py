"""Tests for the JSON output contract of all bridge scripts.

Validates that:
- output_success() returns valid JSON to stdout
- output_error() returns error JSON with required keys and exits with code 1
- All 5 bridge scripts are importable without errors
"""

import importlib
import json
import sys
import os

import pytest


class TestOutputSuccess:
    """Tests for the output_success() function in common.py."""

    def test_output_success_returns_valid_json(self, scripts_dir, capsys):
        """output_success() should print valid JSON to stdout."""
        from common import output_success

        test_data = {"status": "ok", "count": 5}
        with pytest.raises(SystemExit) as exc_info:
            output_success(test_data)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == test_data


class TestOutputError:
    """Tests for the output_error() function in common.py."""

    def test_output_error_returns_error_json(self, scripts_dir, capsys):
        """output_error() should print JSON with error, code, message, retryable keys."""
        from common import output_error

        with pytest.raises(SystemExit):
            output_error("TEST_ERROR", "Something went wrong", retryable=True)

        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["error"] is True
        assert parsed["code"] == "TEST_ERROR"
        assert parsed["message"] == "Something went wrong"
        assert parsed["retryable"] is True

    def test_output_error_exits_with_code_1(self, scripts_dir):
        """output_error() should call sys.exit(1)."""
        from common import output_error

        with pytest.raises(SystemExit) as exc_info:
            output_error("TEST_ERROR", "fail")

        assert exc_info.value.code == 1


class TestBridgeScriptsImportable:
    """Tests that all 5 bridge scripts can be imported without errors."""

    BRIDGE_SCRIPTS = [
        "twitter_search",
        "tweet_scorer",
        "reply_generator",
        "twitter_post",
        "report_generator",
    ]

    def test_all_bridge_scripts_importable(self, scripts_dir):
        """Each bridge script should be importable via importlib."""
        errors = []
        for script_name in self.BRIDGE_SCRIPTS:
            try:
                importlib.import_module(script_name)
            except ImportError as e:
                errors.append(f"{script_name}: {e}")

        assert not errors, f"Failed to import bridge scripts:\n" + "\n".join(errors)
