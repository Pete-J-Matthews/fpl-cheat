#!/usr/bin/env python3
"""
Jersey Refresher

Downloads club shirts from the FPL CDN into the assets bucket named by AWS_S3_BUCKET_NAME,
keyed as jerseys/{SHORT}.png and jerseys/{SHORT}_GK.png. The bucket set was originally built
by hand, so it drifts a season out of date; this replaces every shirt and prunes clubs that
have left the league.

Runs from a laptop — the bucket is reachable over HTTPS, unlike the private database.

Usage:
    python scripts/update_jerseys.py --dry-run    # Report the uploads and prunes, write nothing
    python scripts/update_jerseys.py              # Apply
"""

import argparse
import logging
import os
import sys
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
SHIRT_URL = "https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_{code}{gk}-110.png"
JERSEY_PREFIX = "jerseys/"

# An identifiable client is less likely to be blocked than an anonymous one.
USER_AGENT = os.getenv(
    "FPL_USER_AGENT", "fpl-cheat/1.0 (personal FPL comparison app; contact via repo)"
)

PREMIER_LEAGUE_CLUBS = 20  # The guard standing between a bad response and a prune
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MIN_PNG_BYTES = 1024  # Real shirts are 7-12KB; anything smaller is an error page


def _bucket() -> str:
    """The asset bucket to write to.

    AWS_ENDPOINT_URL is checked too: without it boto3 silently targets real AWS S3 and
    authenticates from ~/.aws/credentials, so a run would go to the wrong account
    entirely rather than fail.
    """
    missing = [
        v for v in ("AWS_S3_BUCKET_NAME", "AWS_ENDPOINT_URL") if not os.getenv(v)
    ]
    if missing:
        raise ValueError(f"Not set: {', '.join(missing)}")
    return os.environ["AWS_S3_BUCKET_NAME"]


def _client():
    """S3 client for the assets bucket.

    Region and credentials come from boto3's own env resolution (AWS_DEFAULT_REGION,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY), so they never reach a traceback here.
    """
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        config=Config(
            signature_version="s3v4",
            connect_timeout=3,
            read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def _get(url: str) -> requests.Response | None:
    """GET with retries. Returns None once the attempts are spent."""
    for attempt in range(MAX_RETRIES):
        if attempt:
            time.sleep(2**attempt)
        try:
            response = requests.get(
                url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}
            )
        except requests.RequestException as exc:
            logger.error(f"{url} attempt {attempt + 1} failed: {exc}")
            continue
        if response.status_code != 200:
            logger.error(f"{url} returned HTTP {response.status_code}")
            continue
        return response
    return None


def shirt_url(code: int, keeper: bool) -> str:
    """CDN URL for a club's outfield or keeper shirt."""
    return SHIRT_URL.format(code=code, gk="_1" if keeper else "")


def jersey_key(short: str, keeper: bool) -> str:
    """Bucket key for a club's outfield or keeper shirt."""
    return f"{JERSEY_PREFIX}{short.upper()}{'_GK' if keeper else ''}.png"


def parse_clubs(bootstrap: dict | None) -> list[dict]:
    """Extract clubs from bootstrap, skipping invalid rows."""
    clubs = []
    for team in (bootstrap or {}).get("teams", []):
        short = team.get("short_name")
        code = team.get("code")
        if not isinstance(short, str) or not short.strip():
            logger.warning(f"Bad short_name {short!r}, skipping")
            continue
        if not isinstance(code, int) or isinstance(code, bool):
            logger.warning(f"Club {short}: bad code {code!r}, skipping")
            continue
        clubs.append({"short": short.strip().upper(), "code": code})
    return clubs


def is_png(body: bytes) -> bool:
    """Whether a response body is a real PNG rather than an error page served as 200."""
    return len(body) >= MIN_PNG_BYTES and body.startswith(PNG_MAGIC)


def download_shirts(clubs: list[dict]) -> tuple[dict[str, bytes], list[str]]:
    """Download both shirts for every club. Returns (key -> png, failed keys)."""
    shirts: dict[str, bytes] = {}
    failed: list[str] = []
    for club in clubs:
        for keeper in (False, True):
            key = jersey_key(club["short"], keeper)
            response = _get(shirt_url(club["code"], keeper))
            if response is None:
                logger.error(f"{key}: download failed")
                failed.append(key)
                continue
            if not is_png(response.content):
                logger.error(f"{key}: not a PNG ({len(response.content)} bytes)")
                failed.append(key)
                continue
            shirts[key] = response.content
            logger.info(f"{key}: {len(response.content):,} bytes")
    return shirts, failed


def list_jerseys(client, bucket: str) -> list[str]:
    """Every key under the jerseys/ prefix. Anything outside it is not ours to touch."""
    keys = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=JERSEY_PREFIX):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def main():
    """Refresh every club shirt in the assets bucket from the FPL CDN."""
    parser = argparse.ArgumentParser(
        description="Refresh club jerseys in the assets bucket from the FPL CDN"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the uploads and prunes without writing to the bucket",
    )
    args = parser.parse_args()

    try:
        bucket = _bucket()
        response = _get(BOOTSTRAP_URL)
        if response is None:
            raise RuntimeError("Could not fetch bootstrap-static")
        clubs = parse_clubs(response.json())

        # Auto-prune deletes live objects, so refuse to act on a payload that is not a full league.
        if len(clubs) != PREMIER_LEAGUE_CLUBS:
            raise RuntimeError(
                f"Got {len(clubs)} clubs, expected {PREMIER_LEAGUE_CLUBS}. "
                "Refusing to upload or prune from a partial bootstrap."
            )
        logger.info(f"{len(clubs)} clubs: {', '.join(c['short'] for c in clubs)}")

        shirts, failed = download_shirts(clubs)
        logger.info(f"Downloaded {len(shirts)} shirts, {len(failed)} failed")

        client = _client()
        stale = [k for k in list_jerseys(client, bucket) if k not in shirts]

        if args.dry_run:
            logger.info(f"DRY RUN: would upload {len(shirts)} shirts to {bucket}")
            logger.info(
                f"DRY RUN: would prune {len(stale)} stale keys: {sorted(stale)}"
                if stale and not failed
                else f"DRY RUN: would prune nothing ({len(stale)} stale keys found)"
            )
            return

        for key, body in shirts.items():
            client.put_object(
                Bucket=bucket, Key=key, Body=body, ContentType="image/png"
            )
        logger.info(f"Uploaded {len(shirts)} shirts to {bucket}")

        # A partial run cannot tell a departed club from a shirt we simply failed to fetch.
        if failed:
            logger.warning(
                f"{len(failed)} shirts failed, so nothing was pruned. "
                f"Stale keys left in place: {sorted(stale)}"
            )
            sys.exit(1)

        if stale:
            client.delete_objects(
                Bucket=bucket, Delete={"Objects": [{"Key": k} for k in stale]}
            )
            logger.info(f"Pruned {len(stale)} stale keys: {sorted(stale)}")
        else:
            logger.info("No stale keys to prune")

        logger.info("Jersey refresh completed successfully")

    except KeyboardInterrupt:
        logger.info("Interrupted.")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
