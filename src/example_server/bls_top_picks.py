"""BLS Top Picks loader module.

Parses the local cache file ``local-cache/bls_top_picks`` (a plain-text file
downloaded from https://www.bls.gov/data/top-picks.htm) into structured Python
objects at import time.

Refresh procedure:
    1. Visit https://www.bls.gov/data/top-picks.htm and copy the series list.
    2. Update ``src/example_server/local-cache/bls_top_picks`` to match.
    3. Re-import this module (or restart the server) so ``TOP_PICKS`` is rebuilt.

Usage::

    from example_server.bls_top_picks import TOP_PICKS, TOP_PICKS_BY_ID, get_top_pick

    entry = get_top_pick("CUUR0000SA0")   # TopPickEntry or None
    for entry in TOP_PICKS:
        print(entry.category, entry.series_id, entry.title)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_CACHE_FILE = Path(__file__).parent / "local-cache" / "bls_top_picks"

# Matches lines like:
#   Title — SERIES_ID      (em-dash U+2014)
#   Title - SERIES_ID      (ASCII hyphen)
# The series ID is the last whitespace-delimited token after the separator.
_SERIES_LINE_RE = re.compile(
    r"^(?P<title>.+?)\s+[—\-]\s+(?P<series_id>[A-Z0-9]+)\s*$"
)


@dataclass(frozen=True)
class TopPickEntry:
    """A single BLS top-picks series with its category context.

    Attributes:
        category:  Section header from the top-picks file
                   (e.g. "Employment", "Productivity", "Price Indexes",
                   "Compensation").
        title:     Human-readable series title as it appears in the cache file.
        series_id: Exact BLS series ID string (upper-case).
    """

    category: str
    title: str
    series_id: str


def _parse_top_picks(path: Path) -> list[TopPickEntry]:
    """Parse *path* and return a list of :class:`TopPickEntry` objects.

    Raises:
        FileNotFoundError: if *path* does not exist.
        ValueError: if a non-blank, non-category line cannot be parsed as a
            series line, so regressions in the cache file are caught at
            import time.
    """
    entries: list[TopPickEntry] = []
    current_category = ""

    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()

        if not line:
            continue

        m = _SERIES_LINE_RE.match(line)
        if m:
            if not current_category:
                raise ValueError(
                    f"{path}:{lineno}: series line found before any category header: "
                    f"{line!r}"
                )
            entries.append(
                TopPickEntry(
                    category=current_category,
                    title=m.group("title").strip(),
                    series_id=m.group("series_id").upper(),
                )
            )
        else:
            # Lines without a dash separator are treated as category headers.
            current_category = line

    return entries


TOP_PICKS: list[TopPickEntry] = _parse_top_picks(_CACHE_FILE)

TOP_PICKS_BY_ID: dict[str, TopPickEntry] = {e.series_id: e for e in TOP_PICKS}


def get_top_pick(series_id: str) -> TopPickEntry | None:
    """Return the :class:`TopPickEntry` for an exact *series_id* match, or ``None``."""
    return TOP_PICKS_BY_ID.get(series_id.strip().upper())
