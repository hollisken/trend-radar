import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from radar.translate_titles import fill_titles, request_translations


def item(identifier, title, **extra):
    return {"id": identifier, "title": title, "topics": [{"name": "fashion"}], **extra}


class TranslationTest(unittest.TestCase):
    def test_reuses_prior_titles_and_preserves_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = base / "2026-11-26.json"
            second = base / "2026-11-27.json"
            first.write_text(json.dumps({"items": [item("a", "First", title_zh="首篇")]}))
            second.write_text(json.dumps({"items": [item("a", "First"), item("b", "Second")]}))
            with patch("radar.translate_titles.request_translations", return_value={"Second": "第二篇"}) as translate:
                self.assertEqual(fill_titles(base, [second.stem], translate), (2, 0))
            translate.assert_called_once_with(["Second"])
            rows = json.loads(second.read_text())["items"]
            self.assertEqual([(r["title"], r["title_zh"]) for r in rows],
                             [("First", "首篇"), ("Second", "第二篇")])

    def test_endpoint_failure_leaves_title_available_for_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            day = base / "2026-11-27.json"
            original = json.dumps({"items": [item("id", "Pending")]})
            day.write_text(original)
            with patch("radar.translate_titles.request_translations", side_effect=TimeoutError) as translate:
                self.assertEqual(fill_titles(base, [day.stem], translate), (0, 1))
            self.assertEqual(day.read_text(), original)

    def test_rejects_mismatched_reply_keys(self):
        with patch("radar.translate_titles.urllib.request.build_opener") as opener:
            response = opener.return_value.open.return_value.__enter__.return_value
            response.read.return_value = json.dumps({"choices": [{"message": {"content": '{"1":"标题"}'}}]}).encode()
            with self.assertRaisesRegex(ValueError, "headline IDs"):
                request_translations("http://127.0.0.1/v1/chat/completions", "test", ["Title"])


if __name__ == "__main__":
    unittest.main()
