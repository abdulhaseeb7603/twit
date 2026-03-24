#!/usr/bin/env python3
"""Shared utilities for all bridge scripts.

Provides:
- Path constants (MEMORY_DB, COOKIES_PATH, MINIMAX_API_URL, SCRIPTS_DIR)
- JSON output helpers (output_success, output_error)
- Operational logging (log_action)
- Retry decorator (retry_with_backoff)
- MiniMax API client (call_minimax)
- Error classification (classify_error)
"""

import json
import sys
import time
import sqlite3
import os
import functools

import httpx

# ── Path constants ──────────────────────────────────────────────────
MEMORY_DB = os.path.expanduser("~/.zeroclaw/workspace/memory/memory.db")
COOKIES_PATH = os.path.expanduser(
    "~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/cookies.json"
)
MINIMAX_API_URL = "https://api.minimax.io/anthropic/v1/messages"
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


# ── JSON output helpers ─────────────────────────────────────────────
def output_success(data: dict):
    """Print success JSON to stdout and exit 0."""
    print(json.dumps(data))
    sys.exit(0)


def output_error(code: str, message: str, retryable: bool = False):
    """Print error JSON to stdout and exit 1."""
    print(json.dumps({
        "error": True,
        "code": code,
        "message": message,
        "retryable": retryable,
    }))
    sys.exit(1)


# ── Operational logging ─────────────────────────────────────────────
def log_action(action_type: str, success: bool, error_code: str = None,
               tokens_used: int = 0, cost_usd: float = 0.0, details: str = ""):
    """Log an action to the agent_actions table in memory.db.

    Never raises -- failures are logged to stderr so the calling script
    can still return its JSON result.
    """
    try:
        os.makedirs(os.path.dirname(MEMORY_DB), exist_ok=True)
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
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
            "INSERT INTO agent_actions "
            "(action_type, timestamp, success, error_code, tokens_used, cost_usd, details) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (action_type, time.time(), int(success), error_code,
             tokens_used, cost_usd, details),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: failed to log action: {e}", file=sys.stderr)


# ── Retry decorator ─────────────────────────────────────────────────
def retry_with_backoff(max_attempts: int = 3, base_delay: float = 2.0):
    """Decorator for retry with exponential backoff.

    Logs each retry attempt to stderr. Raises after final failure.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    print(
                        f"Attempt {attempt + 1} failed: {e}, "
                        f"retrying in {delay}s",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
        return wrapper
    return decorator


# ── MiniMax API client ──────────────────────────────────────────────
def call_minimax(model: str, messages: list, max_tokens: int = 256,
                 system: str = None, temperature: float = 0.7) -> dict:
    """Send a request to MiniMax's Anthropic-compatible endpoint.

    Args:
        model: MiniMax model name (e.g. "MiniMax-M2.5", "MiniMax-M2.5-highspeed")
        messages: List of message dicts with "role" and "content" keys.
        max_tokens: Maximum tokens to generate.
        system: Optional system prompt.
        temperature: Sampling temperature. MUST be > 0 (MiniMax rejects 0.0).

    Returns:
        Parsed JSON response dict from MiniMax.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses.
    """
    api_key = os.environ["MINIMAX_API_KEY"]

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }
    if system:
        body["system"] = system

    response = httpx.post(
        MINIMAX_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ── Error classification ────────────────────────────────────────────
def classify_error(exception) -> tuple:
    """Classify an exception into (error_code, retryable) tuple.

    Returns:
        (str, bool): Error code string and whether the error is retryable.
    """
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        if status == 429:
            return ("RATE_LIMITED", True)
        if status in (502, 503):
            return ("SERVICE_UNAVAILABLE", True)
        return ("HTTP_ERROR", False)

    if isinstance(exception, httpx.TimeoutException):
        return ("TIMEOUT", True)

    # Twikit errors come as generic exceptions -- inspect the message
    msg = str(exception).lower()
    if "cloudflare" in msg:
        return ("CLOUDFLARE_BLOCK", True)
    if "cookie" in msg or "auth" in msg:
        return ("TWIKIT_AUTH_FAILED", False)

    return ("UNKNOWN_ERROR", False)
