# New in this fork. In Oct 2026 LinkedIn started redirecting /jobs/search/ to
# an "AI job search" page (/jobs/search-results) whose markup the tile
# scraper in job_manager.py can't read, and which silently replaces the
# requested location. LinkedIn's public (guest) job endpoints still honor
# keywords/location/f_* filters and return plain HTML, so listings and
# descriptions come from there; the logged-in browser is only used to resolve
# each job's apply target.

import html
import re
from html.parser import HTMLParser
from typing import Iterator

BASE = "https://www.linkedin.com/jobs-guest/jobs/api"
CARD_RE = re.compile(r'<li>(.*?)</li>', re.S)
JOB_ID_RE = re.compile(r'urn:li:jobPosting:(\d+)')
FIELD_RES = {
    "title": re.compile(r'base-search-card__title">\s*(.*?)\s*</h3>', re.S),
    "company": re.compile(r'base-search-card__subtitle">.*?(?:<a[^>]*>)?\s*(.*?)\s*(?:</a>)?\s*</h4>', re.S),
    "location": re.compile(r'job-search-card__location">\s*(.*?)\s*</span>', re.S),
}
DESCRIPTION_RE = re.compile(r'show-more-less-html__markup[^>]*>(.*?)</div>', re.S)


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "br", "li", "div", "ul", "ol", "h1", "h2", "h3", "h4"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n\s*\n+", "\n\n", "".join(self.parts)).strip()


def _clean(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def search_cards(request, query: str, keywords: str, location: str, start: int) -> list[dict]:
    """One page (~10 jobs) of guest search results. `query` is the f_*/distance
    string built by JobManager._get_base_search_url (leading '?')."""
    url = (f"{BASE}/seeMoreJobPostings/search{query}&keywords={keywords}"
           f"&location={location}&start={start}")
    resp = request.get(url)
    if resp.status != 200:
        raise RuntimeError(f"guest search HTTP {resp.status}")
    cards = []
    for block in CARD_RE.findall(resp.text()):
        m = JOB_ID_RE.search(block)
        if not m:
            continue
        card = {"job_id": m.group(1)}
        for key, rx in FIELD_RES.items():
            f = rx.search(block)
            card[key] = _clean(f.group(1)) if f else ""
        cards.append(card)
    return cards


def job_description(request, job_id: str) -> str:
    resp = request.get(f"{BASE}/jobPosting/{job_id}")
    if resp.status != 200:
        return ""
    m = DESCRIPTION_RE.search(resp.text())
    if not m:
        return ""
    parser = _TextExtractor()
    parser.feed(m.group(1))
    return parser.text()
