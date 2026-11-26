# P0 comparison experiment

Same-topic comparison of search channels against the trend-radar baseline, per
the grid plan (docs/grid-plan.md, private). Goal: per channel x engine counts of
unique-increment / dup / blocked / error, plus latency, for 7 days, to set rate
budgets from data and keep only channels with measurable unique increment.

- `queries.json` — topic set (pilot: controllable video generation x virtual try-on)
  and per-side engine lists with polite intervals (EN via SearXNG on a US box,
  CN via direct SERP fetches from a CN box).
- `runner_searx.py` — runs on the SearXNG host, queries it engine by engine.
- `runner_cn.py` — runs on a CN worker (Windows-safe, stdlib), fetches
  baidu/sogou/weixin/bingcn/so and parses result anchors.
- `scorer.py` — runs at home: normalizes URLs, diffs against `data/*.json`
  (last 7 days) and across channels, writes `out/<date>/report.json`.

The wrapper that knows host names lives outside this repo
(`~/.local/bin/grid-p0-run.sh`, systemd user timer `grid-p0.timer`, twice daily).
Raw channel runs and reports are gitignored under `out/`.
