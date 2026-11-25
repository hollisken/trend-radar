import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radar.normalize import canonical_url, clean_text, parse_date


class CanonicalUrlTest(unittest.TestCase):
    def test_strips_tracking_and_fragment(self):
        self.assertEqual(
            canonical_url("HTTPS://Example.COM/Story/?utm_source=x&id=7&fbclid=9#top"),
            "https://example.com/Story?id=7")

    def test_keeps_path_case_and_drops_default_port(self):
        self.assertEqual(canonical_url("https://example.com:443/A/b/"),
                         "https://example.com/A/b")

    def test_keeps_non_default_port(self):
        self.assertEqual(canonical_url("https://example.com:8443/x"),
                         "https://example.com:8443/x")


class CleanTextTest(unittest.TestCase):
    def test_strips_markup_and_entities(self):
        self.assertEqual(clean_text("<p>A &amp; B</p><script>x</script>"), "A & B x")

    def test_truncates_on_word_boundary(self):
        value = clean_text("alpha beta gamma delta", limit=12)
        self.assertTrue(value.endswith("…"))
        self.assertLessEqual(len(value), 13)

    def test_leaves_short_text_alone(self):
        self.assertEqual(clean_text("  a   b  "), "a b")


class ParseDateTest(unittest.TestCase):
    def test_iso_with_z(self):
        self.assertEqual(parse_date("2026-11-25T08:30:00Z"), "2026-11-25T08:30:00+00:00")

    def test_rfc2822(self):
        self.assertEqual(parse_date("Wed, 25 Nov 2026 08:30:00 +0000"),
                         "2026-11-25T08:30:00+00:00")

    def test_naive_value_gets_utc(self):
        self.assertEqual(parse_date("2026-11-25"), "2026-11-25T00:00:00+00:00")

    def test_junk_is_empty(self):
        self.assertEqual(parse_date("not a date"), "")


if __name__ == "__main__":
    unittest.main()
