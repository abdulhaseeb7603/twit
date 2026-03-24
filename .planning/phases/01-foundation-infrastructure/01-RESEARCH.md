# Phase 1: Foundation & Infrastructure - Research

**Researched:** 2026-03-25
**Domain:** ZeroClaw agent runtime, Python bridge layer, SQLite memory, MiniMax API, systemd deployment
**Confidence:** MEDIUM-HIGH

## Summary

Phase 1 builds the entire working skeleton: a ZeroClaw skill with SKILL.toml defining all tool registrations, Python bridge scripts that call Twikit and MiniMax APIs independently, a SQLite memory schema for scored tweets and operational logging, structured error handling with retry logic, cost tracking, and deployment as a systemd service on the user's homeserver.

The most critical finding is that ZeroClaw **clears the entire environment before shell tool execution** and only restores a whitelist of safe variables (PATH, HOME, TERM, LANG, USER, SHELL on Linux). Python scripts cannot access API keys via `os.environ` unless those variables are explicitly listed in `shell_env_passthrough` under the `[autonomy]` section of config.toml. This is a non-obvious requirement that would break every Python bridge script if missed.

Bug #851 (shell tools failing in headless/systemd mode) has been **fixed** in PR #902 (merged 2026-02-19). The fix makes command parsing quote-aware and properly bypasses approval prompts when `autonomy.level = "full"`. The user must ensure their ZeroClaw version includes this fix (commit b43e9eb or later, any v0.5.1+ build).

**Primary recommendation:** Start with `shell_env_passthrough` configuration and a minimal "hello world" shell tool to verify the secrets pipeline works end-to-end before building any real Python scripts.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- All-Python bridge approach -- every tool gets its own standalone Python script (twitter_search.py, tweet_scorer.py, reply_generator.py, twitter_post.py, rate_limiter.py)
- LLM-powered tasks (scoring, reply generation) use separate Python scripts calling MiniMax API directly, NOT ZeroClaw's built-in provider
- Scripts load secrets via ZeroClaw's encrypted secrets system (not plain environment variables)
- Error output format: structured JSON to stdout on both success and failure -- `{"error": true, "code": "TWIKIT_AUTH_FAILED", "message": "...", "retryable": true}`
- Use ZeroClaw's built-in memory system (SQLite + hybrid vector search) with OpenAI embeddings enabled from the start
- Rich metadata per scored tweet: tweet_id, text, username, bio, follower_count, verified, score, category, reason, should_reply, opportunity_summary, found_at, query_used
- Include an operational logging table (agent_actions) tracking: action_type, timestamp, success/fail, error_code, tokens_used, cost_usd
- Development and testing on user's homeserver (Ubuntu Server, 16GB DDR4, 256GB SSD) via SSH
- Homeserver is the initial production target; migrate to VPS only if uptime becomes an issue
- Code deployment via git clone + pull
- ZeroClaw installed directly on homeserver
- Structured JSON error output from all Python scripts to stdout
- Twikit failures trigger: log structured error to ops table, retry with exponential backoff (3 attempts), if still failing log an alert-level entry
- Two-tier error classification: Recoverable (rate limit 429, temporary Cloudflare block) vs Fatal (cookie expired, API key invalid)
- Day-to-day monitoring via ZeroClaw's built-in gateway dashboard (port 42617)

