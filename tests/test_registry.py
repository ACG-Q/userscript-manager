import json
import os
import sys
import io
import tempfile
import unittest
from pathlib import Path

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from userscript_manager.config import CONFIG
from userscript_manager.registry import load_registry, save_registry, RegistryError


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self._saved = CONFIG["registry_file"]
        self._tmp = Path(tempfile.mkdtemp(prefix="usm_reg_"))
        CONFIG["registry_file"] = self._tmp / "registry.json"

    def tearDown(self):
        CONFIG["registry_file"] = self._saved

    def test_missing_file_returns_empty_registry(self):
        self.assertEqual(load_registry(), {"scripts": []})

    def test_corrupt_file_raises_registry_error_with_path(self):
        CONFIG["registry_file"].write_text("{ not json", encoding="utf-8")
        with self.assertRaises(RegistryError) as ctx:
            load_registry()
        self.assertIn(str(CONFIG["registry_file"]), str(ctx.exception))

    def test_save_is_atomic_and_leaves_no_temp_file(self):
        save_registry({"scripts": [{"id": "a"}]})
        self.assertFalse((self._tmp / "registry.json.tmp").exists())
        data = json.loads(CONFIG["registry_file"].read_text(encoding="utf-8"))
        self.assertEqual(data["scripts"][0]["id"], "a")

    def test_missing_scripts_key_defaults_to_empty_list(self):
        CONFIG["registry_file"].write_text('{"foo": 1}', encoding="utf-8")
        data = load_registry()
        self.assertEqual(data["scripts"], [])
        self.assertEqual(data["foo"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
