"""RSS 2.0 and Atom parsing. Publisher-provided fields only."""
from __future__ import annotations

from xml.etree import ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"


def _text(element, *tags: str) -> str:
    for tag in tags:
        found = element.find(tag)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return ""


def _atom_link(entry) -> str:
    fallback = ""
    for link in entry.findall(f"{ATOM}link"):
        href = link.get("href", "").strip()
        if not href:
            continue
        if link.get("rel") in (None, "alternate"):
            return href
        fallback = fallback or href
    return fallback


def parse(body: bytes, source: dict) -> list[dict]:
    """Return raw items for the collector; no cleaning or dedup here."""
    root = ET.fromstring(body)
    items: list[dict] = []
    if root.tag.endswith("rss") or root.find("channel") is not None:
        channel = root.find("channel") or root
        for entry in channel.findall("item"):
            items.append({
                "source_id": source["id"],
                "kind": "news",
                "publisher": source["publisher"],
                "title": _text(entry, "title"),
                "url": _text(entry, "link"),
                "published_at": _text(entry, "pubDate"),
                "summary": _text(entry, "description", CONTENT),
            })
        return items
    if root.tag == f"{ATOM}feed":
        for entry in root.findall(f"{ATOM}entry"):
            items.append({
                "source_id": source["id"],
                "kind": "news",
                "publisher": source.get("publisher") or source["id"],
                "title": _text(entry, f"{ATOM}title"),
                "url": _atom_link(entry) or _text(entry, f"{ATOM}id"),
                "published_at": _text(entry, f"{ATOM}published", f"{ATOM}updated"),
                "summary": _text(entry, f"{ATOM}summary", f"{ATOM}content"),
            })
        return items
    raise ValueError(f"unsupported feed root {root.tag}")
