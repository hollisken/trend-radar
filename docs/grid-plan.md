# 五机研究采集集群方案（Research Grid）

日期：2026-11-26 ｜ 状态：待决策 ｜ 基于：/data-4T/trend-radar（v0.1，元数据 only 管线）

## 1. 目标与总原则

**目标**：用 3 台 AWS 美国（4C8G）+ 2 台天翼国内（4C8G）搭一个"深挖型"信息采集与研究集群，在零封号风险前提下，挖出常规搜索拿不到的知识和信息关联，服务今山海"跨境信息差"策略。

**总原则**：
- 云端五台 = 哑采集层 + 轻处理层；本机 = 大脑（LLM API、BGE-M3 嵌入、KS pgvector、Hermes 编排、深度研究报告）。云端不跑本地大模型（4C8G 只够 7B 量化，性价比低）。
- 全部出站连接（服务器 → 本机推送），不依赖云端入站端口——天翼云电脑通常无固定公网入站，这个设计天然兼容。
- 延续 trend-radar 的既有纪律：礼貌节流、失败即数据、产物是 git 里的 JSON、元数据优先、无凭证优先。
- 官方 API 优先于抓取，抓取优先于浏览器；账号操作原则上不上云。

## 2. 五机分工

| 机器 | 角色 | 部署内容 | 说明 |
|---|---|---|---|
| AWS-US-1 | 编排 + SERP 枢纽 | 调度器（systemd timer + Redis/RQ 队列）、SearXNG 实例 A（duckduckgo/google/bing）、官方 SERP API worker（Brave Search 免费 2000/月、Exa、Serper/Tavily 免费层）、arXiv / OpenAlex / Semantic Scholar / Crossref / PubMed 抓取器 | 集群的"查询入口"。SERP 类请求全部集中在这里做预算控制 |
| AWS-US-2 | 深读 + 全文抽取 | Crawl4AI（首选，纯开源可自托管）+ Trafilatura 正文抽取、Firecrawl 可选、Wayback CDX + 快照 diff、GitHub 深采（repo 元数据/star 历史/contributor/code search，带 token）、deps.dev 依赖图、EDGAR 全文检索、USPTO/EPO 专利 | 唯一"读全文"的机器；Playwright 限 2 worker 以适配 8G 内存 |
| AWS-US-3 | 社区 + 长尾 + RSS | trend-radar 现有小时级采集整体迁移过来、RSSHub、RSS 聚合（Miniflux/Watchtower）、Reddit OAuth API、HN Algolia API、StackExchange API、V2EX/Lobsters、YouTube 字幕（transcript API） | 社区长尾是"常规搜索搜不到"的重灾区；Reddit 用 OAuth 免费额度（100 QPM 的 10%） |
| CN-1 | 国内搜索 + 微信生态 | SearXNG 实例 B（启用 baidu/sogou/360/quark）、搜狗微信搜索（公众号文章——中文信息差核心源）、知乎/头条/百家号低频匿名检索、"国内验证层"（把海外发现回查国内信源） | 美国 IP 搜不到/搜不全的中文长尾只能在这台做 |
| CN-2 | 国内平台 + 中继 | 微博/知乎/B站 匿名公开页低频采集、（可选，见决策点）小红书/抖音、rclone/rsync 中继：把 CN 侧产物回传本机 | 国内平台风控最严，单独隔离一台，出问题不连累搜索层 |

**IP 多样性是防封的物理基础**：3 台 AWS 尽量开在不同 region（如 us-east-1 / us-west-2 / us-east-2），避免同一 /24；两台天翼天然国内出口。5 个独立出口 IP = 5 份独立预算。

## 3. 六层搜索漏斗（"深挖"的具体含义）

常规搜索只用了第 2 层。深挖 = 六层全打 + 层间互证：

1. **官方结构化 API 层**（零封号风险，质量最高）：OpenAlex、Semantic Scholar、Crossref、PubMed、arXiv、EDGAR（美股财报全文）、USPTO/EPO（专利）、OpenCorporates（公司股权关联）、deps.dev（开源依赖图）、GDELT（全球新闻事件时间线）、GitHub API。
2. **SERP 层**（多引擎 × 多 IP）：SearXNG×2 + Brave/Exa/Serper 免费 API。Exa 做语义搜索（"找相似的"而非"找包含关键词的"）。
3. **社区长尾层**：Reddit、HN、StackExchange、V2EX、Lobsters、Hacker News Who is hiring、知乎、公众号——一手经验和内部人信号常只存在于这里。
4. **全文抽取层**：对前三层命中的 URL，AWS-US-2 统一抽正文（Crawl4AI+Trafilatura），存全文供嵌入和实体抽取。元数据 only 的 POLICY 只约束"对外发布"，内部研究语料可以有全文。
5. **历史/档案层**：Wayback CDX 查"这个说法最早出现在什么时候"、快照 diff 看页面随时间变化（识别叙事演变）、GDELT 时间线看提及量突增。
6. **跨语言信息差层**：同一主题用 EN/JA/KO/DE/ES/RU 各搜一遍，找"英文圈在讨论、中文圈没报道"（及反向）——这是今山海品牌策略的直接弹药。

## 4. 关联挖掘层（本机执行，吃云端语料）

这是"信息关联度需要深挖"的答案，全部在本机 GPU + API 上跑：

