import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radar.classify import classify
from radar.dedup import item_id, merge_items


def make_item(url, title, source="feed_a"):
    return {"id": item_id(url), "title": title, "url": url, "topics": [],
            "sightings": [{"source_id": source, "retrieved_at": "2026-11-26T09:00:00+00:00"}]}


class MergeTest(unittest.TestCase):
    def test_same_url_keeps_both_sightings(self):
        first = make_item("https://example.com/a", "Story one", "feed_a")
        second = make_item("https://example.com/a", "Story one, syndicated", "feed_b")
        merged, stats = merge_items([], [first, second])
        self.assertEqual(len(merged), 1)
        self.assertEqual({row["source_id"] for row in merged[0]["sightings"]},
                         {"feed_a", "feed_b"})
        self.assertEqual(stats["duplicates"], 1)

    def test_shared_headline_kept_and_flagged(self):
        left = make_item("https://a.example.com/x", "Same headline", "feed_a")
        right = make_item("https://b.example.com/y", "same headline", "feed_b")
        merged, stats = merge_items([], [left, right])
        self.assertEqual(len(merged), 2)
        self.assertEqual(stats["title_duplicates"], 1)
        flagged = [row for row in merged if "duplicate_title" in row.get("flags", [])]
        self.assertEqual(len(flagged), 1)

    def test_merge_is_idempotent(self):
        incoming = [make_item("https://example.com/a", "Story")]
        merged, _ = merge_items([], incoming)
        merged_again, stats = merge_items(merged, incoming)
        self.assertEqual(len(merged_again), 1)
        self.assertEqual(len(merged_again[0]["sightings"]), 1)
        self.assertEqual(stats["added"], 0)

    def test_fills_missing_fields_from_later_sighting(self):
        bare = make_item("https://example.com/a", "Story")
        rich = make_item("https://example.com/a", "Story")
        rich["summary"] = "filled in later"
        merged, _ = merge_items([bare], [rich])
        self.assertEqual(merged[0]["summary"], "filled in later")


class ClassifyTest(unittest.TestCase):
    def test_fashion_title(self):
        topics = classify("Runway report: designer collection", "quiet luxury textile")
        self.assertEqual(topics[0]["name"], "fashion")
        self.assertGreaterEqual(topics[0]["score"], 0.5)

    def test_paper_gets_research_baseline(self):
        names = [topic["name"] for topic in classify("A model for something", "", kind="paper")]
        self.assertIn("research", names)

    def test_repo_gets_tooling_baseline(self):
        names = [topic["name"] for topic in classify("owner/repo", "", kind="repo")]
        self.assertIn("tooling", names)

    def test_unrelated_text_has_no_topics(self):
        self.assertEqual(classify("Weather forecast for tomorrow"), [])

    def test_scores_bounded(self):
        topics = classify("fashion fashion fashion runway couture",
                          "fashion runway garment apparel textile luxury")
        self.assertTrue(all(0.0 <= topic["score"] <= 1.0 for topic in topics))


if __name__ == "__main__":
    unittest.main()
