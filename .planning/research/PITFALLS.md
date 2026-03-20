# Pitfalls Research

**Domain:** Autonomous Twitter AI Agent (cookie-based auth, LLM scoring, automated posting on personal account)
**Researched:** 2026-03-20
**Confidence:** HIGH (verified across Twikit GitHub issues, ZeroClaw issue tracker, Twitter/X official rules, and multiple practitioner reports)

---

## Critical Pitfalls

### Pitfall 1: Twitter's "This request looks like it might be automated" Block (Code 226)

**What goes wrong:** Twitter's anti-bot system detects automated tweet creation and blocks the action with error code 226, even when other operations (likes, search) still work. This specifically targets posting/replying -- the core action this agent needs.

**Why it happens:** Twitter uses behavioral signals beyond rate limits: request timing regularity, missing UI metrics headers, lack of mouse/keyboard fingerprint data in requests, and consistent user-agent patterns. Cookie-based clients like Twikit lack the browser fingerprinting that a real user session provides.

**How to avoid:**
- Enable Twikit's `enable_ui_metrics=True` parameter -- this sends obfuscated UI metrics that reduce bot detection
- Randomize delays between posts (not fixed intervals -- use jitter: e.g., `base_delay + random(0, base_delay * 0.5)`)
- Never post more than 2-3 replies in quick succession; space them across the 20-min scan window
- Start with supervised mode and manually verify the first 50+ posts before going autonomous
- Consider extracting cookies from a real browser session rather than using Twikit's programmatic login

**Warning signs:** `twikit.errors.Forbidden` (403) or the "automated request" error appearing even once means Twitter has flagged the session. Continuing to post escalates to account lock.

**Phase to address:** Phase 1 (MVP). The `twitter_post.py` bridge script must handle this error gracefully from day one -- catching it, backing off for 30+ minutes, and alerting the user.

