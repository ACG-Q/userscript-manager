import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from tests._helpers import ConfigIsolation
from userscript_manager.config import CONFIG

from build_pages import build_index, build_detail, build_site, render_markdown, empty_state
from build_pages import COMPONENT_CSS, TOKEN_CSS
from build_pages import FILTER_JS as FILTER_JS_SRC
from userscript_manager.issue_stats import IssueStats, LatestReply


def make_script(**overrides):
    script = {
        "id": "abc123", "type": "self", "name": "甲", "version": "1.0.0",
        "author": "作者", "enabled": True, "match": ["*://a/*"],
        "description": "描述", "documentation": "# 文档",
        "changelog": [{"version": "1.0.0", "date": "2026-10-01", "note": "初始版本"}],
        "issue": {"number": 4, "node_id": "I_4",
                  "url": "https://github.com/t/r/issues/4"},
    }
    script.update(overrides)
    return script


def make_stats(answered=True, count=8, replies=None):
    if replies is None:
        replies = (LatestReply(
            author="ACG-Q", body="已修复，更新到 v1.0.1 即可。",
            created_at="2026-10-01T06:00:00Z", is_owner=True,
        ),)
    return IssueStats(
        number=4, url="https://github.com/t/r/issues/4",
        is_closed=answered, reply_count=count, replies=replies,
    )


class TestPages(ConfigIsolation):
    def test_index_escapes_script_name(self):
        html = build_index({"scripts": [make_script(name='<img src=x onerror="a()">')]})
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img", html)

    def test_index_links_install_detail_and_issue(self):
        html = build_index({"scripts": [make_script()]})
        self.assertIn('href="scripts/abc123.html"', html)
        self.assertIn("https://testuser.github.io/testrepo/dist/abc123.user.js", html)
        self.assertIn("https://github.com/t/r/issues/4", html)

    def test_detail_links_install_when_enabled(self):
        html = build_detail(make_script(), make_stats())
        self.assertIn(
            '<a class="btn primary" '
            'href="https://testuser.github.io/testrepo/dist/abc123.user.js">'
            "安装脚本</a>",
            html,
        )

    def test_index_disabled_install_button_is_inert(self):
        html = build_index({"scripts": [make_script(enabled=False)]})
        self.assertNotIn(
            'href="https://testuser.github.io/testrepo/dist/abc123.user.js"', html
        )
        self.assertIn('aria-disabled="true"', html)

    def test_detail_disabled_install_button_is_inert(self):
        html = build_detail(make_script(enabled=False), make_stats())
        self.assertNotIn(
            'href="https://testuser.github.io/testrepo/dist/abc123.user.js"', html
        )
        self.assertIn('aria-disabled="true"', html)

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

    def test_render_markdown_strips_scripts_and_event_handlers(self):
        html = render_markdown(
            "hi <script>alert(1)</script><img src=x onerror=alert(1)>"
        )
        self.assertNotIn("<script", html)
        self.assertNotIn("onerror", html)

    def test_render_markdown_sanitizes_javascript_links(self):
        html = render_markdown("[x](javascript:alert(1))")
        self.assertNotIn("javascript:", html)

    def test_render_markdown_keeps_normal_formatting(self):
        html = render_markdown("# 标题\n\n- 一\n- 二\n\n**粗体** `code`")
        self.assertIn("<h1>", html)
        self.assertIn("<li>", html)
        self.assertIn("<strong>", html)
        self.assertIn("<code>", html)


