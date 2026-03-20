# Feature Research

**Domain:** Autonomous Twitter/X gig-hunting agent for AI engineering freelance leads
**Researched:** 2026-03-20
**Confidence:** MEDIUM-HIGH (core features well-understood; conversion effectiveness is speculative)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that the agent must have or it does not function as a gig-hunting tool. Missing any of these means the agent is fundamentally broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Keyword-based tweet search** | Cannot find gigs without searching | Low | Twikit `search_tweet()`, multiple query patterns |
| **Query rotation** | Single query misses gig types, gets stale results | Low | Cycle through 6+ query templates per the architecture |
| **Tweet deduplication** | Replying to same tweet twice looks broken/spammy | Low | Hash tweet IDs in memory, check before scoring |
| **LLM-powered relevance scoring** | Human can't review 20+ tweets every 20 minutes; need automated filtering | Medium | Structured JSON output (score, category, reason, should_reply) |
| **Score threshold filtering** | Without filtering, agent replies to noise | Low | Start at 70/100, tunable |
| **Contextual reply generation** | Generic replies get ignored and flagged as spam | Medium | Full LLM model with persona prompt, reference specific tweet content |
| **Rate limiting (replies/hour)** | Account suspension without it; Twitter enforces server-side too | Low | 5 replies/hour hard cap, enforced in code AND prompt |
| **Per-user cooldown** | Double-replying to same person looks automated | Low | 24h cooldown, stored in memory |
| **Cookie-based auth management** | Twikit sessions expire; agent stops working silently | Medium | Auto-refresh every 3 days, error detection on auth failure |
| **Interaction history/memory** | Without memory, agent has no context for past interactions | Medium | SQLite + vector search for dedup, context, and reporting |
| **Supervised mode** | Must be able to human-approve all posts during initial tuning | Low | ZeroClaw `autonomy.level = "supervised"` |
| **Cost tracking and spend limits** | Runaway LLM costs with no ceiling is a budget risk | Low | ZeroClaw built-in: daily $5, monthly $50 caps |
| **Error handling and logging** | Silent failures mean missed gigs and undetected breakage | Medium | Log all search/score/reply/post actions; surface errors |
| **Cron-based scan scheduling** | Manual triggering defeats the purpose of autonomy | Low | 20-min interval via ZeroClaw cron |

### Differentiators (Competitive Advantage)

Features that make this agent meaningfully better than someone manually scanning Twitter or using generic automation tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Two-tier model routing** | Fast model for bulk scoring (20+ tweets), quality model for reply drafting (2-5 replies). Saves cost AND latency without sacrificing reply quality. | Low | M2.5-highspeed for scoring, M2.5 full for drafting. ZeroClaw `hint:fast`/`hint:reasoning` handles this automatically. |
| **Configurable persona/skills profile** | User can tune the agent's claimed skills, experience level, and communication style without code changes. Different users = different personas. | Low | Prompt-level configuration in SKILL.toml |
| **Scam/spam tweet detection** | Skipping crypto scams, MLM pitches, and fake gig posts avoids embarrassing replies. Most automation tools do not filter for this. | Medium | Add explicit scam signals to scoring prompt (crypto mentions, "DM me for opportunity", excessive emojis) |
| **Category-aware scoring** | Distinguishing freelance_gig vs contract_role vs fulltime_role vs vague_inquiry lets the agent prioritize what the user actually wants. | Low | Already in scoring schema. Enables filtering by gig type preference. |
| **Daily showcase/brand tweets** | Posting original AI/ML insights builds inbound credibility. Gig posters check your profile before responding to your reply. | Medium | 10 AM daily cron, memory-aware to avoid repetition |
| **Weekly lead report** | Automated summary of leads found, replies sent, response rate, and follow-up actions. Makes the agent's value visible. | Low | Sunday cron job, memory query for past 7 days |
| **Engagement tracking (reply-back detection)** | Knowing when a gig poster actually replies back is the most important conversion signal. Without it you cannot measure if the agent works. | Medium | Search for mentions/replies to your account, match against sent replies in memory |
| **Thread context awareness** | Some gig posts are in threads (original tweet + clarifications). Scoring only the leaf tweet misses context. | Medium | Fetch parent tweet when reply_count > 0 or conversation_id differs |
| **Follower-count / credibility signals** | A gig posted by an account with 50K followers and "CTO at X" in bio is higher value than an anonymous egg account. | Low | Already partially in scoring prompt (bio field). Weight follower count and verified status. |
| **Graceful degradation on Twikit failure** | If Twikit breaks (Cloudflare blocks, cookie expiry), agent should detect, log, and alert -- not silently die. | Medium | Health check on every search; fallback to `twitter-api-client` or Playwright |
| **Provider failover** | If MiniMax API is down, auto-fallback to OpenRouter keeps the agent running. | Low | ZeroClaw `[reliability]` config handles this natively |

