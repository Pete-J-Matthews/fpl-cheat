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
    assert captured["params"] == ("pete%", "pete%")


def test_search_managers_escapes_like_wildcards(captured):
    database.search_managers("50%_a")
    assert captured["params"] == ("50\\%\\_a%", "50\\%\\_a%")


def test_search_managers_matches_the_indexed_expression(captured):
    database.search_managers("pete")
    # DISTINCT blocks the LIMIT from stopping early: 47ms becomes 312ms on a common prefix.
    assert "DISTINCT" not in captured["query"].upper()
    assert captured["query"].count("lower(manager_name) LIKE") == 1
    assert captured["query"].count("lower(team_name) LIKE") == 1
