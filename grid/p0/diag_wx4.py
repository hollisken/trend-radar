import sys
sys.path.insert(0, r"C:\p0\grid\p0")
import runner_cn as R
q = "虚拟试穿 落地 site:mp.weixin.qq.com"
r = R.run_engine("bingcn", q, 20)
print("bingcn site: variant |", r["status"], "| n =", len(r["results"]))
for x in r["results"][:5]:
    print(" -", x["url"][:70], "|", x["title"][:50])
