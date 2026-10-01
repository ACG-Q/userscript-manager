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
from userscript_manager.discussion_stats import DiscussionStats, LatestReply


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


def make_stats(answered=True, count=8, replies=None):
    if replies is None:
        replies = (LatestReply(
            author="ACG-Q", body="已修复，更新到 v1.0.1 即可。",
            created_at="2026-10-01T06:00:00Z", is_owner=True,
        ),)
    return DiscussionStats(
        number=4, url="https://github.com/t/r/discussions/4",
        is_answered=answered, reply_count=count, replies=replies,
    )


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


class TestIndexPanels(unittest.TestCase):
    def test_card_with_stats_shows_badges_and_quote(self):
        html = build_index({"scripts": [make_script()]}, {"abc123": make_stats()})
        self.assertIn("已解决", html)
        self.assertIn("8 条回复", html)
        self.assertIn("v1.0.1", html)
        self.assertIn("仓库所有者", html)

    def test_card_unanswered_badge_without_quote(self):
        html = build_index(
            {"scripts": [make_script()]},
            {"abc123": make_stats(answered=False, count=3, replies=())},
        )
        self.assertIn("3 条回复 · 待解决", html)
        self.assertNotIn('<span class="badge">', html)
        self.assertNotIn('<p class="disc-latest">', html)

    def test_card_without_discussion_shows_empty_state(self):
        html = build_index({"scripts": [make_script(discussion=None)]}, {})
        self.assertIn("还没有讨论", html)
        self.assertIn("/discussions", html)

    def test_card_degraded_keeps_github_link(self):
        html = build_index({"scripts": [make_script()]}, None)
        self.assertIn("摘要暂不可用", html)
        self.assertIn("https://github.com/t/r/discussions/4", html)

    def test_hero_stats_sum_and_dash(self):
        html = build_index({"scripts": [make_script()]}, {"abc123": make_stats(count=8)})
        self.assertIn("<b>8</b>", html)
        html_none = build_index({"scripts": [make_script()]}, None)
        self.assertIn("<b>—</b>", html_none)

    def test_filter_chips_and_data_type(self):
        html = build_index({"scripts": [make_script(type="sync")]}, {})
        self.assertIn('data-type="sync"', html)
        self.assertIn('data-filter="all"', html)
        self.assertIn(".chip", html)

    def test_empty_registry_message(self):
        html = build_index({"scripts": []}, {})
        self.assertIn("暂无脚本", html)


class TestDetailPanels(unittest.TestCase):
    def test_no_discussion_empty_state(self):
        html = build_detail(make_script(discussion=None), make_stats())
        self.assertIn("还没有讨论", html)
        self.assertIn("testuser/testrepo/discussions", html)
        self.assertNotIn("摘要暂不可用", html)

    def test_degraded_panel_keeps_github_link(self):
        html = build_detail(make_script())
        self.assertIn("摘要暂不可用", html)
        self.assertIn("https://github.com/t/r/discussions/4", html)
        self.assertNotIn('<div class="cmt', html)

    def test_stats_panel_shows_badges_and_comments(self):
        html = build_detail(make_script(), make_stats())
        self.assertIn("已解决", html)
        self.assertIn("8 条回复", html)
        self.assertIn('<div class="cmt owner">', html)
        self.assertIn("已修复，更新到 v1.0.1 即可。", html)
        self.assertIn("<time>", html)
        self.assertIn("https://github.com/t/r/discussions/4", html)

    def test_stats_unanswered_zero_replies(self):
        html = build_detail(
            make_script(),
            make_stats(answered=False, count=0, replies=()),
        )
        self.assertNotIn('<span class="badge">', html)
        self.assertIn("0 条回复", html)
        self.assertIn("还没有回复", html)


class TestThemeTokens(unittest.TestCase):
    def test_html_declares_default_theme(self):
        html = build_index({"scripts": []})
        self.assertIn('data-theme="github-light"', html)

    def test_reserved_theme_blocks_present(self):
        html = build_index({"scripts": []})
        self.assertIn('[data-theme="terminal-dark"]', html)
        self.assertIn('[data-theme="vivid-purple"]', html)

    def test_token_layer_defines_brand(self):
        from build_pages import TOKEN_CSS
        self.assertIn("--brand: #0969da", TOKEN_CSS)
        self.assertIn("--font-mono", TOKEN_CSS)

    def test_component_layer_only_uses_variables(self):
        from build_pages import COMPONENT_CSS
        self.assertNotIn("#0969da", COMPONENT_CSS)
        self.assertIn("var(--brand)", COMPONENT_CSS)

    def test_shell_has_nav_and_footer_links(self):
        html = build_index({"scripts": []})
        self.assertIn("https://github.com/testuser/testrepo", html)
        self.assertIn("issues/1", html)
        self.assertIn("管理入口", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