1. **实体抽取**：对语料用 Qwen3.7-Plus / GLM-5.2 抽实体（人物/公司/产品/论文/仓库/融资/政策）+ 关系断言，带出处。
2. **实体关联图**：Postgres 存节点和边（共现边、引用边、依赖边、股权边、共同作者边），NetworkX 离线分析。核心指标：**介数中心性找"桥接实体"**——两个不相干话题通过谁连起来，这就是常规搜索看不到的关联。
3. **向量层**：BGE-M3 嵌入全文入 KS pgvector；kNN 找跨语言近邻；**簇漂移检测**——新实体突然与老实体高频共现 = 弱信号预警。
4. **RAG 图谱**：LightRAG（比 GraphRAG 轻，API LLM 驱动，4C8G 之外的本机跑得动）对语料做"全局问题"回答（"这个领域正在收敛到什么共识"）。
5. **自适应深度研究 agent**：GPT-Researcher / dzhng deep-research / STORM 风格的循环（迭代生成子查询→检索→找信息缺口→再检索），替代现在 deep-research-v2 的固定 41 查询模板；跑在 AWS-US-1，调用六层漏斗。产出直接进 `ks/output/jinshanhai/research/reports/`。

## 5. 数据流与存储

```
五台服务器各自 cron → 产物 JSON（trend-radar schema v2：+full_text/+entities 可选字段）
  → git push 或 rclone 推送到本机（出站）
  → 本机：去重（canonical URL）→ BGE-M3 嵌入 → KS pgvector
  → 实体抽取 → 关联图 → 每周深挖报告 + 弱信号告警（飞书/日报）
```

- 云端各机保留 30 天滚动副本，本机是唯一事实源。
- 体量估算：元数据 ~50MB/天；全文语料 ~2-4GB/月（压缩后），4C8G 与本机 4T 盘都毫无压力。
- 每日健康产物 `health.json`（每个源 ok/fail/条数），本机 cron 汇总，源失败=覆盖缺口而非"无消息"（沿用 competitor-news-monitor 的纪律）。

## 6. 防封预算表（安全基线，写进配置而非口头约定）

| 通道 | 预算 | 触发风控后 |
|---|---|---|
| SearXNG 抓取型引擎（DDG/Google） | ≤1 查/25 秒，≤600 查/天/IP | 熔断 30min→2h→6h 指数退避；换引擎不换 IP |
| 官方 SERP API（Brave/Exa/Serper） | 只用免费额度，额度内无封号风险 | 429 即停当日 |
| GitHub（带 token） | Search 30 次/分、Core 5000/时，实际用 <10% | — |
| Reddit OAuth | ≤10 QPM（限额的 10%） | — |
| arXiv / OpenAlex / S2 / EDGAR / Wayback | 各自礼貌间隔（3s / 1s / 1s / 0.5s / 1s）+ 描述性 UA | — |
| 百度/搜狗（CN-1） | ≤1 查/60 秒，≤300 查/天/IP | 熔断当日，绝不重试轰炸 |
| 搜狗微信（CN-1） | ≤1 查/90 秒，≤150 查/天 | 出现验证码即停 24h |
| 微博/知乎/B站匿名（CN-2） | ≤80 页/天，随机 15-45s 间隔 | 403 即停该机当日 |
| 小红书/抖音（若上云） | ≤50 页/天，纯匿名无账号 | 任何风控信号即永久下线该平台 |

通用规则：描述性 UA、per-host min_interval（trend-radar fetch.py 已有，推广到全部）、同 run 内失败不重试、账号类操作（登录态）只允许在本机浏览器（web-access CDP）执行。

## 7. 分期实施

- **P0 地基（第 1-2 天）**：SSH 加固、WireGuard mesh（5 台 + 本机）、确认 3 台 AWS 的 region/IP 分布、uptime-kuma 监控（US-1）、建 grid 仓库。
- **P1 采集迁移（第 1 周）**：trend-radar 迁到 AWS-3；SearXNG×2 上线；Brave/Exa/Serper 免费 key 接入；产物回传链路打通。验收：本机每天收到 5 台的健康 JSON + 合并后的日增量。
- **P2 深源接入（第 2-3 周）**：OpenAlex/S2/GDELT/EDGAR/Wayback/deps.dev/Reddit/HN/SE 上线；AWS-2 全文抽取管线；语料入 KS。验收：KS 里可按主题检索到带全文的新语料。
- **P3 关联挖掘（第 3-4 周）**：实体抽取 + 关联图 + LightRAG + 跨语言层；CN-1 搜狗微信 + 国内验证层；CN-2 平台层按决策点执行。验收：产出第一份"桥接实体"周报，含至少 3 条常规搜索验证不了的关联。
- **P4 研究 agent（第 4 周起）**：自适应 deep-research 循环上线，每周 1-2 个深挖主题（今山海选题），报告进现有 reports 目录。

## 8. 已知缺口（诚实声明）

- **X/Twitter**：无免费官方 API，Nitter 基本死光。方案：继续用本机 agent-reach 登录态低频查，云端只做 Reddit/HN 替代。若要云端化需付费第三方 API（twitterapi.io 级别），暂不推荐。
- **Google 直抓**：AWS 数据中心 IP 会被 Google 弹验证码，所以 SERP 主力是官方 API + DDG，Google 只作 SearXNG 的补充引擎、低配额。
- **B站海外 IP**：AWS 美国访问 B站部分接口受限，B站相关一律放 CN 侧。
- **天翼云电脑**：本质是云桌面，可能有会话回收/重启策略，需实测其 cron 常驻能力；不行就降级为"定时任务由本机唤醒触发"。

## 9. 需要你提供的输入

1. 5 台机器的 SSH 接入方式（IP/端口/密钥），3 台 AWS 的 region 分布。
2. 各机 OS（默认按 Ubuntu 22.04/24.04 准备）。
3. 免费 API key 由谁注册：Brave Search API、Exa、Serper（或 Tavily）、GitHub token、Reddit OAuth app——注册动作建议你本人做（涉及账号），注册后 key 交给我配置。
