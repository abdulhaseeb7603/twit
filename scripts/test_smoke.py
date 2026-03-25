#!/usr/bin/env python3
"""Smoke test script for the twitter-gig-hunter Phase 1 stack.

Validates: skill recognition, config correctness, script imports,
memory schema, common module functionality, env vars, and ZeroClaw version.

Runs WITHOUT real API keys or Twitter credentials -- purely local.

Output: JSON with tests_passed, tests_failed, total, results.
"""

import importlib
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile

# ── Constants ──────────────────────────────────────────────────────
SCRIPTS_DIR = os.path.expanduser(
    "~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts"
)
CONFIG_PATH = os.path.expanduser("~/.zeroclaw/config.toml")
MEMORY_DB = os.path.expanduser("~/.zeroclaw/workspace/memory/memory.db")

BRIDGE_SCRIPTS = [
    "twitter_search",
    "twitter_post",
    "tweet_scorer",
    "reply_generator",
    "report_generator",
]

REQUIRED_ENV_VARS = [
    "MINIMAX_API_KEY",
    "TWITTER_USERNAME",
    "TWITTER_EMAIL",
    "TWITTER_PASSWORD",
    "OPENAI_API_KEY",
]


def run_test(name, func):
    """Run a single test function and return a result dict."""
    try:
        passed, message = func()
        return {"name": name, "passed": passed, "message": message}
    except Exception as e:
        return {"name": name, "passed": False, "message": f"Exception: {e}"}


# ── Test 1: Skill recognition ─────────────────────────────────────
def test_skill_recognition():
    """Run zeroclaw skills list and verify twitter-gig-hunter appears."""
    try:
        result = subprocess.run(
            ["zeroclaw", "skills", "list"],
            capture_output=True, text=True, timeout=15,
        )
        output = result.stdout + result.stderr
        if "twitter-gig-hunter" in output:
            return (True, "twitter-gig-hunter found in zeroclaw skills list")
        return (False, f"twitter-gig-hunter NOT found. Output: {output[:200]}")
    except FileNotFoundError:
        return (
            False,
            json.dumps({
                "error": True,
                "code": "ZEROCLAW_NOT_FOUND",
                "message": "ZeroClaw not installed or not in PATH",
            }),
        )
    except subprocess.TimeoutExpired:
        return (False, "zeroclaw skills list timed out after 15s")


# ── Test 2: Config validation ─────────────────────────────────────
def test_config_validation():
    """Verify config.toml contains required settings."""
    if not os.path.exists(CONFIG_PATH):
        return (False, f"config.toml not found at {CONFIG_PATH}")

    with open(CONFIG_PATH, "r") as f:
        content = f.read()

    checks = {
        "default_provider with minimax": bool(
            re.search(r"default_provider\s*=.*minimax", content, re.IGNORECASE)
        ),
        "default_model set": bool(
            re.search(r"default_model\s*=", content)
        ),
        "model_routes defined": bool(
            re.search(r"\[\[model_routes\]\]", content)
        ),
        "memory backend": bool(
            re.search(r"\[memory\]", content)
        ),
    }

    # Also try TOML parsing if available
    toml_parsed = False
    try:
        import tomli

        with open(CONFIG_PATH, "rb") as f:
            tomli.load(f)
        toml_parsed = True
    except ImportError:
        try:
            import tomllib

            with open(CONFIG_PATH, "rb") as f:
                tomllib.load(f)
            toml_parsed = True
        except ImportError:
            pass  # Regex fallback is fine
    except Exception as e:
        return (False, f"TOML parse error: {e}")

    failed = [k for k, v in checks.items() if not v]
    if failed:
        return (False, f"Config checks failed: {', '.join(failed)}")

    parse_note = " (TOML parsed)" if toml_parsed else " (regex validated)"
    return (True, f"All config checks passed{parse_note}")


