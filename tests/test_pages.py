import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from userscript_manager.config import CONFIG
_tmp = Path(tempfile.mkdtemp(prefix="usm_pages_"))
CONFIG["registry_file"] = _tmp / "registry.json"
CONFIG["dist_dir"] = _tmp / "dist"
CONFIG["github_pages"]["base_url"] = ""
CONFIG["github_repo"] = "testuser/testrepo"

from build_pages import build_index, build_detail, build_site, render_markdown


def make_script(**overrides):
    script = {
        "id": "abc123", "type": "self", "name": "甲", "version": "1.0.0",
        "author": "作者", "enabled": True, "match": ["*://a/*"],
        "description": "描述", "documentation": "# 文档",
        "changelog": [{"version": "1.0.0", "date": "2026-10-01", "note": "初始版本"}],
        "discussion": {"number": 4, "node_id": "D_4",
                       "url": "https://github.com/t/r/discussions/4"},
    }
    script.update(overrides)
    return script


class TestPages(unittest.TestCase):
    def test_index_escapes_script_name(self):
        html = build_index({"scripts": [make_script(name='<img src=x onerror="a()">')]})
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img", html)

    def test_index_links_install_detail_and_discussion(self):
        html = build_index({"scripts": [make_script()]})
        self.assertIn('href="scripts/abc123.html"', html)
        self.assertIn("https://testuser.github.io/testrepo/dist/abc123.user.js", html)
        self.assertIn("https://github.com/t/r/discussions/4", html)

    def test_detail_escapes_dynamic_fields(self):
        html = build_detail(make_script(name='<script>x</script>'))
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;", html)

    def test_detail_renders_markdown_documentation(self):
        html = build_detail(make_script(documentation="## 用法\n\n- 点击"))
        self.assertIn("<h2>用法</h2>", html)

    def test_build_site_writes_index_and_detail(self):
        written = build_site({"scripts": [make_script()]})
        self.assertTrue((Path(CONFIG["dist_dir"]) / "index.html").exists())
        self.assertTrue((Path(CONFIG["dist_dir"]) / "scripts" / "abc123.html").exists())
        self.assertEqual(len(written), 2)

    def test_render_markdown_basic(self):
        self.assertIn("<h1>t</h1>", render_markdown("# t"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
