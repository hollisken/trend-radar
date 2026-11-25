import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radar import site


class RenderMarkdownTest(unittest.TestCase):
    def test_headings_bullets_and_rule(self):
        rendered = site.render_markdown("# Title\n\n## Part\n\n- one\n- two\n\n---\n")
        self.assertIn("<h1>Title</h1>", rendered)
        self.assertIn("<h2>Part</h2>", rendered)
        self.assertEqual(rendered.count("<li>"), 2)
        self.assertIn("</ul>", rendered)
        self.assertIn("<hr>", rendered)

    def test_links_and_bold(self):
        rendered = site.render_markdown("- **Fashion** — [Story](https://example.com/a?x=1&y=2)")
        self.assertIn('<a href="https://example.com/a?x=1&amp;y=2" rel="noopener nofollow">Story</a>',
                      rendered)
        self.assertIn("<strong>Fashion</strong>", rendered)

    def test_html_is_escaped(self):
        rendered = site.render_markdown("<script>alert(1)</script> [x](https://example.com)")
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_list_closes_before_paragraph(self):
        rendered = site.render_markdown("- a\n\ntext")
        self.assertTrue(rendered.index("</ul>") < rendered.index("<p>text</p>"))


class DigestPagesTest(unittest.TestCase):
    def test_pages_generated_and_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            digest_dir = base / "digest"
            digest_dir.mkdir()
            (digest_dir / "2026-11-26.md").write_text("# Trend Radar — 2026-11-26\n\n- **Fashion** — [x](https://e.com)\n",
                                                       encoding="utf-8")
            site_dir = base / "site"
            data_dir = base / "data"
            data_dir.mkdir()
            (data_dir / "2026-11-26.json").write_text(
                '{"date":"2026-11-26","stats":{"items":1,"by_topic":{"fashion":1}},'
                '"items":[{"id":"1","title":"x","url":"https://e.com","publisher":"P",'
                '"kind":"news","topics":[{"name":"fashion","score":0.9}]}]}', encoding="utf-8")
            count = site.build_digest_pages(digest_dir, site_dir)
            self.assertEqual(count, 1)
            page = (site_dir / "digest" / "2026-11-26.html").read_text(encoding="utf-8")
            self.assertIn("<h1>Trend Radar — 2026-11-26</h1>", page)
            self.assertIn('href="../index.html"', page)
            index = site.build(data_dir)
            self.assertIn('href="digest/2026-11-26.html"', index)


if __name__ == "__main__":
    unittest.main()