# ── Test 3: Python script syntax and imports ──────────────────────
def test_script_imports():
    """Import all bridge scripts + common.py + rate_limiter.py + init_db.py."""
    if not os.path.isdir(SCRIPTS_DIR):
        return (False, f"Scripts directory not found: {SCRIPTS_DIR}")

    # Add scripts dir to path for imports
    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)

    modules_to_check = BRIDGE_SCRIPTS + ["common", "rate_limiter", "init_db"]
    results = []

    for mod_name in modules_to_check:
        mod_path = os.path.join(SCRIPTS_DIR, f"{mod_name}.py")
        if not os.path.exists(mod_path):
            results.append(f"{mod_name}: FILE MISSING")
            continue

        try:
            # Use importlib to actually import, not just syntax check
            spec = importlib.util.spec_from_file_location(
                f"smoke_{mod_name}", mod_path
            )
            mod = importlib.util.module_from_spec(spec)

            # Prevent scripts from running main() on import
            old_argv = sys.argv
            sys.argv = [mod_path]

            # Prevent sys.exit from killing our test runner
            old_exit = sys.exit
            exit_called = []
            sys.exit = lambda code=0: exit_called.append(code)

            try:
                spec.loader.exec_module(mod)
            except SystemExit:
                pass  # Some modules may call sys.exit on import
            finally:
                sys.argv = old_argv
                sys.exit = old_exit

            # Check that bridge scripts import from common
            if mod_name not in ("common",):
                with open(mod_path, "r") as f:
                    src = f.read()
                if "from common import" not in src and "import common" not in src:
                    results.append(f"{mod_name}: does not import from common")
                    continue

            results.append(f"{mod_name}: OK")
        except Exception as e:
            results.append(f"{mod_name}: IMPORT ERROR - {e}")

    failures = [r for r in results if not r.endswith(": OK")]
    if failures:
        return (False, f"Import failures: {'; '.join(failures)}")
    return (True, f"All {len(modules_to_check)} modules imported successfully")


# ── Test 4: Memory schema ─────────────────────────────────────────
def test_memory_schema():
    """Run init_db.py and verify tables exist with correct column counts."""
    # Run init_db.py via subprocess to initialize the schema
    init_script = os.path.join(SCRIPTS_DIR, "init_db.py")
    if not os.path.exists(init_script):
        return (False, "init_db.py not found")

    try:
        result = subprocess.run(
            [sys.executable, init_script],
            capture_output=True, text=True, timeout=15,
            cwd=SCRIPTS_DIR,
        )
        if result.returncode != 0:
            stderr = result.stderr[:200] if result.stderr else ""
            stdout = result.stdout[:200] if result.stdout else ""
            return (False, f"init_db.py failed: stdout={stdout} stderr={stderr}")
    except Exception as e:
        return (False, f"Failed to run init_db.py: {e}")

    # Verify tables and columns
    if not os.path.exists(MEMORY_DB):
        return (False, f"memory.db not found at {MEMORY_DB}")

    conn = sqlite3.connect(MEMORY_DB, timeout=10)
    cursor = conn.cursor()

    # Check scored_tweets
    cursor.execute("PRAGMA table_info(scored_tweets)")
    st_cols = cursor.fetchall()
    if not st_cols:
        conn.close()
        return (False, "scored_tweets table does not exist")

    # Check agent_actions
    cursor.execute("PRAGMA table_info(agent_actions)")
    aa_cols = cursor.fetchall()
    if not aa_cols:
        conn.close()
        return (False, "agent_actions table does not exist")

    # Verify tweet_id column in scored_tweets
    st_col_names = [c[1] for c in st_cols]
    if "tweet_id" not in st_col_names:
        conn.close()
        return (False, f"scored_tweets missing tweet_id. Columns: {st_col_names}")

    # Verify action_type column in agent_actions
    aa_col_names = [c[1] for c in aa_cols]
    if "action_type" not in aa_col_names:
        conn.close()
        return (False, f"agent_actions missing action_type. Columns: {aa_col_names}")

    # Verify column counts
    issues = []
    if len(st_cols) != 17:
        issues.append(f"scored_tweets has {len(st_cols)} cols (expected 17)")
    if len(aa_cols) != 8:
        issues.append(f"agent_actions has {len(aa_cols)} cols (expected 8)")

    conn.close()

    if issues:
        return (False, "; ".join(issues))
    return (
        True,
        f"scored_tweets: {len(st_cols)} cols (OK), "
        f"agent_actions: {len(aa_cols)} cols (OK)",
    )


