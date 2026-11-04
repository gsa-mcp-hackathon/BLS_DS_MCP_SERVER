"""Tests for search_series and suggest_series tools."""

from __future__ import annotations

import example_server.catalog as catalog_module
from example_server.catalog import Catalog


def _capture(module) -> object:
    """Capture the inner tool function from a register() call."""
    captured = {}

    class FakeMCP:
        def tool(self, name, annotations=None):
            def decorator(fn):
                captured["fn"] = fn
                return fn

            return decorator

    module.register(FakeMCP())
    return captured["fn"]


def _fake_catalog_sm_chicago() -> Catalog:
    """Catalog with Chicago area and Illinois state for SM search tests."""
    c = object.__new__(Catalog)
    c._data = {
        ("sm", "area"): {"16980": "Chicago-Naperville-Elgin, IL-IN-WI"},
        ("sm", "state"): {"17": "Illinois", "00": "All States"},
        ("sm", "supersector"): {"00": "Total Nonfarm"},
        ("sm", "industry"): {"00000000": "Total Nonfarm"},
        ("sm", "data_type"): {"01": "All Employees, In Thousands"},
        ("ce", "seasonal"): {
            "S": "Seasonally Adjusted",
            "U": "Not Seasonally Adjusted",
        },
        ("ce", "industry"): {"000000": "Total nonfarm"},
        ("ce", "supersector"): {"00": "Total nonfarm"},
        ("ce", "datatype"): {"01": "ALL EMPLOYEES, THOUSANDS"},
        ("la", "area"): {
            "ST0600000000000": "California",
            "ST1700000000000": "Illinois",
        },
        ("la", "area_type"): {"A": "Statewide"},
        ("la", "measure"): {"03": "unemployment rate", "04": "unemployment"},
        ("jt", "state"): {"00": "Total US"},
        ("jt", "industry"): {"000000": "Total nonfarm"},
        ("jt", "sizeclass"): {"00": "All size classes"},
        ("jt", "dataelement"): {"JO": "Job openings", "HI": "Hires"},
        ("jt", "ratelevel"): {"L": "Level", "R": "Rate"},
        ("cu", "area"): {"0000": "U.S. city average"},
        ("cu", "item"): {"SA0     ": "All items", "SAF1    ": "Food"},
        ("qcew", "area"): {},
        ("qcew", "industry"): {},
    }
    return c


# ---------------------------------------------------------------------------
# search_series
# ---------------------------------------------------------------------------


def test_search_series_chicago_employment(monkeypatch) -> None:
    monkeypatch.setattr(catalog_module, "catalog", _fake_catalog_sm_chicago())
    import example_server.tools.search_series as mod

    # Reload search_series module's catalog reference
    monkeypatch.setattr(mod, "catalog", _fake_catalog_sm_chicago())
    fn = _capture(mod)
    result = fn(query="employment Chicago", survey="SM", limit=10)
    assert result["count"] >= 1
    assert all("series_id" in r for r in result["results"])


def test_search_series_result_shape(monkeypatch) -> None:
    monkeypatch.setattr(catalog_module, "catalog", _fake_catalog_sm_chicago())
    import example_server.tools.search_series as mod

    monkeypatch.setattr(mod, "catalog", _fake_catalog_sm_chicago())
    fn = _capture(mod)
    result = fn(query="Chicago", survey="SM", limit=5)
    for r in result["results"]:
        assert "series_id" in r
        assert "label" in r
        assert "survey" in r
        assert "match_score" in r


def test_search_series_no_match_returns_suggestion(monkeypatch) -> None:
    # Empty catalog + SM survey filter → no area matches → no results
    c = object.__new__(Catalog)
    c._data = {}
    monkeypatch.setattr(catalog_module, "catalog", c)
    import example_server.tools.search_series as mod

    monkeypatch.setattr(mod, "catalog", c)
    fn = _capture(mod)
    result = fn(query="zzznomatch", survey="SM")
    assert result["count"] == 0
    assert "suggestion" in result


def test_search_series_limit_enforced(monkeypatch) -> None:
    monkeypatch.setattr(catalog_module, "catalog", _fake_catalog_sm_chicago())
    import example_server.tools.search_series as mod

    monkeypatch.setattr(mod, "catalog", _fake_catalog_sm_chicago())
    fn = _capture(mod)
    result = fn(query="employment", limit=2)
    assert result["count"] <= 2


def test_search_series_survey_filter(monkeypatch) -> None:
    monkeypatch.setattr(catalog_module, "catalog", _fake_catalog_sm_chicago())
    import example_server.tools.search_series as mod

    monkeypatch.setattr(mod, "catalog", _fake_catalog_sm_chicago())
    fn = _capture(mod)
    result = fn(query="unemployment", survey="LA", limit=5)
    # All results should be LA survey series
    assert all("LA" in r["survey"] or "Local" in r["survey"] for r in result["results"])


# ---------------------------------------------------------------------------
# suggest_series
# ---------------------------------------------------------------------------


def test_suggest_series_cpi_topic() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="consumer price inflation")
    assert result["count"] >= 1
    assert any(
        "CU" in s["series_id"][:2] or "CPI" in s["description"].upper()
        for s in result["suggestions"]
    )


def test_suggest_series_unemployment_topic() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="unemployment rate national")
    assert result["count"] >= 1
    assert any("LA" in s["series_id"][:2] for s in result["suggestions"])


def test_suggest_series_no_match_returns_message() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="zzznomatchkeyword")
    assert result["count"] == 0
    assert "message" in result


def test_suggest_series_limit_enforced() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="employment", limit=2)
    assert result["count"] <= 2


def test_suggest_series_result_shape() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="nonfarm payrolls")
    for s in result["suggestions"]:
        assert "series_id" in s
        assert "survey_name" in s
        assert "description" in s
        assert "rationale" in s


def test_suggest_series_jolts_topic() -> None:
    import example_server.tools.suggest_series as mod

    fn = _capture(mod)
    result = fn(topic="job openings hires quits jolts")
    assert any("JT" in s["series_id"][:2] for s in result["suggestions"])
