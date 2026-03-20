# Stack Research

**Domain:** Autonomous Twitter AI Gig-Hunting Agent
**Researched:** 2026-03-20
**Confidence:** MEDIUM (core stack verified; some ZeroClaw config details have conflicting docs)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **ZeroClaw** | v0.5.1 | Agent runtime (scheduling, memory, provider routing, security) | Single ~3.4MB Rust binary, <5MB RAM, built-in cron/memory/cost-tracking, 28+ LLM providers, encrypted secrets. Released 2026-03-19 -- current stable. | HIGH |
| **Twikit** | 2.3.3 | Twitter search, post, reply (cookie-based, no API key) | Free, no Twitter API key needed, cookie-based auth with `cookies_file` parameter for session persistence. Only viable free option for Twitter automation in 2026. | HIGH |
| **MiniMax M2.5** | Current (Feb 2026 release) | Primary LLM for reply generation (hint:reasoning) | $0.30/1M input, $1.20/1M output -- 1/63rd the cost of Claude Opus 4.6. 200K context. Strong agentic/coding benchmarks. Anthropic-compatible API. | HIGH |
| **MiniMax M2.5-highspeed** | Current | Fast LLM for bulk tweet scoring (hint:fast) | Same model quality at ~100 tok/s (vs ~60 tok/s standard). Same pricing. Identical benchmarks -- purely a latency optimization for scoring 20+ tweets per run. | HIGH |
| **Python** | 3.10+ | Bridge scripts (Twikit + MiniMax API calls) | Twikit requires Python >=3.8. Target 3.10+ for modern syntax (match/case, union types). VPS Ubuntu 22.04+ ships 3.10. | HIGH |
| **SQLite** | Built into ZeroClaw | Memory backend (dedup, interaction history, vector search) | ZeroClaw's built-in memory uses SQLite + FTS5 (BM25) + vector cosine similarity (70/30 hybrid). Zero external deps. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| **httpx** | >=0.27 | HTTP client for MiniMax API calls from bridge scripts | Every bridge script that calls MiniMax directly. Twikit already depends on httpx[socks]. | HIGH |
| **beautifulsoup4** | (twikit dep) | HTML parsing | Transitive dependency of twikit -- do not install separately. | HIGH |
| **filetype** | (twikit dep) | File type detection for media uploads | Transitive dependency of twikit. | HIGH |
| **pyotp** | (twikit dep) | TOTP for 2FA-enabled Twitter accounts | Transitive dependency. Only relevant if Twitter account has 2FA. | MEDIUM |
| **lxml** | (twikit dep) | Fast XML/HTML parser | Transitive dependency of twikit. | HIGH |
| **Js2Py-3.13** | (twikit dep) | JavaScript to Python transpiler for Twitter's obfuscated metrics | Transitive dependency. Enables `enable_ui_metrics=True` which reduces suspension risk. | HIGH |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **ZeroClaw CLI** | Agent management, cron, skill install, service control | `zeroclaw agent`, `zeroclaw cron add`, `zeroclaw service install`, `zeroclaw doctor` |
| **ZeroClaw Gateway** | HTTP dashboard for monitoring (port 42617) | Built-in, shows agent activity + cost tracking |
| **pip** | Python package management | Use `pip install twikit==2.3.3 httpx` on VPS |
| **systemd** | Process management on VPS | ZeroClaw has built-in `zeroclaw service install` for systemd unit generation |
| **curl/jq** | Manual API testing during development | Test MiniMax endpoint and Twikit responses before wiring into skills |

---

## Installation

```bash
# ─── 1. ZeroClaw (Rust binary) ───
curl -fsSL https://raw.githubusercontent.com/zeroclaw-labs/zeroclaw/main/install.sh | bash
# Or build from source:
# git clone https://github.com/zeroclaw-labs/zeroclaw.git
# cd zeroclaw && cargo build --release --locked
# cargo install --path . --force --locked

# ─── 2. Onboard with MiniMax ───
zeroclaw onboard --api-key "$MINIMAX_API_KEY" --provider minimax --model "MiniMax-M2.5"

# ─── 3. Python bridge dependencies ───
pip install twikit==2.3.3 httpx --break-system-packages
# Note: twikit pulls in httpx[socks], beautifulsoup4, filetype, pyotp, lxml, webvtt-py, m3u8, Js2Py-3.13

# ─── 4. Verify ───
zeroclaw doctor
python3 -c "import twikit; print(twikit.__version__)"
```

