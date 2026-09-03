import pytest

from app import database


@pytest.fixture
def captured(monkeypatch):
    calls = {}

    def fake_execute_query(query, params=(), **kwargs):
        calls["query"] = query
        calls["params"] = params
        return []

    monkeypatch.setattr(database, "_execute_query", fake_execute_query)
    return calls


def test_search_managers_ignores_short_queries(captured):
    assert database.search_managers("pet") == []
    assert captured == {}


def test_search_managers_anchors_the_prefix(captured):
    database.search_managers("  Pete  ")
    assert captured["params"] == ("Pete%", "Pete%")


def test_search_managers_stays_distinct_free(captured):
    database.search_managers("pete")
    # DISTINCT blocks the LIMIT from stopping early: 47ms becomes 312ms on a common prefix.
    assert "DISTINCT" not in captured["query"].upper()
    assert captured["query"].upper().count("ILIKE") == 2
