import unittest

from userscript_manager.sources import get_adapter, get_all_adapters
from userscript_manager.sources.base import BROWSER_HEADERS, http_get
from userscript_manager.sources.direct_url import DirectUrlAdapter
from userscript_manager.sources.greasyfork import GreasyForkAdapter
from userscript_manager.sources.github_gist import GitHubGistAdapter, pick_gist_file
from userscript_manager.utils import extract_meta_from_code


class TestAdapterMatching(unittest.TestCase):
    """域名匹配：精确/子域命中，路径伪装与端口不骗过匹配器。"""
    def test_domain_in_path_is_not_matched(self):
        self.assertIsNone(get_adapter("https://evil.example/greasyfork.org/scripts/1"))

    def test_exact_domain_matched(self):
        adapter = get_adapter("https://greasyfork.org/zh-CN/scripts/12345")
        self.assertIsInstance(adapter, GreasyForkAdapter)

    def test_subdomain_matched(self):
        adapter = get_adapter("https://www.greasyfork.org/zh-CN/scripts/12345")
        self.assertIsInstance(adapter, GreasyForkAdapter)

    def test_scheme_and_port_do_not_fool_matcher(self):
        adapter = get_adapter("https://greasyfork.org:8443/scripts/1")
        self.assertIsInstance(adapter, GreasyForkAdapter)
        self.assertIsNone(get_adapter("http://user:pass@evil.example/#greasyfork.org"))


class TestGithubRawDirectMatching(unittest.TestCase):
    """github.com 的 /raw/ 直链归属 DirectUrl；HTML 页（blob/仓库首页）不归属。"""
    RAW_URL = (
        "https://github.com/XIU2/UserScript/raw/refs/heads/master/"
        "GithubEnhanced-High-Speed-Download.user.js"
    )

    def test_github_raw_path_matched_as_direct(self):
        adapter = get_adapter(self.RAW_URL)
        self.assertIsInstance(adapter, DirectUrlAdapter)

    def test_github_blob_page_not_matched(self):
        self.assertIsNone(
            get_adapter("https://github.com/XIU2/UserScript/blob/master/a.user.js")
        )

    def test_github_repo_home_not_matched(self):
        self.assertIsNone(get_adapter("https://github.com/XIU2/UserScript"))

    def test_existing_raw_domains_still_matched(self):
        adapter = get_adapter("https://raw.githubusercontent.com/u/r/main/x.user.js")
        self.assertIsInstance(adapter, DirectUrlAdapter)

    def test_other_hosts_with_raw_path_not_matched(self):
        self.assertFalse(DirectUrlAdapter().matches("https://evil.example/raw/x.js"))


class TestBrowserHeaders(unittest.TestCase):
    """默认 python-requests UA 会被 GreasyFork 等站点 403；所有抓取必须带浏览器头。"""
    def _capture_get(self):
        import userscript_manager.sources.base as base_mod

        captured = {}

        def fake_get(url, timeout=None, headers=None, **kwargs):
            captured["url"] = url
            captured["headers"] = headers
            raise RuntimeError("stop")

        original = base_mod.requests.get
        base_mod.requests.get = fake_get
        return base_mod, captured, original

    def test_http_get_sends_browser_user_agent(self):
        base_mod, captured, original = self._capture_get()
        try:
            with self.assertRaises(RuntimeError):
                http_get("https://example.com/a.user.js")
        finally:
            base_mod.requests.get = original
        self.assertTrue(captured["headers"]["User-Agent"].startswith("Mozilla/"))
        self.assertIn("text/html", captured["headers"]["Accept"])

    def test_greasyfork_fetch_goes_through_browser_headers(self):
        import userscript_manager.sources.base as base_mod

        captured = {}

        def fake_get(url, timeout=None, headers=None, **kwargs):
            captured["headers"] = headers
            raise RuntimeError("stop")

        original = base_mod.requests.get
        base_mod.requests.get = fake_get
        try:
            with self.assertRaises(RuntimeError):
                GreasyForkAdapter().fetch("https://greasyfork.org/zh-CN/scripts/1")
        finally:
            base_mod.requests.get = original
        self.assertEqual(captured["headers"], BROWSER_HEADERS)


class TestSharedMetaExtraction(unittest.TestCase):
    """共享元数据解析器：适配器不得复制实现。"""
    CODE = (
        "// ==UserScript==\n"
        "// @name Shared\n"
        "// @version 3.1.4\n"
        "// @match *://*/*\n"
        "// @grant none\n"
        "// ==/UserScript==\n"
        "fn();"
    )

    def test_base_class_provides_shared_extractor(self):
        adapter = GreasyForkAdapter()
        self.assertEqual(adapter._extract_meta(self.CODE), extract_meta_from_code(self.CODE))

    def test_no_adapter_defines_its_own_copy(self):
        for adapter in get_all_adapters():
            self.assertNotIn(
                "_extract_meta",
                type(adapter).__dict__,
                f"{adapter.name} 不应复制粘贴元数据解析逻辑",
            )

    def test_gist_adapter_uses_shared_extractor(self):
        adapter = GitHubGistAdapter()
        self.assertEqual(adapter._extract_meta(self.CODE), extract_meta_from_code(self.CODE))


