"""Tests for example_server.catalog — local-cache loader."""

from __future__ import annotations

import warnings
from pathlib import Path

from example_server.catalog import Catalog, _load_fixed_width, _load_tsv, catalog

# ---------------------------------------------------------------------------
# Helper: build a minimal Catalog with injected data (avoids hitting disk)
# ---------------------------------------------------------------------------


def _make_catalog(data: dict) -> Catalog:
    """Return a Catalog whose _data dict is replaced with the given mapping."""
    c = object.__new__(Catalog)
    c._data = data
    return c


# ---------------------------------------------------------------------------
# _load_tsv
# ---------------------------------------------------------------------------


def test_load_tsv_basic(tmp_path: Path) -> None:
    f = tmp_path / "test.tsv"
    f.write_text("code\tname\nextra\n01\tAlabama\n02\tAlaska\n", encoding="utf-8")
    result = _load_tsv(f)
    assert result == {"01": "Alabama", "02": "Alaska"}


def test_load_tsv_ignores_extra_columns(tmp_path: Path) -> None:
    f = tmp_path / "test.tsv"
    f.write_text("code\tname\tother\n01\tAlabama\tignored\n", encoding="utf-8")
    result = _load_tsv(f)
    assert result["01"] == "Alabama"


def test_load_tsv_missing_file_warns() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = _load_tsv(Path("/nonexistent/file.tsv"))
    assert result == {}
    assert any("could not read" in str(warning.message) for warning in w)


# ---------------------------------------------------------------------------
# _load_fixed_width
# ---------------------------------------------------------------------------


def test_load_fixed_width_basic(tmp_path: Path) -> None:
    f = tmp_path / "qcew.txt"
    f.write_text(
        "01000 Alabama -- Statewide                \n01001 Autauga County\n",
        encoding="utf-8",
    )
    result = _load_fixed_width(f)
    assert result["01000"] == "Alabama -- Statewide"
    assert result["01001"] == "Autauga County"


def test_load_fixed_width_missing_file_warns() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = _load_fixed_width(Path("/nonexistent/file.txt"))
    assert result == {}
    assert any("could not read" in str(warning.message) for warning in w)


# ---------------------------------------------------------------------------
# Catalog.get
# ---------------------------------------------------------------------------


def test_catalog_get_known_pair() -> None:
    c = _make_catalog({("sm", "area"): {"10180": "Abilene, TX"}})
    assert c.get("sm", "area") == {"10180": "Abilene, TX"}


def test_catalog_get_unknown_pair_returns_empty() -> None:
    c = _make_catalog({})
    assert c.get("zz", "unknown") == {}


def test_catalog_get_case_insensitive() -> None:
    c = _make_catalog({("sm", "area"): {"10180": "Abilene, TX"}})
    assert c.get("SM", "AREA") == {"10180": "Abilene, TX"}


# ---------------------------------------------------------------------------
# Catalog.search
# ---------------------------------------------------------------------------


def test_catalog_search_finds_by_name() -> None:
    c = _make_catalog({("sm", "area"): {"10180": "Abilene, TX", "10420": "Akron, OH"}})
    hits = c.search("sm", "area", "Abilene")
    assert len(hits) == 1
    assert hits[0]["code"] == "10180"
    assert hits[0]["name"] == "Abilene, TX"
    assert hits[0]["survey"] == "sm"
    assert hits[0]["dimension"] == "area"


def test_catalog_search_finds_by_code() -> None:
    c = _make_catalog({("sm", "area"): {"10180": "Abilene, TX"}})
    hits = c.search("sm", "area", "10180")
    assert len(hits) == 1 and hits[0]["code"] == "10180"


def test_catalog_search_case_insensitive() -> None:
    c = _make_catalog({("sm", "area"): {"10180": "Abilene, TX"}})
    assert len(c.search("sm", "area", "ABILENE")) == 1
    assert len(c.search("sm", "area", "abilene")) == 1


def test_catalog_search_no_match_returns_empty() -> None:
    c = _make_catalog({("sm", "area"): {"10180": "Abilene, TX"}})
    assert c.search("sm", "area", "zzznomatch") == []


def test_catalog_search_max_results_respected() -> None:
    data = {str(i).zfill(5): f"City {i}" for i in range(50)}
    c = _make_catalog({("sm", "area"): data})
    hits = c.search("sm", "area", "City", max_results=5)
    assert len(hits) <= 5


def test_catalog_search_exact_code_first() -> None:
    c = _make_catalog(
        {("sm", "area"): {"17": "Illinois", "170": "Contains 17", "99": "Other"}}
    )
    hits = c.search("sm", "area", "17")
    assert hits[0]["code"] == "17"


def test_catalog_search_unknown_pair_returns_empty() -> None:
    c = _make_catalog({})
    assert c.search("zz", "unknown", "anything") == []


# ---------------------------------------------------------------------------
# Module-level singleton smoke test
# ---------------------------------------------------------------------------


def test_module_catalog_sm_area_loaded() -> None:
    """The module-level catalog singleton should have SM area data."""
    data = catalog.get("sm", "area")
    assert isinstance(data, dict)
    assert len(data) > 0  # local-cache file exists and was parsed


def test_module_catalog_la_area_loaded() -> None:
    data = catalog.get("la", "area")
    assert len(data) > 0


def test_module_catalog_qcew_area_loaded() -> None:
    data = catalog.get("qcew", "area")
    assert len(data) > 0