### Claude's Discretion
- Exact Python script internal structure and imports
- SQLite table schemas and index design
- systemd service file configuration
- ZeroClaw SKILL.toml tool argument formats
- Retry backoff timing and thresholds
- Log rotation and retention policy

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFR-01 | ZeroClaw skill defined in SKILL.toml with all tools (search, score, reply_gen, post, report_gen) | SKILL.toml format verified via DeepWiki; tool kinds, argument templating, security restrictions documented |
| INFR-02 | Python bridge scripts handle Twikit and MiniMax API calls independently of ZeroClaw's provider | MiniMax Anthropic-compatible endpoint verified; Twikit async pattern documented; shell_env_passthrough required for secrets |
| INFR-03 | ZeroClaw config includes MiniMax provider, model routing (fast/reasoning), and cost limits | Full config.toml template in architecture doc; model_routes syntax verified; cost section documented |
| INFR-04 | All actions logged with structured error handling -- failures surface clearly | Agent can store custom-category memories; operational logging table design is Claude's discretion |
| INFR-05 | Agent detects Twikit failures (Cloudflare blocks, cookie expiry) and logs/alerts instead of silently dying | Twikit error types researched; two-tier classification pattern defined in CONTEXT.md |
| INFR-06 | Cost tracking enforces $5/day and $50/month spend limits | ZeroClaw [cost] config section verified with daily_limit_usd, monthly_limit_usd, warn_at_percent |
| INFR-07 | Agent deploys to Linux VPS as systemd service via ZeroClaw | `zeroclaw service install` creates user-level systemd service; bug #851 is fixed; homeserver is initial target |
| MEMO-01 | Agent stores all scored tweets in memory (SQLite + vector) with scores, categories, and metadata | ZeroClaw memory uses MemoryEntry with id, key, content, category, timestamp, score; custom categories supported |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ZeroClaw | v0.5.1+ (latest v0.6.1) | Agent runtime, skill system, cron, memory, gateway | Architecture doc specifies v0.5.x; v0.5.1+ required for bug #851 fix |
| Twikit | 2.3.3 | Twitter search, post, reply via cookie auth | Architecture doc pins this version; async Python, no API key needed |
| httpx | 0.28.x | HTTP client for MiniMax API calls | Used in architecture doc examples; async-capable, modern Python HTTP |
| Python | 3.11+ | Bridge script runtime | Required for Twikit async support and modern syntax |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLite3 | (stdlib) | Direct memory.db queries for ops logging | Operational logging table not covered by ZeroClaw's memory API |
| argparse | (stdlib) | CLI argument parsing for bridge scripts | Every bridge script needs --query, --tweet, etc. |
| json | (stdlib) | Structured JSON I/O to stdout | All tool output is JSON per user decision |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx for MiniMax | anthropic SDK | SDK adds dependency; httpx is lighter, already in the stack, gives explicit control |
| Direct SQLite for ops | ZeroClaw memory API | Memory API handles MemoryEntry; ops logging needs a custom table with different columns |

**Installation (on homeserver):**
```bash
# ZeroClaw
curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/main/install.sh | bash

# Python dependencies
pip install twikit==2.3.3 httpx --break-system-packages
```

## Architecture Patterns

### Recommended Project Structure

```
~/.zeroclaw/
  config.toml                           # MiniMax provider, model routing, cost, security
  workspace/
    skills/
      twitter-gig-hunter/
        SKILL.toml                      # Skill manifest with all 5+ tool registrations
        scripts/
          twitter_search.py             # Twikit search wrapper
          tweet_scorer.py               # MiniMax M2.5-highspeed scoring
          reply_generator.py            # MiniMax M2.5 full reply drafting
          twitter_post.py               # Twikit post/reply wrapper
          rate_limiter.py               # Rate limit enforcement (imported by other scripts)
          report_generator.py           # Daily/weekly digest generation
          common.py                     # Shared utilities: error formatting, retry logic, DB helpers
          cookies.json                  # Twikit session cookies (auto-managed)
    memory/
      memory.db                         # ZeroClaw's SQLite (vector + FTS5 + custom tables)
```

### Pattern 1: Structured JSON Output Contract

**What:** Every Python bridge script outputs a single JSON object to stdout. No exceptions.
**When to use:** All tools, always.
**Example:**
```python
# Success output
import json, sys

def output_success(data: dict):
    print(json.dumps(data))
    sys.exit(0)

def output_error(code: str, message: str, retryable: bool = False):
    print(json.dumps({
        "error": True,
        "code": code,
        "message": message,
        "retryable": retryable
    }))
    sys.exit(1)
```
**Confidence:** HIGH -- this is locked in CONTEXT.md decisions.

### Pattern 2: Environment Variable Access via shell_env_passthrough

