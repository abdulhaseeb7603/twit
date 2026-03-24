# Roadmap: Twitter AI Lead Intelligence Agent

## Overview

This roadmap transforms 44 requirements into 6 phases that deliver the Lead Intelligence Agent incrementally. The first priority is standing up infrastructure and proving Twitter I/O works. Then the search-and-score pipeline becomes the core intelligence loop. Lead reporting (daily digests, weekly trends) delivers the primary user value -- actionable opportunity intelligence without requiring any posting. Reply generation and supervised posting layer on as optional engagement. Finally, autonomous scheduling, brand tweets, and deployment complete the system. The key insight: the agent's primary job is finding and reporting opportunities, not auto-replying. Phases 1-3 deliver that core value; Phases 4-6 add engagement capabilities.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Infrastructure** - ZeroClaw skill setup, Python bridge layer, memory schema, error handling, cost tracking, and VPS deployment scaffold
- [ ] **Phase 2: Search & Scoring Pipeline** - Twitter search via Twikit with query rotation, LLM-powered scoring and categorization, dedup, and noise filtering
- [ ] **Phase 3: Lead Intelligence & Reporting** - Daily lead digests, categorized summaries, high-priority flagging, weekly trend reports, and report persistence
- [ ] **Phase 4: Reply Engine** - Contextual reply generation with configurable persona, human-sounding output, and style controls
- [ ] **Phase 5: Supervised Posting & Safety** - Post replies to Twitter with human approval, rate limiting, cooldown enforcement, and interaction logging
- [ ] **Phase 6: Autonomous Operation & Brand Building** - Cron-driven scan loop, daily showcase tweets, cookie auto-refresh, and full hands-off operation

## Phase Details

### Phase 1: Foundation & Infrastructure
**Goal**: The agent runtime, Python bridge layer, memory store, and deployment target are operational -- a working skeleton that downstream phases build on
**Depends on**: Nothing (first phase)
**Requirements**: INFR-01, INFR-02, INFR-03, INFR-04, INFR-05, INFR-06, INFR-07, MEMO-01
**Success Criteria** (what must be TRUE):
  1. ZeroClaw skill loads successfully with SKILL.toml defining all tool registrations (search, score, reply_gen, post, report_gen)
  2. Python bridge scripts can be invoked by ZeroClaw as shell tools and return structured JSON to stdout, including structured error JSON on failure
  3. ZeroClaw config routes LLM calls to MiniMax (fast tier and reasoning tier) with cost limits ($5/day, $50/month) enforced
  4. All scored tweets persist in SQLite with scores, categories, and metadata queryable for later reporting
  5. The agent runs on the Linux VPS as a systemd service and surfaces Twikit failures (Cloudflare blocks, cookie expiry) in structured error logs rather than dying silently
**Plans:** 4 plans

Plans:
- [ ] 01-00-PLAN.md — Wave 0 pytest scaffold: pyproject.toml, conftest.py, and 4 test modules defining behavioral contracts
- [ ] 01-01-PLAN.md — ZeroClaw config.toml and SKILL.toml with MiniMax provider, model routing, cost limits, and 5 tool registrations
- [ ] 01-02-PLAN.md — Python bridge layer: common.py, rate_limiter.py, init_db.py (memory schema), and all 5 bridge scripts
- [ ] 01-03-PLAN.md — Integration verification: smoke tests, deployment script with secrets loading, systemd service, and human sign-off

