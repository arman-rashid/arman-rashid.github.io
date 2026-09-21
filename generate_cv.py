#!/usr/bin/env python3
"""
Generate CV from local index.html and manual JSON.
Reads the local index.html, extracts dynamic content,
reads images from the local filesystem, and renders cv_template.html.
"""
import io
import json
import re
import sys
import base64
import mimetypes
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# ---------- CONFIG ----------
MANUAL_JSON = "cv_manual.json"
TEMPLATE_FILE = "cv_template.html"
OUTPUT_FILE = "cv.html"
WEBSITE_URL = "https://arman-rashid.github.io/"  # fallback if local file missing

# Awards listed first on the CV, in this order (case-insensitive substring match on the title).
# Anything not matched keeps the site's order after these. Edit freely.
AWARD_FIRST = [
    "Prime Minister Research Fellowship", "INSPIRE", "JRF",
    "Gold Medalist", "Vasudevamurthy", "Best Poster", "Best Oral", "Best Presentation",
]

# ---------- HELPERS ----------
def fetch_html():
    """Read local index.html first, fallback to live URL."""
    local_file = Path("index.html")
    if local_file.exists():
        print("📂 Using local index.html", file=sys.stderr)
        return local_file.read_text(encoding="utf-8")
    
    # Fallback: fetch from live site
    try:
        print("🌐 Fetching from live URL (fallback)", file=sys.stderr)
        resp = requests.get(WEBSITE_URL, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"❌ Failed to fetch: {e}", file=sys.stderr)
        raise SystemExit("No data source available.")

