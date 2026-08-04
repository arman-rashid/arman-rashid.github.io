#!/usr/bin/env python3
"""
Fetch Google Scholar statistics and save them to a JSON file.

Statistics collected:
    - Total citations
    - Citations since 2021
    - h-index
    - i10-index
    - Number of publications
    - Last update timestamp (UTC)

Designed for scheduled execution (e.g. GitHub Actions).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scholarly import scholarly

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

SCHOLAR_ID = "jS72zagAAAAJ"
OUTPUT_FILE = Path("scholar_stats.json")
CITATION_START_YEAR = 2021

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)


# ---------------------------------------------------------------------
# Scholar functions
# ---------------------------------------------------------------------

def fetch_author(author_id: str) -> dict[str, Any]:
    """
    Retrieve and fully populate a Google Scholar author profile.

    Parameters
    ----------
    author_id
        Google Scholar author ID.

    Returns
    -------
    dict
        Filled author dictionary.

    Raises
    ------
    Exception
        Any exception raised by scholarly is propagated to the caller.
    """
    author = scholarly.search_author_id(author_id)

    return scholarly.fill(
        author,
        sections=[
            "basics",
            "indices",
            "cites_per_year",
            "publications",
        ],
    )


def calculate_recent_citations(
    cites_per_year: dict[Any, int],
    start_year: int,
) -> int:
    """
    Sum citations beginning with a given year.
    """
    total = 0

    for year, count in cites_per_year.items():
        try:
            if int(year) >= start_year:
                total += count
        except (TypeError, ValueError):
            continue

    return total


def extract_statistics(author: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a Scholar author record into a simplified statistics dictionary.
    """
    cites_per_year = author.get("cites_per_year", {})
    publications = author.get("publications", [])

    return {
        "total_citations": author.get("citedby", 0),
        "citations_since_2021": calculate_recent_citations(
            cites_per_year,
            CITATION_START_YEAR,
        ),
        "h_index": author.get("hindex", 0),
        "i10_index": author.get("i10index", 0),
        "num_publications": len(publications),
        "last_updated": datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d"),
    }


def save_statistics(stats: dict[str, Any], output_file: Path) -> None:
    """
    Save statistics to a JSON file.
    """
    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            stats,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> int:
    """
    Entry point.
    """
    try:
        logging.info("Fetching Google Scholar profile...")

        author = fetch_author(SCHOLAR_ID)
        stats = extract_statistics(author)

        save_statistics(stats, OUTPUT_FILE)

        logging.info(
            "Scholar statistics written to %s",
            OUTPUT_FILE,
        )

        return 0

    except Exception as exc:
        logging.error("Unable to fetch Scholar data: %s", exc)

        # Do not overwrite an existing JSON file.
        logging.info("Existing JSON file has been left unchanged.")

        return 1


if __name__ == "__main__":
    sys.exit(main())
