# Phase 1: Foundation & Infrastructure - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the agent runtime skeleton: ZeroClaw skill definition (SKILL.toml with all tool registrations), Python bridge layer for Twikit and MiniMax API calls, memory schema (SQLite + vector for scored tweets and ops logging), structured error handling, cost tracking ($5/day, $50/month), and deployment to homeserver as systemd service. This is the working skeleton that all downstream phases build on.

</domain>

<decisions>
## Implementation Decisions

### Python bridge structure
- All-Python bridge approach — every tool gets its own standalone Python script (twitter_search.py, tweet_scorer.py, reply_generator.py, twitter_post.py, rate_limiter.py)
- LLM-powered tasks (scoring, reply generation) use separate Python scripts calling MiniMax API directly, NOT ZeroClaw's built-in provider — gives explicit control over each MiniMax call and makes debugging/auditing straightforward
- Scripts load secrets via ZeroClaw's encrypted secrets system (not plain environment variables)
- Error output format: structured JSON to stdout on both success and failure — `{"error": true, "code": "TWIKIT_AUTH_FAILED", "message": "...", "retryable": true}` so ZeroClaw's agent can parse and act on errors

### Memory schema design
- Use ZeroClaw's built-in memory system (SQLite + hybrid vector search) with OpenAI embeddings enabled from the start (`embedding_provider = "openai"`)
- Rich metadata per scored tweet: tweet_id, text, username, bio, follower_count, verified, score, category, reason, should_reply, opportunity_summary, found_at, query_used
- Include an operational logging table (agent_actions) tracking: action_type, timestamp, success/fail, error_code, tokens_used, cost_usd — for debugging and cost monitoring

### Dev & deploy workflow
- Development and testing on user's homeserver (Ubuntu Server, 16GB DDR4, 256GB SSD) via SSH — real Linux environment, no WSL or Docker needed
- Homeserver is the initial production target; migrate to VPS only if uptime becomes an issue
- Code deployment via git clone + pull (push to GitHub, SSH in and git pull) — versioned, works for future VPS migration
- ZeroClaw installed directly on homeserver for full integration testing

### Error handling & logging
- Structured JSON error output from all Python scripts to stdout (decided above)
- Twikit failures trigger: log structured error to ops table, retry with exponential backoff (3 attempts), if still failing log an alert-level entry the agent can surface in reports
- Two-tier error classification:
  - Recoverable (rate limit 429, temporary Cloudflare block): retry with backoff, continue next cycle
  - Fatal (cookie expired, API key invalid): stop retrying, log critical alert, require manual intervention
- Day-to-day monitoring via ZeroClaw's built-in gateway dashboard (port 42617)

### Claude's Discretion
- Exact Python script internal structure and imports
- SQLite table schemas and index design
- systemd service file configuration
- ZeroClaw SKILL.toml tool argument formats
- Retry backoff timing and thresholds
- Log rotation and retention policy

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & stack
- `TWITTER_GIG_AGENT_ARCHITECTURE_V2.md` — Full v2 architecture: stack decisions, ZeroClaw config.toml template, SKILL.toml structure, Python bridge script examples, pipeline design, file structure, deployment steps, cost estimates
- `TWITTER_GIG_AGENT_ARCHITECTURE_V2.md` §5 — Complete ZeroClaw configuration (config.toml) with MiniMax provider, model routing, failover, memory, cost tracking, security, and gateway settings
- `TWITTER_GIG_AGENT_ARCHITECTURE_V2.md` §7 — SKILL.toml definition with all tool registrations and Python script paths
- `TWITTER_GIG_AGENT_ARCHITECTURE_V2.md` §8-9 — Python bridge script examples (tweet_scorer.py, reply_generator.py) showing MiniMax API call patterns

### Requirements
- `.planning/REQUIREMENTS.md` — INFR-01 through INFR-07 (infrastructure) and MEMO-01 (memory schema) are the Phase 1 requirements
- `.planning/ROADMAP.md` — Phase 1 success criteria (5 items that must be TRUE)

### Project context
- `.planning/PROJECT.md` — Constraints, key decisions, and out-of-scope items

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing code — this is the first phase, building from scratch

### Established Patterns
- Architecture doc provides reference implementations for all Python bridge scripts
- ZeroClaw config.toml template is fully defined in the architecture doc

### Integration Points
- ZeroClaw skill system: SKILL.toml in `~/.zeroclaw/workspace/skills/twitter-gig-hunter/`
- Python scripts in `~/.zeroclaw/workspace/skills/twitter-gig-hunter/scripts/`
- ZeroClaw memory: SQLite database at `~/.zeroclaw/workspace/memory/memory.db`
- ZeroClaw gateway dashboard on port 42617
- GitHub repo for code deployment to homeserver

</code_context>

<specifics>
## Specific Ideas

- User has a homeserver (Ubuntu Server, 16GB DDR4, 256GB SSD) that will serve as initial dev and production environment — treat it like a VPS
- Start on homeserver, migrate to VPS only if uptime becomes an issue
- ZeroClaw's built-in memory already supports hybrid vector search (70% cosine + 30% FTS5 BM25) — no external vector DB needed
- ZeroClaw bug #851 (shell tools failing in headless/systemd mode) must be verified early in this phase

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-infrastructure*
*Context gathered: 2026-03-25*
