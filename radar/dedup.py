"""Deduplication: one record per canonical URL, every sighting kept."""
from __future__ import annotations

import hashlib
from collections import Counter


def item_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def title_key(title: str) -> str:
    normalized = " ".join((title or "").lower().split())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def merge_items(existing: list[dict], incoming: list[dict]) -> tuple[list[dict], dict]:
    """Merge incoming items into existing ones by id.

    The same URL seen by several sources stays one record; each sighting is kept so
    provenance is never lost. Identical titles on different URLs are kept and only
    counted, because distinct articles can legitimately share a headline.
    """
    by_id = {item["id"]: item for item in existing}
    title_owners = {title_key(item["title"]): item["id"] for item in existing}
    stats = Counter(added=0, duplicates=0, title_duplicates=0)
    for item in incoming:
        current = by_id.get(item["id"])
        if current is None:
            other = title_owners.get(title_key(item["title"]))
            if other and other != item["id"]:
                stats["title_duplicates"] += 1
                item.setdefault("flags", []).append("duplicate_title")
            title_owners.setdefault(title_key(item["title"]), item["id"])
            by_id[item["id"]] = item
            stats["added"] += 1
            continue
        stats["duplicates"] += 1
        fields = ("source_id", "collector", "via", "engine", "url")
        seen = {tuple(sighting.get(field, "") for field in fields)
                for sighting in current.get("sightings", [])}
        for sighting in item.get("sightings", []):
            key = tuple(sighting.get(field, "") for field in fields)
            if key not in seen:
                current.setdefault("sightings", []).append(sighting)
                seen.add(key)
        for field in ("published_at", "summary", "topics", "title_zh"):
            if not current.get(field) and item.get(field):
                current[field] = item[field]
    merged = sorted(by_id.values(), key=lambda row: (row.get("published_at") or "", row["id"]),
                    reverse=True)
    return merged, dict(stats)
