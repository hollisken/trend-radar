"""Minimal static index: no JavaScript, no external assets."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .digest import TOPIC_EN, TOPIC_ZH, _highlights

STYLE = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:52rem;margin:2rem auto;
padding:0 1rem;line-height:1.55;color:#1b1b1b;background:#fff}
h1{font-size:1.5rem;margin:0 0 .25rem}h2{font-size:1.1rem;margin:2rem 0 .5rem}
.meta{color:#666;font-size:.9rem}ul{padding-left:1.1rem}li{margin:.25rem 0}
a{color:#0b5cad;text-decoration:none}a:hover{text-decoration:underline}
@media (prefers-color-scheme:dark){body{background:#111;color:#e8e8e8}.meta{color:#9a9a9a}a{color:#79b8ff}}
"""


def _load(data_dir: Path, days: int) -> list[dict]:
    rows = []
    for path in sorted(data_dir.glob("20??-??-??.json"), reverse=True)[:days]:
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return rows


def build(data_dir: Path, days: int = 7) -> str:
    rows = _load(data_dir, days)
    parts = ["<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             "<title>Trend Radar</title>", f"<style>{STYLE}</style></head><body>",
             "<h1>Trend Radar · 趋势雷达</h1>",
             '<p class="meta">Public metadata only: headlines, links, dates and publisher '
             "summaries. No article bodies or images.</p>"]
    if not rows:
        parts.append("<p>No data yet.</p>")
    for payload in rows:
        date = html.escape(payload.get("date", ""))
        stats = payload.get("stats", {})
        topics = ", ".join(f"{TOPIC_EN.get(name, name)} / {TOPIC_ZH.get(name, name)} {count}"
                           for name, count in list(stats.get("by_topic", {}).items())[:4])
        parts.append(f"<h2>{date}</h2>")
        parts.append(f'<p class="meta">{stats.get("items", 0)} items · {topics or "no topics"}</p>')
        highlights = _highlights(payload.get("items", []), per_topic=1, limit=5)
        if highlights:
            parts.append("<ul>")
            for topic, item in highlights:
                label = html.escape(TOPIC_EN.get(topic, topic))
                title = html.escape(item.get("title", ""))
                url = html.escape(item.get("url", ""))
                publisher = html.escape(item.get("publisher", ""))
                parts.append(f'<li><strong>{label}</strong> — <a href="{url}" rel="noopener nofollow" '
                             f'target="_blank">{title}</a> <span class="meta">{publisher}</span></li>')
            parts.append("</ul>")
        parts.append(f'<p class="meta"><a href="digest/{date}.md">Digest · 日报</a></p>')
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"
