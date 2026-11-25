import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import radar.cli as cli
from radar import config as config_mod
from radar.fetch import FetchResult

FIXTURES = ROOT / "tests" / "fixtures"
DATE = "2026-11-26"
SOURCE_DEFAULTS = {"enabled": True, "timeout": 5, "max_bytes": 100_000,
                   "min_interval": 0.0, "max_items": 10}
CONFIG = {"sources": {
    "feed": {**SOURCE_DEFAULTS, "id": "feed", "kind": "rss",
             "url": "https://example.com/feed", "publisher": "Example"},
    "papers": {**SOURCE_DEFAULTS, "id": "papers", "kind": "arxiv", "query": "cat:cs.CV"},
    "repos": {**SOURCE_DEFAULTS, "id": "repos", "kind": "github",
              "query": "video created:>{since}", "since_days": 7},
}, "topics": {}, "settings": {}}


def fake_get(url, **kwargs):
    if url == "https://example.com/feed":
        return FetchResult(url, 200, (FIXTURES / "rss_sample.xml").read_bytes())
    if "export.arxiv.org" in url:
        return FetchResult(url, 200, (FIXTURES / "arxiv_sample.xml").read_bytes())
    if "api.github.com" in url:
        return FetchResult(url, 200, (FIXTURES / "github_sample.json").read_bytes())
    return FetchResult(url, None, error="transport_test")


class CliFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.out = self.base / "out"
        self.data = self.base / "data"
        self.digest = self.base / "digest"
        self.site_path = self.base / "site" / "index.html"
        self.readme = self.base / "README.md"
        self.readme.write_text(f"# Title\n\n<!-- BEGIN LATEST -->\n<!-- END LATEST -->\n",
                               encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _collect(self):
        with mock.patch("radar.fetch.get", fake_get), \
                mock.patch("radar.config.load", return_value=CONFIG):
            code = cli.main(["collect", "--out", str(self.out), "--date", DATE,
                             "--run-at", f"{DATE}T09:00:00+00:00"])
        self.assertEqual(code, 0)
        return next(self.out.glob("run-*.json"))

    def test_collect_writes_artifact_with_stats(self):
        artifact = json.loads(self._collect().read_text(encoding="utf-8"))
        self.assertEqual(artifact["date"], DATE)
        self.assertEqual(len(artifact["items"]), 4)
        self.assertEqual(sum(1 for row in artifact["sources"] if row["status"] == "ok"), 3)
        urls = {item["url"] for item in artifact["items"]}
        self.assertIn("https://example.com/runway?id=1", urls)
        for item in artifact["items"]:
            self.assertEqual(len(item["id"]), 16)
            self.assertTrue(item["retrieved_at"].endswith("+00:00"))
            self.assertTrue(item["sightings"])

    def test_merge_is_idempotent(self):
        artifact = self._collect()
        for _ in range(2):
            self.assertEqual(cli.main(["merge", "--run", str(artifact),
                                       "--data-dir", str(self.data)]), 0)
        payload = json.loads((self.data / f"{DATE}.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload["items"]), 4)
        sightings = [len(item["sightings"]) for item in payload["items"]]
        self.assertTrue(all(count == 1 for count in sightings))
        self.assertEqual(payload["stats"]["items"], 4)

    def test_digest_and_readme(self):
        artifact = self._collect()
        cli.main(["merge", "--run", str(artifact), "--data-dir", str(self.data)])
        code = cli.main(["digest", "--date", DATE, "--data-dir", str(self.data),
                         "--digest-dir", str(self.digest), "--readme", str(self.readme)])
        self.assertEqual(code, 0)
        text = (self.digest / f"{DATE}.md").read_text(encoding="utf-8")
        self.assertIn("# Trend Radar", text)
        self.assertIn("# 趋势雷达", text)
        self.assertIn(f"| {DATE} |", self.readme.read_text(encoding="utf-8"))

    def test_digest_without_data_fails_cleanly(self):
        self.assertEqual(cli.main(["digest", "--date", DATE, "--data-dir", str(self.data),
                                   "--digest-dir", str(self.digest)]), 1)

    def test_site_build(self):
        artifact = self._collect()
        cli.main(["merge", "--run", str(artifact), "--data-dir", str(self.data)])
        self.assertEqual(cli.main(["site", "--data-dir", str(self.data),
                                   "--out", str(self.site_path)]), 0)
        html_text = self.site_path.read_text(encoding="utf-8")
        self.assertIn(DATE, html_text)
        self.assertIn("Trend Radar", html_text)
        self.assertIn('rel="noopener nofollow"', html_text)

    def test_collect_reports_failed_source(self):
        broken = {"sources": {**CONFIG["sources"],
                              "feed": {**CONFIG["sources"]["feed"],
                                       "url": "https://unreachable.example.com/feed"}},
                  "topics": {}, "settings": {}}
        with mock.patch("radar.fetch.get", fake_get), \
                mock.patch("radar.config.load", return_value=broken):
            code = cli.main(["collect", "--out", str(self.out), "--date", DATE,
                             "--run-at", f"{DATE}T10:00:00+00:00"])
        self.assertEqual(code, 0)
        artifact = json.loads(next(self.out.glob("run-*.json")).read_text(encoding="utf-8"))
        failed = [row for row in artifact["sources"] if row["status"] == "error"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["error"], "transport_test")


class ConfigTest(unittest.TestCase):
    def test_valid_file_loads_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.toml"
            path.write_text('[sources.feed]\nkind = "rss"\nurl = "https://example.com/f"\n'
                            'publisher = "Ex"\n[topics.fashion]\nkeywords = ["fashion"]\n',
                            encoding="utf-8")
            loaded = config_mod.load(path)
            self.assertEqual(loaded["topics"], {"fashion": ["fashion"]})
            self.assertEqual(loaded["sources"]["feed"]["max_items"], 25)
            self.assertTrue(loaded["sources"]["feed"]["enabled"])

    def test_unknown_kind_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.toml"
            path.write_text('[sources.bad]\nkind = "smtp"\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                config_mod.load(path)

    def test_missing_required_field_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.toml"
            path.write_text('[sources.feed]\nkind = "rss"\nurl = "https://example.com/f"\n',
                            encoding="utf-8")
            with self.assertRaises(ValueError):
                config_mod.load(path)


if __name__ == "__main__":
    unittest.main()
