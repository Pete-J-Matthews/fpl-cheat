"""S3-backed static assets (favicon, club jerseys). Bucket coords come from AWS_* env vars."""

import base64
import logging
import os
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)

FAVICON_KEY = "favicon.svg"
JERSEY_KEY = "jerseys/{short}.png"


class AssetUnavailable(RuntimeError):
    """The asset could not be fetched from the bucket."""


def _bucket() -> Optional[str]:
    return os.getenv("AWS_S3_BUCKET_NAME") or None


@st.cache_resource(show_spinner=False)
def _client():
    """Shared S3 client, or None when the bucket isn't configured."""
    endpoint = os.getenv("AWS_ENDPOINT_URL")
    if not all((os.getenv("AWS_ACCESS_KEY_ID"), os.getenv("AWS_SECRET_ACCESS_KEY"), endpoint, _bucket())):
        logger.warning("Asset bucket not configured; falling back to placeholders.")
        return None

    import boto3  # lazy: skips botocore's import cost when unconfigured
    from botocore.config import Config

    # Credentials come from boto3's own env provider, so they never enter a traceback here.
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=os.getenv("AWS_DEFAULT_REGION"),
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


def get_favicon_data_uri() -> Optional[str]:
    """Favicon as a data: URI, or None if unavailable."""
    try:
        return f"data:image/svg+xml;base64,{_object_b64(FAVICON_KEY)}"
    except AssetUnavailable:
        return None


def get_jersey_b64(team_short: Optional[str]) -> Optional[str]:
    """Base64 PNG for a club's jersey by 3-letter short code, or None."""
    if not team_short:
        return None
    try:
        return _object_b64(JERSEY_KEY.format(short=str(team_short).upper()))
    except AssetUnavailable:
        return None