---

## ZeroClaw Configuration Details

### Provider Setup for MiniMax

The architecture doc uses `custom:https://api.minimax.io/anthropic` as the provider string. Based on ZeroClaw's docs, there are two valid syntaxes for Anthropic-compatible custom endpoints:

**Option A (simple -- from architecture doc):**
```toml
default_provider = "custom:https://api.minimax.io/anthropic"
```

**Option B (explicit provider block -- from ZeroClaw docs):**
```toml
default_provider = "custom:minimax-anthropic"

[model_providers.minimax-anthropic]
name = "anthropic"
base_url = "https://api.minimax.io/anthropic/v1"
api_key = "your-minimax-api-key"
```

**Recommendation:** Start with Option A (matches the architecture doc and is simpler). If it doesn't work, fall back to Option B. The `custom:` prefix tells ZeroClaw to use the URL directly. **MEDIUM confidence** -- the exact syntax may vary between ZeroClaw minor versions; test during Phase 1.

### Model Routes

```toml
[[model_routes]]
hint = "reasoning"
provider = "custom:https://api.minimax.io/anthropic"
model = "MiniMax-M2.5"

[[model_routes]]
hint = "fast"
provider = "custom:https://api.minimax.io/anthropic"
model = "MiniMax-M2.5-highspeed"
```

**Key detail:** The `hint` field may need the `hint:` prefix (e.g., `hint = "hint:reasoning"`) based on some ZeroClaw docs. The architecture doc omits the prefix. Test both formats. **LOW confidence on exact syntax.**

### SKILL.toml Shell Tools

ZeroClaw's security policy blocks `&&`, `||`, and `;` in shell tool commands. Each tool must be a single command invocation. The architecture doc's SKILL.toml correctly uses `command = "python3"` with separate `args` arrays -- this is the right pattern.

**Important:** ZeroClaw runs a static security audit on skill installation that blocks symlinks, suspicious scripts, and unsafe patterns. Bridge scripts should be clean Python with no shell metacharacters.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| **Twitter access** | Twikit 2.3.3 | `twitter-api-client` (npm/Python) | Less maintained, smaller community. Keep as fallback if Twikit breaks. |
| **Twitter access** | Twikit 2.3.3 | Official Twitter API (v2) | Costs $100/month for Basic tier. Free tier is read-only, no posting. Defeats the cost target. |
| **Twitter access** | Twikit 2.3.3 | Playwright browser automation | 50-100x slower, 10x more RAM, harder to deploy on $5 VPS. Nuclear fallback only. |
| **LLM provider** | MiniMax M2.5 (direct) | MiniMax via OpenRouter | OpenRouter adds markup ($0.30->~$0.40 input). Use only as failover. |
| **LLM provider** | MiniMax M2.5 | Claude Haiku 3.5 | ~10x more expensive per token. No cost advantage for this use case. |
| **LLM provider** | MiniMax M2.5 | DeepSeek V3 | Comparable pricing but less stable API availability. MiniMax has native ZeroClaw support. |
| **Agent runtime** | ZeroClaw | LangGraph / CrewAI | Python-based, 100x more RAM, no built-in cron/memory/cost-tracking. Overkill for single-agent. |
| **Agent runtime** | ZeroClaw | OpenClaw | Heavier (~50MB), more features but more complexity. ZeroClaw is purpose-built for lightweight VPS deployment. |
| **Memory/DB** | ZeroClaw built-in SQLite | PostgreSQL + pgvector | External dependency, more RAM, more ops. SQLite is embedded and sufficient for single-agent workload. |
| **Embeddings** | OpenAI text-embedding-3-small | MiniMax embeddings | OpenAI's small model is $0.02/1M tokens and widely supported. MiniMax embedding pricing/availability less clear. |

