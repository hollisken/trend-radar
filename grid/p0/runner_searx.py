"""P0 channel runner: query gzlxy SearXNG (EN topics x EN engines). Stdlib only.
Run ON gzlxy (localhost SearXNG). Emits one JSON run file to --out."""
from __future__ import annotations
import argparse, json, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "jinshanhai-grid-p0/0.1 (research comparison; metadata only)"


def searx(base: str, q: str, engine: str, timeout: float) -> dict:
    url = f"{base}/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "engines": engine, "language": "en", "safesearch": "1"})
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        return {"status": "ok", "results": [
                    {"title": (x.get("title") or "")[:300], "url": x.get("url") or "",
                     "snippet": (x.get("content") or "")[:300]}
                    for x in data.get("results", [])],
                "unresponsive": data.get("unresponsive_engines") or [],
                "elapsed_s": round(time.time() - t0, 1)}
    except Exception as e:
        return {"status": "error", "error": type(e).__name__, "results": [],
                "unresponsive": [], "elapsed_s": round(time.time() - t0, 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--collector", default="gzlxy")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    sx = cfg["searx"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    queries = []
    for topic in cfg["topics"]:
        for q in topic["en"]:
            for engine in sx["engines"]:
                r = searx(sx["base"], q, engine, sx.get("timeout_s", 25))
                queries.append({"topic": topic["id"], "query": q, "engine": engine,
                                "n": len(r["results"]), **r})
                print(f"{engine} | {q} | n={len(r['results'])} | {r['status']}", flush=True)
                time.sleep(sx.get("min_interval_s", 45))
    out = {"schema": 1, "kind": "p0_channel", "channel": f"searx_{a.collector}",
           "date": stamp[:8], "started": stamp, "queries": queries}
    p = Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)


if __name__ == "__main__":
    main()