### Anti-Features (Commonly Requested, Often Problematic)

Things to deliberately NOT build. Each would seem useful but creates more risk than value.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Automated DM outreach** | DMs from unknown accounts are the #1 spam signal on Twitter. Extremely high suspension risk, especially on a personal account. Twitter's spam detection is tuned specifically for automated DMs from non-followers. | Reply publicly with a clear, specific comment. If someone replies back, then manually follow up in DMs. |
| **Auto-follow/unfollow** | Twitter's systems are specifically tuned to detect mass follow/unfollow patterns. Triggers automated suspension immediately. Zero value for gig hunting. | Do not automate any follow behavior. Follow interesting accounts manually. |
| **Auto-like tweets** | Liking gig posts does not get you hired. Twitter detects automated liking patterns and restricts accounts. Wastes API calls for zero conversion value. | Use the reply as the sole engagement mechanism. A good reply is worth 100 likes. |
| **Hashtag stuffing in replies** | Screams "bot." Twitter penalizes hashtag-heavy content in reply visibility. Reduces perceived credibility to zero. | No hashtags in replies, ever. Already enforced in reply generation prompt. |
| **Multi-account support** | Using multiple accounts for the same purpose is sockpuppeting. Twitter will link and ban all accounts. Doubles complexity for negative ROI. | Single personal account. Quality over quantity. |
| **Web dashboard / mobile app** | Massive scope creep for a headless agent. ZeroClaw already has a gateway dashboard. Building a custom UI delays the core value (finding gigs). | Monitor via ZeroClaw gateway at port 42617. Add Discord/Telegram notifications later if needed. |
| **Automated retweet/quote-tweet of gig posts** | Retweeting "hiring AI engineer" posts to your followers is not outreach -- it is content pollution. Makes your timeline look like a job board scraper. | Only create original content (daily showcase tweets) and targeted replies. |
| **"I'd love to connect" template replies** | Generic LinkedIn-speak is the hallmark of bot outreach. Instantly recognized and ignored. Violates the core value prop of "human-sounding replies." | Every reply must reference something specific from the tweet. Enforced in reply generation prompt rules. |
| **Aggressive reply frequency** | Going above 5/hour or 20/day triggers Twitter's automated review. Even if not suspended, high-frequency replies get shadow-deprioritized in Twitter's algorithm. | Stick to the 5/hour, 20/day caps. Quality over quantity. |
| **Sentiment analysis on own replies** | Over-engineering. The LLM already generates contextual replies. Adding a separate sentiment analysis step adds latency and cost for minimal quality improvement. | Trust the reply generation prompt's quality rules. Review manually during supervised mode. |

## Feature Dependencies

```
Cookie Auth Management
  └── Tweet Search (requires active session)
       └── Tweet Deduplication (requires search results + memory)
       └── Tweet Scoring (requires search results)
            └── Score Threshold Filtering (requires scores)
                 └── Reply Generation (requires filtered tweets + persona config)
                      └── Reply Posting (requires generated reply + rate limiter)
                           └── Interaction History Logging (requires posted reply data)
                                └── Engagement Tracking (requires logged interactions)
                                └── Weekly Lead Report (requires logged interactions)

Cron Scheduling ── drives ── Search Loop (every 20 min)
                              Daily Showcase Tweet (10 AM)
                              Weekly Report (Sunday 8 PM)
                              Cookie Refresh (every 3 days)

Memory System ── supports ── Deduplication
                              Per-user Cooldown
                              Interaction History
                              Weekly Reports
                              Daily Tweet Repetition Avoidance

Cost Tracking ── independent, monitors all LLM calls
Supervised Mode ── gates Reply Posting (approval required)
Provider Failover ── independent, activates on MiniMax downtime
```

## MVP Definition

The MVP must prove one thing: **the agent can find real gig posts and generate replies that a human would approve.** It does NOT need to post autonomously.

### MVP (Phase 1) -- Must Have

