---
phase: 1
slug: foundation-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python bridge scripts) + manual ZeroClaw integration tests |
| **Config file** | None — Wave 0 must create pyproject.toml |
| **Quick run command** | `pytest tests/ -x --timeout=30` |
| **Full suite command** | `pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INFR-01 | integration | `zeroclaw skills list \| grep twitter-gig-hunter` | No — Wave 0 | ⬜ pending |
| 01-01-02 | 01 | 1 | INFR-02 | unit | `pytest tests/test_bridge_output.py -x` | No — Wave 0 | ⬜ pending |
| 01-02-01 | 02 | 1 | INFR-03 | integration | `zeroclaw doctor` + manual config review | No — manual | ⬜ pending |
| 01-02-02 | 02 | 1 | INFR-04 | unit | `pytest tests/test_ops_logging.py -x` | No — Wave 0 | ⬜ pending |
| 01-02-03 | 02 | 1 | INFR-05 | unit | `pytest tests/test_error_handling.py -x` | No — Wave 0 | ⬜ pending |
| 01-02-04 | 02 | 1 | INFR-06 | unit | `python3 -c "import toml; ..."` or manual | No — Wave 0 | ⬜ pending |
| 01-02-05 | 02 | 1 | INFR-07 | integration | `systemctl --user status zeroclaw` | No — manual | ⬜ pending |
| 01-02-06 | 02 | 1 | MEMO-01 | unit | `pytest tests/test_memory_schema.py -x` | No — Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures (temp SQLite DB, mock env vars)
- [ ] `tests/test_bridge_output.py` — validates JSON output contract for all scripts
- [ ] `tests/test_error_handling.py` — validates error JSON format and Twikit error classification
- [ ] `tests/test_ops_logging.py` — validates agent_actions table writes
- [ ] `tests/test_memory_schema.py` — validates scored_tweets table schema and queries
- [ ] `pyproject.toml` — test configuration
- [ ] Framework install: `pip install pytest pytest-timeout`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ZeroClaw config routes LLM to MiniMax | INFR-03 | Requires live MiniMax API key and ZeroClaw runtime | Run `zeroclaw doctor`, verify MiniMax endpoint in config |
| systemd service runs and stays up | INFR-07 | Requires deployment to Linux VPS | Run `systemctl --user status zeroclaw`, verify active |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
