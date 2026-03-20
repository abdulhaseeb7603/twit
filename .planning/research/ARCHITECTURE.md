# Architecture Research

**Domain:** Autonomous Twitter AI Agent (Gig Hunting)
**Researched:** 2026-03-20
**Confidence:** MEDIUM-HIGH

## Standard Architecture

### How Autonomous Twitter Agent Systems Are Typically Structured

Autonomous Twitter agents in the wild follow a consistent pattern regardless of framework (Eliza, dot-automation, custom LangChain setups, ZeroClaw skills). The core structure is:

1. **Scheduler** triggers a pipeline on a fixed interval (cron, GitHub Actions, cloud scheduler)
2. **Ingestion** pulls tweets via API or scraping library
3. **Classification/Scoring** runs each tweet through an LLM with structured output
4. **Generation** drafts responses for qualified tweets using a separate (often higher-quality) LLM call
5. **Action** posts replies with rate limiting and cooldowns
6. **Memory** persists state for deduplication, cooldowns, and context

This project follows this exact pattern. The distinguishing factor is the runtime: ZeroClaw manages the agent loop, memory, scheduling, and security -- the custom code is limited to Python bridge scripts invoked as shell tools.

### System Overview

```
                        EXTERNAL SERVICES
    +-----------+     +---------------+     +------------+
    | Twitter/X |     | MiniMax API   |     | OpenRouter |
    | (cookies) |     | (Anthropic-   |     | (fallback) |
    |           |     |  compatible)  |     |            |
    +-----+-----+     +-------+-------+     +------+-----+
          |                   |                     |
          |   PYTHON BRIDGE   |                     |
    ======|===================|=====================|========
          |                   |                     |
    +-----v-------------------v---------------------v-----+
    |              Python Bridge Layer                     |
    |  (4 scripts invoked as shell tools by ZeroClaw)     |
    |                                                     |
    |  twitter_search.py  -- Twikit async client          |
    |  tweet_scorer.py    -- httpx -> MiniMax M2.5-fast   |
    |  reply_generator.py -- httpx -> MiniMax M2.5-full   |
    |  twitter_post.py    -- Twikit async client          |
    |  rate_limiter.py    -- SQLite-backed state          |
    +---------------------+-------------------------------+
                          |
                    stdin/stdout JSON
                          |
    ======================|==================================
                          |
    +---------------------v-------------------------------+
    |              ZeroClaw Daemon (Rust)                  |
    |                                                     |
    |  +----------+  +---------+  +--------------------+  |
    |  | Cron     |  | Gateway |  | Provider Subsystem |  |
    |  | Scheduler|  | :42617  |  | (MiniMax primary,  |  |
    |  | (SQLite) |  | (HTTP)  |  |  OpenRouter fallbk)|  |
    |  +----+-----+  +---------+  +--------------------+  |
    |       |                                             |
    |  +----v-----------------------------------------+   |
    |  |           Agent Loop                         |   |
    |  |  Identity (AIEOS persona + constraints)      |   |
    |  |  Memory   (SQLite + vector + FTS5)           |   |
    |  |  Skills   (twitter-gig-hunter SKILL.toml)    |   |
    |  |  Tools    (shell tool dispatcher)            |   |
    |  |  Security (autonomy level, allowlists)       |   |
    |  |  Cost     (daily/monthly spend tracking)     |   |
    |  +----------------------------------------------+   |
    +-----------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Boundary | Communicates With |
|-----------|---------------|----------|-------------------|
| **ZeroClaw Daemon** | Agent loop, LLM reasoning, memory, scheduling, security, cost tracking | Rust binary, single process | Python scripts (shell exec), MiniMax API (provider), Gateway (HTTP) |
| **Agent Loop** | Decides what to do next based on skill prompt + memory + tool results | Internal to ZeroClaw | All internal subsystems |
| **Cron Scheduler** | Triggers scan pipeline every 20min, daily showcase, weekly report, cookie refresh | SQLite-persisted timers | Agent Loop (triggers tasks) |
| **Provider Subsystem** | Routes LLM calls to MiniMax or OpenRouter fallback with model routing (fast/reasoning) | Config-driven (TOML) | External LLM APIs |
| **Memory** | Deduplication, interaction history, cooldown tracking, weekly reports | SQLite + vector (70% cosine) + FTS5 (30% BM25) | Agent Loop (read/write) |
| **Security Policy** | Command allowlisting, path restrictions, autonomy level enforcement, credential scrubbing | Config-driven | Tool dispatcher (gates execution) |
| **SKILL.toml** | Skill manifest defining persona prompt, tool registrations, workflow instructions | Static file, loaded at startup | Agent Loop (system prompt injection) |
| **twitter_search.py** | Searches Twitter via Twikit async client, returns JSON tweet list | Python process, stdin/stdout | Twitter/X (cookies), ZeroClaw (shell tool) |
| **tweet_scorer.py** | Scores tweet relevance 0-100 via MiniMax M2.5-highspeed | Python process, stdin/stdout | MiniMax API (direct httpx), ZeroClaw (shell tool) |
| **reply_generator.py** | Drafts contextual replies via MiniMax M2.5 full model | Python process, stdin/stdout | MiniMax API (direct httpx), ZeroClaw (shell tool) |
| **twitter_post.py** | Posts replies/tweets via Twikit async client | Python process, stdin/stdout | Twitter/X (cookies), ZeroClaw (shell tool) |
| **rate_limiter.py** | Enforces 5/hour reply limit, 24h per-user cooldown | SQLite state file | Called by twitter_post.py before posting |
| **Gateway** | HTTP dashboard for monitoring, supervised mode approvals | Port 42617 | Browser/user, Agent Loop |

## Recommended Project Structure

```
twitagent/                              # Project root (development)
+-- SKILL.toml                          # Skill manifest
+-- scripts/
|   +-- twitter_search.py              # Twikit search wrapper
|   +-- twitter_post.py                # Twikit post/reply wrapper
|   +-- tweet_scorer.py                # MiniMax scoring (M2.5-highspeed)
|   +-- reply_generator.py            # MiniMax drafting (M2.5-full)
|   +-- rate_limiter.py               # Rate limit enforcement module
|   +-- twikit_client.py              # Shared Twikit session manager
|   +-- config.py                      # Shared config loader (env vars)
+-- tests/
|   +-- test_scorer.py                 # Unit tests with mock LLM responses
|   +-- test_rate_limiter.py           # Rate limit state tests
|   +-- test_search_parsing.py         # Tweet JSON parsing tests
|   +-- fixtures/
|       +-- sample_tweets.json         # Test fixture data
+-- config/
|   +-- zeroclaw_config.toml           # Reference ZeroClaw config
|   +-- queries.json                   # Search query rotation list
+-- deploy/
|   +-- install.sh                     # VPS deployment script
|   +-- systemd/
|       +-- zeroclaw.service           # systemd unit file
+-- requirements.txt                    # Python deps: twikit, httpx
+-- .env.example                        # Template for required env vars

