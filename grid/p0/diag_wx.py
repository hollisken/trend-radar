import urllib.request, urllib.parse, http.cookiejar, gzip, re
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
def get(url, ref=""):
    h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9", "Accept-Encoding": "gzip"}
    if ref: h["Referer"] = ref
    r = op.open(urllib.request.Request(url, headers=h), timeout=20)
    b = r.read()
    if b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
    return r.status, r.geturl(), b.decode("utf-8", "replace")
s1, u1, body1 = get("https://weixin.sogou.com/")
print("HOME", s1, u1, "len", len(body1), "cookies", [c.name for c in cj])
q = urllib.parse.urlencode({"type": "2", "query": "虚拟试穿 落地", "s_from": "input"})
s2, u2, body2 = get("https://weixin.sogou.com/weixin?" + q, "https://weixin.sogou.com/")
print("SEARCH", s2, u2, "len", len(body2))
for marker in ("txt-box", "news-box", "vr-title", "antispider", "验证码", " kap", "id="):
    print("marker", marker, body2.count(marker))
m = re.findall(r'href="([^"]*(?:link|weixin\.qq)[^"]*)"', body2)
print("hrefs sample:", m[:3])