1. **Tweet search with query rotation** -- proves the agent can find gigs
2. **Tweet deduplication via memory** -- prevents embarrassing double-processing
3. **LLM-powered relevance scoring** -- proves filtering works
4. **Score threshold filtering** -- reduces noise to actionable leads
5. **Contextual reply generation** -- proves reply quality is human-grade
6. **Supervised reply posting** -- human approves every post
7. **Rate limiting** -- safety net even in supervised mode
8. **Cookie auth with manual refresh** -- gets Twikit working
9. **Basic error handling and logging** -- know when something breaks
10. **Cost tracking** -- prevent surprise bills

### Phase 2 -- Supervised Autonomy

11. **Cron scheduling (20-min scan loop)** -- hands-off operation
12. **Per-user cooldown enforcement** -- automated politeness
13. **Cookie auto-refresh** -- session resilience
14. **Scoring threshold tuning** -- optimize based on Phase 1 data

### Phase 3 -- Full Autonomy + Brand Building

15. **Switch to full autonomy mode** -- no more human approval
16. **Daily showcase tweets** -- build inbound credibility
17. **Weekly lead report** -- measure agent effectiveness
18. **Engagement tracking (reply-back detection)** -- conversion metrics
19. **Thread context awareness** -- better scoring accuracy
20. **Graceful Twikit failure handling** -- resilience

### Defer Indefinitely

- DM outreach (account safety risk)
- Discord/Telegram notifications (nice-to-have, not core)
- Web dashboard (ZeroClaw gateway suffices)
- Multi-account support (sockpuppeting risk)

## Feature Prioritization Matrix

| Feature | Impact on Gig Conversion | Implementation Effort | Account Safety Risk | Priority |
|---------|--------------------------|----------------------|---------------------|----------|
| Tweet search + query rotation | Critical | Low | Low | P0 |
| LLM relevance scoring | Critical | Medium | None | P0 |
| Contextual reply generation | Critical | Medium | Low | P0 |
| Supervised reply posting | Critical | Low | Very Low | P0 |
| Rate limiting | Low (safety) | Low | Prevents High | P0 |
| Tweet deduplication | Medium | Low | Low | P0 |
| Cookie auth management | Critical (enabler) | Medium | Low | P0 |
| Cost tracking | Low (safety) | Low | None | P0 |
| Per-user cooldown | Medium | Low | Prevents Medium | P1 |
| Cron scheduling | High (enables autonomy) | Low | Low | P1 |
| Category-aware scoring | Medium | Low | None | P1 |
| Configurable persona | Medium | Low | None | P1 |
| Daily showcase tweets | Medium (inbound leads) | Medium | Low | P2 |
| Weekly lead report | Low (visibility) | Low | None | P2 |
| Engagement tracking | High (measures success) | Medium | None | P2 |
| Thread context awareness | Medium | Medium | None | P2 |
| Scam/spam detection | Medium | Low | Prevents embarrassment | P1 |
| Twikit failure handling | Low (resilience) | Medium | None | P2 |
| Provider failover | Low (resilience) | Low (built-in) | None | P1 |

## Sources

- [Top 5 AI Agents for X (Twitter) in 2026](https://noimosai.com/en/blog/top-5-ai-agents-for-x-twitter-in-2026-revolutionizing-your-social-strategy)
- [The Ultimate Guide to AI Twitter Bots in 2026](https://skywork.ai/skypage/en/ai-twitter-bots-automation-autonomy/2029473528737636352)
- [Twitter/X Automation Rules in 2026](https://opentweet.io/blog/twitter-automation-rules-2026)
- [X (Twitter) AI Automation: Complete Guide 2026](https://www.mirra.my/en/blog/x-twitter-ai-automation-complete-guide-2026)
- [Is a Twitter Auto Reply Bot Right for You in 2025?](https://xautodm.com/blog/is-a-twitter-auto-reply-bot-right-for-you-in-2025)
- [Twitter Automation Tools: Complete Guide for 2026](https://www.tweetarchivist.com/twitter-automation-tools-guide-2025)
- [Twikit GitHub Repository](https://github.com/d60/twikit)
- [AI Twitter Bot 2026: Proven Guide to Boost Leads](https://vynta.ai/blog/ai-twitter-bot/)
- [Top 7 Twitter Prospecting Tools in 2026](https://coldiq.com/blog/twitter-prospecting-tools)
- [How to Monitor X/Twitter for Lead Generation 2025](https://ddevi.com/en/blog/how-to-monitor-twitter-for-lead-generation-complete-2025-guide)
