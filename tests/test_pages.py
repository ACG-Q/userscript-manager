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
from build_pages import fetch_discussion_posts, COMPONENT_CSS, TOKEN_CSS
from build_pages import FILTER_JS as FILTER_JS_SRC
from build_pages import LIST_JS as LIST_JS_SRC
from build_pages import DISC_JS as DISC_JS_SRC
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
            'href="https://testuser.github.io/testrepo/dist/abc123.user.js"'
            ' target="_blank" rel="noopener noreferrer">安装脚本</a>',
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
        dist = Path(CONFIG["dist_dir"])
        self.assertTrue((dist / "index.html").exists())
        self.assertTrue((dist / "scripts" / "abc123.html").exists())
        # 新增产物：懒加载数据 + 命令归档页（page-1 与跳转页）
        self.assertTrue((dist / "scripts.json").exists())
        self.assertTrue((dist / "commands" / "page-1.html").exists())
        self.assertTrue((dist / "commands" / "index.html").exists())
        self.assertEqual(len(written), 5)

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
        self.assertEqual(len(written), 5)

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


class TestBuildWarningsFile(ConfigIsolation):
    """拉取失败的原因落到 dist/build-warnings.txt，部署后可在站点根目录查看。"""

    TMP_PREFIX = "usm_warn_"

    def _write_registry(self):
        Path(CONFIG["registry_file"]).write_text(
            json.dumps({"scripts": [make_script(discussions=make_ledger())]}),
            encoding="utf-8",
        )

    def _run_main(self, fake_disc):
        import build_pages as bp
        self._write_registry()
        orig_token = os.environ.get("GITHUB_TOKEN")
        os.environ["GITHUB_TOKEN"] = "fake-token"
        orig = bp.fetch_stats, bp.fetch_discussion_posts
        bp.fetch_stats = lambda *a, **k: {"abc123": make_stats()}
        bp.fetch_discussion_posts = fake_disc
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                rc = bp.main()
        finally:
            bp.fetch_stats, bp.fetch_discussion_posts = orig
            if orig_token is None:
                os.environ.pop("GITHUB_TOKEN", None)
            else:
                os.environ["GITHUB_TOKEN"] = orig_token
        return rc

    def _warnings_file(self):
        return Path(CONFIG["dist_dir"]) / "build-warnings.txt"

    def test_main_writes_warnings_when_fetch_fails(self):
        def fake_disc(client, scripts, problems=None):
            if problems is not None:
                problems.append(
                    "版本帖评论整体拉取失败，详情页回退 Issue 评论渲染：403")
            return None

        self.assertEqual(self._run_main(fake_disc), 0)
        warn = self._warnings_file()
        self.assertTrue(warn.exists())
        self.assertIn("403", warn.read_text(encoding="utf-8"))

    def test_main_removes_stale_warnings_when_fetch_ok(self):
        self._warnings_file().parent.mkdir(parents=True, exist_ok=True)
        self._warnings_file().write_text("旧告警\n", encoding="utf-8")

        def fake_disc(client, scripts, problems=None):
            return {"abc123": make_posts()}

        self.assertEqual(self._run_main(fake_disc), 0)
        self.assertFalse(self._warnings_file().exists())


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


