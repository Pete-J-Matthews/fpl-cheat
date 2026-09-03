"""S3-backed static assets (favicon, club jerseys). Bucket coords come from AWS_* env vars."""

import base64
import logging
import os

import streamlit as st

logger = logging.getLogger(__name__)

FAVICON_KEY = "favicon.svg"
JERSEY_KEY = "jerseys/{short}.png"
JERSEY_GK_KEY = "jerseys/{short}_GK.png"


class AssetUnavailable(RuntimeError):
    """The asset could not be fetched from the bucket."""


def _bucket() -> str | None:
    return os.getenv("AWS_S3_BUCKET_NAME") or None


@st.cache_resource(show_spinner=False)
def _client():
    """Shared S3 client, or None when the bucket isn't configured.

    Endpoint, region and credentials come from boto3's own env resolution, so a missing
    one surfaces as a failed get_object and degrades to a placeholder like any other
    fetch failure.
    """
    if not _bucket():
        logger.warning("Asset bucket not configured; falling back to placeholders.")
        return None

    import boto3  # lazy: skips botocore's import cost when unconfigured
    from botocore.config import Config

    return boto3.client(
        "s3",
        config=Config(
            signature_version="s3v4",
            connect_timeout=3,
            read_timeout=10,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


@st.cache_data(show_spinner=False)
def _object_b64(key: str) -> str:
    """Base64 of the object body. Raises so transient failures aren't cached."""
    client = _client()
    if client is None:
        raise AssetUnavailable(f"bucket not configured (key={key})")
    try:
        body = client.get_object(Bucket=_bucket(), Key=key)["Body"].read()
    except Exception as exc:
        logger.warning("Asset fetch failed for %s: %s", key, type(exc).__name__)
        raise AssetUnavailable(key) from exc
    return base64.b64encode(body).decode("ascii")


def get_favicon_data_uri() -> str | None:
    """Favicon as a data: URI, or None if unavailable."""
    try:
        return f"data:image/svg+xml;base64,{_object_b64(FAVICON_KEY)}"
    except AssetUnavailable:
        return None


def get_jersey_b64(team_short: str | None, is_keeper: bool = False) -> str | None:
    """Base64 PNG for a club's jersey by 3-letter short code, or None."""
    if not team_short:
        return None
    template = JERSEY_GK_KEY if is_keeper else JERSEY_KEY
    try:
        return _object_b64(template.format(short=str(team_short).upper()))
    except AssetUnavailable:
        return None
