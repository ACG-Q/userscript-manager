"""自写脚本入库前自动格式化；同步脚本保持上游原文不重排。"""
import io
import sys
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from tests._helpers import ConfigIsolation, FRESH_REGISTRY
from userscript_manager.config import CONFIG
from userscript_manager.registry import load_registry
from userscript_manager.utils import format_js_code

from userscript_manager.commands import get_command
import userscript_manager.commands.add
import userscript_manager.commands.update

UGLY = (
    "// ==UserScript==\n// @name 丑陋脚本\n// @version 1.0.0\n"
    "// @match *://*/*\n// @grant none\n// ==/UserScript==\n"
    "(function(){if(true){console.log('x');}})();"
)

SCRIPT = """// ==UserScript==
// @name 测试脚本
// @version 1.0.0
// @match *://*/*
// @grant none
// ==/UserScript==
(function() { console.log('Hello'); })();
"""


class TestFormatting(ConfigIsolation):
    TMP_PREFIX = "usm_fmt_"

    def _config_setup(self):
        CONFIG["registry_file"].write_text(FRESH_REGISTRY, encoding="utf-8")
        self.registry = load_registry()

    def _source_path(self, sid):
        return CONFIG["self_scripts_dir"] / sid / "index.js"

    def test_format_js_code_indents_body(self):
        out = format_js_code("function a(){if(true){b();}}")
        self.assertIn("\n", out)
        self.assertIn("b();", out)
        self.assertNotEqual(out, "function a(){if(true){b();}}")

    def test_add_stores_formatted_source_and_keeps_header(self):
        cmd = get_command("add")
        cmd(self.registry, "", UGLY, "```javascript\n" + UGLY + "\n```", True)
        sid = self.registry["scripts"][0]["id"]
        stored = self._source_path(sid).read_text(encoding="utf-8")
        self.assertEqual(stored, format_js_code(UGLY))
        self.assertIn("// @name 丑陋脚本", stored)

    def test_up_stores_formatted_source(self):
        add = get_command("add")
        add(self.registry, "", SCRIPT, "# 文档\n\n```javascript\n" + SCRIPT + "\n```", True)
        sid = self.registry["scripts"][0]["id"]
        up = get_command("up")
        up(self.registry, sid, UGLY, "```javascript\n" + UGLY + "\n```", True)
        stored = self._source_path(sid).read_text(encoding="utf-8")
        self.assertEqual(stored, format_js_code(UGLY))

    def test_synced_source_is_kept_verbatim(self):
        import userscript_manager.commands.add as add_mod
        from userscript_manager.sources.base import ScriptSource

        class FakeAdapter:
            name = "Fake"

            def fetch(self, url):
                return ScriptSource(
                    code=UGLY, meta={"name": "Ugly"}, source_url=url,
                    source_type="direct",
                )

        original = add_mod.get_adapter
        add_mod.get_adapter = lambda url: FakeAdapter()
        try:
            result = get_command("add")(
                self.registry, "https://example.com/x.js", "", "", False
            )
        finally:
            add_mod.get_adapter = original
        self.assertIn("添加成功", result)
        sid = self.registry["scripts"][0]["id"]
        stored = (
            CONFIG["synced_scripts_dir"] / sid / "script.user.js"
        ).read_text(encoding="utf-8")
        self.assertEqual(stored, UGLY)


if __name__ == "__main__":
    unittest.main(verbosity=2)
