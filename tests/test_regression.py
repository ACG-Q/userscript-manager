import io
import json
import os
import sys
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

os.environ.setdefault("AUTHOR_NAME", "Test Author")
os.environ.setdefault("AUTHOR_NAMESPACE", "https://test.dev")
os.environ.setdefault("GITHUB_REPOSITORY", "testuser/testrepo")
os.environ.setdefault("GITHUB_REF_NAME", "main")

from tests._helpers import ConfigIsolation, FRESH_REGISTRY
from userscript_manager.config import CONFIG
from userscript_manager.registry import load_registry
from userscript_manager.issue_parser import parse_comment
import userscript_manager.commands.list
import userscript_manager.commands.add
import userscript_manager.commands.update
import userscript_manager.commands.sync
import userscript_manager.commands.info
import userscript_manager.commands.toggle
import userscript_manager.commands.export
import userscript_manager.commands.remove
from userscript_manager.commands import get_command

SCRIPT = """// ==UserScript==
// @name 测试脚本
// @version 1.0.0
// @match *://*/*
// @grant none
// ==/UserScript==
(function() { console.log('Hello'); })();
"""


class TestEndToEndCommands(ConfigIsolation):
    """八命令端到端生命周期：每个命令都必须有真实断言（曾经是 print-only）。"""

    TMP_PREFIX = "usm_e2e_"

    def _config_setup(self):
        CONFIG["registry_file"].write_text(FRESH_REGISTRY, encoding="utf-8")
        self.registry = load_registry()

    def _run(self, body: str) -> str:
        parsed = parse_comment(body)
        cmd = get_command(parsed.command)
        self.assertIsNotNone(cmd, f"命令 {parsed.command} 未注册")
        return cmd(
            self.registry, parsed.args, parsed.code,
            parsed.markdown, parsed.has_code_block,
        )

    def _add(self) -> str:
        result = self._run("/add\n# 文档标题\n\n```javascript\n" + SCRIPT + "\n```")
        self.assertTrue(result.startswith("✅"), result)
        return result.splitlines()[1].split(": ")[1].strip()

    def test_add_then_list_shows_script(self):
        self._add()
        out = self._run("/list")
        self.assertIn("测试脚本", out)
        self.assertEqual(len(self.registry["scripts"]), 1)

    def test_info_contains_install_link_and_doc(self):
        sid = self._add()
        info = self._run(f"/info {sid}")
        self.assertIn("安装链接", info)
        self.assertIn("文档: 有", info)

    def test_up_bumps_version_and_rewrites_dist(self):
        sid = self._add()
        new_code = SCRIPT.replace("Hello", "Hello v2")
        result = self._run(f"/up {sid}\n```javascript\n{new_code}\n```")
        self.assertIn("更新成功", result)
        self.assertEqual(self.registry["scripts"][0]["version"], "1.0.1")
        dist = self._tmp / "dist" / f"{sid}.user.js"
        self.assertTrue(dist.exists())
        self.assertIn("// @downloadURL", dist.read_text(encoding="utf-8"))

    def test_disable_enable_roundtrip(self):
        sid = self._add()
        self.assertIn("已禁用", self._run(f"/disable {sid}"))
        self.assertFalse(self.registry["scripts"][0]["enabled"])
        self.assertIn("已启用", self._run(f"/enable {sid}"))
        self.assertTrue(self.registry["scripts"][0]["enabled"])

    def test_export_markdown_lists_script(self):
        self._add()
        out = self._run("/export md")
        self.assertIn("# 油猴脚本安装列表", out)
        self.assertIn("测试脚本", out)

    def test_export_json_is_parseable(self):
        self._add()
        data = json.loads(self._run("/export json"))
        self.assertEqual(len(data["scripts"]), 1)
        self.assertEqual(data["scripts"][0]["name"], "测试脚本")

    def test_remove_then_list_empty(self):
        sid = self._add()
        self.assertIn("已删除", self._run(f"/rm {sid}"))
        self.assertEqual(len(self.registry["scripts"]), 1)
        self.assertTrue(self.registry["scripts"][0]["deleted"])
        self.assertFalse((self._tmp / "dist" / f"{sid}.user.js").exists())
        self.assertIn("没有脚本", self._run("/list"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
