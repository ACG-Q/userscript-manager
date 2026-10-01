import os
import sys
import io
import tempfile
import unittest
from pathlib import Path

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from userscript_manager.config import CONFIG
from userscript_manager.registry import load_registry, save_registry
from userscript_manager.utils import ensure_dirs

TMP = Path(tempfile.mkdtemp(prefix="usm_sync_"))
CONFIG["registry_file"] = TMP / "registry.json"
CONFIG["self_scripts_dir"] = TMP / "scripts" / "self"
CONFIG["synced_scripts_dir"] = TMP / "scripts" / "synced"
CONFIG["dist_dir"] = TMP / "dist"
CONFIG["github_pages"]["base_url"] = ""
CONFIG["github_repo"] = "testuser/testrepo"

from userscript_manager.commands import get_command
import userscript_manager.commands.sync
import userscript_manager.commands.add
import userscript_manager.commands.update


class TestSyncPersistence(unittest.TestCase):
    def setUp(self):
        ensure_dirs()
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
            "custom_match": None,
            "documentation": "",
        }
        self.registry["scripts"].append(script_meta)
        save_registry(self.registry)

        # Patch the adapter fetch to return a newer version
        from userscript_manager.sources import direct_url
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


if __name__ == "__main__":
    unittest.main(verbosity=2)