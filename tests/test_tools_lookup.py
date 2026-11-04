"""Tests for lookup_area_code and lookup_industry_code tools."""

from __future__ import annotations

import example_server.catalog as catalog_module
from example_server.catalog import Catalog


def _fake_catalog(
    area_data: dict | None = None, industry_data: dict | None = None
) -> Catalog:
    """Return a Catalog with controlled data for testing."""
    data: dict = {}
    if area_data:
        for key, mapping in area_data.items():
            data[key] = mapping
    if industry_data:
        for key, mapping in industry_data.items():
            data[key] = mapping

    c = object.__new__(Catalog)
    c._data = data
    return c


# ---------------------------------------------------------------------------
# lookup_area_code
# ---------------------------------------------------------------------------


def _call_lookup_area(query: str, survey=None, limit: int = 20) -> dict:
    """Capture and call the lookup_area_code tool function."""
    import example_server.tools.lookup_area_code as mod

    captured = {}

    class FakeMCP:
        def tool(self, name, annotations=None):
            def decorator(fn):
                captured["fn"] = fn
                return fn

            return decorator

    mod.register(FakeMCP())
    return captured["fn"](query=query, survey=survey, limit=limit)


def test_lookup_area_found(monkeypatch) -> None:
    fake = _fake_catalog(
        area_data={
            ("sm", "area"): {
                "10180": "Abilene, TX",
                "16980": "Chicago-Naperville-Elgin, IL-IN-WI",
            },
            ("la", "area"): {},
            ("qcew", "area"): {},
        }
    )
    monkeypatch.setattr(catalog_module, "catalog", fake)

    result = _call_lookup_area("Chicago")
    assert result["count"] >= 1
    codes = [r["code"] for r in result["results"]]
    assert "16980" in codes


def test_lookup_area_no_match(monkeypatch) -> None:
    fake = _fake_catalog(
        area_data={
            ("sm", "area"): {"10180": "Abilene, TX"},
            ("la", "area"): {},
            ("qcew", "area"): {},
        }
    )
    monkeypatch.setattr(catalog_module, "catalog", fake)

    result = _call_lookup_area("zzznomatch")
    assert result["count"] == 0
    assert result["results"] == []


def test_lookup_area_survey_filter(monkeypatch) -> None:
    fake = _fake_catalog(
        area_data={
            ("sm", "area"): {"10180": "Abilene, TX"},
            ("la", "area"): {"ST0100000000000": "Alabama"},
            ("qcew", "area"): {},
        }
    )
    monkeypatch.setattr(catalog_module, "catalog", fake)

    result = _call_lookup_area("Alabama", survey="LA")
    assert all(r["survey"] == "la" for r in result["results"])


def test_lookup_area_limit_enforced(monkeypatch) -> None:
    area_data = {str(i).zfill(5): f"City {i}" for i in range(30)}
    fake = _fake_catalog(
        area_data={
            ("sm", "area"): area_data,
            ("la", "area"): {},
            ("qcew", "area"): {},
        }
    )
    monkeypatch.setattr(catalog_module, "catalog", fake)

    result = _call_lookup_area("City", limit=5)
    assert result["count"] <= 5


def test_lookup_area_result_shape(monkeypatch) -> None:
    fake = _fake_catalog(
        area_data={
            ("sm", "area"): {"10180": "Abilene, TX"},
            ("la", "area"): {},
            ("qcew", "area"): {},
        }
    )
    monkeypatch.setattr(catalog_module, "catalog", fake)

    result = _call_lookup_area("Abilene")
    for r in result["results"]:
        assert "code" in r
        assert "name" in r
        assert "survey" in r
        assert "dimension" in r


# ---------------------------------------------------------------------------
# lookup_industry_code
# ---------------------------------------------------------------------------


def _call_lookup_industry(
    query: str, monkeypatch, fake, survey=None, limit: int = 20
) -> dict:
    import example_server.tools.lookup_industry_code as mod

    monkeypatch.setattr(mod, "catalog", fake)
    captured = {}

    class FakeMCP:
        def tool(self, name, annotations=None):
            def decorator(fn):
                captured["fn"] = fn
                return fn

            return decorator

    mod.register(FakeMCP())
    return captured["fn"](query=query, survey=survey, limit=limit)


def test_lookup_industry_found(monkeypatch) -> None:
    fake = _fake_catalog(
        industry_data={
            ("ce", "industry"): {"00000000": "Total nonfarm", "30000000": "Healthcare"},
            ("sm", "industry"): {},
            ("jt", "industry"): {},
            ("qcew", "industry"): {},
        }
    )
    result = _call_lookup_industry("Healthcare", monkeypatch, fake)
    assert result["count"] >= 1
    codes = [r["code"] for r in result["results"]]
    assert "30000000" in codes


def test_lookup_industry_survey_filter(monkeypatch) -> None:
    fake = _fake_catalog(
        industry_data={
            ("ce", "industry"): {"00000000": "Total nonfarm"},
            ("sm", "industry"): {"00000000": "Total nonfarm SM"},
            ("jt", "industry"): {},
            ("qcew", "industry"): {},
        }
    )
    result = _call_lookup_industry("Total", monkeypatch, fake, survey="SM")
    assert all(r["survey"] == "sm" for r in result["results"])


def test_lookup_industry_result_shape(monkeypatch) -> None:
    fake = _fake_catalog(
        industry_data={
            ("ce", "industry"): {"00000000": "Total nonfarm"},
            ("sm", "industry"): {},
            ("jt", "industry"): {},
            ("qcew", "industry"): {},
        }
    )
    result = _call_lookup_industry("Total", monkeypatch, fake)
    for r in result["results"]:
        assert "code" in r
        assert "name" in r
        assert "survey" in r