class TestNewTabLinks(ConfigIsolation):
    """外链（GitHub / 安装地址）一律新标签打开，站内页面导航保持当前标签。"""

    def test_index_external_links_open_new_tab(self):
        html = build_index({"scripts": [make_script()]}, {"abc123": make_stats()})
        attrs = ' target="_blank" rel="noopener noreferrer"'
        for marker in (
            'href="https://github.com/testuser/testrepo/blob/master/docs/index.md"',
            'href="https://github.com/testuser/testrepo"',
            'href="https://github.com/testuser/testrepo/issues/1"',
            'href="https://github.com/t/r/issues/4"',   # 卡片「讨论」
        ):
            self.assertIn(f"{marker}{attrs}>", html)
        self.assertIn(
            'href="https://testuser.github.io/testrepo/dist/abc123.user.js"'
            f"{attrs}>", html,
        )

    def test_index_internal_links_stay_in_tab(self):
        html = build_index({"scripts": [make_script()]})
        self.assertIn('<a class="btn ghost" href="scripts/abc123.html">详情</a>', html)
        self.assertNotIn('href="scripts/abc123.html" target', html)
        self.assertNotIn('<a class="brand" href="index.html" target', html)

    def test_detail_external_new_tab_and_internal_in_tab(self):
        html = build_detail(make_script(), make_stats())
        self.assertIn(
            'href="https://github.com/t/r/issues/4"'
            ' target="_blank" rel="noopener noreferrer">在 GitHub 打开 →</a>', html,
        )
        self.assertIn('<a class="back" href="../index.html">← 返回列表</a>', html)
        self.assertNotIn('href="../index.html" target', html)
        self.assertNotIn('<a class="brand" href="../index.html" target', html)

    def test_version_panel_link_opens_new_tab(self):
        html = build_detail(make_script(discussions=make_ledger()), None, make_posts())
        self.assertIn(
            'id="discLink" href="https://github.com/t/r/discussions/9"'
            ' target="_blank" rel="noopener noreferrer"', html,
        )


def make_ledger():
    """版本帖账本：旧→新（与 projector 追加顺序一致）。"""
    return [
        {"version": "1.0.0", "number": 7, "node_id": "D_7",
         "url": "https://github.com/t/r/discussions/7", "created_at": "2026-10-01"},
        {"version": "1.0.1", "number": 9, "node_id": "D_9",
         "url": "https://github.com/t/r/discussions/9", "created_at": "2026-10-02"},
    ]


def make_posts(body="搜索结果页还有广告"):
    """fetch_discussion_posts 的展示结果：新→旧，含一条嵌套回复与一个空版本帖。"""
    return [
        {"version": "1.0.1", "number": 9,
         "url": "https://github.com/t/r/discussions/9",
         "is_answered": True, "reply_count": 2,
         "comments": [{
             "author": "u1", "is_owner": False, "is_answer": False,
             "time": "2 天前", "body": body,
             "replies": [{"author": "ACG-Q", "is_owner": True, "is_answer": True,
                          "time": "1 天前", "body": "已修复", "replies": []}],
         }]},
        {"version": "1.0.0", "number": 7,
         "url": "https://github.com/t/r/discussions/7",
         "is_answered": False, "reply_count": 0, "comments": []},
    ]


class TestFetchDiscussionPosts(ConfigIsolation):
    def test_no_ledger_returns_empty_without_client_calls(self):
        class Boom:
            def execute(self, *args, **kwargs):
                raise AssertionError("无版本帖时不应发请求")

        self.assertEqual(fetch_discussion_posts(Boom(), [make_script()]), {})

    def test_posts_ordered_newest_first_with_counts(self):
        class Client:
            def execute(self, query, variables=None):
                nid = variables["id"]
                return {"node": {
                    "title": "版本帖",
                    "url": f"https://github.com/t/r/discussions/{nid[-1]}",
                    "isAnswered": nid == "D_9",
                    "comments": {"totalCount": 1, "nodes": [{
                        "author": {"login": "u1"}, "authorAssociation": "NONE",
                        "body": "有问题", "createdAt": "2026-10-02T06:00:00Z",
                        "isAnswer": False,
                        "replies": {"nodes": [{
                            "author": {"login": "ACG-Q"},
                            "authorAssociation": "OWNER",
                            "body": "已修复", "createdAt": "2026-10-02T07:00:00Z",
                            "isAnswer": True, "replies": {"nodes": []}},
                        ]},
                    }]},
                }}

        out = fetch_discussion_posts(Client(), [make_script(discussions=make_ledger())])
        posts = out["abc123"]
        self.assertEqual([p["version"] for p in posts], ["1.0.1", "1.0.0"])
        self.assertEqual([p["number"] for p in posts], [9, 7])
        self.assertTrue(posts[0]["is_answered"])
        self.assertEqual(posts[0]["reply_count"], 2)  # 顶层 1 条 + 嵌套 1 条
        self.assertEqual(posts[0]["comments"][0]["replies"][0]["author"], "ACG-Q")
        # createdAt 已转成构建时可读的相对时间（不再是原始 ISO 串）
        self.assertTrue(posts[0]["comments"][0]["time"])
        self.assertNotIn("2026-10-02T", posts[0]["comments"][0]["time"])

    def test_fetch_failure_returns_none_for_fallback(self):
        class Client:
            def execute(self, *args, **kwargs):
                raise RuntimeError("boom")

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = fetch_discussion_posts(
                Client(), [make_script(discussions=make_ledger())])
        self.assertIsNone(out)
        self.assertIn("回退", err.getvalue())

    def test_problems_collect_failure_reasons(self):
        class Boom:
            def execute(self, *args, **kwargs):
                raise RuntimeError("403 forbidden")

        problems = []
        with contextlib.redirect_stderr(io.StringIO()):
            out = fetch_discussion_posts(
                Boom(), [make_script(discussions=make_ledger())], problems)
        self.assertIsNone(out)
        self.assertEqual(len(problems), 1)
        self.assertIn("整体拉取失败", problems[0])
        self.assertIn("403 forbidden", problems[0])

    def test_problems_collect_empty_discussion_nodes(self):
        class Client:
            def execute(self, query, variables=None):
                return {"node": None}

        problems = []
        out = fetch_discussion_posts(
            Client(), [make_script(discussions=make_ledger())], problems)
        self.assertEqual(out, {})          # 一个都没拉到 → 详情页回退
        self.assertEqual(len(problems), 2)  # 每个版本帖各记一条
        self.assertIn("拉取为空", problems[0])
        self.assertIn("#9", problems[0])


