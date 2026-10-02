"""registry.json 读写与结构校验。

分工约定（避免两套写入口漂移）：
- 新增条目走 add_script，一步完成改内存+落盘；
- 字段级就地修改（命令直接改 script dict，含软删除/复活）之后用 save_registry 落盘。
"""
import json
import os
from .config import CONFIG


class RegistryError(Exception):
    """registry.json 存在但无法解析时抛出，携带文件路径与修复提示。"""


def load_registry() -> dict:
    """读取并校验 registry.json；文件缺失返回空库，损坏抛 RegistryError。"""
    path = CONFIG["registry_file"]
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise RegistryError(
                f"registry.json 已损坏（{path}）：{e}。"
                "请用 Git 历史恢复该文件，不要直接删除。"
            ) from e
        _validate_registry(data, path)
        if "scripts" not in data:
            data["scripts"] = []
        for s in data["scripts"]:
            # 向后兼容：旧记录加载即补齐软删与讨论账本字段（D3/D7）
            s.setdefault("discussions", [])
            s.setdefault("deleted", False)
        return data
    return {"scripts": []}


def _validate_registry(data: dict, path) -> None:
    """加载即校验结构，避免把 KeyError 延迟到运行时才发现脏数据。"""
    hint = "请用 Git 历史恢复该文件，不要直接删除。"
    if not isinstance(data, dict):
        raise RegistryError(f"registry.json 顶层必须是对象（{path}）。{hint}")
    if "scripts" not in data:
        return
    scripts = data["scripts"]
    if not isinstance(scripts, list):
        raise RegistryError(f"registry.json 的 scripts 必须是数组（{path}）。{hint}")
    for i, s in enumerate(scripts):
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not s.get("id"):
            raise RegistryError(
                f"registry.json 第 {i} 条记录缺少有效 id（{path}）。{hint}"
            )
        if s.get("type") not in ("self", "synced"):
            raise RegistryError(
                f"registry.json 脚本 {s['id']} 的 type 非法：{s.get('type')!r}"
                f"（{path}）。允许值：self / synced。{hint}"
            )


def save_registry(registry: dict) -> None:
    """原子落盘（临时文件 + os.replace），避免写一半损坏。"""
    path = CONFIG["registry_file"]
    tmp = path.parent / (path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def find_script(registry: dict, script_id: str) -> dict | None:
    """按 ID 查找脚本记录，未命中返回 None。"""
    for s in registry["scripts"]:
        if s["id"] == script_id:
            return s
    return None


def find_script_by_source_url(registry: dict, source_url: str) -> dict | None:
    """按来源 URL 查找同步脚本，未命中返回 None（防重复添加）。"""
    for s in registry["scripts"]:
        if s.get("source_url") == source_url:
            return s
    return None


def add_script(registry: dict, script_meta: dict) -> None:
    """追加新脚本并立即落盘（结构性变更的唯一入口之一）。"""
    registry["scripts"].append(script_meta)
    save_registry(registry)
