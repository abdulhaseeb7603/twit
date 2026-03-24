# Requirements: Twitter AI Gig Hunter & Lead Intelligence Agent

**Defined:** 2026-03-20
**Core Value:** Continuously scan Twitter for AI/ML opportunities of all types -- freelance gigs, remote jobs, consulting leads, and automation prospects -- score and categorize them, deliver actionable intelligence via daily reports, and optionally auto-reply to high-value gig posts, all without getting the personal account suspended.

## v1 Requirements

### Search & Filtering

- [ ] **SRCH-01**: Agent searches Twitter via Twikit using keyword queries and returns up to 20 tweets per run
- [ ] **SRCH-02**: Agent rotates through 12+ query templates covering freelance gigs, remote AI/ML jobs, consulting opportunities, and automation prospects
- [ ] **SRCH-03**: Agent deduplicates tweets via memory -- never processes the same tweet twice
- [ ] **SRCH-04**: Agent filters out retweets and obvious noise before scoring
- [ ] **SRCH-05**: Agent fetches parent tweet for thread context when a tweet is part of a conversation
- [ ] **SRCH-06**: Agent incorporates follower count, bio, and verified status as credibility signals in scoring

### Scoring & Classification

- [ ] **SCOR-01**: Agent scores each tweet 0-100 for relevance using MiniMax M2.5-highspeed (fast tier)
- [ ] **SCOR-02**: Scoring returns structured JSON: relevance_score, category, reason, should_reply, opportunity_summary
- [ ] **SCOR-03**: Agent categorizes tweets into: freelance_gig, contract_role, remote_job, consulting_lead, automation_prospect, vague_inquiry, or not_relevant
- [ ] **SCOR-04**: Agent filters tweets at configurable threshold (default 70) -- only high-scoring tweets appear in reports or get replies
- [ ] **SCOR-05**: Agent detects and skips scam/spam tweets (crypto pitches, MLM, fake gigs)

### Lead Intelligence & Reporting

- [ ] **LEAD-01**: Agent generates a daily lead digest -- categorized summary of all high-scoring opportunities found in the last 24 hours
- [ ] **LEAD-02**: Daily digest groups leads by category (freelance, remote jobs, consulting, automation) with tweet links, scores, and one-line summaries
- [ ] **LEAD-03**: Agent flags high-priority leads (score >= 90) with a special indicator in the digest
- [ ] **LEAD-04**: Agent generates weekly trend report -- opportunity volume by category, emerging patterns, top leads of the week
- [ ] **LEAD-05**: Reports are saved to memory and optionally output to a file for easy review

### Reply Generation

- [ ] **RPLY-01**: Agent generates contextual replies using MiniMax M2.5 full model (reasoning tier)
- [ ] **RPLY-02**: Replies reference something specific from the original tweet to show it was read
- [ ] **RPLY-03**: Replies stay under 280 characters with no hashtags or emoji spam
- [ ] **RPLY-04**: Agent persona (skills, experience, style) is configurable via prompt without code changes
- [ ] **RPLY-05**: Replies sound human -- no "I'd love to connect" or generic template language

### Posting & Safety

- [ ] **POST-01**: Agent posts replies to Twitter via Twikit with proper tweet_id targeting
- [ ] **POST-02**: Agent enforces 5 replies/hour hard cap in code (not just prompt)
- [ ] **POST-03**: Agent runs in supervised mode initially -- human approves every post via ZeroClaw gateway
- [ ] **POST-04**: Agent logs all posted replies to memory with timestamp, tweet_id, and user

### Scheduling & Automation

- [ ] **CRON-01**: Agent runs opportunity scan pipeline every 20 minutes via ZeroClaw cron
- [ ] **CRON-02**: Agent posts one original showcase/brand tweet daily at configurable time
- [ ] **CRON-03**: Agent generates and saves daily lead digest automatically
- [ ] **CRON-04**: Agent refreshes Twikit cookies every 3 days via lightweight search to keep session alive
- [ ] **CRON-05**: Agent generates weekly trend report every Sunday

### Content & Style

- [ ] **STYL-01**: Tweet format library -- a config file of viral/effective tweet format templates the agent randomly picks from for daily showcase tweets
- [ ] **STYL-02**: User can add/remove/edit tweet format templates without code changes
- [ ] **STYL-03**: Agent persona (skills, tone, style) configurable via prompt for gig replies separately from showcase tweets

### Infrastructure

