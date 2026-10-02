import json
import os
import sys
import io
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from tests._helpers import ConfigIsolation
from userscript_manager.config import CONFIG
from userscript_manager.registry import load_registry, save_registry, RegistryError


class TestRegistry(ConfigIsolation):
    TMP_PREFIX = "usm_reg_"

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

    def test_script_missing_id_raises(self):
        CONFIG["registry_file"].write_text(
            '{"scripts": [{"type": "self"}]}', encoding="utf-8"
        )
        with self.assertRaises(RegistryError) as ctx:
            load_registry()
        self.assertIn("id", str(ctx.exception))

    def test_script_invalid_type_raises(self):
        CONFIG["registry_file"].write_text(
            '{"scripts": [{"id": "x", "type": "sync"}]}', encoding="utf-8"
        )
        with self.assertRaises(RegistryError) as ctx:
            load_registry()
        self.assertIn("type", str(ctx.exception))

    def test_scripts_not_a_list_raises(self):
        CONFIG["registry_file"].write_text('{"scripts": "nope"}', encoding="utf-8")
        with self.assertRaises(RegistryError):
            load_registry()


if __name__ == "__main__":
    unittest.main(verbosity=2)
