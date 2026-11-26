"""P0 channel runner: direct CN SERP queries from cn-1/cn-2 (stdlib only, Windows-safe).
Engines: baidu, sogou, weixin (sogou wechat), bingcn, so (360). Emits one JSON run file."""
from __future__ import annotations
import argparse, gzip, html, http.cookiejar, io, json, re, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
TAG = re.compile(r"<[^>]+>")
_CJ = http.cookiejar.CookieJar()
_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_CJ))
_WARM = {"weixin": "https://weixin.sogou.com/"}
_warmed: set[str] = set()

ENGINES = {
    # name -> (url builder, result anchor regex, absolute-prefix)
    "baidu": (lambda q: "https://www.baidu.com/s?" + urllib.parse.urlencode({"wd": q, "rn": "20"}),
              re.compile(r'<h3[^>]*class="[^"]*t[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S),
              ""),
    "sogou": (lambda q: "https://www.sogou.com/web?" + urllib.parse.urlencode({"query": q}),
              re.compile(r'<h3 class="vr-title[^"]*">\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S),
              "https://www.sogou.com"),
    "weixin": (lambda q: "https://weixin.sogou.com/weixin?" + urllib.parse.urlencode({"type": "2", "query": q, "s_from": "input"}),
               re.compile(r'<a[^>]*href="(/link\?url=([^"]+))"[^>]*>(.*?)</a>', re.S),
               "https://weixin.sogou.com"),
    "bingcn": (lambda q: "https://cn.bing.com/search?" + urllib.parse.urlencode({"q": q, "count": "20"}),
               re.compile(r'<li class="b_algo".*?<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S),
               ""),
    "so": (lambda q: "https://www.so.com/s?" + urllib.parse.urlencode({"q": q}),
           re.compile(r'<h3[^>]*class="[^"]*title[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S),
           ""),
}
BLOCK_MARKERS = ("验证码", "安全验证", "captcha", "滑动验证", "网络异常", "Access Denied", "403 Forbidden")


def fetch(url: str, timeout: float, referer: str = "") -> tuple[int, str, str]:
    headers = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
               "Accept": "text/html,application/xhtml+xml", "Accept-Encoding": "gzip"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with _OPENER.open(req, timeout=timeout) as r:
            body = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                try: body = gzip.decompress(body)
                except OSError: pass
            return r.status, body.decode("utf-8", "replace"), ""
    except Exception as e:
        return 0, "", type(e).__name__


def clean(s: str) -> str:
    return html.unescape(TAG.sub("", s)).strip()[:300]


def absolutize(href: str, prefix: str) -> str:
    if href.startswith("//"): return "https:" + href
    if href.startswith("/") and prefix: return prefix + href
    return href


def run_engine(name: str, q: str, timeout: float) -> dict:
    build, rx, prefix = ENGINES[name]
    url = build(q)
    t0 = time.time()
    referer = ""
    if name in _WARM and name not in _warmed:
        _warmed.add(name)
        fetch(_WARM[name], timeout)
        referer = _WARM[name]
    status, body, err = fetch(url, timeout, referer)
    out = {"status": "ok", "results": [], "unresponsive": [], "elapsed_s": round(time.time() - t0, 1)}
    if status == 0:
        out.update(status="error", error=err); return out
    low = body[:4000].lower()
    if any(m.lower() in low for m in BLOCK_MARKERS):
        out.update(status="blocked", blocked_marker=True); return out
    seen = set()
    for m in list(rx.finditer(body))[:20]:
        href, title = m.group(1), clean(m.group(2))
        u = absolutize(html.unescape(href.replace("&amp;", "&")), prefix)
        if u.startswith("http") and title and u not in seen:
            seen.add(u)
            out["results"].append({"title": title, "url": u, "snippet": ""})
    out["n_raw"] = len(out["results"])
    if not out["results"] and "result" in body.lower():
        out["parse_suspect"] = True
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--collector", default="cn-1")
    ap.add_argument("--engines", default="", help="comma-separated engine override (machine-level split)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    cn = cfg["cn"]
    if a.engines:
        cn["engines"] = [e.strip() for e in a.engines.split(",") if e.strip()]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    queries = []
    for topic in cfg["topics"]:
        for q in topic["cn"]:
            for engine in cn["engines"]:
                r = run_engine(engine, q, cn.get("timeout_s", 20))
                queries.append({"topic": topic["id"], "query": q, "engine": engine,
                                "n": len(r["results"]), **r})
                print(f"{engine} | {q} | n={len(r['results'])} | {r['status']}", flush=True)
                time.sleep(cn.get("min_interval_s", 60))
    out = {"schema": 1, "kind": "p0_channel", "channel": f"cn_direct_{a.collector}",
           "date": stamp[:8], "started": stamp, "queries": queries}
    p = Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", p)


if __name__ == "__main__":
    main()
