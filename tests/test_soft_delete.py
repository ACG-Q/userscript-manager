"""软删除（/rm 标记 deleted 而非移除条目）与命令侧过滤的端到端测试。"""
import io
import sys
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from tests._helpers import FRESH_REGISTRY, ConfigIsolation
from userscript_manager.commands import get_command
from userscript_manager.config import CONFIG
from userscript_manager.issue_parser import parse_comment
from userscript_manager.registry import load_registry, save_registry
from userscript_manager.utils import now_iso, write_dist_file, write_source_file

SCRIPT = """// ==UserScript==
// @name 测试脚本
// @version 1.0.0
// @match *://*/*
// @grant none
// ==/UserScript==
(function() { console.log('Hello'); })();
"""


class _CommandBase(ConfigIsolation):
    """命令测试基座：空注册表 + 命令分发 + 种子数据/适配器打桩。"""

    TMP_PREFIX = "usm_sd_"

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
        result = self._run("/add\n# 文档\n\n```javascript\n" + SCRIPT + "\n```")
        self.assertTrue(result.startswith("✅"), result)
        return result.splitlines()[1].split(": ")[1].strip()

    def _seed_synced(
        self, script_id="sync123", url="https://example.com/x.user.js", **overrides
    ):
        """写入一条 synced 条目（含源码与 dist 文件）并落盘，返回该条目。"""
        meta = {
            "id": script_id,
            "type": "synced",
            "name": "同步脚本",
            "version": "1.0.0",
            "description": "",
            "author": "",
            "namespace": "",
            "match": ["*://*/*"],
            "grant": ["none"],
            "enabled": True,
            "source_url": url,
            "source_type": "direct",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "last_synced_at": now_iso(),
            "sync_enabled": True,
            "documentation": "",
            "changelog": [],
            "discussions": [],
            "deleted": False,
        }
        meta.update(overrides)
        self.registry["scripts"].append(meta)
        write_source_file(meta, SCRIPT)
        write_dist_file(script_id, SCRIPT)
        save_registry(self.registry)
        return meta


class TestSoftDelete(_CommandBase):
    """/rm 软删除语义：条目保留、文件清理、列表隐藏、同步拒绝。"""

    def test_rm_self_marks_deleted_and_keeps_entry(self):
        sid = self._add()
        out = self._run(f"/rm {sid}")
        self.assertIn("已删除脚本", out)
        self.assertIn("软删除", out)
        self.assertEqual(len(self.registry["scripts"]), 1)
        self.assertTrue(self.registry["scripts"][0]["deleted"])
        again = self._run(f"/rm {sid}")
        self.assertIn("已处于删除状态", again)

    def test_rm_cleans_source_and_dist_files(self):
        sid = self._add()
        self.assertTrue((self._tmp / "dist" / f"{sid}.user.js").exists())
        self._run(f"/rm {sid}")
        self.assertFalse((self._tmp / "dist" / f"{sid}.user.js").exists())
        self.assertFalse((self._tmp / "scripts" / "self" / sid).exists())

    def test_rm_by_url_marks_synced_deleted(self):
        self._seed_synced()
        out = self._run("/rm https://example.com/x.user.js")
        self.assertIn("已删除同步脚本", out)
        self.assertIn("复活", out)
        self.assertTrue(self.registry["scripts"][0]["deleted"])
        self.assertFalse((self._tmp / "dist" / "sync123.user.js").exists())

    def test_list_hides_deleted_entries(self):
        sid = self._add()
        self.assertIn("测试脚本", self._run("/list"))
        self._run(f"/rm {sid}")
        self.assertIn("没有脚本", self._run("/list"))

    def test_sync_refuses_deleted_script(self):
        self._seed_synced()
        self._run("/rm sync123")
        out = self._run("/sync sync123")
        self.assertIn("已删除", out)
        self.assertIn("复活", out)

    def test_sync_all_skips_deleted(self):
        self._seed_synced()
        self._run("/rm sync123")
        out = self._run("/sync-all")
        self.assertIn("没有启用自动同步", out)

    def test_up_refuses_deleted_script(self):
        sid = self._add()
        self._run(f"/rm {sid}")
        out = self._run(
            f"/up {sid}\n# 新文档\n\n```javascript\n"
            + SCRIPT.replace("1.0.0", "1.0.1")
            + "\n```"
        )
        self.assertIn("已删除", out)
        self.assertFalse((self._tmp / "dist" / f"{sid}.user.js").exists())

    def test_export_hides_deleted_entries(self):
        self._seed_synced()
        sid = self._add()
        self._run(f"/rm {sid}")
        out = self._run("/export md")
        self.assertNotIn("测试脚本", out)
        self.assertIn("同步脚本", out)


class TestReviveByAdd(_CommandBase):
    """/add <url> 复活契约：sync/update/rm 三处都承诺「重新 /add 复活」。"""

    def _fake_adapter(self, code=SCRIPT):
        """给 add 模块打桩：绕过网络，返回固定脚本源。"""
        import userscript_manager.commands.add as add_mod
        from userscript_manager.sources.base import ScriptSource

        class FakeAdapter:
            name = "直接链接"

            def fetch(self, url):
                return ScriptSource(code=code, meta={"name": "测试脚本",
                                                     "version": "1.0.0"},
                                    source_url=url, source_type="direct")

        original = add_mod.get_adapter
        add_mod.get_adapter = lambda url: FakeAdapter()
        self.addCleanup(lambda: setattr(add_mod, "get_adapter", original))

    def test_add_url_revives_soft_deleted_synced_script(self):
        self._seed_synced()
        self._run("/rm https://example.com/x.user.js")
        self.assertFalse((self._tmp / "dist" / "sync123.user.js").exists())

        self._fake_adapter()
        out = self._run("/add https://example.com/x.user.js")
        self.assertIn("复活成功", out)
        self.assertIn("sync123", out)

        entry = self.registry["scripts"][0]
        self.assertFalse(entry["deleted"])
        self.assertEqual(entry["id"], "sync123")           # 复用原 ID
        self.assertEqual(len(self.registry["scripts"]), 1)  # 不追加重复条目
        self.assertTrue((self._tmp / "dist" / "sync123.user.js").exists())
        # 复活已落盘：重新读取仍是启用状态
        self.assertFalse(load_registry()["scripts"][0]["deleted"])

    def test_add_url_still_rejects_living_duplicate(self):
        self._seed_synced()
        self._fake_adapter()
        out = self._run("/add https://example.com/x.user.js")
        self.assertIn("已存在", out)
        self.assertNotIn("复活", out)
        self.assertEqual(len(self.registry["scripts"]), 1)

    def test_revive_then_sync_works_again(self):
        """复活后 /sync 不再被「已删除」拦截（sync.py:20 承诺的路径）。"""
        import userscript_manager.commands.sync as sync_mod
        from userscript_manager.sources.base import ScriptSource

        self._seed_synced()
        self._run("/rm https://example.com/x.user.js")
        self._fake_adapter()
        self._run("/add https://example.com/x.user.js")

        class SyncAdapter:
            name = "直接链接"

            def fetch(self, url):
                return ScriptSource(code=SCRIPT, source_url=url,
                                    meta={"name": "测试脚本", "version": "1.0.1"},
                                    source_type="direct")

        original = sync_mod.get_adapter
        sync_mod.get_adapter = lambda url: SyncAdapter()
        self.addCleanup(lambda: setattr(sync_mod, "get_adapter", original))

        out = self._run("/sync sync123")
        self.assertNotIn("已删除", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
