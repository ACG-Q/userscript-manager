import functools
import logging
import pkgutil
import traceback
from collections.abc import Callable
from importlib import import_module
from typing import Any, cast

log = logging.getLogger(__name__)

# 命令统一签名与返回值（registry 快照 → 参数 → Markdown/代码块 → 回帖文本）
CommandFn = Callable[..., str]

_commands: dict[str, CommandFn] = {}
_loaded = False


def _ensure_loaded() -> None:
    """惰性导入全部命令模块，触发其中的 ``@register`` 注册。

    以前注册依赖调用方手动 ``import userscript_manager.commands.xxx``：
    只要某处漏导（或被 linter 当「未用导入」清掉），对应命令就凭空消失，
    而且往往只在单文件运行时才暴露。现在统一由查询入口触发，
    注册不再依赖导入顺序与调用方自觉。
    """
    global _loaded
    if _loaded:
        return
    _loaded = True  # 先置位：子模块注册时不会递归回到这里
    for module in pkgutil.iter_modules(__path__):
        if module.name != "__init__":
            import_module(f"{__name__}.{module.name}")


def register(name: str) -> Callable[[CommandFn], CommandFn]:
    """注册命令并附加统一错误边界：未捕获异常降级为回帖文本，不再炸掉整条流水线。"""
    def decorator(func: CommandFn) -> CommandFn:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> str:
            try:
                return func(*args, **kwargs)
            except Exception:
                log.exception("命令 /%s 执行失败", name)
                tb = traceback.format_exc(limit=3).strip()
                return (
                    f"❌ 命令 /{name} 执行时发生内部错误，已中止（仓库状态可能未变更）。\n"
                    f"```\n{tb}\n```"
                )
        _commands[name] = wrapper
        return cast(CommandFn, wrapper)
    return decorator

def get_command(name: str) -> CommandFn | None:
    """按名称取已注册命令（含错误边界包装）；未注册返回 None。"""
    _ensure_loaded()
    return _commands.get(name)

def get_all_commands() -> dict[str, CommandFn]:
    """返回全部已注册命令的副本（名称 -> 包装函数）。"""
    _ensure_loaded()
    return _commands.copy()
