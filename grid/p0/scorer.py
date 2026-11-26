"""P0 scorer (home): compare channel runs against the trend-radar baseline corpus.
Computes per channel x engine: unique-increment / dup / blocked / error / timeout stats.
Usage: python3 scorer.py --date 20261126 [--days 7]"""
from __future__ import annotations
import argparse, json, re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl, urlunsplit

REPO = Path("/data-4T/trend-radar")
OUT = REPO / "grid/p0/out"
TRACK = re.compile(r"^(utm_|spm|fbclid|gclid|bc_|sc_|from=|ref$|refer$)", re.I)


def norm(url: str) -> str:
    if not url:
        return ""
    try:
        s = urlsplit(url.strip())
        host = (s.hostname or "").lower().removeprefix("www.")
        q = "&".join(f"{k}={v}" for k, v in parse_qsl(s.query, keep_blank_values=True)
                     if not TRACK.match(k))
        path = re.sub(r"/$", "", s.path or "/")
        return urlunsplit((s.scheme or "https", host, path, q, ""))
    except ValueError:
        return url.strip()


def is_redirect_wrapper(url: str) -> bool:
    h = (urlsplit(url).hostname or "").lower()
    return h in {"www.baidu.com", "baidu.com"} and "/link" in url or "sogou.com" in h and "/link" in url


def baseline_urls(days: int) -> set[str]:
    cutoff = date.today() - timedelta(days=days)
    urls: set[str] = set()
    for f in sorted((REPO / "data").glob("*.json")):
        try:
            d = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if d < cutoff:
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        for it in data.get("items", []):
            urls.add(norm(it.get("url", "")))
    return urls


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.utcnow().strftime("%Y%m%d"))
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    base = baseline_urls(a.days)
    day_dir = OUT / a.date
    files = sorted(day_dir.glob("*.json"))
    per: dict[str, dict] = {}
    url_channels: dict[str, set] = defaultdict(set)
    uniques: dict[str, list] = defaultdict(list)
    for f in files:
        run = json.loads(f.read_text(encoding="utf-8"))
        ch = run["channel"]
        for qr in run["queries"]:
            eng = qr["engine"]
            k = f"{ch}/{eng}"
            st = per.setdefault(k, {"results": 0, "unique": 0, "dup": 0, "ok": 0,
                                    "error": 0, "blocked": 0, "parse_suspect": 0,
                                    "queries": 0, "elapsed_sum": 0.0})
            st["queries"] += 1
            st["elapsed_sum"] += qr.get("elapsed_s", 0)
            if qr["status"] == "error":
                st["error"] += 1
            elif qr["status"] == "blocked":
                st["blocked"] += 1
            else:
                st["ok"] += 1
                if qr.get("parse_suspect"):
                    st["parse_suspect"] += 1
            for r in qr["results"]:
                u = norm(r["url"])
                if not u:
                    continue
                st["results"] += 1
                url_channels[u].add(k)
                if u in base:
                    st["dup"] += 1
                else:
                    st["unique"] += 1
                    if len(uniques[k]) < 200:
                        uniques[k].append({"url": r["url"], "title": r["title"][:120],
                                           "query": qr["query"], "redirect": is_redirect_wrapper(r["url"])})
    for k, st in per.items():
        st["avg_elapsed_s"] = round(st.pop("elapsed_sum") / max(st["queries"], 1), 1)
        st["unique_rate"] = round(st["unique"] / max(st["results"], 1), 2)
    multi = sum(1 for v in url_channels.values() if len(v) > 1)
    report = {"date": a.date, "baseline_days": a.days, "baseline_urls": len(base),
              "channels": dict(sorted(per.items())),
              "cross_channel_overlap_urls": multi,
              "unique_total": len([u for u, v in url_channels.items() if len(v) == 1]),
              "uniques": uniques}
    day_dir.mkdir(parents=True, exist_ok=True)
    (day_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"| channel/engine | queries | ok | err | blocked | results | unique | dup | unique_rate | avg_s |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k, st in report["channels"].items():
        lines.append(f"| {k} | {st['queries']} | {st['ok']} | {st['error']} | {st['blocked']} | "
                     f"{st['results']} | {st['unique']} | {st['dup']} | {st['unique_rate']} | {st['avg_elapsed_s']} |")
    print(f"# P0 report {a.date}  baseline={len(base)} urls  cross-overlap={multi}\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