class TestGistFileSelection(unittest.TestCase):
    """Gist 文件选择：优先 .user.js，回退 .js，再回退首个。"""
    def test_prefers_user_js(self):
        files = {
            "notes.txt": {"content": "x", "raw_url": "r1"},
            "main.user.js": {"content": "c", "raw_url": "r2"},
            "util.js": {"content": "y", "raw_url": "r3"},
        }
        name, info = pick_gist_file(files)
        self.assertEqual(name, "main.user.js")
        self.assertEqual(info["raw_url"], "r2")

    def test_falls_back_to_js_then_first(self):
        name, _ = pick_gist_file({"a.txt": {"raw_url": "r1"}, "b.js": {"raw_url": "r2"}})
        self.assertEqual(name, "b.js")
        name, _ = pick_gist_file({"only.txt": {"raw_url": "r1"}})
        self.assertEqual(name, "only.txt")


class TestGistFetchResolvesViaApi(unittest.TestCase):
    """Gist 页面 URL 解析到 API 并选中 .user.js。"""
    def test_page_url_uses_api_and_picks_user_js(self):
        import userscript_manager.sources.base as base_mod

        calls = []
        captured_headers = []

        class FakeResp:
            def __init__(self, text="", json_data=None):
                self._text = text
                self._json = json_data

            def raise_for_status(self):
                pass

            @property
            def text(self):
                return self._text

            def json(self):
                return self._json

        def fake_get(url, timeout=None, **kwargs):
            calls.append(url)
            captured_headers.append(kwargs.get("headers"))
            if url.startswith("https://api.github.com/gists/"):
                return FakeResp(json_data={
                    "files": {
                        "a.txt": {"content": "junk", "raw_url": "r1"},
                        "s.user.js": {"content": "USERJS", "raw_url": "r2"},
                    }
                })
            return FakeResp(text="FIRST_FILE_RAW")

        original_get = base_mod.requests.get
        base_mod.requests.get = fake_get
        try:
            src = GitHubGistAdapter().fetch("https://gist.github.com/user/deadbeef1234")
        finally:
            base_mod.requests.get = original_get

        self.assertIn("https://api.github.com/gists/deadbeef1234", calls)
        self.assertEqual(src.code, "USERJS")


class TestGreasyForkFetchFallbacks(unittest.TestCase):
    """抓取链：update 子域 ID 直取优先；失败回退内嵌 → 安装直链 → /code 页；全失败聚合报错。"""
    PAGE = "https://greasyfork.org/zh-CN/scripts/12345-demo"
    UPDATE = "https://update.greasyfork.org/scripts/12345.user.js"
    INSTALL = "https://update.greasyfork.org/scripts/12345/Demo.user.js"
    CODE = "// ==UserScript==\n// @name GF\n// @version 2.0.0\n// ==/UserScript==\nfn();"

    def _fetch_with(self, responses):
        """responses: url -> 正文字符串（200）或状态码整数（模拟 HTTP 错误）。"""
        import userscript_manager.sources.base as base_mod
        import requests as requests_lib

        calls = []

        class FakeResp:
            def __init__(self, text="", status=200):
                self.text = text
                self.status_code = status

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests_lib.HTTPError(f"{self.status_code} error", response=self)

        def fake_get(url, timeout=None, headers=None, **kwargs):
            calls.append(url)
            if url not in responses:
                raise AssertionError(f"意外请求: {url}")
            value = responses[url]
            if isinstance(value, int):
                return FakeResp(status=value)
            return FakeResp(text=value)

        original = base_mod.requests.get
        base_mod.requests.get = fake_get
        try:
            src = GreasyForkAdapter().fetch(self.PAGE)
        finally:
            base_mod.requests.get = original
        return src, calls

    def test_update_direct_by_id_is_primary(self):
        src, calls = self._fetch_with({self.UPDATE: self.CODE})
        self.assertEqual(src.code, self.CODE)
        self.assertEqual(src.source_type, "greasyfork")
        self.assertEqual(calls, [self.UPDATE])

    def test_install_link_fallback_when_update_blocked(self):
        page = f'<html><a href="{self.INSTALL}">安装此脚本</a></html>'
        src, calls = self._fetch_with({
            self.UPDATE: 403, self.PAGE: page, self.INSTALL: self.CODE,
        })
        self.assertEqual(src.code, self.CODE)
        self.assertEqual(calls, [self.UPDATE, self.PAGE, self.INSTALL])

    def test_code_page_fallback_parses_prettyprint(self):
        code_page = f'<html><pre class="prettyprint linenums">{self.CODE}</pre></html>'
        src, calls = self._fetch_with({
            self.UPDATE: 403,
            self.PAGE: "<html>no embedded code</html>",
            self.PAGE + "/code": code_page,
        })
        self.assertEqual(src.code, self.CODE)
        self.assertEqual(calls, [self.UPDATE, self.PAGE, self.PAGE + "/code"])

    def test_all_entries_fail_reports_each_status(self):
        with self.assertRaises(ValueError) as ctx:
            self._fetch_with({
                self.UPDATE: 403,
                self.PAGE: 403,
            })
        msg = str(ctx.exception)
        self.assertIn("update直链 403", msg)
        self.assertIn("主页 403", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