**What:** ZeroClaw clears environment before shell execution. Scripts access secrets ONLY through explicitly whitelisted variables.
**When to use:** Any Python script needing API keys or credentials.
**Example (config.toml):**
```toml
[autonomy]
level = "supervised"
workspace_only = true
shell_env_passthrough = [
    "MINIMAX_API_KEY",
    "TWITTER_USERNAME",
    "TWITTER_EMAIL",
    "TWITTER_PASSWORD",
    "OPENAI_API_KEY"
]
allowed_commands = [
    "python3", "pip", "git", "ls", "cat", "grep",
    "curl", "echo", "mkdir", "cp", "rm"
]
```
**Confidence:** HIGH -- verified via DeepWiki security docs that ZeroClaw calls `cmd.env_clear()` then restores only safe vars + `shell_env_passthrough` list.

### Pattern 3: Twikit Async Cookie Management

**What:** Twikit is async-only. Scripts must use asyncio.run() and handle cookie persistence.
**When to use:** twitter_search.py, twitter_post.py
**Example:**
```python
import asyncio
from twikit import Client

COOKIES_PATH = "~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/cookies.json"

async def get_client() -> Client:
    client = Client("en-US")
    import os
    cookies_path = os.path.expanduser(COOKIES_PATH)
    if os.path.exists(cookies_path):
        client.load_cookies(cookies_path)
    else:
        await client.login(
            auth_info_1=os.environ["TWITTER_USERNAME"],
            auth_info_2=os.environ["TWITTER_EMAIL"],
            password=os.environ["TWITTER_PASSWORD"]
        )
        client.save_cookies(cookies_path)
    return client
```
**Confidence:** HIGH -- verified from Twikit docs and PyPI.

### Pattern 4: MiniMax Anthropic-Compatible API Calls

**What:** MiniMax M2.5 uses an Anthropic-compatible endpoint. NOT the OpenAI-format endpoint.
**When to use:** tweet_scorer.py, reply_generator.py, report_generator.py
**Example:**
```python
import httpx, os

MINIMAX_API_URL = "https://api.minimax.io/anthropic/v1/messages"

def call_minimax(model: str, messages: list, max_tokens: int = 256, system: str = None) -> dict:
    api_key = os.environ["MINIMAX_API_KEY"]
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
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
```
**Confidence:** HIGH -- endpoint and model names verified via MiniMax official docs.

### Pattern 5: Operational Logging via Direct SQLite

**What:** ZeroClaw's memory API uses MemoryEntry (id, key, content, category, timestamp, score). For structured ops logging (tokens_used, cost_usd, error_code), use a custom SQLite table in the same memory.db file.
**When to use:** Every script should log its action to the agent_actions table.
**Example:**
```python
import sqlite3, os, time

MEMORY_DB = os.path.expanduser("~/.zeroclaw/workspace/memory/memory.db")

def log_action(action_type: str, success: bool, error_code: str = None,
               tokens_used: int = 0, cost_usd: float = 0.0, details: str = ""):
    conn = sqlite3.connect(MEMORY_DB)
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
        "INSERT INTO agent_actions (action_type, timestamp, success, error_code, tokens_used, cost_usd, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (action_type, time.time(), int(success), error_code, tokens_used, cost_usd, details)
    )
    conn.commit()
    conn.close()
```
**Confidence:** MEDIUM -- ZeroClaw's memory.db is a standard SQLite file; adding custom tables should work but needs verification that ZeroClaw doesn't purge unknown tables.

### Anti-Patterns to Avoid

