#!/usr/bin/env python3
"""Twikit post/reply wrapper -- posts tweets or replies with rate limiting.

Usage:
    python3 twitter_post.py --action reply --tweet-id 123456 --text "Great work!"
    python3 twitter_post.py --action tweet --text "Hello world"

Output (stdout): {"posted": true, "action": "...", "tweet_id": "..."}
Errors (stdout): {"error": true, "code": "...", "message": "...", "retryable": ...}
Debug/warnings go to stderr only.
"""

import argparse
import asyncio
import json
import os
import sys
import time

from common import (
    COOKIES_PATH,
    classify_error,
    log_action,
    output_error,
    output_success,
)
from rate_limiter import check_rate_limit


async def get_client():
    """Create and authenticate a Twikit client with cookie persistence."""
    from twikit import Client

    client = Client("en-US", enable_ui_metrics=True)

    if os.path.exists(COOKIES_PATH):
        client.load_cookies(COOKIES_PATH)
        print("Loaded existing cookies", file=sys.stderr)
    else:
        username = os.environ["TWITTER_USERNAME"]
        email = os.environ["TWITTER_EMAIL"]
        password = os.environ["TWITTER_PASSWORD"]
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
        )
        client.save_cookies(COOKIES_PATH)
        print("Logged in and saved cookies", file=sys.stderr)

    return client


async def post_tweet(action: str, text: str, tweet_id: str = None) -> dict:
    """Post a tweet or reply using Twikit."""
    client = await get_client()

    if action == "reply":
        if not tweet_id:
            raise ValueError("--tweet-id is required for reply action")
        result = await client.create_tweet(text=text, reply_to=tweet_id)
    else:
        result = await client.create_tweet(text=text)

    # Extract the posted tweet's ID from the response
    response_id = getattr(result, "id", None) or str(result)

    return {
        "posted": True,
        "action": action,
        "tweet_id": str(response_id),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Post a tweet or reply to Twitter."
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["reply", "tweet"],
        help="Action type: 'reply' or 'tweet'.",
    )
    parser.add_argument(
        "--tweet-id",
        default=None,
        help="Tweet ID to reply to (required for --action reply).",
    )
    parser.add_argument("--text", required=True, help="Text content to post.")
    args = parser.parse_args()

    # Check rate limit before posting
    rate_status = check_rate_limit()
    if not rate_status["allowed"]:
        log_action(
            action_type="twitter_post",
            success=False,
            error_code="RATE_LIMIT_EXCEEDED",
            details=f"remaining={rate_status['remaining']} reset_in={rate_status['reset_in_seconds']}s",
        )
        output_error(
            "RATE_LIMIT_EXCEEDED",
            f"Rate limit exceeded. {rate_status['remaining']} posts remaining. "
            f"Reset in {rate_status['reset_in_seconds']} seconds.",
            retryable=True,
        )

    start = time.time()
    try:
        result = asyncio.run(
            asyncio.wait_for(
                post_tweet(args.action, args.text, args.tweet_id),
                timeout=45,
            )
        )
        elapsed = time.time() - start
        log_action(
            action_type="twitter_post",
            success=True,
            details=f"action={args.action} tweet_id={result.get('tweet_id', '')} elapsed={elapsed:.1f}s",
        )
        output_success(result)

    except asyncio.TimeoutError:
        log_action(
            action_type="twitter_post",
            success=False,
            error_code="TIMEOUT",
            details=f"action={args.action} timed out after 45s",
        )
        output_error("TIMEOUT", "Post timed out after 45 seconds", retryable=True)

    except Exception as e:
        code, retryable = classify_error(e)
        log_action(
            action_type="twitter_post",
            success=False,
            error_code=code,
            details=f"action={args.action} error={str(e)[:200]}",
        )
        output_error(code, str(e)[:500], retryable=retryable)


if __name__ == "__main__":
    main()