# Deployed to VPS as:
~/.zeroclaw/workspace/skills/twitter-gig-hunter/
+-- SKILL.toml
+-- scripts/
    +-- (all Python scripts)
```

### Key Structural Decisions

**Shared Twikit client module (`twikit_client.py`).** Both `twitter_search.py` and `twitter_post.py` need a Twikit client with cookie management. Extract this into a shared module to avoid duplicating login/cookie logic. Each script invocation is a separate process, so the client must load cookies from disk each time -- this shared module handles that.

**Rate limiter as importable module, not separate script.** The rate limiter needs to be checked *before* posting, so `twitter_post.py` should import and call it directly rather than being a separate shell tool. This avoids a race condition where the agent calls rate_limiter and twitter_post as separate steps.

**Query rotation in config file, not hardcoded in SKILL.toml.** Moving queries to `queries.json` allows tuning rotation without re-deploying the skill manifest.

## Architectural Patterns

### Pattern 1: Process-Per-Invocation Bridge

**What:** Each tool call spawns a new Python process. No long-running Python daemon.

**Why this matters:** ZeroClaw's shell tool system invokes `python3 script.py --args` as a subprocess. The script runs, prints JSON to stdout, and exits. ZeroClaw captures stdout as the tool result. This means:
- No persistent Python state between calls (stateless by design)
- Cookie/session state must be persisted to disk (cookies.json)
- Rate limit state must be persisted to disk (SQLite file)
- Each invocation pays Python startup cost (~200-400ms)

**Implication:** Keep scripts lean. Heavy imports (like Twikit's full client init) add latency per call. Consider lazy imports and minimal dependencies per script.

```python
# Good: Load only what's needed
import json, sys, os
# Defer heavy imports
async def main():
    from twikit import Client  # Only imported when actually running
    ...
