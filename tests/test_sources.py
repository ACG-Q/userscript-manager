import unittest

from userscript_manager.sources import get_adapter, get_all_adapters
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
        import userscript_manager.sources.github_gist as mod

        calls = []

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

        def fake_get(url, timeout=None):
            calls.append(url)
            if url.startswith("https://api.github.com/gists/"):
                return FakeResp(json_data={
                    "files": {
                        "a.txt": {"content": "junk", "raw_url": "r1"},
                        "s.user.js": {"content": "USERJS", "raw_url": "r2"},
                    }
                })
            return FakeResp(text="FIRST_FILE_RAW")

        original_get = mod.requests.get
        mod.requests.get = fake_get
        try:
            src = GitHubGistAdapter().fetch("https://gist.github.com/user/deadbeef1234")
        finally:
            mod.requests.get = original_get

        self.assertIn("https://api.github.com/gists/deadbeef1234", calls)
        self.assertEqual(src.code, "USERJS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
