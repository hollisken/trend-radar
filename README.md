# Trend Radar

**English** · [中文](#中文)

A small, dependency-free pipeline that turns public feeds, papers and repositories
into a daily, machine-readable signal set. It publishes **metadata only**: titles,
canonical links, dates, publisher-provided summaries and our own topic labels.
No article bodies, images or paywalled text — see [POLICY.md](POLICY.md).

Built for cheap, interruptible CPU workers: every step is a bounded batch that can
be killed and resumed, and the output is plain JSON in git.

**Live site / 在线站点**: <https://hollisken.github.io/trend-radar/> — daily digests as HTML.

## What it collects / 采集范围

| Family / 类别 | Source / 来源 | Fields / 字段 |
|---|---|---|
| Publisher news / 媒体资讯 | Public RSS feeds (WWD, Retail Dive, Glossy, Hypebeast, Footwear News) | title, link, date, publisher summary |
| Papers / 论文 | arXiv API, keyword queries | title, abstract, authors, date, link |
| Repositories / 仓库 | GitHub Search API, newly created with traction | repo name, description, stars, language, link |

## Daily artifact / 每日产物

`data/<YYYY-MM-DD>.json`

```json
{
  "schema_version": 1,
  "date": "2026-11-26",
  "sources": [{"id": "wwd", "kind": "rss", "status": "ok", "items": 10}],
  "items": [{
    "id": "8f2c…", "title": "…", "url": "https://…", "publisher": "WWD",
    "kind": "news", "published_at": "2026-11-26T08:00:00+00:00",
    "summary": "…", "topics": [{"name": "fashion", "score": 0.83}],
    "retrieved_at": "2026-11-26T09:00:03+00:00",
    "sightings": [{"source_id": "wwd", "retrieved_at": "2026-11-26T09:00:03+00:00"}]
  }],
  "stats": {"items": 1, "by_topic": {"fashion": 1}},
  "terms_note": "Metadata only…"
}
```

One record per canonical URL. When several sources report the same link, the record
keeps every sighting, so provenance is never collapsed away.

## Usage / 使用

```bash
python3 -m radar.cli collect --date 2026-11-26 --out out      # any host with network
python3 -m radar.cli merge --run out/run-2026-11-26-090000Z.json
python3 -m radar.cli digest --date 2026-11-26
python3 -m radar.cli site
```

`collect` is safe to run hourly; `merge` is idempotent per item id; `digest` is
deterministic for a given day file, so re-running it produces the same page.

Tests use only the standard library:

```bash
python3 -m unittest discover -s tests -v
python3 -m pytest -q        # if pytest is available
```

## Design notes / 设计说明

- **Politeness**: per-host minimum interval, bounded response size, descriptive
  User-Agent, no retries against a failing host in the same run.
- **Failures are data**: each source reports `ok` or an error string; one broken
  source never stops the run.
- **Deterministic labels**: keyword rules with a version string, so label changes
  are visible in the data (`stats.rules_version`).
- **No credentials**: the pipeline uses public endpoints only. Publishing is done
  outside this code by whoever runs it.

## Roadmap / 路线

- Embedding-based topic clustering as an alternative to keyword rules, scored
  against a frozen sample set.
- Per-source history so a feed that disappears is visible in the digest.
- Optional static site publishing from `data/`.

## Latest data / 最新数据

<!-- BEGIN LATEST -->
| Date / 日期 | Items / 条目 | Top topics / 主要主题 | Sources / 来源 | Digest / 日报 |
|---|---|---|---|---|
| 2026-11-26 | 154 | Tooling 28, AI video 23, Research 21 | 9/9 | [EN · 中文](digest/2026-11-26.md) |
| 2026-11-25 | 163 | Tooling 25, Retail 15, Fashion 14 | 9/9 | [EN · 中文](digest/2026-11-25.md) |
<!-- END LATEST -->

## License / 许可

MIT. Aggregated items belong to their publishers; see [POLICY.md](POLICY.md).