### Phase 2: Search & Scoring Pipeline
**Goal**: The agent finds AI/ML opportunity tweets across all categories, scores and categorizes them, and stores results -- the core intelligence loop
**Depends on**: Phase 1
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06, SCOR-01, SCOR-02, SCOR-03, SCOR-04, SCOR-05, MEMO-03
**Success Criteria** (what must be TRUE):
  1. Agent searches Twitter and returns up to 20 tweets per run, rotating through 12+ query templates covering freelance gigs, remote jobs, consulting leads, and automation prospects
  2. Agent never processes the same tweet twice -- duplicates are caught via memory lookup before scoring
  3. Each tweet receives a structured score (0-100) with category classification (freelance_gig, contract_role, remote_job, consulting_lead, automation_prospect, vague_inquiry, or not_relevant) and only tweets above the configurable threshold (default 70) proceed
  4. Agent skips retweets, noise, and scam/spam tweets (crypto pitches, MLM, fake gigs) before or during scoring
  5. Agent enriches scoring with thread context (parent tweet) and credibility signals (follower count, bio, verified status)
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Lead Intelligence & Reporting
**Goal**: The user receives actionable daily intelligence about AI/ML opportunities found on Twitter, organized by category with high-priority flags, plus weekly trend analysis
**Depends on**: Phase 2
**Requirements**: LEAD-01, LEAD-02, LEAD-03, LEAD-04, LEAD-05, MEMO-04, CRON-03, CRON-05
**Success Criteria** (what must be TRUE):
  1. A daily digest is automatically generated summarizing all high-scoring opportunities from the last 24 hours, grouped by category (freelance, remote jobs, consulting, automation) with tweet links, scores, and one-line summaries
  2. Leads scoring 90 or above are flagged with a special high-priority indicator in the digest
  3. A weekly trend report is generated every Sunday showing opportunity volume by category, emerging patterns, and top leads of the week
  4. All reports are saved to memory and optionally output to a file the user can review outside ZeroClaw
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Reply Engine
**Goal**: The agent generates high-quality, human-sounding replies to opportunity tweets that reference specific content from the original post, with a configurable persona
**Depends on**: Phase 2
**Requirements**: RPLY-01, RPLY-02, RPLY-03, RPLY-04, RPLY-05, STYL-03
**Success Criteria** (what must be TRUE):
  1. Agent generates contextual replies using MiniMax M2.5 full model that reference something specific from the original tweet
  2. All generated replies stay under 280 characters with no hashtags or emoji spam and avoid generic template language ("I'd love to connect")
  3. The agent persona (skills, experience, tone, style) is configurable via prompt config without code changes, with separate persona settings for gig replies versus showcase tweets
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

### Phase 5: Supervised Posting & Safety
**Goal**: The agent can post replies to Twitter with mandatory human approval, hard rate limits, and full interaction logging -- proving the engagement loop works safely before autonomy
**Depends on**: Phase 4
**Requirements**: POST-01, POST-02, POST-03, POST-04, MEMO-02
**Success Criteria** (what must be TRUE):
  1. Agent posts replies to Twitter via Twikit with correct tweet_id targeting, but only after human approval through ZeroClaw gateway (supervised mode)
  2. A hard cap of 5 replies per hour is enforced in code (not just prompt), preventing any burst posting regardless of how many opportunities are found
  3. Every posted reply is logged to memory with timestamp, tweet_id, and target user, and this log is checked before replying to enforce dedup and interaction history
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

### Phase 6: Autonomous Operation & Brand Building
**Goal**: The agent runs hands-off on a 20-minute scan loop, posts daily showcase tweets for inbound credibility, and auto-refreshes its Twitter session -- fully autonomous lead intelligence
**Depends on**: Phase 3, Phase 5
**Requirements**: CRON-01, CRON-02, CRON-04, STYL-01, STYL-02
**Success Criteria** (what must be TRUE):
  1. Agent runs the full opportunity scan pipeline every 20 minutes via ZeroClaw cron without manual intervention
  2. Agent posts one original showcase/brand tweet daily at a configurable time, randomly selecting from a user-editable library of tweet format templates
  3. Agent refreshes Twikit cookies every 3 days via lightweight search to keep the session alive without manual re-authentication
**Plans**: TBD

Plans:
- [ ] 06-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6
Note: Phases 3 and 4 both depend on Phase 2 and could theoretically execute in parallel, but sequential execution is recommended for a solo developer.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Infrastructure | 0/4 | Planning complete | - |
| 2. Search & Scoring Pipeline | 0/2 | Not started | - |
| 3. Lead Intelligence & Reporting | 0/2 | Not started | - |
| 4. Reply Engine | 0/1 | Not started | - |
| 5. Supervised Posting & Safety | 0/1 | Not started | - |
| 6. Autonomous Operation & Brand Building | 0/1 | Not started | - |