**Confidence:** HIGH -- documented in [Twikit Issue #392](https://github.com/d60/twikit/issues/392) and [Issue #170](https://github.com/d60/twikit/issues/170).

---

### Pitfall 2: Personal Account Suspension from Cookie-Based Automation

**What goes wrong:** Using cookie-based automation (Twikit) on a personal Twitter account risks permanent suspension. Twitter's official automation rules (updated Feb 2026) state that scripts logging in with passwords or driving headless browsers are not recognized as authorized applications and can result in permanent suspension. X's Head of Product announced: "If a human is not tapping on the screen, the account and all associated accounts will likely be suspended."

**Why it happens:** Cookie-based tools operate outside Twitter's sanctioned OAuth framework. Twitter has no way to distinguish Twikit from a credential-stuffing bot. The personal account has no "developer app" association that marks it as legitimate automation.

**How to avoid:**
- Accept this risk explicitly in project planning -- this is the single biggest risk to the entire project
- Keep rate limits extremely conservative (the 5/hour cap in the architecture is good; consider starting at 2-3/hour)
- Run in supervised mode for at minimum 2 weeks, not just "the first 2 weeks"
- Do NOT automate follows, likes, or retweets -- only search (read) and reply (write). Twitter's detection specifically targets engagement automation patterns
- Build a "kill switch" -- a way to immediately stop all posting remotely (e.g., a file flag the cron checks, or ZeroClaw gateway command)
- Have a backup plan for if the account gets locked (Twitter typically offers phone verification to unlock on first offense)

**Warning signs:** Sudden increase in CAPTCHAs during login, "verify your identity" prompts, rate limit responses (429) appearing at lower-than-expected volumes, or the Code 226 error from Pitfall 1.

**Phase to address:** Phase 1 (design) and Phase 2 (supervised operation). Rate limiting and safety controls must be architected before any tweet is sent.

**Confidence:** HIGH -- based on [X's official automation rules](https://help.x.com/en/rules-and-policies/x-automation) and [OpenTweet's 2026 analysis](https://opentweet.io/blog/twitter-automation-rules-2026).

---

### Pitfall 3: Cookie/Session Expiry Causing Silent Pipeline Failure

**What goes wrong:** Twikit sessions expire after 3-7 days of inactivity (sometimes 6 hours under aggressive invalidation). When this happens, searches return empty results or throw `Unauthorized` (401) errors. If not handled, the agent continues running its LLM pipeline on zero tweets -- burning MiniMax tokens on empty scoring loops while finding no leads.

**Why it happens:** Twitter invalidates session tokens on a schedule, especially for sessions showing bot-like patterns. The architecture's 3-day keep-alive cron may not be frequent enough under Twitter's newer (2026) session policies.

**How to avoid:**
- Use Twikit's `cookies_file` parameter to persist cookies and attempt auto-refresh on each login
- Implement a health check at the START of every scan loop: search for a known term (e.g., "twitter"), verify you get >0 results. If zero, trigger re-authentication before proceeding
- Build the re-auth flow directly into the search script: catch `Unauthorized`, call `client.login()` with stored credentials, save new cookies, retry once
- Shorten the cookie refresh cron to daily (not every 3 days) until session stability is proven
- Log every auth failure with timestamps to detect patterns

**Warning signs:** Consecutive scan runs returning zero tweets. Search results dropping to empty suddenly. `401 Unauthorized` in logs.

**Phase to address:** Phase 1 (MVP). The `twitter_search.py` script needs built-in re-auth retry logic from the start.

**Confidence:** HIGH -- documented in [Twikit Issue #176](https://github.com/d60/twikit/issues/176) and [Twikit docs](https://twikit.readthedocs.io/en/latest/twikit.html).

---

### Pitfall 4: ZeroClaw Shell Commands Blocked in Headless/Non-Interactive Mode

**What goes wrong:** Even with `autonomy.level = "full"`, ZeroClaw's security policy blocks shell tool execution when running in non-interactive environments (Docker, systemd service, cron). The approval prompt reads EOF from stdin and denies the command. The agent then fabricates results instead of reporting the failure.

**Why it happens:** ZeroClaw's security validation fires at the tool execution layer regardless of autonomy settings. Bug #851 documented this: `is_command_allowed()` triggers approval prompts that cannot be answered without a terminal.

**How to avoid:**
- Verify that the VPS deployment uses a ZeroClaw version that includes the fix from PR #902 (quote-aware command parsing). The fix is now in the codebase but may not be in all release builds
- Test the EXACT deployment scenario (systemd service calling agent with shell tools) BEFORE building the full pipeline
- Run `zeroclaw doctor` on the VPS to validate the configuration
- If the bug persists in your version, use `zeroclaw agent -m` from a tmux/screen session as a workaround rather than pure systemd

**Warning signs:** Agent logs showing tool calls but the Python scripts never actually execute. Memory filling up with "results" that look plausible but are fabricated by the LLM. Empty `cookies.json`. No actual tweets appearing on the account despite "successful" runs in logs.

**Phase to address:** Phase 1 (MVP). This must be tested in the actual deployment environment before anything else works.

**Confidence:** HIGH -- documented in [ZeroClaw Issue #851](https://github.com/zeroclaw-labs/zeroclaw/issues/851).

---

### Pitfall 5: LLM Fabricating Tool Outputs When Tools Fail

**What goes wrong:** When a ZeroClaw shell tool fails (script error, timeout, permission denied), the LLM agent may hallucinate a plausible-looking response rather than reporting failure. The agent "completes" its pipeline with fake tweet data, fake scores, and fake reply confirmations -- while nothing actually happened on Twitter.

**Why it happens:** LLMs are trained to be helpful and produce coherent output. When a tool returns an error or empty output, the model's instinct is to generate what "should" have been returned. ZeroClaw's shell tool has a 60-second timeout and 1MB output limit -- exceeding either produces truncated/empty output the LLM may misinterpret.

**How to avoid:**
- Every Python bridge script must output a clear, structured error on failure: `{"error": true, "message": "..."}` -- never exit silently
- Add explicit instructions in SKILL.toml prompt: "If any tool returns an error or empty result, STOP the pipeline and report the error. Do NOT make up data."
- Implement a verification step: after `twitter_post` claims success, query memory or run a follow-up search to confirm the reply exists
- Log all tool invocations and outputs independently (outside the LLM's view) so you can audit what actually ran

**Warning signs:** Memory entries showing interactions that don't exist on the actual Twitter account. Reply counts in weekly reports that don't match Twitter's own reply count. Agent reporting "posted 5 replies" but the account shows 0 new activity.

**Phase to address:** Phase 1 (MVP) for error handling in scripts; Phase 2 (supervised) for verification and audit logging.

**Confidence:** HIGH -- this is a well-documented pattern in agentic AI systems and explicitly mentioned in [ZeroClaw Issue #851](https://github.com/zeroclaw-labs/zeroclaw/issues/851) where the agent fabricated results when shell tools were blocked.

---

## Technical Debt Patterns

### Debt 1: Hardcoded MiniMax API Endpoint

**What goes wrong:** The architecture hardcodes `https://api.minimax.io/anthropic/v1/messages` in every Python bridge script. If MiniMax changes their endpoint URL (which has happened -- the v1 architecture used the wrong OpenAI-format endpoint), every script needs manual updating.

**How to avoid:** Pass the API URL and key as environment variables or read from a shared config file. One source of truth for the endpoint.

**Phase to address:** Phase 1.

### Debt 2: Duplicate Rate Limiting Logic

**What goes wrong:** Rate limiting is enforced in three places: `rate_limiter.py`, the SKILL.toml prompt (agent self-tracking), and the cron frequency. These can drift out of sync. The prompt says "5/hour" but the actual limiter could be configured differently.

**How to avoid:** Rate limiting should be enforced ONLY in `rate_limiter.py` (the source of truth). The prompt should say "the tool will enforce limits" rather than stating specific numbers. Cron frequency should be documented as separate from per-run limits.

**Phase to address:** Phase 1.

### Debt 3: No Retry/Backoff Abstraction

**What goes wrong:** Each Python bridge script independently implements HTTP calls with its own timeout and error handling. When MiniMax or Twitter rate-limits, each script handles it differently (or not at all). The `tweet_scorer.py` example has a 30-second timeout but no retry logic.

**How to avoid:** Create a shared `http_client.py` module with exponential backoff, configurable retries, and consistent error output format. All bridge scripts import from it.

**Phase to address:** Phase 1.

---

## Integration Gotchas

### Gotcha 1: Twikit LoginFlow "Currently Not Accessible" (Error 366)

**What it is:** Twikit's `client.login()` fails with `BadRequest: flow name LoginFlow is currently not accessible`. This is Twitter throttling programmatic login attempts, not a Twikit bug.

**When it hits:** After multiple login attempts in a short period, after an account gets temporarily locked, or when Twitter is doing infrastructure updates.

**How to handle:** Do NOT retry login in a tight loop -- this makes it worse. Wait 15-30 minutes. Use cookie-based session resumption (`cookies_file`) to minimize login frequency. Log in manually via browser and export cookies as a fallback.

**Confidence:** HIGH -- [Twikit Issue #199](https://github.com/d60/twikit/issues/199), [Issue #221](https://github.com/d60/twikit/issues/221).

### Gotcha 2: ZeroClaw Skill Audit Blocks .sh Files

**What it is:** ZeroClaw's skill installation performs static security analysis and flags files with extensions like `.sh`, `.ps1`, `.bat` as high-risk, potentially blocking skill installation.

**When it hits:** If you include shell wrapper scripts in the skill directory, or if any file exceeds 512KB.

**How to handle:** Use `.py` files exclusively for all bridge scripts (which the current architecture already does). Keep all scripts under 512KB. Do not include `.sh` helpers in the skill package.

**Confidence:** HIGH -- documented in [ZeroClaw Skills System](https://deepwiki.com/zeroclaw-labs/zeroclaw/11.5-skills-system).

### Gotcha 3: MiniMax M2.5 Endpoint Format Confusion

**What it is:** MiniMax M2.5 has TWO endpoint formats: the OpenAI-compatible endpoint (`api.minimax.chat/v1`) and the Anthropic-compatible endpoint (`api.minimax.io/anthropic`). Using the wrong one causes "invalid role: developer" errors.

**When it hits:** During initial setup, or if copying config from older MiniMax tutorials that used the OpenAI format.

**How to handle:** Always use the Anthropic-compatible endpoint for M2.5. Document this prominently. The architecture doc already flags this but it bears repeating in setup scripts.

**Confidence:** MEDIUM -- sourced from the architecture doc's own notes. Needs verification against current MiniMax docs at setup time.

### Gotcha 4: JSON Argument Passing Through ZeroClaw Shell Tools

**What it is:** ZeroClaw's shell tools pass arguments as command-line strings. The `tweet_scorer` takes `--tweet "{json}"` which means the JSON must be properly escaped for shell execution. Nested quotes, special characters in tweet text, and Unicode can all break argument parsing.

**When it hits:** When scoring tweets that contain quotes, apostrophes, dollar signs, backticks, or other shell-special characters -- which is extremely common in real tweets.

**How to handle:** Use base64 encoding for JSON arguments, or write JSON to a temp file and pass the file path. Do NOT rely on shell escaping of arbitrary tweet text.

**Phase to address:** Phase 1. This will cause failures on the first real-world tweets if not handled.

**Confidence:** HIGH -- standard shell escaping problem, compounded by ZeroClaw's semicolon-parsing behavior documented in Issue #851.

---

## Performance Traps

### Trap 1: Scoring 20 Tweets Sequentially Burns Time and Tokens

**What goes wrong:** The pipeline scores 20 tweets one-by-one via individual MiniMax API calls. At 1-3 seconds per call, this is 20-60 seconds per scan. With 72 runs/day, that is 24-72 minutes of scoring latency daily, plus the token cost on tweets that are obviously irrelevant.

**How to avoid:** Batch scoring -- send 5-10 tweets in a single prompt and ask for a JSON array of scores. MiniMax M2.5 has 200K context; you can easily fit 20 tweet summaries in one call. This cuts API calls from 20 to 2-4 per run and reduces total tokens (shared prompt overhead).

**Phase to address:** Phase 2 (optimization). Get single-tweet scoring working first, then batch.

### Trap 2: Memory Database Growing Unbounded

**What goes wrong:** Every scanned tweet, every score, every interaction gets saved to SQLite memory. At 20 tweets x 72 runs/day = 1,440 entries/day. After 3 months, that is 130K+ entries. Vector search performance degrades, FTS5 index grows, and the $5 VPS starts struggling.

**How to avoid:** Implement TTL-based cleanup: purge tweet records older than 30 days (keep only interactions where you actually replied). Run cleanup as a weekly cron job. Monitor `memory.db` file size.

**Phase to address:** Phase 3 (fully autonomous, long-term operation).

### Trap 3: Cron Overlap When Scan Runs Long

**What goes wrong:** The 20-minute cron interval assumes each scan completes within 20 minutes. If MiniMax is slow, or Twikit hits rate limits with backoff, a scan can take longer. ZeroClaw starts a new scan while the previous one is still running, causing duplicate replies and doubled API costs.

**How to avoid:** Use a lockfile mechanism -- each scan creates a lockfile at start, checks for it before running, removes it on completion. Or use ZeroClaw's task system to chain scans sequentially rather than cron.

**Phase to address:** Phase 2 (when enabling cron).

---

## Security Mistakes

### Mistake 1: Storing Twitter Credentials in Environment Variables on VPS

**What goes wrong:** The deployment instructions export `TWITTER_PASSWORD` as a plain environment variable. Any process on the VPS can read `/proc/*/environ`. If the VPS is compromised, the attacker gets both the Twitter account and MiniMax API key.

**How to avoid:** Use ZeroClaw's built-in encrypted secrets (ChaCha20-Poly1305). Store credentials via `zeroclaw secret set TWITTER_PASSWORD "..."` and read them in Python via ZeroClaw's secret retrieval mechanism, not `os.environ`.

**Phase to address:** Phase 1 (deployment).

### Mistake 2: cookies.json Readable by Any Process

**What goes wrong:** Twikit saves session cookies to `cookies.json` in the skill workspace. These cookies provide full access to the Twitter account -- equivalent to a logged-in session. No file permissions are set by default.

**How to avoid:** Set `chmod 600` on `cookies.json` immediately after creation. Ensure the systemd service runs as a dedicated user, not root. Consider encrypting cookies at rest (ZeroClaw's workspace is not encrypted by default, only its own secrets store is).

**Phase to address:** Phase 1 (deployment).

### Mistake 3: MiniMax API Key in Bridge Scripts Can Be Exfiltrated

**What goes wrong:** The Python bridge scripts receive the MiniMax API key via environment variable. If ZeroClaw's workspace security is misconfigured (e.g., `workspace_only = false`), a compromised skill could exfiltrate the key via an outbound HTTP call.

**How to avoid:** Keep `workspace_only = true` always. Keep `allowed_commands` minimal. Never add `wget` or unrestricted `curl` to allowed commands without URL whitelisting. Monitor MiniMax API usage dashboard for unexpected charges.

**Phase to address:** Phase 1 (configuration).

---

## "Looks Done But Isn't" Checklist

| Looks Done | Actually Isn't | How to Verify |
|---|---|---|
| "Agent posted 5 replies today" | LLM may have fabricated the posting results | Check actual Twitter account for those replies |
| "Cookie refresh cron working" | The search may succeed but cookies are already stale for posting | Actually post a test tweet, not just search |
| "Scoring threshold at 70 catches good leads" | Scoring may be miscalibrated -- 70 might include garbage or miss real leads | Manually score 50 tweets blind, compare with agent scores |
| "Rate limiter enforces 5/hour" | Rate limiter resets on script restart, not on a rolling window | Check if restarting the agent resets the counter |
| "Memory dedup prevents double-replies" | Dedup checks tweet ID but not conversation thread; may reply to the same thread via different tweets | Search memory for same user within 24h, not just same tweet ID |
| "Supervised mode catches bad replies" | Supervised mode requires someone actively watching the gateway dashboard | Set up alerts/notifications, not just dashboard availability |
| "Daily showcase tweet builds brand" | The LLM may produce repetitive, generic content that hurts credibility | Review showcase tweets weekly for uniqueness and quality |
| "Failover to OpenRouter works" | OpenRouter may route to a different model that formats output differently, breaking JSON parsing | Test failover path explicitly with the same scoring/reply prompts |

---

## Recovery Strategies

### Recovery 1: Account Gets Temporarily Locked

**Steps:**
1. Immediately stop all cron jobs: `zeroclaw cron list` then `zeroclaw cron remove <id>` for each
2. Log in to Twitter manually via browser, complete any verification (phone, email, CAPTCHA)
3. Wait 24-48 hours before resuming ANY automation
4. When resuming, start with search-only (no posting) for 24h to rebuild session trust
5. Reduce rate limits by 50% for the first week back
6. Review what triggered the lock (check logs for burst patterns)

### Recovery 2: Cookie Auth Completely Broken (Twikit Update or Twitter API Change)

**Steps:**
1. Check [Twikit GitHub issues](https://github.com/d60/twikit/issues) for reports from other users
2. If Twikit is broken, switch to `twitter-api-client` (same cookie approach, different library) -- the architecture doc has a code snippet for this
3. If all cookie-based approaches are broken, fall back to Playwright browser automation (slower but more resilient)
4. Keep search queries and scoring logic decoupled from the Twitter client so swapping is a one-file change

### Recovery 3: MiniMax API Down or Budget Exhausted

**Steps:**
1. ZeroClaw's failover should auto-switch to OpenRouter -- verify this is configured
2. If cost limit is hit, the agent should stop gracefully, not crash. Verify `[cost]` config stops tool execution, not just logging
3. Reset budget counters: check if ZeroClaw has a `zeroclaw cost reset` command or if it auto-resets daily

### Recovery 4: Memory Database Corrupted

**Steps:**
1. SQLite databases can survive `PRAGMA integrity_check` -- run this first
2. If corrupt, delete `memory.db` and let ZeroClaw recreate it. You lose interaction history (dedup state, cooldown tracking) but the agent restarts cleanly
3. Keep a daily backup cron: `cp memory.db memory.db.bak` before the first scan of the day

---

## Pitfall-to-Phase Mapping

| Phase | Pitfalls to Address | Priority |
|---|---|---|
| **Phase 1 (MVP)** | Code 226 handling in twitter_post.py, Session re-auth retry in twitter_search.py, ZeroClaw headless mode testing on VPS, Shell escaping for JSON args (use base64 or tempfile), Error output format in all bridge scripts, Encrypted secrets (not env vars), cookies.json permissions, Shared HTTP client with retry/backoff, Single source of truth for API endpoint config | CRITICAL -- none of these can be deferred |
| **Phase 2 (Supervised)** | Cron overlap lockfile, Scoring calibration (manual validation of threshold), Rate limiter rolling window verification, Failover path testing with actual prompts, Audit logging independent of LLM, Batch scoring optimization | HIGH -- catch issues during supervised operation |
| **Phase 3 (Autonomous)** | Memory database TTL cleanup, Showcase tweet quality monitoring, "Looks Done But Isn't" verification checks, Long-term session stability monitoring, Budget reset automation | MEDIUM -- operational sustainability |

---

## Sources

- [Twikit Issue #392 - "This request looks like it might be automated"](https://github.com/d60/twikit/issues/392)
- [Twikit Issue #170 - Automated request detection](https://github.com/d60/twikit/issues/170)
- [Twikit Issue #176 - Cookie login issue](https://github.com/d60/twikit/issues/176)
- [Twikit Issue #199 - LoginFlow not accessible](https://github.com/d60/twikit/issues/199)
- [Twikit Issue #221 - LoginFlow error](https://github.com/d60/twikit/issues/221)
- [Twikit Documentation](https://twikit.readthedocs.io/en/latest/twikit.html)
- [ZeroClaw Issue #851 - autonomy level=full broken in non-interactive mode](https://github.com/zeroclaw-labs/zeroclaw/issues/851)
- [ZeroClaw Skills System](https://deepwiki.com/zeroclaw-labs/zeroclaw/11.5-skills-system)
- [ZeroClaw Tools and Skills](https://deepwiki.com/zeroclaw-labs/zeroclaw/11-tools-and-skills)
- [X's Official Automation Rules](https://help.x.com/en/rules-and-policies/x-automation)
- [OpenTweet - Twitter Automation Rules 2026](https://opentweet.io/blog/twitter-automation-rules-2026)
- [Scraperly - How to Scrape Twitter/X in 2026](https://scraperly.com/scrape/twitter)
- [ZeroClaw Config Reference](https://github.com/zeroclaw-labs/zeroclaw/blob/master/docs/reference/api/config-reference.md)