- **Using os.environ directly without shell_env_passthrough:** ZeroClaw clears the env. Your script will get KeyError on every API key lookup.
- **Printing anything except JSON to stdout:** ZeroClaw parses stdout as the tool result. Debug logging must go to stderr or a log file.
- **Using shell chaining (&&, ||, ;) in SKILL.toml commands:** ZeroClaw's security audit blocks these patterns.
- **Synchronous Twikit calls:** Twikit is async-only in 2.3.x. Must use asyncio.run().
- **Using MiniMax's OpenAI endpoint (api.minimax.chat/v1):** Causes "invalid role: developer" errors. Must use the Anthropic-compatible endpoint.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Agent runtime / scheduling | Custom Python scheduler | ZeroClaw cron + skill system | Built-in persistence, restart recovery, security sandboxing |
| Memory / vector search | Custom embedding + search pipeline | ZeroClaw built-in memory (SQLite + vector + FTS5) | 70/30 hybrid search, embedding cache, LRU eviction -- already there |
| Encrypted secrets storage | Custom encryption layer | ZeroClaw secrets (ChaCha20-Poly1305) + shell_env_passthrough | Battle-tested encryption, auto-decrypt on load |
| Service management | Custom systemd unit file | `zeroclaw service install` | Generates correct user-level systemd unit with restart-on-failure |
| Cost tracking | Custom token counter | ZeroClaw [cost] config | Built-in daily/monthly limits with warn_at_percent |
| HTTP retries | Custom retry loop in every script | httpx with tenacity or manual retry wrapper | Consistent backoff logic, single implementation |

**Key insight:** ZeroClaw provides most infrastructure. The Python scripts should be thin wrappers that call APIs and format JSON output -- avoid duplicating what ZeroClaw already handles.

## Common Pitfalls

### Pitfall 1: Missing shell_env_passthrough
**What goes wrong:** Python scripts crash with KeyError trying to read API keys from environment.
**Why it happens:** ZeroClaw clears all environment variables before shell execution for security.
**How to avoid:** Add all required env vars to `[autonomy].shell_env_passthrough` in config.toml. Test with a simple `python3 -c "import os; print(os.environ.get('MINIMAX_API_KEY', 'MISSING'))"` shell tool first.
**Warning signs:** Any "KeyError" or "None" in script output for environment variables.

### Pitfall 2: Wrong MiniMax API Endpoint
**What goes wrong:** "invalid role: developer" errors or malformed responses.
**Why it happens:** MiniMax has two endpoints -- OpenAI-compatible (api.minimax.chat/v1) and Anthropic-compatible (api.minimax.io/anthropic/v1). M2.5 requires the Anthropic-compatible one.
**How to avoid:** Always use `https://api.minimax.io/anthropic/v1/messages`. Verify the endpoint returns `content[0].text` format (Anthropic), not `choices[0].message.content` (OpenAI).
**Warning signs:** HTTP 400 errors, "invalid role" messages, unexpected response structure.

### Pitfall 3: Twikit Cookie Expiry in Headless Mode
**What goes wrong:** Twikit throws authentication errors after cookies expire (3-7 days of inactivity).
**Why it happens:** Twitter session cookies have limited lifetime. No browser to refresh them.
**How to avoid:** Implement a cookie refresh mechanism (lightweight search every 3 days). Catch auth errors and attempt re-login with stored credentials. Log cookie expiry as a fatal error requiring manual intervention if re-login also fails.
**Warning signs:** Sudden "Unauthorized" or 403 responses from Twikit after days of working.

### Pitfall 4: Printing Debug Output to stdout
**What goes wrong:** ZeroClaw tries to parse debug print statements as JSON tool output.
**Why it happens:** ZeroClaw shell tools capture stdout as the tool result.
**How to avoid:** All debug/logging output goes to stderr (`print("debug", file=sys.stderr)`). Only the final JSON result goes to stdout.
**Warning signs:** Tool returns "parse error" or garbled results.

### Pitfall 5: ShellTool 60-Second Timeout
**What goes wrong:** Long-running Twikit searches or MiniMax calls get killed.
**Why it happens:** ZeroClaw enforces a 60-second timeout on shell tool execution.
**How to avoid:** Keep individual API calls under 30 seconds (httpx timeout=30). If searching 20 tweets takes too long, consider batching or reducing count. MiniMax calls with max_tokens=256 should be fast.
**Warning signs:** Tool output is empty or truncated; ZeroClaw logs show "timeout".

### Pitfall 6: SQLite Concurrent Access
**What goes wrong:** "database is locked" errors when multiple scripts try to write to memory.db simultaneously.
**Why it happens:** SQLite has limited concurrent write support. If ZeroClaw's memory system and your custom ops table both write at once, conflicts arise.
**How to avoid:** Use WAL mode (`PRAGMA journal_mode=WAL`), keep transactions short, use timeouts on connection (`sqlite3.connect(db, timeout=10)`).
**Warning signs:** Intermittent "database is locked" errors in script output.