```

### Pattern 2: Dual-Channel LLM Usage

**What:** ZeroClaw's agent reasoning uses MiniMax via the provider subsystem. The Python bridge scripts *also* call MiniMax directly via httpx.

**Why:** The agent's "brain" (ZeroClaw provider) handles high-level decision-making -- deciding which tools to call, interpreting results, managing workflow. The scoring/generation scripts call MiniMax independently for specialized tasks with custom prompts optimized for structured output.

**Implication:** Two separate consumers of the same MiniMax API key. Both count against the same token plan and rate limits. The cost tracking in ZeroClaw only sees the provider-side usage; the Python bridge usage is invisible to ZeroClaw's cost limiter.

**Mitigation:** Add manual token counting in Python scripts and log it. Or route Python bridge calls through ZeroClaw's provider (less flexible but unified cost tracking).

### Pattern 3: Memory as Shared State

**What:** ZeroClaw's built-in memory (SQLite + vector) is the single source of truth for:
- Tweet deduplication (have we seen this tweet before?)
- User cooldowns (have we replied to this person in 24h?)
- Interaction history (what did we reply with?)
- Weekly reporting data

**Why:** The agent loop reads/writes memory natively. Python bridge scripts do NOT have direct access to ZeroClaw's memory -- they communicate results back to the agent via stdout, and the agent decides what to remember.

**Implication:** The Python scripts should return rich JSON so the agent has enough context to make good memory storage decisions. The agent prompt must explicitly instruct memory saves.

### Pattern 4: Supervised-to-Autonomous Graduation

**What:** Start with `autonomy.level = "supervised"` (human approves every action via Gateway), graduate to `"full"` after 2 weeks of confidence-building.

**Why:** Using a personal Twitter account. A bad reply or rate-limit violation could mean account suspension.

**Build order implication:** The Gateway dashboard and supervised approval flow must work before the cron scheduler is enabled. Never automate before you can monitor.

## Data Flow

### Main Pipeline (every 20 minutes)

```
1. CRON TRIGGER
   ZeroClaw cron fires -> Agent Loop activates
   Agent reads skill prompt, checks memory for last query index

2. SEARCH
   Agent calls: twitter_search --query "hiring AI engineer" --count 20
   Python: Twikit.search_tweet(query) -> JSON array of tweets
   Agent: Receives tweet list, checks memory for duplicates

3. SCORE (for each new tweet)
   Agent calls: tweet_scorer --tweet '{"text":"...", "username":"..."}'
   Python: httpx POST to MiniMax M2.5-highspeed -> JSON score
   Agent: Receives score, filters >= 70, saves all leads to memory

4. DRAFT (for high-scoring tweets only, typically 2-5)
   Agent calls: reply_generator --tweet '...' --score-data '...'
   Python: httpx POST to MiniMax M2.5 full -> reply text
   Agent: Receives draft, reviews against persona constraints

5. POST (if approved -- or if in full autonomy mode)
   Agent calls: twitter_post --action reply --tweet-id 123 --text "..."
   Python: rate_limiter.check() -> Twikit.create_tweet(reply_to=id)
   Agent: Receives confirmation, saves interaction to memory

6. MEMORY UPDATE
   Agent saves: tweets found, scores, replies sent, outcomes
   Used for: dedup next run, cooldowns, weekly report
```

### Data Contracts Between Components

**twitter_search.py stdout:**
```json
{
  "tweets": [
    {
      "id": "1234567890",
      "text": "Looking for an AI engineer...",
      "username": "hiring_manager",
      "bio": "CTO at startup",
      "likes": 42,
      "replies": 7,
      "created_at": "2026-03-20T14:30:00Z"
    }
  ],
  "query_used": "hiring AI engineer",
  "count": 15
}
```

**tweet_scorer.py stdout:**
```json
{
  "relevance_score": 85,
  "category": "freelance_gig",
  "reason": "Direct request for AI/ML freelancer with specific project scope",
  "should_reply": true
}
```

**reply_generator.py stdout:**
```json
{
  "reply_text": "Built RAG pipelines for 3 production apps last year. Happy to share approach if you want to DM details.",
  "char_count": 98,
  "model_used": "MiniMax-M2.5"
}
```

**twitter_post.py stdout:**
```json
{
  "success": true,
  "tweet_id": "9876543210",
  "action": "reply",
  "replied_to": "1234567890",
  "rate_limit_remaining": 3
}
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Scoring Through the Agent's Brain

**What:** Having the ZeroClaw agent reason about tweet relevance in its own context window instead of calling the dedicated scorer tool.

**Why bad:** The agent's context window fills with 20+ tweets per run. Token costs explode. The agent's general-purpose reasoning is worse at structured classification than a dedicated prompt. And you lose the ability to tune scoring independently.

**Instead:** Always use the dedicated `tweet_scorer.py` with its purpose-built prompt. The agent should call it as a tool, not try to score internally.

### Anti-Pattern 2: Stateful Python Daemon

