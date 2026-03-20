# Twitter AI Gig Hunter & Lead Intelligence Agent

## What This Is

An autonomous AI agent that runs on ZeroClaw's Rust-based agent runtime, continuously scans Twitter/X for AI/ML opportunities — freelance gigs, remote jobs, consulting leads, and automation prospects — via Twikit (cookie-based, no API key), scores and categorizes them with MiniMax M2.5, delivers daily intelligence reports, and optionally auto-replies to high-value gig posts. All from a single ~16MB binary on a $5 VPS.

## Core Value

The agent must continuously surface actionable AI/ML opportunities from Twitter across all categories (freelance, jobs, consulting, automation), deliver categorized daily digests so the user can act on the best leads, and optionally engage with high-value posts — without getting the personal account suspended.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Twitter search via Twikit with query rotation and dedup
- [ ] Tweet scoring via MiniMax M2.5-highspeed with structured JSON output
- [ ] Reply generation via MiniMax M2.5 full model with configurable persona
- [ ] Tweet posting via Twikit with rate limiting and cooldowns
- [ ] ZeroClaw skill definition (SKILL.toml + Python bridge scripts)
- [ ] ZeroClaw configuration (MiniMax provider, model routing, failover, cost tracking)
- [ ] Memory integration (SQLite + vector search for dedup and interaction history)
- [ ] Cron scheduling (20-min scan loop, daily showcase tweet, weekly report)
- [ ] Safety controls (5 replies/hour, 24h per-user cooldown, spend limits)
- [ ] Supervised mode for initial human approval of all posts
- [ ] Cookie refresh mechanism for Twikit session keep-alive
- [ ] Deployment to Linux VPS as systemd service

### Out of Scope

- Discord/Telegram notifications — defer to Phase 3+, not core to gig hunting
- DM outreach — risky for account safety, revisit after trust is established
- OAuth login for Twitter — using cookie-based auth via Twikit
- Mobile app or web dashboard — agent is headless, monitored via ZeroClaw gateway
- Multi-account support — single personal Twitter account only

## Context

- **Development approach:** Building locally on Windows, deploying to Linux VPS
- **Twitter account:** Using personal account — reply quality and rate limiting are critical to avoid suspension
- **Agent persona:** Skills profile will be kept flexible/configurable; user will fine-tune prompts after initial build
- **Architecture doc:** Full v2 architecture defined in `TWITTER_GIG_AGENT_ARCHITECTURE_V2.md` — covers stack, pipeline, config, deployment, and cost estimates
- **Infra ready:** VPS is running and MiniMax API key is available
- **Cost target:** ~$0.79/day (~$24/month) including VPS, MiniMax tokens, and embeddings

## Constraints

- **Agent runtime:** ZeroClaw v0.5.x — must use its skill/tool system, cron, memory, and provider subsystem
- **Twitter library:** Twikit v2.3.3 — cookie-based, no official API key; inherent fragility risk
- **LLM provider:** MiniMax M2.5 via direct API (user's token plan) — Anthropic-compatible endpoint at `api.minimax.io/anthropic`
- **Rate limits:** Max 5 replies/hour, 24h cooldown per user, 20 tweets/day cap
- **Budget:** $5/day daily limit, $50/month monthly limit enforced by ZeroClaw cost tracking
- **Security:** Supervised autonomy initially; workspace-only execution; encrypted secrets

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| MiniMax M2.5 as primary LLM | User has token plan, $0.30/1M input is cost-effective, ZeroClaw has native support | — Pending |
| Twikit over official Twitter API | Free, no API key needed, supports search + post + reply | — Pending |
| Two-tier model routing (fast/reasoning) | Scoring needs speed (20+ tweets), drafting needs quality (2-5 replies) | — Pending |
| Personal Twitter account | No dedicated account; makes safety controls higher priority | — Pending |
| Configurable persona prompts | User will tune agent personality/skills after MVP works | — Pending |
| OpenRouter as failover only | Direct MiniMax API is cheaper; OpenRouter adds markup | — Pending |

---
*Last updated: 2026-03-20 after initialization*
