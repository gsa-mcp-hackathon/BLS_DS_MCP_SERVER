"""Local-cache catalog loader.

Parses every BLS reference file under local-cache/ once at import time and
exposes code→name lookups and substring search for all survey dimensions.

Usage:
    from example_server.catalog import catalog

    names = catalog.get("sm", "area")          # {"00000": "Statewide", ...}
    hits  = catalog.search("la", "area", "Chicago", max_results=5)
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Absolute path to the local-cache directory (sibling of this file).
_CACHE_DIR = Path(__file__).parent / "local-cache"

# Registry: (survey, dimension) → (path, is_fixed_width, key_col, val_col).
# key_col/val_col are 0-based column indices for TSV files (ignored for fixed-width).
# Defaults are key_col=0, val_col=1.  Override when the TSV has a different layout.
_REGISTRY: dict[tuple[str, str], tuple[Path, bool, int, int]] = {
    # SM — State and Metro Area Employment
    ("sm", "area"): (_CACHE_DIR / "sm.area", False, 0, 1),
    ("sm", "state"): (_CACHE_DIR / "sm.state", False, 0, 1),
    ("sm", "supersector"): (_CACHE_DIR / "sm.supersector", False, 0, 1),
    ("sm", "data_type"): (_CACHE_DIR / "sm.data_type", False, 0, 1),
    ("sm", "industry"): (_CACHE_DIR / "sm.industry", False, 0, 1),
    # CE — Current Employment Statistics
    ("ce", "industry"): (
        _CACHE_DIR / "ce.industry",
        False,
        0,
        3,
    ),  # col3 = industry_name
    ("ce", "datatype"): (_CACHE_DIR / "ce.datatype", False, 0, 1),
    ("ce", "seasonal"): (_CACHE_DIR / "ce.seasonal", False, 0, 1),
    ("ce", "supersector"): (_CACHE_DIR / "ce.supersector", False, 0, 1),
    # LA — Local Area Unemployment Statistics
    # la.area: col0=area_type_code, col1=area_code, col2=area_text → key=col1, val=col2
    ("la", "area"): (_CACHE_DIR / "la.area", False, 1, 2),
    ("la", "area_type"): (_CACHE_DIR / "la.area_type", False, 0, 1),
    ("la", "measure"): (_CACHE_DIR / "la.measure", False, 0, 1),
    # JT — Job Openings & Labor Turnover
    ("jt", "area"): (_CACHE_DIR / "jt.area", False, 0, 1),
    ("jt", "state"): (_CACHE_DIR / "jt.state", False, 0, 1),
    ("jt", "industry"): (_CACHE_DIR / "jt.industry", False, 0, 1),
    ("jt", "dataelement"): (_CACHE_DIR / "jt.dataelement", False, 0, 1),
    ("jt", "sizeclass"): (_CACHE_DIR / "jt.sizeclass", False, 0, 1),
    ("jt", "ratelevel"): (_CACHE_DIR / "jt.ratelevel", False, 0, 1),
    # CU — Consumer Price Index
    ("cu", "area"): (_CACHE_DIR / "cu.area", False, 0, 1),
    ("cu", "item"): (_CACHE_DIR / "cu.item", False, 0, 1),
    # QCEW — Quarterly Census of Employment & Wages (fixed-width)
    ("qcew", "area"): (_CACHE_DIR / "qcew-area-titles-txt.txt", True, 0, 1),
    ("qcew", "industry"): (_CACHE_DIR / "qcew-industry-titles.txt", True, 0, 1),
    ("qcew", "datatype"): (_CACHE_DIR / "qcew-datatype-titles-txt.txt", True, 0, 1),
    ("qcew", "ownership"): (_CACHE_DIR / "qcew-ownership-titles-txt.txt", True, 0, 1),
    ("qcew", "size"): (_CACHE_DIR / "qcew-size-titles-text.txt", True, 0, 1),
    # BD — Business Dynamics Statistics
    ("bd", "industry"): (_CACHE_DIR / "bd.industry", False, 0, 1),
    ("bd", "state"): (_CACHE_DIR / "bd.state", False, 0, 1),
    ("bd", "dataclass"): (_CACHE_DIR / "bd.dataclass", False, 0, 1),
    ("bd", "dataelement"): (_CACHE_DIR / "bd.dataelement", False, 0, 1),
    ("bd", "ratelevel"): (_CACHE_DIR / "bd.ratelevel", False, 0, 1),
    ("bd", "seasonal"): (_CACHE_DIR / "bd.seasonal", False, 0, 1),
    # AP — Average Energy Prices
    ("ap", "area"): (_CACHE_DIR / "ap.area", False, 0, 1),
    ("ap", "item"): (_CACHE_DIR / "ap.item", False, 0, 1),
    # PC — Producer Price Index
    ("pc", "industry"): (_CACHE_DIR / "pc.industry", False, 0, 1),
    ("pc", "product"): (_CACHE_DIR / "pc.product", False, 0, 1),
    # CW — Occupational Wages
    ("cw", "area"): (_CACHE_DIR / "cw.area", False, 0, 1),
    ("cw", "item"): (_CACHE_DIR / "cw.item", False, 0, 1),
    # SU — Average Weekly Hours
    ("su", "area"): (_CACHE_DIR / "su.area", False, 0, 1),
    ("su", "item"): (_CACHE_DIR / "su.item", False, 0, 1),
    # WP — Work-Related Injuries & Illnesses
    ("wp", "group"): (_CACHE_DIR / "wp.group", False, 0, 1),
    ("wp", "item"): (_CACHE_DIR / "wp.item", False, 0, 1),
    # NB — National Compensation Survey
    ("nb", "industry"): (_CACHE_DIR / "nb.industry", False, 0, 1),
    ("nb", "occupation"): (_CACHE_DIR / "nb.occupation", False, 0, 1),
    ("nb", "datatype"): (_CACHE_DIR / "nb.datatype", False, 0, 1),
    ("nb", "estimate"): (_CACHE_DIR / "nb.estimate", False, 0, 1),
    ("nb", "ownership"): (_CACHE_DIR / "nb.ownership", False, 0, 1),
    ("nb", "provision"): (_CACHE_DIR / "nb.provision", False, 0, 1),
    ("nb", "subcell"): (_CACHE_DIR / "nb.subcell", False, 0, 1),
}


def _load_tsv(path: Path, key_col: int = 0, val_col: int = 1) -> dict[str, str]:
    """Read a tab-separated file and return {key_col: val_col}."""
    mapping: dict[str, str] = {}
    needed = max(key_col, val_col)
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            header = True
            for line in fh:
                if header:
                    header = False
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) > needed:
                    mapping[parts[key_col].strip()] = parts[val_col].strip()
    except OSError as exc:
        warnings.warn(f"catalog: could not read {path}: {exc}", stacklevel=2)
    return mapping


def _load_fixed_width(path: Path) -> dict[str, str]:
    """Read a QCEW fixed-width file: first 5 chars = code, rest = description."""
    mapping: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if len(line) >= 6:
                    code = line[:5].strip()
                    name = line[5:].strip()
                    if code:
                        mapping[code] = name
    except OSError as exc:
        warnings.warn(f"catalog: could not read {path}: {exc}", stacklevel=2)
    return mapping


class Catalog:
    """Pre-loaded code→name lookup tables for all BLS local-cache files."""

    def __init__(self) -> None:
        self._data: dict[tuple[str, str], dict[str, str]] = {}
        for (survey, dimension), (path, is_fw, key_col, val_col) in _REGISTRY.items():
            if is_fw:
                self._data[(survey, dimension)] = _load_fixed_width(path)
            else:
                self._data[(survey, dimension)] = _load_tsv(path, key_col, val_col)

    def get(self, survey: str, dimension: str) -> dict[str, str]:
        """Return the code→name mapping for a survey+dimension pair.

        Returns an empty dict for unknown pairs — never raises.
        """
        return self._data.get((survey.lower(), dimension.lower()), {})

    def search(
        self,
        survey: str,
        dimension: str,
        query: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Case-insensitive substring search over codes and names.

        Returns a list of {"code", "name", "survey", "dimension"} dicts,
        sorted: exact code match first, starts-with second, contains third.
        """
        mapping = self.get(survey, dimension)
        q = query.strip().lower()

        exact: list[dict[str, Any]] = []
        starts: list[dict[str, Any]] = []
        contains: list[dict[str, Any]] = []

        for code, name in mapping.items():
            code_l = code.lower()
            name_l = name.lower()
            entry = {
                "code": code,
                "name": name,
                "survey": survey.lower(),
                "dimension": dimension.lower(),
            }
            if q == code_l or q == name_l:
                exact.append(entry)
            elif code_l.startswith(q) or name_l.startswith(q):
                starts.append(entry)
            elif q in code_l or q in name_l:
                contains.append(entry)

        results = exact + starts + contains
        return results[:max_results]


# Module-level singleton — loaded once at import time.
catalog = Catalog()