**What:** Running a long-lived Python process that the agent communicates with via IPC/sockets instead of ZeroClaw's shell tool pattern.

**Why bad:** Violates ZeroClaw's security model (shell tools are sandboxed, audited, and scrubbed). Adds complexity with no benefit -- ZeroClaw already manages the lifecycle. A crash in the daemon would silently break the pipeline without ZeroClaw knowing.

**Instead:** Embrace process-per-invocation. Persist state to disk (cookies.json, rate_limit.db). Accept the ~300ms Python startup cost per tool call.

### Anti-Pattern 3: Bypassing Memory for Dedup

**What:** Having Python scripts maintain their own dedup set (e.g., a local JSON file of seen tweet IDs) instead of letting the agent check ZeroClaw memory.

**Why bad:** Creates two sources of truth. Memory is the agent's persistent brain -- it needs to know what it has and hasn't seen for all decisions, not just dedup. Splitting state makes the weekly report incomplete and cooldown logic fragile.

**Instead:** Return all tweets from search, let the agent check memory for duplicates, and let the agent decide what to remember. The Python scripts should be stateless (except for cookies and rate limits which are operational state, not application state).

### Anti-Pattern 4: Direct MiniMax Calls Without Timeout/Retry

**What:** Making bare httpx.post() calls to MiniMax without timeout, retry, or error handling.

**Why bad:** MiniMax API can have intermittent latency spikes or 5xx errors. A hung request blocks the entire pipeline run. No retry means transient failures cause lost scoring opportunities.

**Instead:** Use httpx with explicit timeout (30s), retry with exponential backoff (3 attempts), and graceful fallback (score 0 on failure so the pipeline continues).

### Anti-Pattern 5: Hardcoded Persona in Python Scripts

**What:** Embedding the full persona/skills description in each Python script's prompt.

**Why bad:** When the user tunes their persona (which they will -- the PROJECT.md explicitly says this), they have to update multiple files. The agent's SKILL.toml persona and the reply_generator.py persona can drift.

**Instead:** Have the agent pass relevant persona context as an argument to reply_generator.py, or load it from a shared config file. The SKILL.toml is the single source of truth for persona.

## Integration Points

### Critical Integration: ZeroClaw Shell Tool <-> Python Script

**Contract:** ZeroClaw invokes `python3 script.py --args`. Script prints JSON to stdout. ZeroClaw captures stdout as `ToolResult.output`. The agent sees the raw stdout string.

**Constraints discovered from research:**
- 60-second timeout per shell tool execution (ZeroClaw enforced)
- 1MB output limit (ZeroClaw enforced)
- Credential scrubbing applied to output (API keys in stdout get redacted)
- Security policy validates command before execution

**Implication for build:** All Python scripts must complete in <60s including Python startup + network calls. For scoring 20 tweets, this means either batch them in one call or accept sequential single-tweet calls.

**Recommendation:** Batch scoring -- pass all 20 tweets as a JSON array to tweet_scorer.py, score them in a loop within one process invocation, return all scores at once. This avoids 20 x ~300ms Python startups.

### Critical Integration: Twikit Cookie Session

**How it works:** Twikit uses Twitter's internal API with session cookies. First login requires username/email/password. Subsequent calls reuse cookies from `cookies.json`.

**Key facts (verified):**
- Twikit v2.0+ is async-only (no sync client). All scripts must use `asyncio.run()`.
- Latest stable release is 2.3.1 (not 2.3.3 as stated in the architecture doc -- version needs correction).
- `cookies_file` parameter in `Client.login()` handles auto-save/load of cookies (added in v2.3.0).
- `enable_ui_metrics=True` (default in v2.3.1) uses Js2Py to reduce suspension risk.

**Risk:** Cookie expiry after 3-7 days of inactivity. Mitigated by the keep-alive cron job (every 3 days). If cookies expire, manual re-login is needed -- the script should detect auth failure and log clearly.

### Integration: MiniMax Anthropic-Compatible API

**Endpoint:** `https://api.minimax.io/anthropic/v1/messages`
**Auth:** Bearer token (MiniMax API key)
**Format:** Anthropic Messages API format (model, max_tokens, messages, optional system)
**Models:** `MiniMax-M2.5` (reasoning), `MiniMax-M2.5-highspeed` (fast)

**Gotcha:** Some Anthropic parameters are silently ignored (thinking, top_k, stop_sequences). Do not rely on these for structured output enforcement. Instead, use strong prompt engineering for JSON output.

### Integration: ZeroClaw Memory

**Access:** Only through the agent loop (not directly from Python scripts)
**Backend:** SQLite with hybrid search (70% vector cosine + 30% FTS5 BM25)
**Embedding:** OpenAI text-embedding-3-small (configurable)