---

## What NOT to Use

| Technology | Why Avoid |
|------------|-----------|
| **Twitter Official API (Basic/Pro)** | $100-5000/month. Completely breaks the $24/month cost target. Cookie-based Twikit is the only viable free path. |
| **Selenium/Playwright for Twitter** | Massive resource overhead (headless browser = 200-500MB RAM). Only consider if Twikit AND twitter-api-client both break. |
| **LangChain** | Unnecessary abstraction layer. ZeroClaw's skill/tool system already provides agent orchestration. Adding LangChain creates two competing control planes. |
| **OpenAI GPT-4o** | $2.50/1M input is 8x more than MiniMax M2.5. No benefit for tweet scoring/reply generation. |
| **Vector databases (Pinecone, Weaviate, Chroma)** | ZeroClaw has built-in SQLite vector search with 70/30 hybrid scoring. External vector DB is unnecessary complexity for <100K documents. |
| **Docker** (initially) | ZeroClaw is a single static binary. Docker adds overhead on a $5 VPS. Use systemd directly. Consider Docker only if you need reproducible environments later. |
| **puppeteer-stealth** | Deprecated as of Feb 2025. No longer bypasses current Cloudflare versions. If you need browser automation, use Nodriver or SeleniumBase UC Mode instead. |
| **MiniMax OpenAI-format endpoint** (`api.minimax.chat/v1`) | Causes "invalid role: developer" errors with M2.5. Must use the Anthropic-compatible endpoint (`api.minimax.io/anthropic`). |

---

## Version Compatibility Matrix

| Component | Min Version | Tested Version | Max Version | Notes |
|-----------|-------------|----------------|-------------|-------|
| ZeroClaw | v0.5.0 | v0.5.1 | v0.5.x | v0.5.1 adds model_switch tool and autonomous skill creation |
| Twikit | 2.3.0 | 2.3.3 | 2.3.3 (pin) | Pin exactly -- Twitter's internal API changes can break newer versions |
| Python | 3.8 | 3.10+ | 3.13 | Twikit requires >=3.8; target 3.10+ for modern features |
| httpx | 0.25 | 0.27+ | latest | Twikit depends on httpx[socks]; standalone httpx for bridge scripts |
| MiniMax M2.5 | N/A (API) | Current | Current | API model -- no local versioning. Monitor for deprecation notices. |
| Ubuntu (VPS) | 22.04 | 22.04 LTS | 24.04 LTS | Ships Python 3.10; systemd compatible |

### Pinning Strategy

- **Pin twikit exactly** (`twikit==2.3.3`): Twitter's internal API is a moving target. A twikit update could break cookie auth or search.
- **Pin ZeroClaw to minor** (`v0.5.x`): The config format and skill system are stable within minor versions.
- **Float httpx**: httpx is well-maintained with backward-compatible releases.
- **Don't pin MiniMax model**: It's a hosted API. Monitor the MiniMax changelog for model deprecations.

---

## Key Integration Points

### 1. ZeroClaw <-> MiniMax M2.5
- ZeroClaw's `custom:` provider sends requests to MiniMax's Anthropic-compatible endpoint
- Model routing (`hint:fast` / `hint:reasoning`) auto-selects M2.5-highspeed vs M2.5
- Failover to OpenRouter if MiniMax API is unreachable
- Cost tracking enforces $5/day and $50/month limits

### 2. ZeroClaw <-> Python Bridge Scripts
- SKILL.toml defines shell tools that invoke `python3 <script> --args`
- ZeroClaw passes arguments via template replacement in the `args` array
- Scripts return JSON to stdout; ZeroClaw parses the output
- Security policy: no `&&`, `||`, `;` in commands; workspace-only file access