class TestDetailVersionSwitch(ConfigIsolation):
    def test_switcher_renders_dropdown_payload_and_comments(self):
        html = build_detail(make_script(discussions=make_ledger()),
                            make_stats(), make_posts())
        self.assertIn('id="discData"', html)
        self.assertIn('id="discVerBtn"', html)
        self.assertIn('<span id="discVerLabel">v1.0.1（最新）</span>', html)
        self.assertIn('>v1.0.0<span class="num">#7</span></button>', html)
        self.assertIn('data-i="1"', html)
        self.assertIn('aria-selected="true"', html)
        self.assertIn('aria-haspopup="listbox"', html)
        self.assertIn("https://github.com/t/r/discussions/9", html)
        self.assertIn("在 GitHub 打开本帖", html)
        # 评论与徽标来自版本帖，不再是 Issue 回复
        self.assertIn("2 条回复", html)
        self.assertIn("已解决", html)
        self.assertIn('<div class="cmt owner">', html)
        self.assertIn("answer-tag", html)
        self.assertIn("cmt-replies", html)
        self.assertIn("搜索结果页还有广告", html)
        self.assertNotIn("已修复，更新到 v1.0.1 即可。", html)
        # 空版本帖：服务端空态 + 供切换复用的模板
        self.assertIn("该版本帖还没有评论", html)
        self.assertIn('<template id="discEmpty">', html)
        # 详情页注入切换脚本
        self.assertIn("discVerBtn", DISC_JS_SRC)
        self.assertNotIn("disc-ver", FILTER_JS_SRC)

    def test_payload_escapes_script_close_tag(self):
        html = build_detail(make_script(discussions=make_ledger()), None,
                            make_posts(body="</script><b>注入</b>"))
        payload = html.split('id="discData">')[1].split("</script>")[0]
        self.assertNotIn("<", payload)
        self.assertNotIn(">", payload)
        self.assertIn("\\u003c", payload)
        # 服务端渲染的正文保持文本转义
        self.assertIn("&lt;/script&gt;", html)

    def test_missing_posts_falls_back_to_issue_panel(self):
        html = build_detail(make_script(discussions=make_ledger()),
                            make_stats(), None)
        self.assertNotIn("discData", html)
        self.assertNotIn("discVerBtn", html)
        self.assertIn("已修复，更新到 v1.0.1 即可。", html)
        self.assertIn('href="https://github.com/t/r/issues/4"', html)

    def test_index_card_has_no_version_switcher(self):
        html = build_index({"scripts": [make_script(discussions=make_ledger())]},
                           {"abc123": make_stats()})
        self.assertNotIn("discData", html)
        self.assertNotIn("discVerBtn", html)

    def test_build_site_writes_version_panel(self):
        build_site({"scripts": [make_script(discussions=make_ledger())]},
                   {"abc123": make_stats()}, {"abc123": make_posts()})
        page_html = (Path(CONFIG["dist_dir"]) / "scripts" / "abc123.html") \
            .read_text(encoding="utf-8")
        self.assertIn('id="discVerBtn"', page_html)
        self.assertIn("discData", page_html)

    def test_switcher_css_and_js_defined(self):
        for cls in (".disc-ver-btn", ".disc-ver-menu", ".disc-ver-item",
                    ".disc-badges", ".cmt-who", ".cmt-replies", ".answer-tag"):
            self.assertIn(cls, COMPONENT_CSS)
        for token in ("discData", "discVerBtn", "setOpen", "aria-selected",
                      "discEmpty"):
            self.assertIn(token, DISC_JS_SRC)
        # 移动端触控目标
        self.assertIn(".disc-ver-btn { min-height: 44px; }", COMPONENT_CSS)

    def test_unsafe_post_url_drops_link(self):
        posts = make_posts()
        posts[0]["url"] = "javascript:alert(1)"
        html = build_detail(make_script(discussions=make_ledger()), None, posts)
        self.assertNotIn('id="discLink"', html)
        self.assertNotIn("javascript:", html)


