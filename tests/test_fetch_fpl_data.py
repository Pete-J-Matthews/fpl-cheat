from types import SimpleNamespace

import pytest

from scripts import fetch_fpl_data
from scripts.fetch_fpl_data import FPLDataFetcher, RateLimited, parse_managers


def page(*entries):
    return {"standings": {"results": list(entries)}}


def row(entry, name="Ada L", team="Ada FC"):
    return {"entry": entry, "player_name": name, "entry_name": team}


def test_parse_managers_keeps_valid_and_drops_invalid():
    data = page(
        row(1),
        row(None),
        {"entry": 2, "player_name": "  ", "entry_name": "T"},
        {"entry": 3, "player_name": "N", "entry_name": None},
        {"entry": True, "player_name": "N", "entry_name": "T"},
        row(4),
    )
    assert [m["manager_id"] for m in parse_managers(data, 1)] == [1, 4]


def test_parse_managers_handles_missing_page():
    assert parse_managers(None, 1) == []


@pytest.mark.parametrize("boundary", [1, 7, 50, 1024, 3000])
def test_find_last_page_binary_search(monkeypatch, boundary):
    calls = []

    def fake_fetch_page(self, p):
        calls.append(p)
        return page(row(p)) if p <= boundary else page()

    monkeypatch.setattr(FPLDataFetcher, "fetch_page", fake_fetch_page)
    assert FPLDataFetcher().find_last_page() == boundary
    assert len(calls) < 40  # Search stays logarithmic


def test_find_last_page_zero_when_standings_empty(monkeypatch):
    monkeypatch.setattr(FPLDataFetcher, "fetch_page", lambda self, p: page())
    assert FPLDataFetcher().find_last_page() == 0


class FakeDB:
    def __init__(self, short_by=0):
        self.rows = {}
        self.watermarks = []
        self.short_by = short_by

    def upsert_managers(self, managers):
        self.rows.update({m["manager_id"]: m for m in managers})
        return len(managers) - self.short_by

    def set_last_page(self, last_page):
        self.watermarks.append(last_page)

    def get_manager_count(self):
        return len(self.rows)


def test_fetch_all_managers_covers_every_page(monkeypatch):
    monkeypatch.setattr(fetch_fpl_data, "WINDOW_PAGES", 10)
    monkeypatch.setattr(
        FPLDataFetcher, "fetch_page", lambda self, p: page(row(p * 100))
    )
    db = FakeDB()
    total = FPLDataFetcher().fetch_all_managers(1, 25, db, max_workers=4)
    assert total == 25
    assert db.watermarks == [10, 20, 25]


def test_throttling_halves_workers_and_retries_window(monkeypatch):
    monkeypatch.setattr(fetch_fpl_data, "WINDOW_PAGES", 5)
    monkeypatch.setattr(fetch_fpl_data.time, "sleep", lambda s: None)
    seen_workers = []
    state = {"throttles": 2}

    def fake_window(self, pages, workers):
        seen_workers.append(workers)
        if state["throttles"]:
            state["throttles"] -= 1
            raise RateLimited(pages[0], 429, 1)
        return {p: page(row(p)) for p in pages}

    monkeypatch.setattr(FPLDataFetcher, "fetch_window", fake_window)
    db = FakeDB()
    FPLDataFetcher().fetch_all_managers(1, 5, db, max_workers=8)
    assert seen_workers == [4, 2, 1]  # Halves per throttle, window retried
    assert len(db.rows) == 5


def test_window_mostly_failing_stops_the_fetch(monkeypatch):
    monkeypatch.setattr(fetch_fpl_data, "WINDOW_PAGES", 10)
    monkeypatch.setattr(
        FPLDataFetcher, "fetch_window", lambda self, pages, w: dict.fromkeys(pages)
    )
    db = FakeDB()
    assert FPLDataFetcher().fetch_all_managers(1, 100, db, max_workers=4) == 0
    assert db.watermarks == []


def stub_session(monkeypatch, response):
    session = SimpleNamespace(get=lambda *a, **k: response)
    monkeypatch.setattr(fetch_fpl_data, "_session", lambda: session)


def test_fetch_page_raises_ratelimited_and_reads_retry_after(monkeypatch):
    stub_session(
        monkeypatch, SimpleNamespace(status_code=429, headers={"Retry-After": "17"})
    )
    with pytest.raises(RateLimited) as exc:
        FPLDataFetcher().fetch_page(1)
    assert exc.value.retry_after == 17
    assert exc.value.status == 429


def test_retry_after_falls_back_when_header_absent_or_junk():
    backoff = fetch_fpl_data.DEFAULT_BACKOFF
    assert fetch_fpl_data._retry_after(SimpleNamespace(headers={})) == backoff
    junk = SimpleNamespace(headers={"Retry-After": "soon"})
    assert fetch_fpl_data._retry_after(junk) == backoff
    assert (
        fetch_fpl_data._retry_after(SimpleNamespace(headers={"Retry-After": "9999"}))
        == 300
    )


def test_fetch_page_returns_none_after_retries(monkeypatch):
    monkeypatch.setattr(fetch_fpl_data.time, "sleep", lambda s: None)
    stub_session(monkeypatch, SimpleNamespace(status_code=500, headers={}))
    assert FPLDataFetcher().fetch_page(1) is None


def test_find_last_page_raises_rather_than_truncating_on_failure(monkeypatch):
    monkeypatch.setattr(fetch_fpl_data.time, "sleep", lambda s: None)
    monkeypatch.setattr(
        FPLDataFetcher, "fetch_page", lambda self, p: page(row(p)) if p < 8 else None
    )
    with pytest.raises(RuntimeError, match="probing for the end"):
        FPLDataFetcher().find_last_page()


def test_short_upsert_does_not_advance_the_watermark(monkeypatch):
    monkeypatch.setattr(fetch_fpl_data, "WINDOW_PAGES", 5)
    monkeypatch.setattr(FPLDataFetcher, "fetch_page", lambda self, p: page(row(p)))
    db = FakeDB(short_by=1)
    with pytest.raises(RuntimeError, match="of 5 managers"):
        FPLDataFetcher().fetch_all_managers(1, 5, db, max_workers=4)
    assert db.watermarks == []
