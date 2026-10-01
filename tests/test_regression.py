import os
import sys
import io
import tempfile
from pathlib import Path

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Point config to a temp workspace
TMP = Path(tempfile.mkdtemp(prefix="usm_test_"))
os.environ["AUTHOR_NAME"] = "Test Author"
os.environ["AUTHOR_NAMESPACE"] = "https://test.dev"
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"
os.environ["GITHUB_REF_NAME"] = "main"

from userscript_manager.config import CONFIG
CONFIG["registry_file"] = TMP / "registry.json"
CONFIG["self_scripts_dir"] = TMP / "scripts" / "self"
CONFIG["synced_scripts_dir"] = TMP / "scripts" / "synced"
CONFIG["dist_dir"] = TMP / "dist"

from userscript_manager.registry import load_registry, save_registry
from userscript_manager.utils import ensure_dirs
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

ensure_dirs()
registry = load_registry()

SCRIPT = """// ==UserScript==
// @name 测试脚本
// @version 1.0.0
// @match *://*/*
// @grant none
// ==/UserScript==
(function() { console.log('Hello'); })();
"""

def run(cmd_body):
    p = parse_comment(cmd_body)
    f = get_command(p.command)
    result = f(registry, p.args, p.code, p.markdown, p.has_code_block)
    save_registry(registry)
    return result

# 1. Add
r = run("/add\n# 文档标题\n\n```javascript\n" + SCRIPT + "\n```")
print("ADD:", r.splitlines()[0])
script_id = r.splitlines()[1].split(": ")[1].strip()

# 2. List
print("LIST:", run("/list").splitlines()[0], "| 数量:", len(registry["scripts"]))

# 3. Info - verify doc path set
info = run(f"/info {script_id}")
assert "安装链接" in info, "info 应包含安装链接"
print("INFO: 文档字段 =", "文档: 有" in info)

# 4. Update (version bump)
NEW_SCRIPT = SCRIPT.replace("1.0.0", "1.0.0").replace("Hello", "Hello v2")
r = run(f"/up {script_id}\n```javascript\n" + NEW_SCRIPT.replace("// @version 1.0.0", "// @version 1.0.0") + "\n```")
print("UP:", r.splitlines()[0])

# 5. Verify version incremented in registry
s = registry["scripts"][0]
print("VERSION after up:", s["version"], "(应 1.0.1)")
assert s["version"] == "1.0.1", f"版本应为 1.0.1, 实际 {s['version']}"

# 6. dist file exists
dist = TMP / "dist" / f"{script_id}.user.js"
assert dist.exists(), "dist 文件应存在"
print("DIST: exists, 头部 downloadURL =", any("// @downloadURL" in l for l in dist.read_text(encoding="utf-8").splitlines()))

# 7. Toggle
print("DISABLE:", run(f"/disable {script_id}").splitlines()[0])
print("ENABLE:", run(f"/enable {script_id}").splitlines()[0])

# 8. Export
print("EXPORT md:", run("/export md").splitlines()[0])
print("EXPORT json:", run("/export json").splitlines()[0][:30])

# 9. Remove
print("RM:", run(f"/rm {script_id}").splitlines()[0])
print("LIST after rm:", run("/list").splitlines()[0])

print("\nALL PASSED")