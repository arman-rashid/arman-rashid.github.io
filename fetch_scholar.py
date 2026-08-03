#!/usr/bin/env python3
"""
Fetch Google Scholar stats and save to JSON.
Run this weekly via GitHub Action.
"""
import json
import sys
from scholarly import scholarly

SCHOLAR_ID = "jS72zagAAAAJ"   # your Google Scholar ID
OUTPUT_FILE = "scholar_stats.json"

def get_scholar_stats(user_id):
    try:
        # Search for the author
        search_query = scholarly.search_author_id(user_id)
        author = scholarly.fill(search_query, sections=['basics', 'indices', 'cites_per_year'])
        # Extract data
        total_citations = author.get('citedby', 0)
        h_index = author.get('hindex', 0)
        i10_index = author.get('i10index', 0)
        # Citations per year – sum from 2021 onward
        cites_per_year = author.get('cites_per_year', {})
        citations_since_2021 = sum(
            count for year, count in cites_per_year.items()
            if int(year) >= 2021
        )
        return {
            "total_citations": total_citations,
            "citations_since_2021": citations_since_2021,
            "h_index": h_index,
            "i10_index": i10_index,
        }
    except Exception as e:
        print(f"Error fetching scholar data: {e}", file=sys.stderr)
        return None

def main():
    stats = get_scholar_stats(SCHOLAR_ID)
    if stats is None:
        # Keep existing file if we can't fetch new data
        print("No new data – leaving existing JSON untouched.", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Scholar stats written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
