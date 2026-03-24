#!/usr/bin/env python3
"""MiniMax M2.5-highspeed tweet scoring -- classifies tweet relevance.

Usage:
    python3 tweet_scorer.py --tweet '{"text": "...", "username": "...", ...}'

Output (stdout): {"relevance_score": N, "category": "...", "reason": "...",
                   "should_reply": true/false, "opportunity_summary": "..."}
Errors (stdout): {"error": true, "code": "...", "message": "...", "retryable": ...}
Debug/warnings go to stderr only.
"""

import argparse
import json
import os
import sqlite3
import sys
import time

from common import (
    MEMORY_DB,
    call_minimax,
    classify_error,
    log_action,
    output_error,
    output_success,
)

VALID_CATEGORIES = {
    "freelance_gig",
    "contract_role",
    "remote_job",
    "consulting_lead",
    "automation_prospect",
    "vague_inquiry",
    "not_relevant",
}

SCORING_SYSTEM_PROMPT = """You are a tweet relevance scorer for an AI engineer seeking freelance and contract work.

Analyze the tweet and return ONLY valid JSON (no markdown, no backticks, no explanation):
{
  "relevance_score": <0-100 integer>,
  "category": "<one of: freelance_gig, contract_role, remote_job, consulting_lead, automation_prospect, vague_inquiry, not_relevant>",
  "reason": "<one sentence explaining the score>",
  "should_reply": <true or false>,
  "opportunity_summary": "<one-line summary of the opportunity>"
}

Scoring guide:
- 90-100: Direct freelance/contract opportunity mentioning AI/ML skills
- 70-89: Strong signal (hiring, looking for help) related to AI/ML
- 50-69: Tangential (general tech hiring, vague AI mentions)
- 20-49: Weak signal (tech discussion, no hiring intent)
- 0-19: Not relevant (spam, off-topic, memes)

Set should_reply=true only for scores >= 70."""


def store_scored_tweet(tweet: dict, score_data: dict, query: str = None):
    """Store a scored tweet in the scored_tweets table."""
    try:
        conn = sqlite3.connect(MEMORY_DB, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """INSERT OR REPLACE INTO scored_tweets
            (tweet_id, text, username, bio, follower_count, verified,
             score, category, reason, should_reply, opportunity_summary,
             found_at, query_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(tweet.get("id", "")),
                tweet.get("text", ""),
                tweet.get("username", "unknown"),
                tweet.get("bio", ""),
                tweet.get("follower_count", 0),
                int(bool(tweet.get("verified", False))),
                score_data.get("relevance_score", 0),
                score_data.get("category", "not_relevant"),
                score_data.get("reason", ""),
                int(bool(score_data.get("should_reply", False))),
                score_data.get("opportunity_summary", ""),
                time.time(),
                query,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: failed to store scored tweet: {e}", file=sys.stderr)


def parse_score_response(text: str) -> dict:
    """Parse and validate the LLM scoring response."""
    # Strip markdown code fences if present
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1]
    if clean.endswith("```"):
        clean = clean.rsplit("```", 1)[0]
    clean = clean.strip()

    data = json.loads(clean)

    # Validate and clamp score
    score = int(data.get("relevance_score", 0))
    score = max(0, min(100, score))

    # Validate category
    category = data.get("category", "not_relevant")
    if category not in VALID_CATEGORIES:
        category = "not_relevant"

    return {
        "relevance_score": score,
        "category": category,
        "reason": str(data.get("reason", "")),
        "should_reply": bool(data.get("should_reply", False)),
        "opportunity_summary": str(data.get("opportunity_summary", "")),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Score a tweet's relevance for AI gig opportunities."
    )
    parser.add_argument(
        "--tweet", required=True, help="JSON string of tweet data."
    )
    args = parser.parse_args()

    try:
        tweet = json.loads(args.tweet)
    except json.JSONDecodeError as e:
        output_error("INVALID_INPUT", f"Failed to parse tweet JSON: {e}")

    user_prompt = (
        f'Tweet: "{tweet.get("text", "")}"\n'
        f'Author: @{tweet.get("username", "unknown")} | '
        f'Bio: {tweet.get("bio", "N/A")}\n'
        f'Followers: {tweet.get("follower_count", 0)} | '
        f'Verified: {tweet.get("verified", False)}'
    )

    try:
        # Use MiniMax-M2.5-highspeed for fast bulk scoring
        # temperature=0.1 for deterministic scoring (NOT 0.0 -- MiniMax rejects 0.0)
        response = call_minimax(
            model="MiniMax-M2.5-highspeed",
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=256,
            system=SCORING_SYSTEM_PROMPT,
            temperature=0.1,
        )

        # Extract text from Anthropic-format response
        response_text = response["content"][0]["text"]
        score_data = parse_score_response(response_text)

        # Extract usage for logging
        usage = response.get("usage", {})
        tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        # MiniMax M2.5-highspeed pricing: $0.15/1M input, $0.60/1M output
        cost_usd = (
            usage.get("input_tokens", 0) * 0.15 / 1_000_000
            + usage.get("output_tokens", 0) * 0.60 / 1_000_000
        )

        # Store in scored_tweets table
        store_scored_tweet(tweet, score_data)

        log_action(
            action_type="tweet_scorer",
            success=True,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            details=f"score={score_data['relevance_score']} category={score_data['category']}",
        )
        output_success(score_data)

    except json.JSONDecodeError:
        log_action(
            action_type="tweet_scorer",
            success=False,
            error_code="PARSE_ERROR",
            details=f"Failed to parse LLM response for tweet by @{tweet.get('username', 'unknown')}",
        )
        output_error(
            "PARSE_ERROR",
            "Failed to parse scoring response as JSON",
            retryable=True,
        )

    except Exception as e:
        code, retryable = classify_error(e)
        log_action(
            action_type="tweet_scorer",
            success=False,
            error_code=code,
            details=f"error={str(e)[:200]}",
        )
        output_error(code, str(e)[:500], retryable=retryable)


if __name__ == "__main__":
    main()