### Pitfall 7: MiniMax Temperature Range
**What goes wrong:** API returns error for temperature values.
**Why it happens:** MiniMax Anthropic-compatible API requires temperature in range (0.0, 1.0] -- strictly greater than 0, less than or equal to 1.
**How to avoid:** Never set temperature=0. Use temperature=0.1 for deterministic scoring, temperature=0.7 for creative replies.
**Warning signs:** HTTP 400 with parameter validation error.

## Code Examples

### SKILL.toml with All Tool Registrations (Phase 1)

```toml
# Source: Architecture doc section 7, adapted for Phase 1 skeleton
[skill]
name = "twitter-gig-hunter"
description = "Autonomous Twitter agent that finds AI engineering gigs, scores opportunities, and generates lead intelligence"
version = "1.0.0"

[[prompts]]
text = """
You are an AI engineering gig hunter on Twitter/X.

WORKFLOW (run each step in order):
1. Call `twitter_search` with the next query from rotation
2. For each tweet returned, call `tweet_scorer` to classify it
3. For tweets scoring >=70, call `reply_generator` to draft a reply
4. Review each draft, then call `twitter_post` to send it
5. Call `report_generator` to create summaries when requested

HARD RULES:
- NEVER reply to the same person twice in 24 hours
- NEVER exceed 5 replies per hour
- If a tool returns {"error": true}, check the "retryable" field
- For retryable errors, wait and retry once. For non-retryable, skip and log.
"""

[[tools]]
name = "twitter_search"
description = "Search Twitter for tweets matching a query. Returns JSON array of tweet objects."
kind = "shell"
command = "python3"
args = [
    "~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/twitter_search.py",
    "--query", "{query}",
    "--count", "{count}"
]

[[tools]]
name = "tweet_scorer"
description = "Score a tweet's relevance 0-100 for AI gig opportunities. Returns JSON with relevance_score, category, reason, should_reply."
kind = "shell"
command = "python3"
args = [
    "~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/tweet_scorer.py",
    "--tweet", "{tweet_json}"
]

[[tools]]
name = "reply_generator"
description = "Generate a contextual reply to a high-scoring gig tweet. Returns JSON with reply_text."
kind = "shell"
command = "python3"
args = [
    "~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/reply_generator.py",
    "--tweet", "{tweet_json}",
    "--score-data", "{score_json}"
]

[[tools]]
name = "twitter_post"
description = "Post a reply or original tweet to Twitter. Returns JSON with post status."
kind = "shell"
command = "python3"
args = [
    "~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/twitter_post.py",
    "--action", "{action}",
    "--tweet-id", "{tweet_id}",
    "--text", "{text}"
]

[[tools]]
name = "report_generator"
description = "Generate daily or weekly lead digest from memory. Returns JSON with report content."
kind = "shell"
command = "python3"
args = [
    "~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/report_generator.py",
    "--type", "{report_type}",
    "--days", "{days}"
]
```

### Shared Error Handling Module (common.py)

```python
#!/usr/bin/env python3
"""Shared utilities for all bridge scripts."""

import json
import sys
import time
import sqlite3
import os
import functools

MEMORY_DB = os.path.expanduser("~/.zeroclaw/workspace/memory/memory.db")

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
        "retryable": retryable
    }))
    sys.exit(1)

def log_action(action_type: str, success: bool, error_code: str = None,
               tokens_used: int = 0, cost_usd: float = 0.0, details: str = ""):
    """Log an action to the agent_actions table in memory.db."""
    try:
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
            "INSERT INTO agent_actions (action_type, timestamp, success, error_code, tokens_used, cost_usd, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (action_type, time.time(), int(success), error_code, tokens_used, cost_usd, details)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: failed to log action: {e}", file=sys.stderr)

def retry_with_backoff(max_attempts: int = 3, base_delay: float = 2.0):
    """Decorator for retry with exponential backoff."""
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
                    print(f"Attempt {attempt+1} failed: {e}, retrying in {delay}s", file=sys.stderr)
                    time.sleep(delay)
        return wrapper
    return decorator
```

