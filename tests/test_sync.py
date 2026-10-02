import sys
import io
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from tests._helpers import ConfigIsolation, FRESH_REGISTRY
from userscript_manager.config import CONFIG
from userscript_manager.registry import load_registry, save_registry

from userscript_manager.commands import get_command
import userscript_manager.commands.sync
import userscript_manager.commands.add
import userscript_manager.commands.update


class TestSyncPersistence(ConfigIsolation):
    """同步落盘：版本变更写回、拒绝非油猴内容。"""
    TMP_PREFIX = "usm_sync_"

    def _config_setup(self):
        # 每个用例从空注册表开始，避免 tests[0] 位置假设被同文件兄弟用例破坏
        CONFIG["registry_file"].write_text(FRESH_REGISTRY, encoding="utf-8")
        self.registry = load_registry()

    def test_sync_script_persists_changes(self):
        # Simulate a synced script whose source code changed upstream
        script_meta = {
            "id": "sync123",
            "type": "synced",
            "name": "Sync Script",
            "version": "1.0.0",
            "description": "",
            "author": "",
            "namespace": "",
            "match": ["*://*/*"],
            "grant": ["none"],
            "enabled": True,
            "source_url": "https://raw.githubusercontent.com/user/repo/main/script.user.js",
            "source_type": "direct",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "last_synced_at": "2026-01-01T00:00:00Z",
            "sync_enabled": True,
            "documentation": "",
        }
        self.registry["scripts"].append(script_meta)
        save_registry(self.registry)

        # Patch requests.get to return a newer version
        import requests

        original_code = """// ==UserScript==
// @name Sync Script
// @version 1.1.0
// @match *://*/*
// @grant none
// ==/UserScript==
new_body();
"""

        class FakeResp:
            def raise_for_status(self):
                pass
            @property
            def text(self):
                return original_code

        original_get = requests.get

        def fake_get(url, timeout=None):
            return FakeResp()

        requests.get = fake_get
        try:
            sync = get_command("sync")
            result = sync(self.registry, "sync123", "", "", False)
        finally:
            requests.get = original_get

        self.assertIn("已更新到 v1.1.0", result)

        # KEY ASSERTION: reload from disk, version must be persisted
        reloaded = load_registry()
        s = reloaded["scripts"][0]
        self.assertEqual(s["version"], "1.1.0", "sync 后版本应持久化到 registry.json")
        self.assertIsNotNone(s["last_synced_at"])

    def test_sync_rejects_non_userscript_content(self):
        script_meta = {
            "id": "syncbad",
            "type": "synced",
            "name": "Bad",
            "version": "1.0.0",
            "description": "",
            "author": "",
            "namespace": "",
            "match": ["*://*/*"],
            "grant": ["none"],
            "enabled": True,
            "source_url": "https://example.com/x.js",
            "source_type": "direct",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "last_synced_at": None,
            "sync_enabled": True,
            "documentation": "",
        }
        self.registry["scripts"].append(script_meta)
        save_registry(self.registry)

        import userscript_manager.commands.sync as sync_mod
        from userscript_manager.sources.base import ScriptSource

        class FakeAdapter:
            name = "Fake"

            def fetch(self, url):
                return ScriptSource(
                    code="<html>error page</html>",
                    meta={},
                    source_url=url,
                    source_type="direct",
                )

        original = sync_mod.get_adapter
        sync_mod.get_adapter = lambda url: FakeAdapter()
        try:
            result = get_command("sync")(self.registry, "syncbad", "", "", False)
        finally:
            sync_mod.get_adapter = original

        self.assertIn("不是有效的油猴脚本", result)
        reloaded = load_registry()["scripts"][0]
        self.assertIsNone(reloaded["last_synced_at"])


if __name__ == "__main__":
    unittest.main(verbosity=2)