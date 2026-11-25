import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radar.digest import (README_BEGIN, README_END, build_digest, readme_block,
                          update_readme)


def sample(date="2026-11-26", items=3, ok=2, failed=1):
    sources = [{"id": f"src{index}", "kind": "rss", "status": "ok", "items": 5}
               for index in range(ok)]
    sources += [{"id": f"bad{index}", "kind": "rss", "status": "error", "items": 0,
                 "error": "http_403"} for index in range(failed)]
    rows = [{"id": f"id{index}", "title": f"Headline {index}", "url": f"https://example.com/{index}",
             "publisher": "WWD", "kind": "news", "published_at": "2026-11-26T08:00:00+00:00",
             "summary": "short summary", "topics": [{"name": "fashion", "score": 0.9}]}
            for index in range(items)]
    return {"date": date, "sources": sources, "items": rows,
            "stats": {"items": items, "by_topic": {"fashion": items},
                      "duplicates_in_run": 1, "title_duplicates": 0}}


class DigestTest(unittest.TestCase):
    def test_bilingual_sections_and_numbers(self):
        text = build_digest("2026-11-26", sample())
        self.assertIn("# Trend Radar — 2026-11-26", text)
        self.assertIn("# 趋势雷达 — 2026-11-26", text)
        self.assertIn("Items: 3", text)
        self.assertIn("条目：3 条", text)
        self.assertIn("bad0 (http_403)", text)
        self.assertIn("Headline 0", text)

    def test_deterministic(self):
        current = sample()
        self.assertEqual(build_digest("2026-11-26", current),
                         build_digest("2026-11-26", current))

    def test_reports_previous_day_delta(self):
        text = build_digest("2026-11-26", sample(items=5), sample(date="2026-11-25", items=3))
        self.assertIn("vs previous day: +2", text)

    def test_no_items_is_stated(self):
        empty = sample(items=0)
        empty["items"] = []
        text = build_digest("2026-11-26", empty)
        self.assertIn("No items matched", text)
        self.assertIn("今日没有命中", text)


class ReadmeTest(unittest.TestCase):
    def test_block_and_update(self):
        block = readme_block([{"date": "2026-11-26", "items": 3,
                               "by_topic": {"fashion": 3}, "sources_ok": 2,
                               "sources_total": 3}])
        self.assertIn("| 2026-11-26 | 3 |", block)
        text = f"# Title\n\n{README_BEGIN}\nold\n{README_END}\n\ntail\n"
        updated = update_readme(text, block)
        self.assertIn("| 2026-11-26 | 3 |", updated)
        self.assertNotIn("old", updated)
        self.assertTrue(updated.startswith("# Title"))
        self.assertTrue(updated.endswith("tail\n"))

    def test_missing_markers_raise(self):
        with self.assertRaises(ValueError):
            update_readme("no markers here", "x")


if __name__ == "__main__":
    unittest.main()