class TestIndexLazyLoad(ConfigIsolation):
    """首屏 SSR 前 10 张卡片，其余由 scripts.json 滚动追加。"""

    def _registry(self, n):
        return {"scripts": [make_script(id=f"s{i:02d}", name=f"脚本{i}")
                            for i in range(n)]}

    def test_overflow_list_renders_loader_and_defers_rest(self):
        html = build_index(self._registry(12))
        self.assertIn('id="scriptList"', html)
        self.assertIn('data-batch="10"', html)
        self.assertIn('data-total="12"', html)
        self.assertIn('id="loadMore"', html)
        self.assertIn('id="listSentinel"', html)
        self.assertIn("scripts.json", LIST_JS_SRC)
        self.assertIn("fetch('scripts.json')", html)   # LIST_JS 已注入
        # 只有首屏 10 张卡服务端渲染，其余走 JSON
        self.assertEqual(html.count('class="script-card"'), 10)
        body = html[html.find("<body>"):html.find("</body>")]
        self.assertEqual(body.count("<div"), body.count("</div>"),
                         "scriptList/sentinel 必须配平")

    def test_small_list_has_no_loader(self):
        html = build_index(self._registry(3))
        self.assertIn('data-total="3"', html)
        self.assertNotIn('id="loadMore"', html)
        self.assertNotIn("fetch('scripts.json')", html)
        self.assertEqual(html.count('class="script-card"'), 3)

    def test_scripts_json_contains_all_cards(self):
        build_site(self._registry(12))
        raw = (Path(CONFIG["dist_dir"]) / "scripts.json").read_text(encoding="utf-8")
        items = json.loads(raw)
        self.assertEqual(len(items), 12)
        self.assertEqual(items[0]["type"], "self")
        self.assertIn('data-type="self"', items[0]["html"])
        self.assertIn('href="scripts/s00.html"', items[0]["html"])

    def test_empty_registry_has_no_loader(self):
        html = build_index({"scripts": []})
        self.assertIn('data-total="0"', html)
        self.assertNotIn('id="loadMore"', html)


