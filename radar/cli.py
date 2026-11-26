"""Command line entry points.

collect  runs on any host with network access and writes one run artifact.
merge    folds a run artifact into data/<date>.json (idempotent per item id).
digest   writes the bilingual daily digest and refreshes the README table.
site     rebuilds the static index from the last days of data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from . import collect as collect_mod
from . import config as config_mod
from . import dedup, digest as digest_mod, site as site_mod

DEFAULT_DATA = Path("data")
DEFAULT_DIGEST = Path("digest")
DEFAULT_README = Path("README.md")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _merge_sources(previous: list[dict], incoming: list[dict]) -> list[dict]:
    merged = {row["id"]: dict(row) for row in previous}
    for row in incoming:
        current = merged.get(row["id"])
        if current is None:
            merged[row["id"]] = {**row, "runs": 1, "items_run": row.get("items", 0)}
            continue
        current.update({key: row[key] for key in ("status", "error", "kind", "elapsed_ms")})
        current["runs"] = current.get("runs", 0) + 1
        current["items_run"] = current.get("items_run", 0) + row.get("items", 0)
    return sorted(merged.values(), key=lambda item: item["id"])


def cmd_collect(args) -> int:
    cfg = config_mod.load(args.config)
    date = args.date or dt.date.today().isoformat()
    run_at = args.run_at or _now()
    only = set(filter(None, args.sources.split(","))) if args.sources else None
    run = collect_mod.collect(cfg, date, run_at, only, collector=args.collector)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = run_at[11:19].replace(":", "")
    path = out / f"run-{date}-{stamp}Z.json"
    _write(path, json.dumps(run, ensure_ascii=False, indent=1) + "\n")
    ok = sum(1 for row in run["sources"] if row["status"] == "ok")
    print(json.dumps({"artifact": str(path), "items": run["stats"]["items"],
                      "sources_ok": ok, "sources_total": len(run["sources"]),
                      "date": date}, ensure_ascii=False))
    return 0


def cmd_merge(args) -> int:
    run = _read_json(Path(args.run))
    if not run or not run.get("items"):
        print("merge: nothing to merge", file=sys.stderr)
        return 1
    data_dir = Path(args.data_dir)
    path = data_dir / f"{run['date']}.json"
    current = _read_json(path, default={
        "schema_version": run.get("schema_version", 1), "date": run["date"],
        "items": [], "sources": [], "stats": {}})
    items, counts = dedup.merge_items(current.get("items", []), run["items"])
    stats = collect_mod.summarize(items)
    stats.update({"duplicates_in_run": counts.get("duplicates", 0),
                  "title_duplicates": counts.get("title_duplicates", 0)})
    current.update({
        "schema_version": run.get("schema_version", 1),
        "date": run["date"],
        "updated_at": run["run_at"],
        "sources": _merge_sources(current.get("sources", []), run.get("sources", [])),
        "items": items,
        "stats": stats,
        "terms_note": run.get("terms_note", ""),
    })
    _write(path, json.dumps(current, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"data": str(path), "items": stats["items"],
                      "added": counts.get("added", 0),
                      "duplicates": counts.get("duplicates", 0)}, ensure_ascii=False))
    return 0


def cmd_digest(args) -> int:
    data_dir, digest_dir = Path(args.data_dir), Path(args.digest_dir)
    date = args.date or (dt.date.today() - dt.timedelta(days=1)).isoformat()
    current = _read_json(data_dir / f"{date}.json")
    if not current:
        print(f"digest: no data for {date}", file=sys.stderr)
        return 1
    previous = _read_json(data_dir / f"{(dt.date.fromisoformat(date) - dt.timedelta(days=1)).isoformat()}.json")
    _write(digest_dir / f"{date}.md", digest_mod.build_digest(date, current, previous))
    if args.readme:
        readme = Path(args.readme)
        rows = []
        for offset in range(7):
            day = (dt.date.fromisoformat(date) - dt.timedelta(days=offset)).isoformat()
            payload = _read_json(data_dir / f"{day}.json")
            if not payload:
                continue
            sources = payload.get("sources", [])
            rows.append({"date": day, "items": payload.get("stats", {}).get("items", 0),
                         "by_topic": payload.get("stats", {}).get("by_topic", {}),
                         "sources_ok": sum(1 for row in sources if row.get("status") == "ok"),
                         "sources_total": len(sources)})
        if readme.exists():
            _write(readme, digest_mod.update_readme(readme.read_text(encoding="utf-8"),
                                                    digest_mod.readme_block(rows)))
    print(json.dumps({"digest": str(digest_dir / f"{date}.md")}, ensure_ascii=False))
    return 0


def cmd_site(args) -> int:
    html_text = site_mod.build(Path(args.data_dir), days=args.days)
    out = Path(args.out)
    _write(out, html_text)
    pages = site_mod.build_digest_pages(Path(args.digest_dir), out.parent)
    topics = site_mod.build_topic_pages(Path(args.data_dir), args.days, out.parent)
    print(json.dumps({"site": str(out), "digest_pages": pages, "topic_pages": topics},
                     ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("collect", help="fetch sources once and write a run artifact")
    p.add_argument("--config")
    p.add_argument("--date")
    p.add_argument("--run-at", dest="run_at")
    p.add_argument("--sources", help="comma separated source ids")
    p.add_argument("--collector", help="public label for the node running the collection")
    p.add_argument("--out", default="out")
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("merge", help="merge a run artifact into the daily data file")
    p.add_argument("--run", required=True)
    p.add_argument("--data-dir", dest="data_dir", default=str(DEFAULT_DATA))
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("digest", help="write the bilingual digest and README table")
    p.add_argument("--date")
    p.add_argument("--data-dir", dest="data_dir", default=str(DEFAULT_DATA))
    p.add_argument("--digest-dir", dest="digest_dir", default=str(DEFAULT_DIGEST))
    p.add_argument("--readme", default=str(DEFAULT_README))
    p.set_defaults(func=cmd_digest)

    p = sub.add_parser("site", help="build the static index page")
    p.add_argument("--data-dir", dest="data_dir", default=str(DEFAULT_DATA))
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--digest-dir", dest="digest_dir", default=str(DEFAULT_DIGEST))
    p.add_argument("--out", default="docs/index.html")
    p.set_defaults(func=cmd_site)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