### 3. Python Bridge <-> Twikit
- Bridge scripts import twikit, load cookies from `cookies.json`
- `Client.login(cookies_file="cookies.json")` handles auth + session persistence
- `enable_ui_metrics=True` (default in 2.3.3) reduces suspension risk by sending obfuscated metrics
- Rate limiting enforced in `rate_limiter.py` (5 replies/hour, 24h per-user cooldown)

### 4. Python Bridge <-> MiniMax API (Direct)
- Bridge scripts call MiniMax's Anthropic-compatible endpoint directly via httpx
- This is separate from ZeroClaw's provider -- bridge scripts use the same API key but make independent calls
- Scoring uses M2.5-highspeed; reply generation uses M2.5 full
- Structured JSON output parsing with fallback for malformed responses

---

## Cost Summary

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| VPS (Hetzner CX22) | ~$5.00 | 2 vCPU, 4GB RAM, 40GB SSD |
| MiniMax M2.5 tokens | ~$18.00 | ~1M input + 260K output per day at 72 runs/day |
| OpenAI embeddings | ~$0.60 | text-embedding-3-small for memory vectors |
| **Total** | **~$24/month** | Within $50/month budget with margin |

---

## Sources

- [ZeroClaw GitHub](https://github.com/zeroclaw-labs/zeroclaw) - v0.5.1 release notes, config reference
- [ZeroClaw Provider Configuration (DeepWiki)](https://deepwiki.com/zeroclaw-labs/zeroclaw/3.3-provider-configuration) - Custom provider syntax, model routes
- [ZeroClaw Skills System (DeepWiki)](https://deepwiki.com/zeroclaw-labs/zeroclaw/11-tools-and-skills-system) - SKILL.toml format, security policy
- [ZeroClaw Creating Skills (DeepWiki)](https://deepwiki.com/zeroclaw-labs/zeroclaw/11.6-creating-and-installing-skills) - Shell tool configuration
- [ZeroClaw Config Reference](https://github.com/zeroclaw-labs/zeroclaw/blob/master/docs/reference/api/config-reference.md) - Full config.toml spec
- [Twikit PyPI](https://pypi.org/project/twikit/) - v2.3.3, dependencies, Python requirement
- [Twikit GitHub](https://github.com/d60/twikit) - Cookie auth, session management
- [Twikit Documentation](https://twikit.readthedocs.io/en/latest/twikit.html) - cookies_file parameter, enable_ui_metrics
- [MiniMax M2.5 Pricing](https://platform.minimax.io/docs/pricing/overview) - $0.30/1M input, $1.20/1M output
- [MiniMax M2.5 on OpenRouter](https://openrouter.ai/minimax/minimax-m2.5) - Pricing comparison, highspeed variant
- [MiniMax M2.5 Models Page](https://www.minimax.io/models/text) - Model specs, API endpoint
- [MiniMax M2.5 Analysis (Artificial Analysis)](https://artificialanalysis.ai/models/minimax-m2-5) - Performance benchmarks, throughput
- [ZeroClaw + MiniMax Setup Guide (BitDoze)](https://www.bitdoze.com/zeroclaw-setup-guide/) - Integration walkthrough

---

## Open Questions (Need Phase-Specific Research)

1. **ZeroClaw model_routes hint syntax**: Does the hint field use `"reasoning"` or `"hint:reasoning"`? Conflicting docs. Must test during Phase 1 setup.
2. **ZeroClaw custom provider format**: Simple `custom:URL` vs explicit `[model_providers]` block -- which works for MiniMax's Anthropic endpoint? Test both.
3. **Twikit Cloudflare stability**: Reports of intermittent Cloudflare blocks on Twitter. No twikit-specific data found. Monitor GitHub issues. Have `twitter-api-client` ready as fallback.
4. **MiniMax M2.5-highspeed model identifier**: Architecture doc uses `"MiniMax-M2.5-highspeed"` but official docs may use a different string. Verify against MiniMax API docs during setup.
5. **Embedding provider**: Architecture doc uses OpenAI `text-embedding-3-small`. Could MiniMax or a local model (e.g., via Ollama) reduce costs further? Low priority -- embeddings are ~$0.60/month.
