"""Guards the published output: metadata only, and no private material in the repo."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Built from fragments so this file does not itself contain the literals it forbids.
FORBIDDEN = [
    "".join(["/data-4T", "/feprg"]),
    "".join(["/var/lib/", "skyeye"]),
    "".join(["/etc/", "skyeye"]),
    "".join(["/opt/", "skyeye-node"]),
    "".join(["127.0.0.1:", "808"]),
    "".join(["xi", "02"]),
    "".join(["oracle", "-oci"]),
    "".join(["us", "-one"]),
    "".join(["us", "-two"]),
    "".join(["guang", "zhou"]),
]
SUFFIXES = {".py", ".md", ".toml", ".json", ".txt", ".xml", ".html", ".yml", ".yaml", ".cfg"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv"}
HTML_TAG = re.compile(r"<[a-zA-Z/][^>]*>")
IMAGE_REF = re.compile(r"https?://\S+\.(?:jpe?g|png|gif|webp|avif)\b", re.IGNORECASE)


def repo_files():
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        if path.suffix.lower() in SUFFIXES:
            yield path


class NoPrivateMaterialTest(unittest.TestCase):
    def test_no_forbidden_literals(self):
        hits = []
        for path in repo_files():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for needle in FORBIDDEN:
                if needle in text:
                    hits.append(f"{path.relative_to(ROOT)}: {needle}")
        self.assertEqual(hits, [], f"private material found: {hits}")

    def test_no_env_files(self):
        self.assertEqual([p.name for p in ROOT.rglob(".env*") if p.is_file()], [])


class PublishedDataTest(unittest.TestCase):
    def test_items_are_metadata_only(self):
        for path in sorted((ROOT / "data").glob("20??-??-??.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertIn("terms_note", payload)
            for item in payload.get("items", []):
                for field in ("id", "title", "url", "retrieved_at"):
                    self.assertTrue(item.get(field), f"{path.name}: missing {field}")
                self.assertTrue(item["url"].startswith("http"), item["url"])
                self.assertTrue(item.get("sightings"), f"{path.name}: no sighting")
                summary = item.get("summary", "")
                self.assertLessEqual(len(summary), 281)
                self.assertIsNone(HTML_TAG.search(item["title"]), item["title"])
                self.assertIsNone(HTML_TAG.search(summary), summary)
                self.assertIsNone(IMAGE_REF.search(summary), summary)


class ReadmeTest(unittest.TestCase):
    def test_markers_present_once(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("<!-- BEGIN LATEST -->"), 1)
        self.assertEqual(text.count("<!-- END LATEST -->"), 1)


if __name__ == "__main__":
    unittest.main()