class TestIndexPanels(ConfigIsolation):
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

    def test_card_without_issue_shows_empty_state(self):
        html = build_index({"scripts": [make_script(issue=None)]}, {})
        self.assertIn("还没有讨论", html)
        self.assertIn("/issues", html)

    def test_card_degraded_keeps_github_link(self):
        html = build_index({"scripts": [make_script()]}, None)
        self.assertIn("摘要暂不可用", html)
        self.assertIn("https://github.com/t/r/issues/4", html)

    def test_hero_stats_sum_and_dash(self):
        html = build_index({"scripts": [make_script()]}, {"abc123": make_stats(count=8)})
        self.assertIn("<b>8</b>", html)
        html_none = build_index({"scripts": [make_script()]}, None)
        self.assertIn("<b>—</b>", html_none)

    def test_filter_chips_and_data_type(self):
        html = build_index({"scripts": [make_script(type="synced")]}, {})
        self.assertIn('data-type="synced"', html)
        self.assertIn('data-filter="all"', html)
        # data-filter 必须与 data-type 同值，否则「同步」筛选永远匹配不到卡片
        self.assertIn('data-filter="synced"', html)
        self.assertNotIn('data-filter="sync"', html)
        self.assertIn(".chip", html)

    def test_empty_registry_message(self):
        html = build_index({"scripts": []}, {})
        self.assertIn("暂无脚本", html)

    def test_stats_panel_wraps_disc_head_in_sc_disc(self):
        html = build_index({"scripts": [make_script()]}, {"abc123": make_stats()})
        self.assertIn('<div class="sc-disc"><div class="disc-head">', html)

    def test_index_div_tags_balanced_with_stats(self):
        html = build_index({"scripts": [make_script()]}, {"abc123": make_stats()})
        body = html[html.find("<body>"):html.find("</body>")]
        self.assertEqual(
            body.count("<div"), body.count("</div>"),
            "div 开闭标签必须配平，否则 frame 会被提前关闭",
        )

    def test_hidden_cards_css_rule_present(self):
        from build_pages import COMPONENT_CSS
        self.assertIn("[hidden] { display: none !important; }", COMPONENT_CSS)

    def test_pills_have_tooltips(self):
        html = build_index({"scripts": [make_script()]}, {"abc123": make_stats()})
        self.assertIn('data-tip="本仓库自主编写的脚本"', html)
        self.assertIn('data-tip="当前版本"', html)
        self.assertIn('data-tip="脚本已启用，安装链接可用"', html)
        self.assertIn('data-tip="讨论已被标记为已解决"', html)
        self.assertIn('data-tip="讨论回复总数"', html)

    def test_sync_and_disabled_have_tooltips(self):
        html = build_index(
            {"scripts": [make_script(type="synced", source_type="direct",
                                     enabled=False)]},
            {},
        )
        self.assertIn('data-tip="从外部来源自动同步的脚本"', html)
        self.assertIn('data-tip="脚本已禁用，暂不可安装"', html)

    def test_filter_empty_state_present_and_hidden(self):
        html = build_index({"scripts": [make_script()]}, {})
        self.assertIn('id="filter-empty" hidden', html)
        self.assertIn("没有符合筛选条件的脚本", html)
        self.assertIn("filter-empty", FILTER_JS_SRC)
        self.assertIn('class="empty-state"', html)
        self.assertNotIn('class="empty"', html)

    def test_list_url_filters_by_label(self):
        html = build_index({"scripts": [make_script(issue=None)]})
        self.assertIn("q=is%3Aissue+label%3Ascript", html)


