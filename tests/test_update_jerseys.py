from types import SimpleNamespace

import pytest

from scripts import update_jerseys

PNG = update_jerseys.PNG_MAGIC + b"\x00" * 2000


def response(content: bytes = PNG, teams: int = 20) -> SimpleNamespace:
    """Stands in for a requests.Response, serving either a shirt or a bootstrap payload."""
    return SimpleNamespace(
        content=content, status_code=200, json=lambda: bootstrap(teams)
    )


class FakeS3:
    """Records writes instead of making them."""

    def __init__(self, existing: list[str] | None = None):
        self.existing = existing or []
        self.puts: list[str] = []
        self.deleted: list[list[str]] = []

    def get_paginator(self, _name):
        pages = [{"Contents": [{"Key": k} for k in self.existing]}]
        return SimpleNamespace(paginate=lambda **_kw: pages)

    def put_object(self, Key, **_kw):
        self.puts.append(Key)

    def delete_objects(self, Delete, **_kw):
        self.deleted.append([o["Key"] for o in Delete["Objects"]])


def clubs(n: int) -> list[dict]:
    return [{"short": f"C{i:02d}", "code": i} for i in range(1, n + 1)]


def bootstrap(n: int) -> dict:
    return {"teams": [{"short_name": f"C{i:02d}", "code": i} for i in range(1, n + 1)]}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("AWS_S3_BUCKET_NAME", "placeholder")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://placeholder.invalid")


@pytest.fixture
def fake_s3(monkeypatch):
    s3 = FakeS3(existing=["jerseys/GONE.png", "jerseys/C01.png"])
    monkeypatch.setattr(update_jerseys, "_client", lambda: s3)
    return s3


def stub_downloads(monkeypatch, fail_urls=()):
    """Serve a valid PNG for every shirt URL except those in fail_urls."""

    def fake_get(url):
        if url == update_jerseys.BOOTSTRAP_URL:
            raise AssertionError("bootstrap should be stubbed separately")
        return None if url in fail_urls else response()

    monkeypatch.setattr(update_jerseys, "_get", fake_get)


def stub_all(monkeypatch, teams: int = 20):
    """Serve a valid response for every URL, bootstrap included."""
    monkeypatch.setattr(update_jerseys, "_get", lambda _url: response(teams=teams))


def test_urls_and_keys_distinguish_keepers():
    assert update_jerseys.shirt_url(3, keeper=False).endswith("shirt_3-110.png")
    assert update_jerseys.shirt_url(3, keeper=True).endswith("shirt_3_1-110.png")
    assert update_jerseys.jersey_key("ars", keeper=False) == "jerseys/ARS.png"
    assert update_jerseys.jersey_key("ars", keeper=True) == "jerseys/ARS_GK.png"


def test_parse_clubs_skips_invalid_rows():
    parsed = update_jerseys.parse_clubs(
        {
            "teams": [
                {"short_name": "ars", "code": 3},
                {"short_name": "  ", "code": 4},
                {"short_name": "LIV", "code": None},
                {"short_name": "MCI", "code": True},
            ]
        }
    )
    assert parsed == [{"short": "ARS", "code": 3}]


def test_is_png_rejects_error_pages_and_stubs():
    assert update_jerseys.is_png(PNG)
    assert not update_jerseys.is_png(b"<html>404</html>" * 200)
    assert not update_jerseys.is_png(update_jerseys.PNG_MAGIC)


def test_download_shirts_reports_failures(monkeypatch):
    bad = update_jerseys.shirt_url(2, keeper=True)
    stub_downloads(monkeypatch, fail_urls={bad})
    shirts, failed = update_jerseys.download_shirts(clubs(2))
    assert sorted(shirts) == [
        "jerseys/C01.png",
        "jerseys/C01_GK.png",
        "jerseys/C02.png",
    ]
    assert failed == ["jerseys/C02_GK.png"]


def test_full_run_uploads_and_prunes(monkeypatch, env, fake_s3):
    stub_all(monkeypatch)
    monkeypatch.setattr("sys.argv", ["update_jerseys.py"])
    update_jerseys.main()
    assert len(fake_s3.puts) == 40
    assert fake_s3.deleted == [["jerseys/GONE.png"]]


def test_short_bootstrap_aborts_before_touching_bucket(monkeypatch, env, fake_s3):
    stub_all(monkeypatch, teams=19)
    monkeypatch.setattr("sys.argv", ["update_jerseys.py"])
    with pytest.raises(SystemExit) as exc:
        update_jerseys.main()
    assert exc.value.code == 1
    assert fake_s3.puts == []
    assert fake_s3.deleted == []


def test_failed_download_uploads_but_never_prunes(monkeypatch, env, fake_s3):
    bad = update_jerseys.shirt_url(2, keeper=True)

    def fake_get(url):
        if url == update_jerseys.BOOTSTRAP_URL:
            return response()
        return None if url == bad else response()

    monkeypatch.setattr(update_jerseys, "_get", fake_get)
    monkeypatch.setattr("sys.argv", ["update_jerseys.py"])
    with pytest.raises(SystemExit) as exc:
        update_jerseys.main()
    assert exc.value.code == 1
    assert len(fake_s3.puts) == 39
    assert fake_s3.deleted == []


def test_dry_run_writes_nothing(monkeypatch, env, fake_s3):
    stub_all(monkeypatch)
    monkeypatch.setattr("sys.argv", ["update_jerseys.py", "--dry-run"])
    update_jerseys.main()
    assert fake_s3.puts == []
    assert fake_s3.deleted == []


def test_missing_bucket_raises(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://placeholder.invalid")
    monkeypatch.delenv("AWS_S3_BUCKET_NAME", raising=False)
    with pytest.raises(ValueError, match="AWS_S3_BUCKET_NAME"):
        update_jerseys._bucket()


def test_missing_endpoint_raises(monkeypatch):
    """Without an endpoint boto3 would target real AWS S3 and the wrong credentials."""
    monkeypatch.setenv("AWS_S3_BUCKET_NAME", "placeholder")
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    with pytest.raises(ValueError, match="AWS_ENDPOINT_URL"):
        update_jerseys._bucket()
