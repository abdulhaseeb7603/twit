# Project Research Summary

**Project:** TwitAgent
**Domain:** Autonomous Twitter AI Agent (Gig Hunting / Freelance Lead Generation)
**Researched:** 2026-03-20
**Confidence:** MEDIUM

## Executive Summary

TwitAgent is an autonomous Twitter agent that scans for AI/ML freelance gig postings, scores them for relevance using an LLM, and replies with contextual, human-sounding responses -- all running on a $5/month VPS within a ~$24/month total budget. The established pattern for this type of system is a scheduled pipeline: ingest tweets, classify/score via LLM, generate replies, post with rate limiting, and persist state in memory. The recommended stack is ZeroClaw (lightweight Rust agent runtime with built-in scheduling, memory, and cost tracking), Twikit (cookie-based Twitter access, no API key), and MiniMax M2.5 (1/63rd the cost of Claude Opus for adequate quality). Python bridge scripts handle Twitter I/O and LLM calls, invoked by ZeroClaw as shell tools.

The single biggest risk is account suspension. Cookie-based automation operates outside Twitter's sanctioned OAuth framework, and Twitter's 2026 automation policy explicitly warns that non-human-initiated actions lead to suspension. This is not a hypothetical -- it is an accepted tradeoff that must be mitigated through extremely conservative rate limits (start at 2-3 replies/hour, not 5), mandatory supervised mode for at minimum 2 weeks, and robust error handling that detects Twitter's Code 226 "automated request" warning and immediately backs off. A secondary cluster of risks involves ZeroClaw's headless mode shell tool execution (documented bug #851), LLM hallucination of tool outputs when tools fail, and session cookie expiry causing silent pipeline death. All three require Phase 1 mitigations.

The recommended approach is a three-phase build: (1) Foundation and MVP with supervised posting, proving the agent can find real gigs and generate approvable replies; (2) Supervised autonomy with cron scheduling, calibrated scoring, and operational hardening; (3) Full autonomy with brand-building, engagement tracking, and long-term sustainability. Development of Python bridge scripts (Phases 1-2) can happen locally on Windows without ZeroClaw; ZeroClaw integration and VPS deployment follow.

## Key Findings

### Recommended Stack

The stack is optimized for a single-agent, single-account deployment on a minimal VPS. ZeroClaw provides the agent runtime (scheduling, memory, security, cost tracking) as a ~3.4MB Rust binary using <5MB RAM. Twikit provides free Twitter access via cookie-based auth (the only viable free option -- official API starts at $100/month). MiniMax M2.5 provides LLM capabilities at $0.30/1M input tokens with an Anthropic-compatible API format.

**Core technologies:**
- **ZeroClaw v0.5.1:** Agent runtime -- scheduling, memory (SQLite + vector + FTS5), cost tracking, security, all in one binary
- **Twikit 2.3.x:** Cookie-based Twitter search/post -- free, no API key, pin version exactly due to Twitter API instability
- **MiniMax M2.5 / M2.5-highspeed:** LLM for scoring (highspeed) and reply generation (full) -- $0.30-1.20/1M tokens, Anthropic-compatible endpoint
- **Python 3.10+:** Bridge scripts connecting Twikit and MiniMax to ZeroClaw via shell tools
- **SQLite:** Built into ZeroClaw for memory, dedup, cooldowns, interaction history

**Version correction:** Architecture doc states Twikit v2.3.3 but latest verified release is v2.3.1. Pin to the actual latest stable.

### Expected Features

The MVP must prove one thing: the agent can find real gig posts and generate replies a human would approve. Autonomous posting is Phase 2+.

**Must have (table stakes):**
- Keyword-based tweet search with query rotation
- Tweet deduplication via memory
- LLM-powered relevance scoring with threshold filtering (start at 70/100)
- Contextual reply generation referencing specific tweet content
- Rate limiting (5 replies/hour hard cap, 24h per-user cooldown)
- Supervised mode (human approves every post)
- Cookie-based auth management
- Cost tracking with daily/monthly spend limits
- Error handling and structured logging

**Should have (differentiators):**
- Two-tier model routing (fast for scoring, quality for drafting)
- Configurable persona/skills profile
- Scam/spam tweet detection
- Daily showcase/brand tweets for inbound credibility
- Engagement tracking (reply-back detection)
- Provider failover (MiniMax -> OpenRouter)

**Defer indefinitely:**
- Automated DM outreach (highest suspension risk)
- Auto-follow/unfollow (instant suspension trigger)
- Multi-account support (sockpuppeting)
- Custom web dashboard (ZeroClaw gateway suffices)

### Architecture Approach

The system follows a process-per-invocation bridge pattern: ZeroClaw manages the agent loop, scheduling, and memory, while 4 Python scripts (twitter_search, tweet_scorer, reply_generator, twitter_post) are invoked as shell tools via `python3 script.py --args`, returning JSON to stdout. Python scripts are stateless between invocations; all persistent state lives in ZeroClaw's memory or on-disk files (cookies.json, rate_limit.db). A dual-channel LLM pattern exists: ZeroClaw's provider subsystem handles agent reasoning, while Python scripts call MiniMax directly for specialized scoring/generation tasks.

**Major components:**
1. **ZeroClaw Daemon** -- Agent loop, cron scheduling, memory (SQLite + vector), security, cost tracking
2. **Python Bridge Layer** -- 4 scripts (search, score, generate, post) + shared modules (twikit_client, rate_limiter, config, http_client)
3. **SKILL.toml** -- Skill manifest defining persona, tool registrations, workflow instructions
4. **External Services** -- Twitter/X (cookies), MiniMax API (Anthropic-compatible), OpenRouter (fallback)

### Critical Pitfalls

1. **Twitter Code 226 "automated request" block** -- Enable `enable_ui_metrics=True`, randomize delays with jitter, never burst replies. Handle this error in twitter_post.py from day one with 30+ minute backoff.
2. **Personal account suspension from cookie-based automation** -- Accept this risk explicitly. Start at 2-3 replies/hour, supervised mode for 2+ weeks, build a kill switch, have phone verification ready for first-offense unlock.
3. **Cookie/session expiry causing silent pipeline death** -- Health check at start of every scan (search for known term, verify >0 results). Build re-auth retry into twitter_search.py. Shorten cookie refresh to daily.
4. **ZeroClaw shell tools blocked in headless/systemd mode** -- Bug #851. Test the EXACT deployment scenario (systemd service with shell tools) before building the full pipeline. Fallback: run via tmux/screen.
5. **LLM fabricating tool outputs on failure** -- Every script must output structured error JSON on failure. SKILL.toml prompt must explicitly say "STOP on error, do NOT make up data." Verify posts actually exist on Twitter.

## Implications for Roadmap

### Phase 1: Foundation and MVP (Supervised Posting)
**Rationale:** All downstream phases depend on working Twitter I/O and LLM scoring. Must prove the core pipeline works before automating it. Must address all critical pitfalls before any tweet is sent.
**Delivers:** Working end-to-end pipeline: search -> score -> draft -> human-approved post. Verified on actual VPS deployment.
**Features addressed:** Tweet search with query rotation, deduplication, LLM scoring, threshold filtering, contextual reply generation, supervised posting, rate limiting, cookie auth, cost tracking, error handling.
**Pitfalls addressed:** Code 226 handling, session re-auth retry, ZeroClaw headless mode testing, JSON argument escaping (use base64/tempfile), structured error output, encrypted secrets, cookies.json permissions, shared HTTP client with retry/backoff.
**Build order:** config.py -> rate_limiter.py -> twikit_client.py -> twitter_search.py -> twitter_post.py -> tweet_scorer.py -> reply_generator.py -> SKILL.toml -> ZeroClaw config -> end-to-end test on VPS.

### Phase 2: Supervised Autonomy (Cron-Driven Operation)
**Rationale:** Once the pipeline is proven in supervised mode, enable cron scheduling while still requiring human approval. This phase is about operational hardening and scoring calibration.
**Delivers:** Hands-off scanning with human-gated posting. Calibrated scoring threshold. Batch scoring optimization.
**Features addressed:** Cron scheduling (20-min scan loop), per-user cooldown enforcement, cookie auto-refresh, scoring threshold tuning, category-aware scoring, configurable persona, scam/spam detection, provider failover.
**Pitfalls addressed:** Cron overlap lockfile, scoring calibration (manual validation of 50+ tweets), rate limiter rolling window verification, failover path testing, audit logging, batch scoring optimization.

### Phase 3: Full Autonomy and Brand Building
**Rationale:** After 2+ weeks of supervised operation with confidence in scoring quality and safety controls, graduate to full autonomy. Add features that build inbound credibility and measure effectiveness.
**Delivers:** Fully autonomous gig-hunting agent with brand presence and conversion metrics.
**Features addressed:** Full autonomy mode, daily showcase tweets, weekly lead report, engagement tracking (reply-back detection), thread context awareness, graceful Twikit failure handling.
**Pitfalls addressed:** Memory database TTL cleanup (30-day purge), showcase tweet quality monitoring, "looks done but isn't" verification checks, long-term session stability, budget reset automation.

### Phase Ordering Rationale

- **Python scripts before ZeroClaw integration:** Bridge scripts can be developed and tested locally on Windows without ZeroClaw. This front-loads the most uncertain work (Twikit auth, MiniMax API format) before adding the runtime layer.
- **Search before scoring, scoring before posting:** Each component's output defines the next component's input contract. Building in pipeline order avoids rework.
- **Supervised before autonomous:** Personal account safety requires human validation of every post during calibration. This is non-negotiable -- the risk of account suspension from bad automated replies is existential to the project.
- **Brand building last:** Showcase tweets and engagement tracking are force multipliers that only matter once the core reply pipeline is proven effective. Premature brand building on a poorly-calibrated agent wastes credibility.
- **VPS deployment within Phase 1, not deferred:** The ZeroClaw headless mode bug (#851) means deployment environment testing must happen early. Discovering this breaks in Phase 3 would require rearchitecting.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** ZeroClaw custom provider syntax (conflicting docs on `custom:URL` vs `[model_providers]` block), model_routes hint format (`"reasoning"` vs `"hint:reasoning"`), and Twikit version discrepancy (2.3.1 vs 2.3.3). All require hands-on testing during setup.
- **Phase 1:** JSON argument passing through ZeroClaw shell tools -- base64 encoding vs tempfile approach needs prototyping.
- **Phase 2:** Scoring calibration methodology -- no established pattern for threshold tuning in this domain. Will need manual validation.

Phases with standard patterns (skip deeper research):
- **Phase 1 (Python scripts):** Standard async Python with httpx and Twikit. Well-documented APIs.
- **Phase 2 (cron/scheduling):** ZeroClaw cron is well-documented. Lockfile pattern is standard.
- **Phase 3 (brand building):** Standard LLM content generation. No novel architecture needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Core stack (ZeroClaw, Twikit, MiniMax) verified. ZeroClaw config syntax has conflicting docs -- needs hands-on testing. Twikit version discrepancy (2.3.1 vs 2.3.3) needs resolution. |
| Features | MEDIUM-HIGH | Feature landscape well-understood from multiple practitioner sources. Conversion effectiveness (do replies actually land gigs?) is speculative -- only provable in production. |
| Architecture | MEDIUM-HIGH | Process-per-invocation bridge pattern is standard and well-documented. Dual-channel LLM usage (provider + direct) creates a cost tracking blind spot that needs mitigation. |
| Pitfalls | HIGH | Pitfalls verified across Twikit GitHub issues, ZeroClaw issue tracker, and official Twitter automation rules. The suspension risk is real and well-documented. |

**Overall confidence:** MEDIUM

The architecture and pitfalls are well-researched. The main uncertainty is operational: will ZeroClaw's custom provider syntax work with MiniMax on first try? Will Twikit's cookie auth remain stable? Will the scoring threshold produce quality leads? These are "test it and find out" gaps that cannot be resolved through more research.

### Gaps to Address

- **ZeroClaw custom provider syntax:** Two competing formats in docs. Must test both during Phase 1 setup. Low-risk (one will work), but blocks all LLM functionality if neither does.
- **Twikit version pinning:** Architecture doc says 2.3.3, architecture research says latest is 2.3.1. Verify actual latest stable release before starting.
- **Dual-channel cost tracking:** Python bridge scripts call MiniMax directly, bypassing ZeroClaw's cost limiter. Need manual token counting in scripts or a unified tracking approach.
- **MiniMax M2.5-highspeed model identifier:** The exact model string for API calls needs verification against current MiniMax docs.
- **Scoring threshold calibration:** No data on what score threshold produces quality leads. Must be tuned empirically during Phase 2 supervised operation.
- **Cookie session longevity under 2026 Twitter policies:** Reports range from 6 hours to 7 days. Daily refresh cron is recommended until actual behavior is observed.

## Sources

### Primary (HIGH confidence)
- [ZeroClaw GitHub](https://github.com/zeroclaw-labs/zeroclaw) -- v0.5.1 release, config reference, Issue #851
- [ZeroClaw DeepWiki](https://deepwiki.com/zeroclaw-labs/zeroclaw/) -- Provider config, skills system, security policy
- [Twikit GitHub](https://github.com/d60/twikit) -- Issues #170, #176, #199, #221, #392; release history
- [Twikit Documentation](https://twikit.readthedocs.io) -- cookies_file parameter, enable_ui_metrics
- [X Official Automation Rules](https://help.x.com/en/rules-and-policies/x-automation) -- Suspension policies
- [MiniMax API Docs](https://platform.minimax.io/docs/) -- Pricing, Anthropic-compatible endpoint

### Secondary (MEDIUM confidence)
- [OpenTweet - Twitter Automation Rules 2026](https://opentweet.io/blog/twitter-automation-rules-2026) -- Practitioner analysis of enforcement
- [BitDoze - ZeroClaw + MiniMax Setup](https://www.bitdoze.com/zeroclaw-setup-guide/) -- Integration walkthrough
- [Artificial Analysis - MiniMax M2.5](https://artificialanalysis.ai/models/minimax-m2-5) -- Benchmarks, throughput
- [MiniMax on OpenRouter](https://openrouter.ai/minimax/minimax-m2.5) -- Pricing comparison

### Tertiary (LOW confidence)
- ZeroClaw model_routes hint syntax -- conflicting docs, needs testing
- Twikit v2.3.3 existence -- architecture doc claims it, GitHub releases show v2.3.1 as latest
- MiniMax M2.5-highspeed model string -- exact API identifier unverified

---
*Research completed: 2026-03-20*
*Ready for roadmap: yes*
