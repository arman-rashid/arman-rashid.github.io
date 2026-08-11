#!/usr/bin/env python3
import json
import os
import logging
import requests
from datetime import datetime, timezone

SCHOLAR_ID = "jS72zagAAAAJ"
OUTPUT_FILE = "scholar_stats.json"
SERPAPI_URL = "https://serpapi.com/search.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)


def get_api_key():
    key = os.environ.get("a163598bd2e93e8b439ce22c3b8253df46d02a0db0f6e0e93328819d5bf561c1")
    if not key:
        raise RuntimeError(
            "SERPAPI_KEY environment variable not set. "
            "Add it as a GitHub Actions secret and pass it into the workflow step."
        )
    return key


def fetch_author_data(api_key):
    """Single call to SerpApi's google_scholar_author engine.
    num=100 pulls up to 100 articles in one page (sorted by year desc),
    which comfortably covers a normal-sized publication list without
    needing pagination.
    """
    params = {
        "engine": "google_scholar_author",
        "author_id": SCHOLAR_ID,
        "hl": "en",
        "num": 100,
        "sort": "pubdate",
        "api_key": api_key,
    }
    r = requests.get(SERPAPI_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    if "error" in data:
        raise RuntimeError(f"SerpApi error: {data['error']}")

    return data


def extract_cited_by_table(data):
    """cited_by.table has rows like:
    [{"citations": {"all": N, "since_20XX": M}},
     {"h_index": {"all": N, "since_20XX": M}},
     {"i10_index": {"all": N, "since_20XX": M}}]
    The 'since_20XX' key name shifts every year (rolling ~5yr window),
    so find it dynamically rather than hardcoding a year.
    """
    table = data.get("cited_by", {}).get("table", [])
    result = {"total_citations": 0, "h_index": 0, "i10_index": 0}

    for entry in table:
        if "citations" in entry:
            result["total_citations"] = entry["citations"].get("all", 0)
        elif "h_index" in entry:
            result["h_index"] = entry["h_index"].get("all", 0)
        elif "i10_index" in entry:
            result["i10_index"] = entry["i10_index"].get("all", 0)

    return result


def compute_citations_since_2021(data):
    articles = data.get("articles", [])
    total = 0
    for article in articles:
        try:
            year = int(article.get("year", 0))
        except (TypeError, ValueError):
            year = 0
        if year >= 2021:
            cited = article.get("cited_by", {}).get("value", 0)
            try:
                total += int(cited)
            except (TypeError, ValueError):
                pass
    return total


def fetch_fresh_stats():
    api_key = get_api_key()
    data = fetch_author_data(api_key)

    stats = extract_cited_by_table(data)
    stats["citations_since_2021"] = compute_citations_since_2021(data)
    stats["num_publications"] = len(data.get("articles", []))
    stats["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return stats


def main():
    try:
        stats = fetch_fresh_stats()
    except Exception as e:
        # Don't let a transient API hiccup take down the whole CV build —
        # keep whatever stats we last successfully fetched instead.
        logging.error(f"Failed to fetch fresh Scholar stats: {e}")
        if os.path.exists(OUTPUT_FILE):
            logging.warning(
                f"Leaving existing {OUTPUT_FILE} untouched so the CV "
                "build can continue with the last known-good stats."
            )
        else:
            logging.warning(
                f"No existing {OUTPUT_FILE} to fall back to; "
                "downstream steps may need to handle a missing file."
            )
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()