#!/usr/bin/env python3
"""MiniMax M2.5 reply drafting -- generates contextual replies to gig tweets.

Usage:
    python3 reply_generator.py --tweet '{"text":"...","username":"..."}' \
        --score-data '{"relevance_score":85,"category":"freelance_gig",...}'

Output (stdout): {"reply_text": "...", "char_count": N, "references_original": true/false}
Errors (stdout): {"error": true, "code": "...", "message": "...", "retryable": ...}
Debug/warnings go to stderr only.
"""

import argparse
import json
import os
import sys

from common import (
    SCRIPTS_DIR,
    call_minimax,
    classify_error,
    log_action,
    output_error,
    output_success,
)

DEFAULT_PERSONA = (
    "AI engineer with 4+ years shipping production ML systems. "
    "Skills: Python, LLMs (GPT/Claude/Llama), RAG pipelines, fine-tuning, "
    "vector databases, MLOps, agent frameworks, FastAPI, Docker, AWS/GCP."
)

DEFAULT_SYSTEM_PROMPT = """You are a skilled AI engineer replying to a Twitter post about a gig opportunity.

PERSONA: {persona}

RULES:
- Max 280 characters (hard Twitter limit)
- Sound human and genuine -- like a real person, not a chatbot
- Be specific about what you can bring to their project
- NO hashtags, NO emoji spam, NO "I'd love to connect"
- NO generic phrases like "great opportunity" or "very interested"
- Reference something specific from their tweet to show you read it
- End with a soft call-to-action (DM, link, etc.)

Return ONLY the reply text. No quotes, no explanation, no JSON wrapping."""


def load_persona() -> str:
    """Load persona from persona.json if it exists, else use default."""
    persona_path = os.path.join(SCRIPTS_DIR, "persona.json")
    if os.path.exists(persona_path):
        try:
            with open(persona_path) as f:
                data = json.load(f)
            return data.get("persona", DEFAULT_PERSONA)
        except Exception as e:
            print(f"Warning: failed to load persona.json: {e}", file=sys.stderr)
    return DEFAULT_PERSONA


def main():
    parser = argparse.ArgumentParser(
        description="Generate a contextual reply to a high-scoring gig tweet."
    )
    parser.add_argument(
        "--tweet", required=True, help="JSON string of tweet data."
    )
    parser.add_argument(
        "--score-data", required=True, help="JSON string of scoring output."
    )
    args = parser.parse_args()

    try:
        tweet = json.loads(args.tweet)
    except json.JSONDecodeError as e:
        output_error("INVALID_INPUT", f"Failed to parse tweet JSON: {e}")

    try:
        score_data = json.loads(args.score_data)
    except json.JSONDecodeError as e:
        output_error("INVALID_INPUT", f"Failed to parse score-data JSON: {e}")

    persona = load_persona()
    system_prompt = DEFAULT_SYSTEM_PROMPT.format(persona=persona)

    user_prompt = (
        f'Tweet from @{tweet.get("username", "unknown")}:\n'
        f'"{tweet.get("text", "")}"\n\n'
        f'Classification: {score_data.get("category", "unknown")}\n'
        f'Score: {score_data.get("relevance_score", 0)}/100\n'
        f'Reason: {score_data.get("reason", "")}\n\n'
        f"Write a reply (max 280 chars)."
    )

    try:
        response = call_minimax(
            model="MiniMax-M2.5",
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=200,
            system=system_prompt,
            temperature=0.7,
        )

        # Extract text from Anthropic-format response
        reply_text = response["content"][0]["text"].strip().strip('"')

        # Enforce 280-character Twitter limit
        if len(reply_text) > 280:
            reply_text = reply_text[:277] + "..."

        # Check if the reply references something from the original tweet
        tweet_text_lower = tweet.get("text", "").lower()
        reply_lower = reply_text.lower()
        # Simple heuristic: check if any significant word from tweet appears in reply
        tweet_words = {
            w for w in tweet_text_lower.split() if len(w) > 4
        }
        references_original = any(w in reply_lower for w in tweet_words)

        # Extract usage for logging
        usage = response.get("usage", {})
        tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        # MiniMax M2.5 pricing: $0.30/1M input, $1.20/1M output
        cost_usd = (
            usage.get("input_tokens", 0) * 0.30 / 1_000_000
            + usage.get("output_tokens", 0) * 1.20 / 1_000_000
        )

        result = {
            "reply_text": reply_text,
            "char_count": len(reply_text),
            "references_original": references_original,
        }

        log_action(
            action_type="reply_generator",
            success=True,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            details=f"chars={len(reply_text)} refs_original={references_original}",
        )
        output_success(result)

    except Exception as e:
        code, retryable = classify_error(e)
        log_action(
            action_type="reply_generator",
            success=False,
            error_code=code,
            details=f"error={str(e)[:200]}",
        )
        output_error(code, str(e)[:500], retryable=retryable)


if __name__ == "__main__":
    main()
