import functools
import logging
import traceback

log = logging.getLogger(__name__)

_commands: dict = {}

def register(name: str):
    """注册命令并附加统一错误边界：未捕获异常降级为回帖文本，不再炸掉整条流水线。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
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
        return wrapper
    return decorator

def get_command(name: str):
    """按名称取已注册命令（含错误边界包装）；未注册返回 None。"""
    return _commands.get(name)

def get_all_commands() -> dict:
    """返回全部已注册命令的副本（名称 -> 包装函数）。"""
    return _commands.copy()
