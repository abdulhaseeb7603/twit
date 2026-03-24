#!/usr/bin/env python3
"""Twikit search wrapper -- searches Twitter for tweets matching a query.

Usage:
    python3 twitter_search.py --query "hiring AI engineer" --count 20

Output (stdout): {"tweets": [...], "count": N, "query": "..."}
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


async def search_tweets(query: str, count: int = 20) -> dict:
    """Search Twitter and return structured tweet data."""
    client = await get_client()

    results = await client.search_tweet(query, product="Latest", count=count)

    tweets = []
    for tweet in results:
        # Filter out retweets
        if tweet.text and tweet.text.startswith("RT @"):
            continue

        tweet_data = {
            "id": tweet.id,
            "text": tweet.text,
            "username": tweet.user.screen_name if tweet.user else "unknown",
            "name": tweet.user.name if tweet.user else "unknown",
            "bio": tweet.user.description if tweet.user else "",
            "follower_count": tweet.user.followers_count if tweet.user else 0,
            "verified": bool(tweet.user.verified) if tweet.user else False,
            "created_at": str(tweet.created_at) if tweet.created_at else "",
        }
        tweets.append(tweet_data)

    return {
        "tweets": tweets,
        "count": len(tweets),
        "query": query,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search Twitter for tweets matching a query."
    )
    parser.add_argument("--query", required=True, help="Search query string.")
    parser.add_argument(
        "--count", type=int, default=20, help="Maximum tweets to return."
    )
    args = parser.parse_args()

    start = time.time()
    try:
        # 45-second timeout (leave 15s buffer for ZeroClaw's 60s limit)
        result = asyncio.run(
            asyncio.wait_for(
                search_tweets(args.query, args.count),
                timeout=45,
            )
        )
        elapsed = time.time() - start
        log_action(
            action_type="twitter_search",
            success=True,
            details=f"query={args.query} count={result['count']} elapsed={elapsed:.1f}s",
        )
        output_success(result)

    except asyncio.TimeoutError:
        log_action(
            action_type="twitter_search",
            success=False,
            error_code="TIMEOUT",
            details=f"query={args.query} timed out after 45s",
        )
        output_error("TIMEOUT", "Search timed out after 45 seconds", retryable=True)

    except Exception as e:
        code, retryable = classify_error(e)
        log_action(
            action_type="twitter_search",
            success=False,
            error_code=code,
            details=f"query={args.query} error={str(e)[:200]}",
        )
        output_error(code, str(e)[:500], retryable=retryable)


if __name__ == "__main__":
    main()