class TestDetailPanels(ConfigIsolation):
    def test_no_issue_empty_state(self):
        html = build_detail(make_script(issue=None), make_stats())
        self.assertIn("还没有讨论", html)
        self.assertIn("testuser/testrepo/issues", html)
        self.assertNotIn("摘要暂不可用", html)

    def test_degraded_panel_keeps_github_link(self):
        html = build_detail(make_script())
        self.assertIn("摘要暂不可用", html)
        self.assertIn("https://github.com/t/r/issues/4", html)
        self.assertNotIn('<div class="cmt', html)

    def test_stats_panel_shows_badges_and_comments(self):
        html = build_detail(make_script(), make_stats())
        self.assertIn("已解决", html)
        self.assertIn("8 条回复", html)
        self.assertIn('<div class="cmt owner">', html)
        self.assertIn("已修复，更新到 v1.0.1 即可。", html)
        self.assertIn("<time>", html)
        self.assertIn("https://github.com/t/r/issues/4", html)

    def test_stats_unanswered_zero_replies(self):
        html = build_detail(
            make_script(),
            make_stats(answered=False, count=0, replies=()),
        )
        self.assertNotIn('<span class="badge">', html)
        self.assertIn("0 条回复", html)
        self.assertIn("还没有回复", html)

    def test_detail_has_back_button_and_relative_home(self):
        html = build_detail(make_script(), make_stats())
        self.assertIn("返回列表", html)
        self.assertIn('href="../index.html"', html)
        self.assertIn('class="brand" href="../index.html"', html)

    def test_index_brand_links_home(self):
        html = build_index({"scripts": []})
        self.assertIn('class="brand" href="index.html"', html)

    def test_detail_pills_have_tooltips(self):
        html = build_detail(make_script(), make_stats())
        self.assertIn('data-tip="本仓库自主编写的脚本"', html)
        self.assertIn('data-tip="当前版本"', html)
        self.assertIn('data-tip="脚本已启用，安装链接可用"', html)
        self.assertIn('data-tip="讨论已被标记为已解决"', html)

    def test_empty_changelog_uses_empty_state(self):
        html = build_detail(make_script(changelog=[]))
        self.assertIn('class="empty-state"', html)
        self.assertIn("暂无更新记录。", html)

    def test_issue_empty_states_use_component(self):
        card = build_index({"scripts": [make_script(issue=None)]})
        self.assertIn('class="empty-state sm"', card)
        self.assertIn("还没有讨论", card)
        degraded = build_detail(make_script(), None)
        self.assertIn('class="empty-state sm"', degraded)
        self.assertIn("摘要暂不可用", degraded)
        with_disc = build_detail(make_script(), make_stats(replies=()))
        self.assertIn("还没有回复", with_disc)

    def test_empty_state_renders_svg_text_and_variants(self):
        html = empty_state("没有数据")
        self.assertIn('class="empty-state"', html)
        self.assertIn("<svg", html)
        self.assertIn("没有数据", html)
        self.assertIn('role="status"', html)
        self.assertIn('class="empty-state sm"', empty_state("x", small=True))

    def test_empty_state_injects_link_and_filter_attrs(self):
        html = empty_state("x", link_html='<a href="https://e">发起讨论 →</a>')
        self.assertIn('<a href="https://e">发起讨论 →</a>', html)
        f = empty_state("x", elem_id="filter-empty", hidden=True)
        self.assertIn('id="filter-empty" hidden', f)

    def test_empty_state_css_defined(self):
        self.assertIn(".empty-state {", COMPONENT_CSS)
        self.assertIn(".empty-state.sm", COMPONENT_CSS)

    def test_tooltip_css_and_tokens_defined(self):
        self.assertIn("content: attr(data-tip)", COMPONENT_CSS)
        self.assertIn("--tip-bg", TOKEN_CSS)
        self.assertIn("--tip-fg", TOKEN_CSS)


class TestBuildSiteStats(ConfigIsolation):
    def _read(self, *parts):
        return (Path(CONFIG["dist_dir"]).joinpath(*parts)).read_text(encoding="utf-8")

    def test_passes_stats_to_index_and_detail(self):
        written = build_site({"scripts": [make_script()]}, {"abc123": make_stats()})
        self.assertIn("8 条回复", self._read("index.html"))
        self.assertIn('<div class="cmt owner">', self._read("scripts", "abc123.html"))
        self.assertEqual(len(written), 2)

    def test_none_stats_degrades_all_pages(self):
        build_site({"scripts": [make_script()]}, None)
        self.assertIn("<b>—</b>", self._read("index.html"))
        self.assertIn("摘要暂不可用", self._read("scripts", "abc123.html"))


class TestMainWiring(ConfigIsolation):
    TMP_PREFIX = "usm_main_"

    def _write_registry(self):
        Path(CONFIG["registry_file"]).write_text(
            json.dumps({"scripts": [make_script()]}), encoding="utf-8"
        )

    def _read_index(self):
        return (Path(CONFIG["dist_dir"]) / "index.html").read_text(encoding="utf-8")

    def test_main_without_token_degrades_and_warns(self):
        import build_pages as bp
        self._write_registry()
        orig_token = os.environ.pop("GITHUB_TOKEN", None)
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                rc = bp.main()
        finally:
            if orig_token is not None:
                os.environ["GITHUB_TOKEN"] = orig_token
        self.assertEqual(rc, 0)
        self.assertIn("GITHUB_TOKEN", err.getvalue())
        self.assertIn("<b>—</b>", self._read_index())

    def test_main_with_token_fetches_and_injects(self):
        import build_pages as bp
        self._write_registry()
        orig_token = os.environ.pop("GITHUB_TOKEN", None)
        os.environ["GITHUB_TOKEN"] = "fake-token"
        called = {}

        def fake_fetch(client, owner, name, scripts):
            called.update(owner=owner, name=name)
            return {"abc123": make_stats()}

        orig_fetch = bp.fetch_stats
        bp.fetch_stats = fake_fetch
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                rc = bp.main()
        finally:
            bp.fetch_stats = orig_fetch
            os.environ.pop("GITHUB_TOKEN", None)
            if orig_token is not None:
                os.environ["GITHUB_TOKEN"] = orig_token
        self.assertEqual(rc, 0)
        self.assertEqual(called, {"owner": "testuser", "name": "testrepo"})
        self.assertIn("8 条回复", self._read_index())


