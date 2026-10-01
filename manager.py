#!/usr/bin/env python3
import os
import sys
import io
from pathlib import Path

# Fix encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add project root to path so we can import userscript_manager
sys.path.insert(0, str(Path(__file__).parent))

from userscript_manager.config import CONFIG
from userscript_manager.registry import load_registry
from userscript_manager.issue_parser import parse_comment, ParsedComment
from userscript_manager.commands import get_command
from userscript_manager.utils import ensure_dirs

# Import all commands to register them
import pkgutil
import userscript_manager.commands as commands_pkg

for _module in pkgutil.iter_modules(commands_pkg.__path__):
    __import__(f"userscript_manager.commands.{_module.name}")

def main():
    comment_body = os.getenv("COMMENT_BODY", "")
    comment_user = os.getenv("COMMENT_USER", "")
    repo_owner = os.getenv("REPO_OWNER", "")
    issue_number = os.getenv("ISSUE_NUMBER", "")
    
    # Check if it's the command panel issue (issue #1)
    if CONFIG.get("control_issue_number") and issue_number:
        try:
            if int(issue_number) != CONFIG["control_issue_number"]:
                print(f"非命令面板 Issue #{issue_number}，忽略执行")
                return
        except ValueError:
            print(f"无效的 ISSUE_NUMBER: {issue_number}")
            return
    
    # Only repo owner can execute commands
    if comment_user != repo_owner:
        print(f"权限不足：{comment_user} 不是仓库所有者 {repo_owner}")
        return
    
    parsed = parse_comment(comment_body)
    if not parsed.command:
        print("未识别命令")
        return
    
    func = get_command(parsed.command)
    if not func:
        print(f"未知命令: {parsed.command}")
        return
    
    ensure_dirs()
    registry = load_registry()
    result = func(registry, parsed.args, parsed.code, parsed.markdown, parsed.has_code_block)
    print(result)
    
    # Write result for GitHub Actions to pick up
    with open("command_result.txt", "w", encoding="utf-8") as f:
        f.write(result)

if __name__ == "__main__":
    main()