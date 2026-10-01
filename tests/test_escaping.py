import sys
import io
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from userscript_manager.escaping import escape_html, escape_md_cell


class TestEscaping(unittest.TestCase):
    def test_escape_html_blocks_tag_breakout(self):
        out = escape_html('<img src=x onerror="alert(1)">')
        self.assertNotIn("<img", out)
        self.assertIn("&lt;img", out)
        self.assertIn("&quot;", out)

    def test_escape_md_cell_strips_table_breakout(self):
        out = escape_md_cell("a|b\nc")
        self.assertEqual(out, "a\\|b c")


if __name__ == "__main__":
    unittest.main(verbosity=2)