class TestThemeTokens(ConfigIsolation):
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


class TestThemeTokensFilled(ConfigIsolation):
    def _block(self, name):
        from build_pages import TOKEN_CSS
        start = TOKEN_CSS.index(f'[data-theme="{name}"]')
        end = TOKEN_CSS.index("}", start)
        return TOKEN_CSS[start:end]

    def test_terminal_dark_block_fills_all_key_tokens(self):
        block = self._block("terminal-dark")
        self.assertNotIn("预留", block)
        for tok in ("--brand:", "--brand-hover:", "--primary:", "--bg:", "--bg-subtle:",
                    "--page-bg:", "--text:", "--text-muted:", "--border:", "--success:",
                    "--danger:", "--info-bg:", "--warn-bg:", "--neutral-bg:",
                    "--tip-bg:", "--hero-bg:", "--hero-fg:", "--hero-sub:", "--on-accent:"):
            self.assertIn(tok, block)

    def test_vivid_purple_block_fills_all_key_tokens(self):
        block = self._block("vivid-purple")
        self.assertNotIn("预留", block)
        for tok in ("--brand: #6e56cf", "--primary: linear-gradient", "--page-bg:",
                    "--text:", "--border:", "--tip-bg:", "--hero-bg: linear-gradient",
                    "--hero-fg: #fff", "--on-accent:"):
            self.assertIn(tok, block)

    def test_root_defines_new_tokens(self):
        from build_pages import TOKEN_CSS
        for tok in ("--hero-bg: #f6f8fa", "--hero-fg: #1f2328",
                    "--hero-sub: #57606a", "--on-accent: #fff"):
            self.assertIn(tok, TOKEN_CSS)

    def test_component_layer_uses_new_tokens(self):
        from build_pages import COMPONENT_CSS
        for ref in ("var(--hero-bg)", "var(--hero-fg)", "var(--hero-sub)", "var(--on-accent)"):
            self.assertIn(ref, COMPONENT_CSS)


class TestThemeDrawerMarkup(ConfigIsolation):
    def test_index_and_detail_contain_rail_and_drawer(self):
        for html in (build_index({"scripts": []}), build_detail(make_script())):
            self.assertIn('id="themeRail"', html)
            self.assertIn('id="settingsDrawer"', html)
            self.assertIn('id="sdOverlay"', html)

    def test_drawer_has_three_theme_rows_with_preview(self):
        html = build_index({"scripts": []})
        for theme in ("github-light", "terminal-dark", "vivid-purple"):
            self.assertIn(f'data-theme="{theme}"', html)
        for pv in ("pv-a", "pv-b", "pv-c", "tl-label", "tl-preview", "sd-soon"):
            self.assertIn(pv, html)

    def test_drawer_styles_present(self):
        from build_pages import COMPONENT_CSS, PREVIEW_CSS
        for cls in (".theme-rail", ".settings-drawer", ".theme-list",
                    ".tl-preview", ".swatch", ".check"):
            self.assertIn(cls, COMPONENT_CSS)
        self.assertIn("grid-template-columns: repeat(2, 1fr)", COMPONENT_CSS)
        for cls in (".pv-a", ".pv-b", ".pv-c", ".swatch-a", ".swatch-b", ".swatch-c"):
            self.assertIn(cls, PREVIEW_CSS)


class TestThemeDrawerJS(ConfigIsolation):
    def test_head_applies_stored_theme_before_paint(self):
        for html in (build_index({"scripts": []}), build_detail(make_script())):
            head = html.split("</head>")[0]
            self.assertIn("asm-theme", head)
            self.assertIn('setAttribute("data-theme"', head.replace("'", '"'))

    def test_page_wires_drawer_and_persistence(self):
        html = build_index({"scripts": []})
        self.assertIn("asm-theme", html)
        self.assertIn("applyTheme", html)
        self.assertIn("Escape", html)
        self.assertIn("settingsDrawer", html)
        self.assertIn("localStorage", html)

    def test_initial_theme_attribute_unchanged_fallback(self):
        html = build_index({"scripts": []})
        self.assertIn('<html lang="zh-CN" data-theme="github-light">', html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
