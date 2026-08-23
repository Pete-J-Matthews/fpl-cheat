import pytest

from app import fpl_api


class MockResponse:
    def __init__(self, json_data, raise_for_status_exc=None):
        self._json_data = json_data
        self._raise_for_status_exc = raise_for_status_exc

    def raise_for_status(self):
        if self._raise_for_status_exc:
            raise self._raise_for_status_exc

    def json(self):
        return self._json_data


def test_build_element_lookup_positions_and_team_id():
    bootstrap = {
        "elements": [
            {"id": 1, "web_name": "Salah", "element_type": 3, "team": 9},
            {"id": 2, "web_name": "Gabriel", "element_type": 2, "team": 1},
            {"id": 3, "web_name": "Haaland", "element_type": 4, "team": 11},
            {"id": "bad", "web_name": "ShouldBeIgnored", "element_type": 1, "team": 0},
            {"web_name": "NoId", "element_type": 1, "team": 0},
        ]
    }

    lookup = fpl_api.build_element_lookup(bootstrap, include_team_id=False)
    assert set(lookup.keys()) == {1, 2, 3}
    assert lookup[1]["name"] == "Salah"
    assert lookup[1]["position"] == "MID"
    assert lookup[2]["position"] == "DEF"
    assert lookup[3]["position"] == "FWD"

    lookup_with_team = fpl_api.build_element_lookup(bootstrap, include_team_id=True)
    assert lookup_with_team[1]["team_id"] == 9
    assert lookup_with_team[2]["team_id"] == 1
    assert lookup_with_team[3]["team_id"] == 11


def test_fetch_bootstrap_success(monkeypatch):
    expected = {"events": [{"id": 1}]}
    calls = []

    def mock_get(url, timeout=None, headers=None):
        calls.append({"url": url, "timeout": timeout, "headers": headers})
        return MockResponse(expected)

    monkeypatch.setattr(fpl_api.requests, "get", mock_get)
    result = fpl_api.fetch_bootstrap()

    assert result == expected
    assert calls[0]["url"] == fpl_api.FPL_BOOTSTRAP_URL
    assert calls[0]["timeout"] == 10
    assert "User-Agent" in calls[0]["headers"]


def test_fetch_bootstrap_failure_returns_none(monkeypatch):
    def mock_get(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(fpl_api.requests, "get", mock_get)
    assert fpl_api.fetch_bootstrap() is None


@pytest.mark.parametrize(
    "events, expected_id",
    [
        ([{"id": "10", "is_current": True}], 10),
        ([{"id": "5", "is_current": False, "is_next": True}], 5),
        ([], 1),
    ],
)
def test_get_current_event_id_variants(monkeypatch, events, expected_id):
    data = {"events": events}

    def mock_get(url, timeout=None, headers=None):
        assert url == fpl_api.FPL_BOOTSTRAP_URL
        return MockResponse(data)

    monkeypatch.setattr(fpl_api.requests, "get", mock_get)
    assert fpl_api.get_current_event_id() == expected_id


def test_get_current_event_id_handles_exception(monkeypatch):
    def mock_get(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(fpl_api.requests, "get", mock_get)
    assert fpl_api.get_current_event_id() == 1


def test_fetch_entry_picks_success(monkeypatch):
    manager_id = 123
    event_id = 34
    expected = {"picks": [{"element": 1}]}
    calls = []

    def mock_get(url, timeout=None, headers=None):
        calls.append({"url": url, "timeout": timeout, "headers": headers})
        return MockResponse(expected)

    monkeypatch.setattr(fpl_api.requests, "get", mock_get)
    result = fpl_api.fetch_entry_picks(manager_id, event_id)

    assert result == expected
    assert calls[0]["url"] == fpl_api.FPL_ENTRY_PICKS_URL.format(
        manager_id=manager_id, event_id=event_id
    )
    assert calls[0]["timeout"] == 10
