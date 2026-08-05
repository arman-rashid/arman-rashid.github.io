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



def setup_proxy():
    """Route scholarly's requests through free rotating proxies.

    Google Scholar aggressively blocks the fixed IP ranges used by GitHub
    Actions runners, so requests made directly from the workflow are often
    blocked/captcha'd. scholarly ships a free-proxy pool (no paid service
    needed) that rotates the source IP for us. If it fails to find a
    working proxy (e.g. all free proxies are currently dead), fall back to
    a direct connection rather than hard-failing the whole run.
    """

    from scholarly import scholarly, ProxyGenerator

    pg = ProxyGenerator()

    try:
        success = pg.FreeProxies()
    except Exception as e:
        logging.warning(f"Could not set up free proxy pool: {e}")
        success = False

    if success:
        scholarly.use_proxy(pg)
        logging.info("Using a free rotating proxy for Scholar requests.")
    else:
        logging.warning(
            "No working free proxy found; continuing without a proxy "
            "(requests may get blocked by Google)."
        )

    return pg if success else None


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



def get_working_free_proxy(attempts=5):
    """Return a {'http':..., 'https':...} proxies dict from a free proxy,
    or None if none could be found. Uses the same free-proxy pool that
    scholarly's ProxyGenerator.FreeProxies() draws from."""

    try:
        from fp.fp import FreeProxy
    except Exception as e:
        logging.warning(f"free-proxy package not available: {e}")
        return None

    for _ in range(attempts):
        try:
            proxy = FreeProxy(rand=True, timeout=1).get()
        except Exception:
            continue
        if proxy:
            return {"http": proxy, "https": proxy}

    return None


def get_citations_since_2021(proxies=None):

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
        proxies=proxies,
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

    setup_proxy()

    author = get_profile_stats()


    citations_since_2021 = (
        get_citations_since_2021(
            proxies=get_working_free_proxy()
        )
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