**Implication:** Python scripts cannot query or write to memory. All memory operations go through the agent's natural language instructions. The skill prompt must explicitly tell the agent what to remember and when to check memory.

## Build Order (Dependency-Driven)

The following build order respects component dependencies:

```
Phase 1: Foundation (no external deps needed)
  1. config.py            -- Env var loader, shared constants
  2. rate_limiter.py       -- SQLite-backed rate limiting (testable in isolation)

Phase 2: Twitter Integration (needs Twitter cookies)
  3. twikit_client.py     -- Shared async Twikit session manager
  4. twitter_search.py    -- Search wrapper (first external integration test)
  5. twitter_post.py      -- Post wrapper (test with a throwaway tweet)

Phase 3: LLM Pipeline (needs MiniMax API key)
  6. tweet_scorer.py      -- Scoring with M2.5-highspeed
  7. reply_generator.py   -- Reply drafting with M2.5 full

Phase 4: Skill Assembly (needs ZeroClaw installed)
  8. SKILL.toml           -- Wire all tools together
  9. queries.json         -- Query rotation config
  10. ZeroClaw config.toml -- Provider, memory, security, cost

Phase 5: Integration & Safety
  11. Manual end-to-end test via `zeroclaw agent -m "..."`
  12. Supervised mode validation via Gateway
  13. Cron scheduling enabled

Phase 6: Deployment
  14. VPS deployment (systemd service)
  15. Monitoring and graduated autonomy
```

**Why this order:**
- Phases 1-3 can be developed and tested locally on Windows without ZeroClaw
- Phase 2 before Phase 3 because search results define the data contract for scoring
- Phase 4 is pure integration -- no new logic, just wiring
- Phase 5 must follow Phase 4 because supervised mode requires the Gateway
- Phase 6 is deployment-only, no new code

## Scalability Considerations

| Concern | Current Scale (MVP) | If 3x Load | Notes |
|---------|-------------------|------------|-------|
| Tweets per scan | 20 | 60 | Batch scorer handles this; watch 60s timeout |
| Replies per day | ~15-20 | N/A | Capped by safety limits, not architecture |
| Memory size | ~1K entries/month | ~3K | SQLite handles millions; not a concern |
| MiniMax tokens | ~1M input/day | ~3M | $1.80/day; within $5 daily limit |
| Twikit sessions | 1 account | 1 account | Multi-account is out of scope |
| Python startup cost | ~300ms x 4 tools/run | Same | Fixed cost, not load-dependent |

## Version Corrections

**Twikit version:** The architecture doc states v2.3.3, but the latest release is **v2.3.1** (Feb 2025). Pin to `twikit==2.3.1` in requirements.txt. Confidence: HIGH (verified via GitHub releases page).

## Sources

- [ZeroClaw Tools and Skills System - DeepWiki](https://deepwiki.com/zeroclaw-labs/zeroclaw/11-tools-and-skills-system) -- Tool trait, shell tool execution, security policy, credential scrubbing
- [ZeroClaw Skills System - DeepWiki](https://deepwiki.com/zeroclaw-labs/zeroclaw/11.5-skills-system) -- SKILL.toml format, tool kinds (shell/http/script), security auditing
- [Twikit GitHub Releases](https://github.com/d60/twikit/releases) -- Version history, breaking changes (async-only since v2.0)
- [Twikit GitHub Repository](https://github.com/d60/twikit) -- Cookie-based auth, no API key needed
- [MiniMax Anthropic-Compatible API Docs](https://platform.minimax.io/docs/api-reference/text-anthropic-api) -- Endpoint, supported models, ignored parameters
- [MiniMax M2.5 API Setup Guide - Verdent](https://www.verdent.ai/guides/minimax-m2-5-api-setup) -- SDK integration patterns
- [Deconstructing ZeroClaw - One Page Code](https://onepagecode.substack.com/p/deconstructing-zeroclaw-the-ultra) -- Architecture overview
- [ZeroClaw Official Site](https://zeroclaw.net/) -- Runtime description
- [Autonomous Twitter Agent Architectures - Upstash Blog](https://upstash.com/blog/hacker-news-x-agent) -- Common patterns
- [dot-automation - GitHub](https://github.com/pippinlovesdot/dot-automation) -- Personality-driven agent architecture
- [OpenClaw Twitter Skill](https://openclawindex.com/news/how-openclaw-ai-agent-twitter-skill-bridges-your-ai-model-like-claude-or-gpt-with-twitterx-api) -- Skill-based Twitter integration patterns