### Scored Tweets Memory Schema

```sql
-- Custom table for scored tweets (alongside ZeroClaw's built-in memory tables)
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
);

CREATE INDEX IF NOT EXISTS idx_scored_tweets_score ON scored_tweets(score);
CREATE INDEX IF NOT EXISTS idx_scored_tweets_category ON scored_tweets(category);
CREATE INDEX IF NOT EXISTS idx_scored_tweets_found_at ON scored_tweets(found_at);
CREATE INDEX IF NOT EXISTS idx_scored_tweets_username ON scored_tweets(username);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scored_tweets_tweet_id ON scored_tweets(tweet_id);

-- Operational logging table
CREATE TABLE IF NOT EXISTS agent_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    timestamp REAL NOT NULL,
    success INTEGER NOT NULL,
    error_code TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_actions_type ON agent_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_agent_actions_timestamp ON agent_actions(timestamp);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ZeroClaw shell tools block in headless | Fixed: quote-aware parsing, level=full honored | 2026-02-19 (PR #902) | systemd deployment now works reliably |
| MiniMax via OpenAI endpoint | Anthropic-compatible endpoint is primary | MiniMax M2.5 launch | Must use api.minimax.io/anthropic, not api.minimax.chat/v1 |
| ZeroClaw v0.5.0 | v0.6.1 is latest stable | 2026-03-24 | New features but v0.5.1+ is minimum for bug #851 fix |
| Twikit sync API | Async-only in 2.3.x | Twikit 2.0+ | All client methods require await + asyncio.run() |

**Deprecated/outdated:**
- MiniMax OpenAI-format endpoint for M2.5: Causes errors. Use Anthropic-compatible endpoint only.
- ZeroClaw pre-v0.5.1: Bug #851 breaks shell tools in systemd/headless mode.

## Open Questions

1. **Custom SQLite tables in memory.db**
   - What we know: ZeroClaw uses memory.db with specific tables (chunks, chunks_vec, embedding_cache, state_snapshots, etc.)
   - What's unclear: Whether ZeroClaw will drop/ignore custom tables on upgrade or memory reset
   - Recommendation: Test by creating a custom table and running `zeroclaw doctor` or memory operations. If problematic, use a separate SQLite file for ops data.

2. **ZeroClaw version on homeserver**
   - What we know: Latest is v0.6.1; minimum needed is v0.5.1+ for bug #851 fix
   - What's unclear: What version is currently installed (if any)
   - Recommendation: First task should verify ZeroClaw version; upgrade if needed.

3. **Twikit enable_ui_metrics for anti-detection**
   - What we know: Twikit Client accepts `enable_ui_metrics=True` parameter that sends obfuscated metrics, potentially reducing suspension risk
   - What's unclear: Whether this actually helps in 2026; whether it causes other issues
   - Recommendation: Enable it by default -- low risk, potential benefit.

4. **MiniMax M2.7 availability**
   - What we know: MiniMax has released M2.7 and M2.7-highspeed models on the Anthropic-compatible endpoint
   - What's unclear: Whether user's token plan covers M2.7; pricing difference
   - Recommendation: Stick with M2.5 as specified in architecture doc. M2.7 is a future upgrade path.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python bridge scripts) + manual ZeroClaw integration tests |
| Config file | None -- Wave 0 must create pytest.ini or pyproject.toml |
| Quick run command | `pytest tests/ -x --timeout=30` |
| Full suite command | `pytest tests/ -v --timeout=60` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFR-01 | SKILL.toml loads in ZeroClaw | integration | `zeroclaw skills list \| grep twitter-gig-hunter` | No -- Wave 0 |
| INFR-02 | Python scripts return valid JSON on success/error | unit | `pytest tests/test_bridge_output.py -x` | No -- Wave 0 |
| INFR-03 | Config routes to MiniMax with cost limits | integration | `zeroclaw doctor` + manual config review | No -- manual |
| INFR-04 | Actions logged to agent_actions table | unit | `pytest tests/test_ops_logging.py -x` | No -- Wave 0 |
| INFR-05 | Twikit errors produce structured JSON, not crashes | unit | `pytest tests/test_error_handling.py -x` | No -- Wave 0 |
| INFR-06 | Cost config present with correct limits | unit | `python3 -c "import toml; c=toml.load(...);"` or manual | No -- Wave 0 |
| INFR-07 | systemd service runs and stays up | integration | `systemctl --user status zeroclaw` | No -- manual |
| MEMO-01 | Scored tweets persist in SQLite with all metadata fields | unit | `pytest tests/test_memory_schema.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x --timeout=30`
- **Per wave merge:** `pytest tests/ -v --timeout=60` + `zeroclaw skills list`
- **Phase gate:** Full suite green + `zeroclaw doctor` passes + systemd service running

### Wave 0 Gaps
- [ ] `tests/conftest.py` -- shared fixtures (temp SQLite DB, mock env vars)
- [ ] `tests/test_bridge_output.py` -- validates JSON output contract for all scripts
- [ ] `tests/test_error_handling.py` -- validates error JSON format and Twikit error classification
- [ ] `tests/test_ops_logging.py` -- validates agent_actions table writes
- [ ] `tests/test_memory_schema.py` -- validates scored_tweets table schema and queries
- [ ] `pyproject.toml` or `pytest.ini` -- test configuration
- [ ] Framework install: `pip install pytest pytest-timeout`

## Sources

### Primary (HIGH confidence)
- [DeepWiki: ZeroClaw Tools and Skills System](https://deepwiki.com/zeroclaw-labs/zeroclaw/11-tools-and-skills-system) -- shell tool execution, security policy, timeout/output limits
- [DeepWiki: Creating and Installing Skills](https://deepwiki.com/zeroclaw-labs/zeroclaw/11.6-creating-and-installing-skills) -- SKILL.toml format, field reference, tool kinds
- [DeepWiki: Security and Autonomy Configuration](https://deepwiki.com/zeroclaw-labs/zeroclaw/3.6-security-and-autonomy-configuration) -- shell_env_passthrough, environment sanitization
- [MiniMax Anthropic-Compatible API](https://platform.minimax.io/docs/api-reference/text-anthropic-api) -- endpoint URL, supported models, parameter constraints
- [GitHub Issue #851](https://github.com/zeroclaw-labs/zeroclaw/issues/851) -- shell tools in headless mode bug, confirmed FIXED in PR #902
- [Twikit PyPI](https://pypi.org/project/twikit/) -- version 2.3.3, async API, cookie management
- [Twikit Documentation](https://twikit.readthedocs.io/en/latest/twikit.html) -- Client API, login/cookie methods

### Secondary (MEDIUM confidence)
- [ZeroClaw GitHub Wiki: Configuration](https://github.com/zeroclaw-labs/zeroclaw/wiki/04-Configuration) -- secrets encryption, three-tier config priority
- [ZeroClaw GitHub Releases](https://github.com/zeroclaw-labs/zeroclaw/releases) -- version history, v0.6.1 latest
- Architecture doc `TWITTER_GIG_AGENT_ARCHITECTURE_V2.md` -- full config.toml template, Python script examples, deployment steps

### Tertiary (LOW confidence)
- Custom SQLite tables in ZeroClaw's memory.db -- no official documentation on compatibility; needs hands-on testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified via official sources, versions confirmed
- Architecture: HIGH -- SKILL.toml format, shell tool behavior, and config.toml structure verified via DeepWiki and official wiki
- Secrets/env handling: HIGH -- shell_env_passthrough mechanism verified, critical pitfall documented
- MiniMax API: HIGH -- endpoint, model names, parameter constraints verified via official docs
- Twikit patterns: HIGH -- async API, cookie management verified via PyPI and readthedocs
- Custom SQLite tables: LOW -- needs validation that ZeroClaw won't purge them
- systemd deployment: MEDIUM -- `zeroclaw service install` documented, bug #851 fixed, but exact unit file contents not verified

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (30 days -- stable domain, ZeroClaw releasing frequently)
