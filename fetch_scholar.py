#!/usr/bin/env python3
import json
import sys
from scholarly import scholarly

SCHOLAR_ID = "jS72zagAAAAJ"
OUTPUT_FILE = "scholar_stats.json"

def get_scholar_stats(user_id):
    try:
        search_query = scholarly.search_author_id(user_id)
        author = scholarly.fill(search_query, sections=['basics', 'indices', 'cites_per_year'])
        total_citations = author.get('citedby', 0)
        h_index = author.get('hindex', 0)
        i10_index = author.get('i10index', 0)
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
        print(f"Error: {e}", file=sys.stderr)
        return None

def main():
    stats = get_scholar_stats(SCHOLAR_ID)
    if stats is None:
        print("No data – keeping existing JSON.", file=sys.stderr)
        sys.exit(1)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
