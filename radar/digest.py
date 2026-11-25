"""Daily bilingual digest and README table generation."""
from __future__ import annotations

TOPIC_EN = {
    "fashion": "Fashion", "retail": "Retail", "beauty": "Beauty",
    "ai-video": "AI video", "research": "Research", "tooling": "Tooling",
    "sustainability": "Sustainability",
}
TOPIC_ZH = {
    "fashion": "时装", "retail": "零售", "beauty": "美妆",
    "ai-video": "AI 视频", "research": "研究", "tooling": "工具",
    "sustainability": "可持续",
}
HIGHLIGHT_TOPICS = ("fashion", "ai-video", "retail", "research", "tooling")
README_BEGIN = "<!-- BEGIN LATEST -->"
README_END = "<!-- END LATEST -->"


def _highlights(items: list[dict], per_topic: int = 2, limit: int = 8) -> list[tuple[str, dict]]:
    picked: list[tuple[str, dict]] = []
    used: set[str] = set()
    for topic in HIGHLIGHT_TOPICS:
        count = 0
        for item in items:
            names = [entry["name"] for entry in item.get("topics", [])]
            if topic not in names or item["id"] in used:
                continue
            picked.append((topic, item))
            used.add(item["id"])
            count += 1
            if count >= per_topic:
                break
        if len(picked) >= limit:
            break
    return picked[:limit]


def _bullet(entry: tuple[str, dict], language: str) -> str:
    topic, item = entry
    label = (TOPIC_ZH if language == "zh" else TOPIC_EN).get(topic, topic)
    publisher = item.get("publisher") or item.get("kind", "")
    suffix = f" ({publisher})" if publisher else ""
    return f"- **{label}** — [{item['title']}]({item['url']}){suffix}"


def build_digest(date: str, current: dict, previous: dict | None = None) -> str:
    stats = current.get("stats", {})
    sources = current.get("sources", [])
    ok = [row for row in sources if row.get("status") == "ok"]
    failed = [row for row in sources if row.get("status") != "ok"]
    items = current.get("items", [])
    delta = ""
    if previous:
        change = stats.get("items", 0) - previous.get("stats", {}).get("items", 0)
        delta = f"{change:+d}"
    topics = stats.get("by_topic", {})

    lines = [f"# Trend Radar — {date}", ""]
    lines += ["## Highlights", ""]
    highlights = _highlights(items)
    lines += [_bullet(entry, "en") for entry in highlights] or ["- No items matched the highlight topics."]
    lines += ["", "## Coverage", "",
              f"- Items: {stats.get('items', 0)} (vs previous day: {delta or 'n/a'})",
              f"- Sources ok: {len(ok)}/{len(sources)}; failing: "
              + (", ".join(f"{row['id']} ({row['error']})" for row in failed) or "none"),
              f"- Duplicates collapsed: {stats.get('duplicates_in_run', 0)}; "
              f"shared headlines kept: {stats.get('title_duplicates', 0)}",
              "- Topics: " + ", ".join(f"{TOPIC_EN.get(name, name)} {count}"
                                       for name, count in topics.items())]
    updated = (current.get("updated_at") or "")[:16].replace("T", " ")
    if updated:
        lines.append(f"- Data updated: {updated} UTC")
    if previous:
        new_sources = [row["id"] for row in ok
                       if row["id"] not in {item["id"] for item in previous.get("sources", [])}]
        if new_sources:
            lines.append("- New sources reporting today: " + ", ".join(new_sources))
    lines += ["", "---", "", f"# 趋势雷达 — {date}", "", "## 今日要点", ""]
    lines += [_bullet(entry, "zh") for entry in highlights] or ["- 今日没有命中要点主题的条目。"]
    lines += ["", "## 覆盖情况", "",
              f"- 条目：{stats.get('items', 0)} 条（较前一日 {delta or '无对比'}）",
              f"- 正常来源：{len(ok)}/{len(sources)}；异常："
              + ("、".join(f"{row['id']}（{row['error']}）" for row in failed) or "无"),
              f"- 合并重复：{stats.get('duplicates_in_run', 0)} 条；标题相同但链接不同："
              f"{stats.get('title_duplicates', 0)} 条",
              "- 主题分布：" + "，".join(f"{TOPIC_ZH.get(name, name)} {count}"
                                        for name, count in topics.items())]
    if updated:
        lines.append(f"- 数据更新时间：{updated} UTC")
    lines += [
              "", "数据仅含标题、链接、日期与发布方摘要，不含正文或图片；详见 POLICY.md。", ""]
    return "\n".join(lines)


def readme_block(rows: list[dict]) -> str:
    lines = ["| Date / 日期 | Items / 条目 | Top topics / 主要主题 | Sources / 来源 | Digest / 日报 |",
             "|---|---|---|---|---|"]
    for row in rows:
        topics = ", ".join(f"{TOPIC_EN.get(name, name)} {count}"
                           for name, count in list(row.get("by_topic", {}).items())[:3])
        lines.append(f"| {row['date']} | {row.get('items', 0)} | {topics} | "
                     f"{row.get('sources_ok', 0)}/{row.get('sources_total', 0)} | "
                     f"[EN · 中文](digest/{row['date']}.md) |")
    return "\n".join(lines)


def update_readme(text: str, block: str) -> str:
    if README_BEGIN not in text or README_END not in text:
        raise ValueError("README markers missing")
    head, rest = text.split(README_BEGIN, 1)
    _, tail = rest.split(README_END, 1)
    return f"{head}{README_BEGIN}\n{block}\n{README_END}{tail}"
