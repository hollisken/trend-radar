import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radar.sources import arxiv, github, rss

FIXTURES = ROOT / "tests" / "fixtures"


class RssTest(unittest.TestCase):
    def setUp(self):
        body = (FIXTURES / "rss_sample.xml").read_bytes()
        self.items = rss.parse(body, {"id": "feed", "publisher": "Example"})

    def test_keeps_three_raw_items(self):
        self.assertEqual(len(self.items), 3)
        self.assertEqual(self.items[0]["url"], "https://example.com/runway?utm_source=rss&id=1")

    def test_carries_publisher(self):
        self.assertTrue(all(item["publisher"] == "Example" for item in self.items))

    def test_atom_feed(self):
        body = (FIXTURES / "atom_sample.xml").read_bytes()
        items = rss.parse(body, {"id": "atom", "publisher": "Atom Example"})
        self.assertEqual(items[0]["url"], "https://example.org/beauty")
        self.assertEqual(items[1]["url"], "https://example.org/second")

    def test_unsupported_root_raises(self):
        with self.assertRaises(Exception):
            rss.parse(b"<html><body/></html>", {"id": "x", "publisher": "X"})


class ArxivTest(unittest.TestCase):
    def test_parse_entry(self):
        body = (FIXTURES / "arxiv_sample.xml").read_bytes()
        items = arxiv.parse(body, {"id": "papers"})
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["kind"], "paper")
        self.assertEqual(item["publisher"], "arXiv")
        self.assertEqual(item["url"], "http://arxiv.org/abs/2611.00001v1")
        self.assertEqual(item["meta"]["authors"], ["Ada Lovelace", "Grace Hopper"])

    def test_url_shape(self):
        url = arxiv.build_url('cat:cs.CV AND all:"video"', 5)
        self.assertIn("max_results=5", url)
        self.assertIn("sortBy=submittedDate", url)


class GithubTest(unittest.TestCase):
    def test_parse_repository(self):
        body = (FIXTURES / "github_sample.json").read_bytes()
        items = github.parse(body, {"id": "repos"})
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["kind"], "repo")
        self.assertEqual(item["publisher"], "example")
        self.assertEqual(item["meta"]["stars"], 321)

    def test_url_encodes_query(self):
        url = github.build_url("virtual try-on created:>{since}", 10)
        self.assertIn("per_page=10", url)
        self.assertIn("sort=stars", url)


if __name__ == "__main__":
    unittest.main()
