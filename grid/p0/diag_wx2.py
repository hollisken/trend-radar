import urllib.request, urllib.parse, gzip, random, string
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
def rnd(n): return "".join(random.choices(string.hexdigits.upper(), k=n))
def get(url, cookie="", ref=""):
    h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9", "Accept-Encoding": "gzip",
         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    if cookie: h["Cookie"] = cookie
    if ref: h["Referer"] = ref
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20)
        b = r.read()
        if b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
        return r.status, b.decode("utf-8", "replace")
    except Exception as e:
        return 0, type(e).__name__
Q = "https://weixin.sogou.com/weixin?" + urllib.parse.urlencode(
    {"type": "2", "query": "虚拟试穿 落地", "s_from": "input", "ie": "utf8", "_sug_": "n", "_sug_type_": ""})
for tag, ck in [
    ("plain", ""),
    ("snuid", f"SNUID={rnd(32)}"),
    ("snuid+suv+su1", f"SNUID={rnd(32)}; SUV={rnd(32)}{rnd(14)}; SUID=1{rnd(16)}"),
    ("snuid+ssut", f"SNUID={rnd(32)}; SUV={rnd(32)}{rnd(14)}"),
]:
    get("https://weixin.sogou.com/")  # warm regardless
    s, body = get(Q, ck, "https://weixin.sogou.com/")
    print(tag, "status", s, "len", len(body) if isinstance(body, str) else body,
          "txtbox", body.count("txt-box") if isinstance(body, str) else "-",
          "antispider", body.count("antispider") if isinstance(body, str) else "-")
