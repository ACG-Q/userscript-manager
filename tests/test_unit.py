import sys
import io
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from tests._helpers import ConfigIsolation
from userscript_manager.issue_parser import parse_comment, extract_first_code_block, extract_all_code_blocks
from userscript_manager.utils import (
    extract_meta_from_code, strip_header, increment_version, build_dist_for_synced,
    build_userscript_header,
)


class TestIssueParser(unittest.TestCase):
    def test_simple_command(self):
        p = parse_comment("/list")
        self.assertEqual(p.command, "list")
        self.assertEqual(p.args, "")

    def test_command_with_args(self):
        p = parse_comment("/info abc-123")
        self.assertEqual(p.command, "info")
        self.assertEqual(p.args, "abc-123")

    def test_uppercase_command_normalized(self):
        p = parse_comment("/List")
        self.assertEqual(p.command, "list")

    def test_add_with_code_block(self):
        body = "/add\n# 文档\n\n```javascript\nvar x = 1;\n```"
        p = parse_comment(body)
        self.assertEqual(p.command, "add")
        self.assertTrue(p.has_code_block)
        self.assertEqual(p.code.strip(), "var x = 1;")
        self.assertIn("# 文档", p.markdown)

    def test_no_command(self):
        p = parse_comment("这是一句普通评论")
        self.assertIsNone(p.command)

    def test_code_block_with_language(self):
        code, found = extract_first_code_block("```javascript\nalert(1);\n```")
        self.assertTrue(found)
        self.assertEqual(code.strip(), "alert(1);")

    def test_multiple_code_blocks(self):
        blocks = extract_all_code_blocks("```\na\n```\n```\nb\n```")
        self.assertEqual(len(blocks), 2)


class TestUtils(ConfigIsolation):
    REDIRECT_PATHS = False

    def test_extract_meta(self):
        code = "// ==UserScript==\n// @name My Script\n// @version 2.0.0\n// @match *://a.com/*\n// @match *://b.com/*\n// @grant GM_xmlhttpRequest\n// ==/UserScript==\nbody()"
        meta = extract_meta_from_code(code)
        self.assertEqual(meta["name"], "My Script")
        self.assertEqual(meta["version"], "2.0.0")
        self.assertEqual(meta["match"], ["*://a.com/*", "*://b.com/*"])
        self.assertEqual(meta["grant"], ["GM_xmlhttpRequest"])

    def test_strip_header(self):
        code = "// ==UserScript==\n// @name X\n// ==/UserScript==\n\nfunction main() {}\n"
        self.assertEqual(strip_header(code).strip(), "function main() {}")

    def test_increment_version(self):
        self.assertEqual(increment_version("1.2.3"), "1.2.4")
        self.assertEqual(increment_version("1.0"), "1.0.1")
        self.assertEqual(increment_version("not-a-version"), "1.0.1")

    def test_increment_version_two_segments_keeps_major(self):
        self.assertEqual(increment_version("2.5"), "2.5.1")

    def test_increment_version_preserves_fourth_segment(self):
        self.assertEqual(increment_version("1.2.3.4"), "1.2.3.5")

    def test_increment_version_keeps_prerelease_suffix(self):
        self.assertEqual(increment_version("1.2.3-beta"), "1.2.4-beta")

    def test_extract_meta_empty_value_does_not_swallow_next_line(self):
        meta = extract_meta_from_code("// @name\n// @version 1.2.3\n")
        self.assertNotIn("name", meta)
        self.assertEqual(meta.get("version"), "1.2.3")

    def test_extract_meta_last_line_without_newline(self):
        meta = extract_meta_from_code("// ==UserScript==\n// @version 1.2.3")
        self.assertEqual(meta.get("version"), "1.2.3")

    def test_build_dist_for_synced_rewrites_urls(self):
        original = "// ==UserScript==\n// @name X\n// @downloadURL https://old.example/x.js\n// @updateURL https://old.example/x.js\n// @match *://*/*\n// ==/UserScript==\nfn();\n"
        script_meta = {"id": "abc123"}
        out = build_dist_for_synced(script_meta, original)
        self.assertIn("https://testuser.github.io/testrepo/dist/abc123.user.js", out)
        self.assertNotIn("old.example", out)

    def test_build_dist_for_synced_inserts_missing_urls(self):
        original = "// ==UserScript==\n// @name X\n// @match *://*/*\n// ==/UserScript==\nfn();\n"
        out = build_dist_for_synced({"id": "abc123"}, original)
        self.assertIn("// @downloadURL", out)
        self.assertIn("// @updateURL", out)

    def test_build_header_has_download_url(self):
        meta = {"id": "xyz", "name": "T", "version": "1.0.0"}
        header = build_userscript_header(meta, "fn();")
        self.assertIn("// ==UserScript==", header)
        self.assertIn("// @downloadURL", header)
        self.assertIn("fn();", header)


if __name__ == "__main__":
    unittest.main(verbosity=2)