# ── Test 5: Common module unit tests ──────────────────────────────
def test_common_module():
    """Test classify_error and output_error from common.py."""
    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)

    try:
        import importlib
        import common as common_mod

        # Reload to ensure fresh state
        importlib.reload(common_mod)
    except Exception as e:
        return (False, f"Failed to import common: {e}")

    issues = []

    # Test classify_error with httpx.HTTPStatusError (429)
    try:
        mock_response = type("MockResponse", (), {"status_code": 429})()
        mock_request = type("MockRequest", (), {"url": "http://test"})()
        exc_429 = common_mod.httpx.HTTPStatusError(
            "Rate limited", request=mock_request, response=mock_response
        )
        code, retryable = common_mod.classify_error(exc_429)
        if code != "RATE_LIMITED":
            issues.append(f"429 returned code '{code}', expected 'RATE_LIMITED'")
        if not retryable:
            issues.append("429 returned retryable=False, expected True")
    except Exception as e:
        issues.append(f"classify_error(429) raised: {e}")

    # Test classify_error with generic Exception
    try:
        code, retryable = common_mod.classify_error(Exception("something broke"))
        if code != "UNKNOWN_ERROR":
            issues.append(f"generic exc returned code '{code}', expected 'UNKNOWN_ERROR'")
        if retryable:
            issues.append("generic exc returned retryable=True, expected False")
    except Exception as e:
        issues.append(f"classify_error(generic) raised: {e}")

    # Test output_error produces valid JSON (capture stdout)
    try:
        import io

        old_stdout = sys.stdout
        old_exit = sys.exit
        captured = io.StringIO()
        sys.stdout = captured
        exit_code = []
        sys.exit = lambda c=0: exit_code.append(c)

        try:
            common_mod.output_error("TEST_CODE", "test message", retryable=True)
        except SystemExit:
            pass
        finally:
            sys.stdout = old_stdout
            sys.exit = old_exit

        output = captured.getvalue().strip()
        if output:
            parsed = json.loads(output)
            if not parsed.get("error"):
                issues.append("output_error JSON missing 'error: true'")
            if parsed.get("code") != "TEST_CODE":
                issues.append(f"output_error code is '{parsed.get('code')}' not 'TEST_CODE'")
        else:
            issues.append("output_error produced no stdout")
    except json.JSONDecodeError as e:
        issues.append(f"output_error produced invalid JSON: {e}")
    except Exception as e:
        issues.append(f"output_error test raised: {e}")

    if issues:
        return (False, "; ".join(issues))
    return (True, "classify_error and output_error work correctly")


# ── Test 6: Environment variables check ───────────────────────────
def test_env_vars():
    """Check that required environment variables are set."""
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        return (
            False,
            f"Missing env vars: {', '.join(missing)}. "
            "Set them in ~/.bashrc or ~/.profile",
        )
    return (True, f"All {len(REQUIRED_ENV_VARS)} required env vars are set")


# ── Test 7: ZeroClaw version check ───────────────────────────────
def test_zeroclaw_version():
    """Verify ZeroClaw is installed and report version."""
    try:
        result = subprocess.run(
            ["zeroclaw", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout + result.stderr
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", output)
        if not match:
            return (False, f"Could not parse version from: {output[:100]}")

        version_str = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
        return (True, f"ZeroClaw v{version_str} installed")
    except FileNotFoundError:
        return (
            False,
            json.dumps({
                "error": True,
                "code": "ZEROCLAW_NOT_FOUND",
                "message": "ZeroClaw not installed or not in PATH",
            }),
        )
    except subprocess.TimeoutExpired:
        return (False, "zeroclaw --version timed out after 10s")


# ── Main ──────────────────────────────────────────────────────────
def main():
    tests = [
        ("skill_recognition", test_skill_recognition),
        ("config_validation", test_config_validation),
        ("script_imports", test_script_imports),
        ("memory_schema", test_memory_schema),
        ("common_module", test_common_module),
        ("env_vars", test_env_vars),
        ("zeroclaw_version", test_zeroclaw_version),
    ]

    results = [run_test(name, func) for name, func in tests]

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    output = {
        "tests_passed": passed,
        "tests_failed": failed,
        "total": len(results),
        "results": results,
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
