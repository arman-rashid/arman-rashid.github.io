#!/usr/bin/env python3

import json
import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone


SCHOLAR_ID = "jS72zagAAAAJ"

OUTPUT_FILE = "scholar_stats.json"


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)



def get_profile_stats():

    from scholarly import scholarly

    author = scholarly.search_author_id(
        SCHOLAR_ID
    )

    author = scholarly.fill(
        author,
        sections=[
            "basics",
            "indices",
            "publications"
        ]
    )

    return author



def get_citations_since_2021():

    url = (
        "https://scholar.google.com/"
        "citations"
        f"?user={SCHOLAR_ID}"
        "&hl=en"
        "&view_op=list_works"
        "&pagesize=100"
        "&as_ylo=2021"
    )


    headers = {
        "User-Agent":
        "Mozilla/5.0"
    }


    r = requests.get(
        url,
        headers=headers,
        timeout=20
    )


    if r.status_code != 200:
        return 0


    soup = BeautifulSoup(
        r.text,
        "html.parser"
    )


    citations = 0


    rows = soup.find_all(
        "tr",
        class_="gsc_a_tr"
    )


    for row in rows:

        cells = row.find_all(
            "td"
        )


        if len(cells) < 2:
            continue


        try:

            cited = cells[1].text.strip()

            if cited:
                citations += int(cited)

        except Exception:
            pass


    return citations



def main():

    author = get_profile_stats()


    citations_since_2021 = (
        get_citations_since_2021()
    )


    stats = {

        "total_citations":
            author.get(
                "citedby",
                0
            ),

        "citations_since_2021":
            citations_since_2021,

        "h_index":
            author.get(
                "hindex",
                0
            ),

        "i10_index":
            author.get(
                "i10index",
                0
            ),

        "num_publications":
            len(
                author.get(
                    "publications",
                    []
                )
            ),

        "last_updated":
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d"
            )
    }


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            stats,
            f,
            indent=2
        )


    print(json.dumps(
        stats,
        indent=2
    ))



if __name__ == "__main__":
    main()