- [ ] **INFR-01**: ZeroClaw skill defined in SKILL.toml with all tools (search, score, reply_gen, post, report_gen)
- [x] **INFR-02**: Python bridge scripts handle Twikit and MiniMax API calls independently of ZeroClaw's provider
- [ ] **INFR-03**: ZeroClaw config includes MiniMax provider, model routing (fast/reasoning), and cost limits
- [x] **INFR-04**: All actions logged with structured error handling -- failures surface clearly
- [x] **INFR-05**: Agent detects Twikit failures (Cloudflare blocks, cookie expiry) and logs/alerts instead of silently dying
- [ ] **INFR-06**: Cost tracking enforces $5/day and $50/month spend limits
- [ ] **INFR-07**: Agent deploys to Linux VPS as systemd service via ZeroClaw

### Memory & State

- [x] **MEMO-01**: Agent stores all scored tweets in memory (SQLite + vector) with scores, categories, and metadata
- [ ] **MEMO-02**: Agent stores all sent replies in memory with timestamps for cooldown/reporting
- [ ] **MEMO-03**: Agent checks memory before replying to enforce dedup and interaction history
- [ ] **MEMO-04**: Memory supports queries for daily digest and weekly report generation

## v2 Requirements

### Enhanced Safety

- **SAFE-01**: Per-user 24h cooldown enforced in code (currently prompt-only)
- **SAFE-02**: Provider failover from MiniMax to OpenRouter on API downtime

### Engagement & Conversion

- **ENGM-01**: Agent tracks reply-backs (when opportunity posters respond to agent's replies)
- **ENGM-02**: Agent tracks conversion funnel: tweets found -> scored -> replied -> response received

### Advanced Features

- **ADVN-01**: Discord/Telegram notifications for high-value leads (score >=90)
- **ADVN-02**: DM follow-up capability for warm leads (manual trigger only)
- **ADVN-03**: A/B testing of reply styles to optimize response rate
- **ADVN-04**: Lead export to CSV/JSON for CRM integration

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated DM outreach | #1 spam signal on Twitter, extremely high suspension risk on personal account |
| Auto-follow/unfollow | Twitter detects mass follow patterns, triggers immediate suspension |
| Auto-like tweets | Zero conversion value, Twitter detects automated liking |
| Multi-account support | Sockpuppeting risk, Twitter links and bans all accounts |
| Web dashboard / mobile app | ZeroClaw gateway suffices, massive scope creep |
| Hashtag stuffing | Screams "bot", Twitter penalizes in reply visibility |
| Template/generic replies | Violates core value of human-sounding engagement |
| Auto-reply to all opportunity types | User wants to review leads first, only auto-reply to select gig posts |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SRCH-01 | Phase 2 | Pending |
| SRCH-02 | Phase 2 | Pending |
| SRCH-03 | Phase 2 | Pending |
| SRCH-04 | Phase 2 | Pending |
| SRCH-05 | Phase 2 | Pending |
| SRCH-06 | Phase 2 | Pending |
| SCOR-01 | Phase 2 | Pending |
| SCOR-02 | Phase 2 | Pending |
| SCOR-03 | Phase 2 | Pending |
| SCOR-04 | Phase 2 | Pending |
| SCOR-05 | Phase 2 | Pending |
| LEAD-01 | Phase 3 | Pending |
| LEAD-02 | Phase 3 | Pending |
| LEAD-03 | Phase 3 | Pending |
| LEAD-04 | Phase 3 | Pending |
| LEAD-05 | Phase 3 | Pending |
| RPLY-01 | Phase 4 | Pending |
| RPLY-02 | Phase 4 | Pending |
| RPLY-03 | Phase 4 | Pending |
| RPLY-04 | Phase 4 | Pending |
| RPLY-05 | Phase 4 | Pending |
| POST-01 | Phase 5 | Pending |
| POST-02 | Phase 5 | Pending |
| POST-03 | Phase 5 | Pending |
| POST-04 | Phase 5 | Pending |
| CRON-01 | Phase 6 | Pending |
| CRON-02 | Phase 6 | Pending |
| CRON-03 | Phase 3 | Pending |
| CRON-04 | Phase 6 | Pending |
| CRON-05 | Phase 3 | Pending |
| STYL-01 | Phase 6 | Pending |
| STYL-02 | Phase 6 | Pending |
| STYL-03 | Phase 4 | Pending |
| INFR-01 | Phase 1 | Pending |
| INFR-02 | Phase 1 | Complete |
| INFR-03 | Phase 1 | Pending |
| INFR-04 | Phase 1 | Complete |
| INFR-05 | Phase 1 | Complete |
| INFR-06 | Phase 1 | Pending |
| INFR-07 | Phase 1 | Pending |
| MEMO-01 | Phase 1 | Complete |
| MEMO-02 | Phase 5 | Pending |
| MEMO-03 | Phase 2 | Pending |
| MEMO-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 44 total
- Mapped to phases: 44
- Unmapped: 0

---
*Requirements defined: 2026-03-20*
*Last updated: 2026-03-20 after roadmap revision for lead intelligence scope*
