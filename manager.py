#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Fix encoding on Windows.
# 用 reconfigure 而不是重包一层 TextIOWrapper：重包会关掉原流的缓冲，
# 在 pytest 捕获下会把捕获文件提前关闭，导致整目录收集/退出阶段崩溃。
if sys.platform == "win32":
    for _name in ("stdout", "stderr"):
        _stream = getattr(sys, _name, None)
        _reconfigure = getattr(_stream, "reconfigure", None)
        if _reconfigure is None:
            continue  # 测试框架替换的捕获流没有 reconfigure，保持原样
        try:
            _reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass  # 流已关闭或不支持重配置

# Add project root to path so we can import userscript_manager
sys.path.insert(0, str(Path(__file__).parent))

# 命令注册由 userscript_manager.commands.get_command 惰性触发（pkgutil 自动发现），
# 不再依赖这里手动逐个 import ——漏导会让命令凭空消失，且只在单文件运行时才暴露。
from userscript_manager.commands import get_command
from userscript_manager.config import CONFIG
from userscript_manager.issue_parser import parse_comment
from userscript_manager.registry import load_registry
from userscript_manager.utils import ensure_dirs


def _finish(message: str) -> None:
    """打印并落盘结果——所有早退路径都必须走这里，否则 Actions 会误报「操作完成」。"""
    print(message)
    Path("command_result.txt").write_text(message, encoding="utf-8")


def main():
    """Actions 入口：解析面板命令 → 执行 → 回写结果（所有路径都经 _finish）。"""
    comment_body = os.getenv("COMMENT_BODY", "")
    comment_user = os.getenv("COMMENT_USER", "")
    repo_owner = os.getenv("REPO_OWNER", "")
    issue_number = os.getenv("ISSUE_NUMBER", "")
    
    # Check if it's the command panel issue (issue #1)
    if CONFIG.get("control_issue_number") and issue_number:
        try:
            if int(issue_number) != CONFIG["control_issue_number"]:
                _finish(f"非命令面板 Issue #{issue_number}，忽略执行")
                return
        except ValueError:
            _finish(f"无效的 ISSUE_NUMBER: {issue_number}")
            return
    
    # Only repo owner can execute commands
    if comment_user != repo_owner:
        _finish(f"权限不足：{comment_user} 不是仓库所有者 {repo_owner}")
        return
    
    parsed = parse_comment(comment_body)
    if not parsed.command:
        _finish("未识别命令")
        return
    
    func = get_command(parsed.command)
    if not func:
        _finish(f"未知命令: {parsed.command}")
        return
    
    ensure_dirs()
    registry = load_registry()
    result = func(registry, parsed.args, parsed.code, parsed.markdown, parsed.has_code_block)
    _finish(result)

if __name__ == "__main__":
    main()