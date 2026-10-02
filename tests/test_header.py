import io
import os
import sys
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from tests._helpers import ConfigIsolation
from userscript_manager.utils import (
    build_userscript_header, ensure_userscript_urls, sync_header_version,
)

FULL_HEADER = """// ==UserScript==
// @name         甲
// @version      1.0.0
// @require      https://cdn.example/lib.min.js
// @run-at       document-start
// @icon         https://cdn.example/icon.png
// @exclude      https://ads.example/*
// @match        *://*/*
// ==/UserScript==
main();
"""


class TestHeaderPreservation(ConfigIsolation):
    """头部保留：@require/@run-at 等字段不被同步流程改写。"""
    REDIRECT_PATHS = False

    def test_require_run_at_icon_exclude_preserved(self):
        out = build_userscript_header({"id": "x", "version": "1.0.0"}, FULL_HEADER)
        for field in ("// @require ", "// @run-at ", "// @icon ", "// @exclude "):
            self.assertIn(field, out)
        self.assertIn("main();", out)

    def test_version_synced_to_meta_version(self):
        out = build_userscript_header({"id": "x", "version": "1.2.3"}, FULL_HEADER)
        self.assertIn("// @version      1.2.3", out)

    def test_urls_not_duplicated_when_present(self):
        code = FULL_HEADER.replace("// @match", "// @downloadURL  https://old/x.js\n// @match")
        out = ensure_userscript_urls(code, "https://new/x.js")
        self.assertEqual(out.count("// @downloadURL"), 1)
        self.assertIn("https://new/x.js", out)
        self.assertNotIn("old", out)

    def test_missing_urls_inserted_before_header_end(self):
        out = ensure_userscript_urls(FULL_HEADER, "https://u/x.js")
        self.assertIn("// @downloadURL  https://u/x.js", out.splitlines())
        self.assertLess(out.index("// @downloadURL"), out.index("// ==/UserScript==", 5))

    def test_headerless_code_gets_synthesized_header(self):
        out = build_userscript_header({"id": "x", "name": "N", "version": "1.0.0"}, "fn();")
        self.assertIn("// @name         N", out)
        self.assertIn("// @downloadURL", out)
        self.assertIn("fn();", out)

    def test_sync_header_version_inserts_missing_line(self):
        out = sync_header_version("// ==UserScript==\n// @name A\n// ==/UserScript==", "9.9.9")
        self.assertIn("// @version      9.9.9", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
