"""Source configuration loading and validation (stdlib tomllib)."""
from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "sources.toml"
KINDS = {"rss", "arxiv", "github"}
REQUIRED = {"rss": ("url", "publisher"), "arxiv": ("query",), "github": ("query",)}
DEFAULTS = {"timeout": 15, "max_bytes": 2_000_000, "min_interval": 2.0,
            "max_items": 25, "max_topic_tags": 3}


def load(path: Path | str | None = None) -> dict:
    config_path = Path(path) if path else DEFAULT_CONFIG
    with open(config_path, "rb") as handle:
        raw = tomllib.load(handle)
    settings = {**DEFAULTS, **raw.get("settings", {})}
    sources = {}
    for source_id, spec in raw.get("sources", {}).items():
        kind = spec.get("kind")
        if kind not in KINDS:
            raise ValueError(f"source {source_id}: unknown kind {kind!r}")
        missing = [field for field in REQUIRED[kind] if not spec.get(field)]
        if missing:
            raise ValueError(f"source {source_id}: missing {', '.join(missing)}")
        entry = {**settings, **spec}
        entry["id"] = source_id
        entry.setdefault("enabled", True)
        sources[source_id] = entry
    topics = {}
    for name, spec in raw.get("topics", {}).items():
        keywords = spec.get("keywords") if isinstance(spec, dict) else spec
        if not keywords:
            raise ValueError(f"topic {name}: no keywords")
        topics[name] = list(keywords)
    return {"sources": sources, "topics": topics, "settings": settings}
