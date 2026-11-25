"""GitHub Search API: recently created repositories with traction."""
from __future__ import annotations

import json
from urllib.parse import urlencode

API = "https://api.github.com/search/repositories"


def build_url(query: str, per_page: int) -> str:
    params = urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": per_page})
    return f"{API}?{params}"


def parse(body: bytes, source: dict) -> list[dict]:
    payload = json.loads(body)
    items = []
    for repo in payload.get("items", []):
        url = repo.get("html_url") or ""
        name = repo.get("full_name") or ""
        if not url or not name:
            continue
        items.append({
            "source_id": source["id"],
            "kind": "repo",
            "publisher": (repo.get("owner") or {}).get("login") or "",
            "title": name,
            "url": url,
            "published_at": repo.get("created_at") or "",
            "summary": repo.get("description") or "",
            "meta": {"stars": repo.get("stargazers_count"), "language": repo.get("language"),
                     "topics": (repo.get("topics") or [])[:5]},
        })
    return items