class TestCardDiscussionLink(ConfigIsolation):
    """卡片「讨论」按钮优先指向最新版本帖。"""

    def test_prefers_latest_version_post(self):
        html = build_index(
            {"scripts": [make_script(discussions=make_ledger())]},
            {"abc123": make_stats()},
        )
        # 账本最新一条是 v1.0.1 → discussions/9
        self.assertIn('href="https://github.com/t/r/discussions/9"', html)
        self.assertNotIn('href="https://github.com/t/r/issues/4"', html)

    def test_falls_back_to_script_issue(self):
        html = build_index({"scripts": [make_script()]}, {"abc123": make_stats()})
        self.assertIn('href="https://github.com/t/r/issues/4"', html)

    def test_falls_back_to_issue_list_without_issue(self):
        html = build_index({"scripts": [make_script(issue=None, discussions=[])]}, {})
        self.assertIn("q=is%3Aissue+label%3Ascript", html)


class TestCommandArchivePages(ConfigIsolation):
    """命令归档静态分页：每页 5 条，新→旧。"""

    def _commands_dir(self):
        return Path(CONFIG["dist_dir"]) / "commands"

    def _write_archive(self, count):
        entries = [
            {"command_id": f"IC_{i}", "author": "ACG-Q",
             "command": f"/cmd {i}", "created_at": "2026-10-02T03:00:00Z",
             "results": [{"id": f"IR_{i}", "author": "github-actions[bot]",
                          "body": f"**执行结果：** ok {i}",
                          "created_at": "2026-10-02T03:01:00Z"}],
             "archived_at": "2026-10-03T00:00:00Z"}
            for i in range(1, count + 1)
        ]
        path = Path(CONFIG["archive_file"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema": 1, "commands": entries},
                                   ensure_ascii=False), encoding="utf-8")

    def test_pages_split_five_per_page_newest_first(self):
        self._write_archive(12)
        build_site({"scripts": []}, {})
        cmds = self._commands_dir()
        self.assertTrue((cmds / "page-1.html").exists())
        self.assertTrue((cmds / "page-3.html").exists())
        self.assertFalse((cmds / "page-4.html").exists())
        p1 = (cmds / "page-1.html").read_text(encoding="utf-8")
        self.assertIn("/cmd 12", p1)          # 新→旧，第 1 页是最新 5 条
        self.assertIn("/cmd 8", p1)
        self.assertNotIn("/cmd 7<", p1)       # 第 7 条在第 2 页
        self.assertIn('href="page-2.html"', p1)
        self.assertNotIn('href="page-0.html"', p1)
        p3 = (cmds / "page-3.html").read_text(encoding="utf-8")
        self.assertIn("/cmd 1", p3)
        self.assertIn("第 3 / 3 页", p3)
        self.assertNotIn('href="page-4.html"', p3)

    def test_nav_and_footer_link_to_archive(self):
        index = build_index({"scripts": []})
        self.assertIn('href="commands/page-1.html"', index)
        detail = build_detail(make_script())
        self.assertIn('href="../commands/page-1.html"', detail)
        self.assertIn('href="../commands/page-1.html"', detail)

    def test_empty_archive_shows_empty_state_with_panel_link(self):
        build_site({"scripts": []}, {})
        p1 = (self._commands_dir() / "page-1.html").read_text(encoding="utf-8")
        self.assertIn("还没有归档的命令记录", p1)
        self.assertIn("issues/1", p1)
        self.assertTrue((self._commands_dir() / "index.html").exists())

    def test_shrinking_archive_removes_stale_pages(self):
        self._write_archive(12)
        build_site({"scripts": []}, {})
        self._write_archive(3)
        build_site({"scripts": []}, {})
        cmds = self._commands_dir()
        self.assertTrue((cmds / "page-1.html").exists())
        self.assertFalse((cmds / "page-2.html").exists())

    def test_command_body_is_escaped(self):
        path = Path(CONFIG["archive_file"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema": 1, "commands": [{
            "command_id": "IC_x", "author": "<b>u</b>",
            "command": "</script><i>x</i>", "created_at": "",
            "results": [], "archived_at": "2026-10-03T00:00:00Z",
        }]}, ensure_ascii=False), encoding="utf-8")
        build_site({"scripts": []}, {})
        p1 = (self._commands_dir() / "page-1.html").read_text(encoding="utf-8")
        self.assertNotIn("</script><i>", p1)
        self.assertIn("&lt;/script&gt;", p1)
        self.assertIn("&lt;b&gt;u&lt;/b&gt;", p1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
