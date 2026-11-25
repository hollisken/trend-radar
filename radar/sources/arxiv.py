"""arXiv API: metadata for recent papers matching a query."""
from __future__ import annotations

from urllib.parse import quote

from xml.etree import ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"
API = "http://export.arxiv.org/api/query"


def build_url(query: str, max_results: int) -> str:
    return (f"{API}?search_query={quote(query)}&start=0&max_results={max_results}"
            "&sortBy=submittedDate&sortOrder=descending")


def parse(body: bytes, source: dict) -> list[dict]:
    root = ET.fromstring(body)
    items = []
    for entry in root.findall(f"{ATOM}entry"):
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
        if not title:
            continue
        authors = [(author.findtext(f"{ATOM}name") or "").strip()
                   for author in entry.findall(f"{ATOM}author")][:3]
        items.append({
            "source_id": source["id"],
            "kind": "paper",
            "publisher": "arXiv",
            "title": title,
            "url": (entry.findtext(f"{ATOM}id") or "").strip(),
            "published_at": (entry.findtext(f"{ATOM}published") or "").strip(),
            "summary": " ".join((entry.findtext(f"{ATOM}summary") or "").split()),
            "meta": {"authors": [name for name in authors if name]},
        })
    return items
