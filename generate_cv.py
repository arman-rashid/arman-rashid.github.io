#!/usr/bin/env python3
"""
Generate CV from local index.html and manual JSON.
Reads the local index.html, extracts dynamic content,
reads images from the local filesystem, and renders cv_template.html.
"""
import json
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
                    b64 = base64.b64encode(f.read()).decode()
                return f"data:{mime_type};base64,{b64}"
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

def extract_stats(soup):
    """Return list of (number, label) from .stat-card - only first 4."""
    stats = []
    cards = soup.select(".stats-fullwidth .stat-card")
    for card in cards[:4]:
        num = card.select_one(".number")
        label = card.select_one(".label")
        if num and label:
            n = num.get_text(strip=True)
            lbl = label.get_text(strip=True)
            stats.append((n, lbl))
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
        pubs.append({
            "title": title.get_text(strip=True) if title else "",
            "authors": authors.get_text(strip=True) if authors else "",
            "journal": journal_text,
            "flag": flag,
        })
    return pubs

def extract_awards(soup):
    """Return list of award strings from .award-card."""
    awards = []
    cards = soup.select(".award-card")
    for card in cards:
        title = card.select_one(".award-title")
        desc = card.select_one(".award-desc")
        if title:
            t = title.get_text(strip=True)
            d = desc.get_text(strip=True) if desc else ""
            awards.append((t, d))
    return awards

def render_stats(stats):
    html = ""
    for num, label in stats:
        html += f'<div><span>{num}</span>{label}</div>\n'
    return html

def render_education(edu):
    html = ""
    for year, degree, inst in edu:
        html += f'''<div class="edu-item">
        <span class="edu-year">{year}</span><br>
        <span class="edu-deg">{degree}</span><br>
        <span class="edu-inst">{inst}</span>
      </div>\n'''
    return html

def render_publications(pubs):
    html = ""
    for idx, p in enumerate(pubs, 1):
        num = f"{idx:02d}"
        flag_html = f'<span class="pub-flag">{p["flag"]}</span>' if p["flag"] else ""
        html += f'''<li class="pub">
          <span class="pub-num">{num}</span>
          <div>
            <div class="pub-title">{p["title"]}</div>
            <div class="pub-authors">{p["authors"]}</div>
            <div class="pub-venue">{p["journal"]} {flag_html}</div>
          </div>
        </li>\n'''
    return html

def render_awards(awards):
    html = ""
    for title, desc in awards:
        html += f'<li><b>{title}</b> — {desc}</li>\n'
    return html

# ---------- MAIN ----------
def main():
    # 1. Load manual JSON
    with open(MANUAL_JSON, "r", encoding="utf-8") as f:
        manual = json.load(f)

    # 2. Fetch HTML (local first, fallback to web)
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")

    # 3. Extract dynamic data (photo from local filesystem)
    photo_b64 = extract_photo(soup, base_dir=".")
    stats = extract_stats(soup)
    edu = extract_education(soup)
    pubs = extract_publications(soup)
    awards = extract_awards(soup)

    # 4. Read template
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    # 5. Replace placeholders
    template = template.replace("<!-- PHOTO_BASE64 -->", photo_b64)
    template = template.replace("<!-- STATS -->", render_stats(stats))
    template = template.replace("<!-- EDUCATION -->", render_education(edu))
    template = template.replace("<!-- PUBLICATIONS -->", render_publications(pubs))
    template = template.replace("<!-- AWARDS -->", render_awards(awards))
    template = template.replace("<!-- EXPERTISE -->", f'<p>{manual["expertise_paragraph"]}</p>')

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
