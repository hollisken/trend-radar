"""One collection pass: fetch each enabled source, normalize, dedupe within the run."""
from __future__ import annotations

import datetime as dt
import time
from collections import Counter

from . import classify, dedup, fetch, normalize
from .sources import arxiv, github, rss

PARSERS = {"rss": rss.parse, "arxiv": arxiv.parse, "github": github.parse}
SCHEMA_VERSION = 1
TERMS_NOTE = ("Metadata only: titles, links, dates, publisher summaries, abstracts and "
              "repository descriptions. No article bodies, images or paywalled text. "
              "See POLICY.md.")


def _request(source: dict, today: dt.date) -> tuple[str, str]:
    if source["kind"] == "rss":
        return source["url"], "application/rss+xml, application/atom+xml;q=0.9, */*;q=0.5"
    if source["kind"] == "arxiv":
        return arxiv.build_url(source["query"], source["max_items"]), "application/atom+xml"
    days = int(source.get("since_days", 7))
    query = source["query"].replace("{since}", (today - dt.timedelta(days=days)).isoformat())
    return github.build_url(query, source["max_items"]), "application/vnd.github+json"


VIA = {"rss": "RSS", "arxiv": "arXiv API", "github": "GitHub API", "searx": "SearXNG"}


def build_item(raw: dict, topics: dict | None, retrieved_at: str,
               collector: str = "local") -> dict | None:
    url = normalize.canonical_url(raw.get("url", ""))
    title = normalize.clean_text(raw.get("title", ""), 200)
    if not url or "//" not in url or not title:
        return None
    kind = raw.get("kind", "news")
    item = {
        "id": dedup.item_id(url),
        "title": title,
        "url": url,
        "publisher": normalize.clean_text(raw.get("publisher") or "", 80),
        "kind": kind,
        "published_at": normalize.parse_date(raw.get("published_at", "")),
        "summary": normalize.clean_text(raw.get("summary", "")),
        "topics": classify.classify(title, raw.get("summary", ""), topics, kind),
        "retrieved_at": retrieved_at,
        "collector": collector,
        "via": VIA.get(raw.get("source_kind", "rss"), raw.get("source_kind", "")),
        "search_engine": raw.get("engine", ""),
        "sightings": [{"source_id": raw["source_id"], "collector": collector,
                       "via": VIA.get(raw.get("source_kind", "rss"), raw.get("source_kind", "")),
                       "engine": raw.get("engine", ""), "retrieved_at": retrieved_at}],
    }
    if raw.get("meta"):
        item["meta"] = raw["meta"]
    return item


def summarize(items: list[dict]) -> dict:
    by_topic: Counter = Counter()
    by_kind: Counter = Counter()
    for item in items:
        by_kind[item.get("kind", "news")] += 1
        for topic in item.get("topics", [])[:1]:
            by_topic[topic["name"]] += 1
    return {
        "items": len(items),
        "by_topic": dict(sorted(by_topic.items(), key=lambda pair: (-pair[1], pair[0]))),
        "by_kind": dict(sorted(by_kind.items())),
        "rules_version": classify.RULES_VERSION,
    }


def collect(config: dict, date: str, run_at: str, only: set[str] | None = None,
            fetcher=None, collector: str | None = None) -> dict:
    """Walk the sources once and return a run artifact ready to merge."""
    fetcher = fetcher or fetch.get
    collector = collector or config.get("settings", {}).get("collector") or "local"
    today = dt.date.fromisoformat(date)
    topics = config.get("topics") or None
    sources_report: list[dict] = []
    collected: list[dict] = []
    seen_urls: Counter = Counter()
    for source_id, source in sorted(config["sources"].items()):
        if not source.get("enabled", True) or (only and source_id not in only):
            continue
        started = time.monotonic()
        report = {"id": source_id, "kind": source["kind"], "status": "ok", "items": 0, "error": ""}
        try:
            url, accept = _request(source, today)
            result = fetcher(url, timeout=source["timeout"], max_bytes=source["max_bytes"],
                             min_interval=source["min_interval"], accept=accept)
            if not result.ok:
                report.update(status="error", error=result.error or f"http_{result.status}")
            else:
                raw_items = PARSERS[source["kind"]](result.body, source)[:source["max_items"]]
                for raw in raw_items:
                    raw["source_kind"] = source["kind"]
                    item = build_item(raw, topics, run_at, collector)
                    if item is None:
                        continue
                    seen_urls[item["url"]] += 1
                    collected.append(item)
                report["items"] = len(raw_items)
        except Exception as exc:  # one bad source must not stop the run
            report.update(status="error", error=f"{type(exc).__name__}: {exc}"[:200])
        report["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        sources_report.append(report)
    items, merge_stats = dedup.merge_items([], collected)
    stats = summarize(items)
    stats.update({"duplicates_in_run": merge_stats.get("duplicates", 0),
                  "title_duplicates": merge_stats.get("title_duplicates", 0)})
    return {
        "schema_version": SCHEMA_VERSION,
        "run_at": run_at,
        "date": date,
        "collector": collector,
        "sources": sources_report,
        "items": items,
        "stats": stats,
        "terms_note": TERMS_NOTE,
    }