def _shrink_image(raw, max_w=420):
    """Downscale a large portrait so the CV isn't ~250 KB heavier than needed.
    Optional: silently returns the original bytes if Pillow isn't installed."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw))
        im.load()
        if im.mode not in ("RGB", "L") or im.width <= max_w:
            return raw, None
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=84, optimize=True, progressive=True)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return raw, None


def extract_photo(soup, base_dir="."):
    """
    Extract profile image from .profile-ring img.
    If src is a local path (e.g., images/...), read it from disk and encode to base64.
    """
    img = soup.select_one(".profile-ring img")
    if not img:
        return ""
    src = img.get("src", "").strip()
    
    # If already base64, return as-is
    if src.startswith("data:image"):
        return src
    
    # If it's a relative local path, read from filesystem
    if not src.startswith("http"):
        img_path = Path(base_dir) / src
        if img_path.exists():
            try:
                mime_type, _ = mimetypes.guess_type(str(img_path))
                if not mime_type:
                    mime_type = "image/jpeg"
                with open(img_path, "rb") as f:
                    raw, small_mime = _shrink_image(f.read())
                b64 = base64.b64encode(raw).decode()
                return f"data:{small_mime or mime_type};base64,{b64}"
            except Exception as e:
                print(f"⚠️  Could not read local image {img_path}: {e}", file=sys.stderr)
                return src
    
    # If it's a full URL, fetch it and encode
    if src.startswith("http"):
        try:
            resp = requests.get(src, timeout=10)
            resp.raise_for_status()
            b64 = base64.b64encode(resp.content).decode()
            ext = src.split(".")[-1].lower()
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
            return f"data:{mime};base64,{b64}"
        except Exception as e:
            print(f"⚠️  Could not fetch remote image: {e}", file=sys.stderr)
            return src
    
    return src

def render_stats_note(scholar_stats):
    """Small note under the stats row showing when Scholar data last synced."""
    last_updated = (scholar_stats or {}).get("last_updated")
    if last_updated:
        return f"Source: Google Scholar, {last_updated}"
    return "Source: Google Scholar"


def load_scholar_stats(path="scholar_stats.json"):
    """Load scholar_stats.json if present, else return empty dict."""
    p = Path(path)
    if not p.exists():
        print(f"⚠️  {path} not found; JS-driven stats will show as '—'", file=sys.stderr)
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Could not parse {path}: {e}", file=sys.stderr)
        return {}


# Maps the stat-card's span id -> key in scholar_stats.json.
# These numbers are populated client-side by JS in index.html, so a static
# HTML scrape only ever sees the placeholder "…" - we must pull them from
# scholar_stats.json directly instead.
_SCHOLAR_STAT_IDS = {
    "num-publications": "num_publications",
    "total-citations": "total_citations",
    "citations-since-2021": "citations_since_2021",
    "h-index": "h_index",
    "i10-index": "i10_index",
}


def extract_stats(soup, scholar_stats=None):
    """Return list of (number, label) from ALL .stat-card entries.

    Cards whose number is written directly in the HTML are read as-is.
    Cards whose number is filled in by JS at runtime (identified by their
    span id) are instead read from scholar_stats.json.
    """
    scholar_stats = scholar_stats or {}
    stats = []
    cards = soup.select(".stats-fullwidth .stat-card")
    for card in cards:
        num_el = card.select_one(".number")
        label_el = card.select_one(".label")
        if not (num_el and label_el):
            continue

        span_id = num_el.get("id")
        if span_id in _SCHOLAR_STAT_IDS:
            n = scholar_stats.get(_SCHOLAR_STAT_IDS[span_id])
            n = str(n) if n is not None else "—"
        else:
            n = num_el.get_text(strip=True)

        # separator=" " avoids concatenating nested spans, e.g.
        # "Journal" + "Covers" -> "JournalCovers"
        lbl = label_el.get_text(separator=" ", strip=True)
        stats.append((n, lbl))

    # "204 Citations" next to "204 Citations since 2021" reads as a typo
    totals = {n for n, l in stats if l.strip().lower() == "citations"}
    stats = [(n, l) for n, l in stats
             if not (l.lower().startswith("citations since") and n in totals)]
    return stats

def extract_education(soup):
    """Return list of (year, degree, institution) from .edu-item."""
    edu = []
    items = soup.select(".edu-item")
    for item in items:
        year_el = item.select_one(".year")
        detail = item.select_one(".detail")
        if year_el and detail:
            year = year_el.get_text(strip=True)
            h4 = detail.select_one("h4")
            p = detail.select_one("p")
            degree = h4.get_text(strip=True) if h4 else ""
            inst = p.get_text(strip=True) if p else ""
            edu.append((year, degree, inst))
    return edu

def extract_publications(soup):
    """Return list of publications from .pub-item."""
    pubs = []
    items = soup.select(".pub-item")
    for item in items:
        info = item.select_one(".pub-info")
        if not info:
            continue
        title = info.select_one("h4")
        authors = info.select_one(".authors")
        journal = info.select_one(".journal")
        flag = ""
        if journal:
            badge = journal.select_one(".badge")
            if badge:
                flag = badge.get_text(strip=True)
                journal_text = journal.get_text(strip=True).replace(flag, "").strip()
            else:
                journal_text = journal.get_text(strip=True)
        else:
            journal_text = ""
        link = info.select_one("a[href*='doi.org']")
        doi = link["href"].split("doi.org/", 1)[1] if link else ""
        year_m = re.search(r"\b(?:19|20)\d{2}\b", journal_text)
        pubs.append({
            "year": int(year_m.group(0)) if year_m else 0,
            "doi": doi,
            "title": title.get_text(strip=True) if title else "",
            # decode_contents() (not get_text()) keeps inner tags like
            # <span class="gold">U. Rashid</span> so the CV can bold the
            # author's own name, and it preserves whitespace around tags
            # that get_text(strip=True) otherwise swallows (e.g. "Obel OB,
            # <span>U. Rashid</span>" losing the space before the span).
            "authors": authors.decode_contents().strip() if authors else "",
            "journal": journal_text,
            "flag": flag,
        })
    pubs.sort(key=lambda p: -p["year"])  # stable: newest first, site order kept within a year
    return pubs

def extract_awards(soup):
    """Return list of award strings from .award-card."""
    awards = []
    cards = soup.select(".award-card")
    for card in cards:
        title = card.select_one(".award-title")
        desc = card.select_one(".award-desc")
        if title:
            t = re.sub(r"^[\W_]+", "", title.get_text(strip=True))  # drop leading emoji
            d = desc.get_text(strip=True) if desc else ""
            awards.append((t, d))

    def rank(item):
        low = item[0].lower()
        for i, key in enumerate(AWARD_FIRST):
            if key.lower() in low:
                return i
        return len(AWARD_FIRST)
    awards.sort(key=rank)  # stable
    return awards

def render_stats(stats):
    html = ""
    for num, label in stats:
        html += f'<div><span>{num}</span>{label}</div>\n'
    return html

def render_education(edu):
    html = ""
    for year, degree, inst in reversed(edu):  # newest first
        html += f'''<div class="edu-item">
        <span class="edu-year">{year}</span>
        <span class="edu-deg">{degree}</span>
        <span class="edu-inst">{inst}</span>
      </div>\n'''
    return html

def _flag_html(flag):
    if not flag:
        return ""
    label = re.sub(r"^\s*featured\s*[-–—:]\s*", "", flag, flags=re.I)
    low = label.lower()
    kind = " flag-cover" if "cover" in low else " flag-hot" if "hot" in low else ""
    return f'<span class="flag{kind}">{label}</span>'

def render_publications(pubs):
    html = ""
    for p in pubs:
        doi = (f'<a class="doi" href="https://doi.org/{p["doi"]}" target="_blank" rel="noopener">'
               f'doi:{p["doi"]}</a>') if p.get("doi") else ""
        html += f'''<li class="pub">
          <div class="pub-title">{p["title"]}</div>
          <div class="pub-authors">{p["authors"]}</div>
          <div class="pub-venue"><span>{p["journal"]}</span>{_flag_html(p["flag"])}{doi}</div>
        </li>\n'''
    return html

def render_awards(awards):
    html = ""
    for title, desc in awards:
        html += f'<li><span class="aw-t">{title}</span><span class="aw-d">{desc}</span></li>\n'
    return html

def render_expertise(text):
    """The JSON paragraph has several paragraphs glued together ('...platforms.Developed...').
    Split at those glue points and at newlines so it reads as short paragraphs."""
    parts = []
    for block in text.split("\n"):
        parts += re.split(r"(?<=[a-z)])\.(?=[A-Z])", block)
    parts = [p.strip() + ("" if p.strip().endswith(".") else ".") for p in parts if p.strip()]
    return "\n".join(f"<p>{p}</p>" for p in parts)

# ---------- MAIN ----------
def main():
    # 1. Load manual JSON
    with open(MANUAL_JSON, "r", encoding="utf-8") as f:
        manual = json.load(f)

    # 2. Fetch HTML (local first, fallback to web)
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")

    # 3. Extract dynamic data (photo from local filesystem)
    scholar_stats = load_scholar_stats()
    photo_b64 = extract_photo(soup, base_dir=".")
    stats = extract_stats(soup, scholar_stats)
    edu = extract_education(soup)
    pubs = extract_publications(soup)
    awards = extract_awards(soup)

    # 4. Read template
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    # 5. Replace placeholders
    template = template.replace("<!-- PHOTO_BASE64 -->", photo_b64)
    template = template.replace("<!-- STATS -->", render_stats(stats))
    template = template.replace("<!-- STATS_NOTE -->", render_stats_note(scholar_stats))
    template = template.replace("<!-- EDUCATION -->", render_education(edu))
    template = template.replace("<!-- PUBLICATIONS -->", render_publications(pubs))
    template = template.replace("<!-- AWARDS -->", render_awards(awards))
    template = template.replace("<!-- EXPERTISE -->", render_expertise(manual["expertise_paragraph"]))

    skills_general = manual["skills"].get("General & Design", [])
    skills_instr = manual["skills"].get("Instrumentation & Spectroscopy", [])
    gen_li = "\n".join(f"<li>{s}</li>" for s in skills_general)
    instr_li = "\n".join(f"<li>{s}</li>" for s in skills_instr)
    template = template.replace("<!-- SKILLS_GENERAL -->", gen_li)
    template = template.replace("<!-- SKILLS_INSTR -->", instr_li)

    # 6. Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"✅ CV generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
