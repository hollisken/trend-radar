"""Minimal static index: no JavaScript, no external assets."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from .digest import TOPIC_EN, TOPIC_ZH, _highlights, provenance

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
        topics = " · ".join(
            f'<a href="topic/{name}.html#day-{date}">{TOPIC_EN.get(name, name)} / '
            f'{TOPIC_ZH.get(name, name)} {count}</a>'
            for name, count in stats.get("by_topic", {}).items())
        parts.append(f"<h2>{date}</h2>")
        parts.append(f'<p class="meta">{stats.get("items", 0)} items · {topics or "no topics"}</p>')
        highlights = _highlights(payload.get("items", []), per_topic=1, limit=5)
        if highlights:
            parts.append("<ul>")
            for topic, item in highlights:
                label = html.escape(TOPIC_EN.get(topic, topic))
                title = html.escape(item.get("title", ""))
                url = html.escape(item.get("url", ""))
                source = html.escape(provenance(item))
                parts.append(f'<li><strong>{label}</strong> — <a href="{url}" rel="noopener nofollow" '
                             f'target="_blank">{title}</a> <span class="meta">· {source}</span></li>')
            parts.append("</ul>")
        parts.append(f'<p class="meta"><a href="digest/{date}.html">Digest · 日报</a></p>')
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")


def render_markdown(text: str) -> str:
    """Render the small Markdown subset used by the digest; everything is escaped first."""
    out: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in text.splitlines():
        line = raw.rstrip()
        escaped = html.escape(line)
        escaped = LINK.sub(lambda m: f'<a href="{m.group(2)}" rel="noopener nofollow">{m.group(1)}</a>',
                           escaped)
        escaped = BOLD.sub(r"<strong>\1</strong>", escaped)
        if not line.strip():
            close_list()
            continue
        if line.startswith("## "):
            close_list()
            out.append(f"<h2>{escaped[3:]}</h2>")
        elif line.startswith("# "):
            close_list()
            out.append(f"<h1>{escaped[2:]}</h1>")
        elif line.strip() == "---":
            close_list()
            out.append("<hr>")
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{escaped[2:]}</li>")
        else:
            close_list()
            out.append(f"<p>{escaped}</p>")
    close_list()
    return "\n".join(out)


def build_digest_pages(digest_dir: Path, site_dir: Path) -> int:
    """Render every digest/*.md into site/digest/*.html so the published site is self-contained."""
    target = site_dir / "digest"
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(digest_dir.glob("20??-??-??.md")):
        body = render_markdown(path.read_text(encoding="utf-8"))
        page = ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                f"<title>Trend Radar · {path.stem}</title><style>{STYLE}</style></head><body>"
                f"{body}\n<p class=\"meta\"><a href=\"../index.html\">← Trend Radar</a></p>"
                "</body></html>\n")
        (target / f"{path.stem}.html").write_text(page, encoding="utf-8")
        count += 1
    return count


def build_topic_pages(data_dir: Path, days: int, site_dir: Path) -> int:
    """Show each day's primary-topic items by their recorded acquisition source."""
    grouped: dict[str, dict[str, list[dict]]] = {}
    for payload in _load(data_dir, days):
        for item in payload.get("items", []):
            if topics := item.get("topics"):
                grouped.setdefault(topics[0]["name"], {}).setdefault(payload["date"], []).append(item)
    target = site_dir / "topic"
    target.mkdir(parents=True, exist_ok=True)
    for name, dates in grouped.items():
        en = html.escape(TOPIC_EN.get(name, name))
        zh = html.escape(TOPIC_ZH.get(name, name))
        parts = ['<!doctype html><html lang="zh-Hans"><head><meta charset="utf-8">',
                 '<meta name="viewport" content="width=device-width,initial-scale=1">',
                 f'<title>{en} · Trend Radar</title><style>{STYLE}</style></head><body>',
                 f'<h1>{en} / {zh}</h1>',
                 '<p><a href="../index.html">← 趋势雷达 / Trend Radar</a></p>']
        for date, items in dates.items():
            day = html.escape(date)
            sources: dict[tuple, list[dict]] = {}
            for item in items:
                keys = {(s.get("source_id") or "unknown", s.get("via") or item.get("via") or "",
                         s.get("engine") or "", s.get("collector") or item.get("collector") or "")
                        for s in item.get("sightings", [])}
                for key in keys or {("unknown", "", "", "")}:
                    sources.setdefault(key, []).append(item)
            sections = []
            parts.append(f'<h2 id="day-{day}">{day} · {len(items)} 条 / items</h2><ul>')
            for idx, (key, rows) in enumerate(sorted(sources.items())):
                source_id, via, engine, collector = key
                values = [source_id, via, engine, collector or "节点未记录 / Unknown collector"]
                label = html.escape(" · ".join(filter(None, values)))
                anchor = f'{day}-source-{idx}'
                parts.append(f'<li><a href="#{anchor}">{label}</a> ({len(rows)})</li>')
                sections.append(f'<h3 id="{anchor}">{label}</h3><ul>')
                for item in rows:
                    original = html.escape(item["title"])
                    translated = html.escape(item.get("title_zh") or "")
                    title = f'{translated} <span class="meta">({original})</span>' if translated else original
                    url = item["url"]
                    if url.startswith(("https://", "http://")):
                        title = f'<a href="{html.escape(url)}" rel="noopener nofollow">{title}</a>'
                    details = " · ".join(filter(None, (item.get("publisher"), (item.get("published_at") or "")[:10])))
                    sections.append(f'<li>{title} <span class="meta">{html.escape(details)}</span></li>')
                sections.append('</ul>')
            parts.extend(['</ul>', *sections])
        parts.append('</body></html>')
        (target / f"{name}.html").write_text("\n".join(parts) + "\n", encoding="utf-8")
    return len(grouped)
