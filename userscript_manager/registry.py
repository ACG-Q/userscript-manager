import json
import os
from .config import CONFIG


class RegistryError(Exception):
    """registry.json 存在但无法解析时抛出，携带文件路径与修复提示。"""


def load_registry() -> dict:
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
        if "scripts" not in data:
            data["scripts"] = []
        return data
    return {"scripts": []}


def save_registry(registry: dict) -> None:
    path = CONFIG["registry_file"]
    tmp = path.parent / (path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def find_script(registry: dict, script_id: str) -> dict | None:
    for s in registry["scripts"]:
        if s["id"] == script_id:
            return s
    return None


def find_script_by_source_url(registry: dict, source_url: str) -> dict | None:
    for s in registry["scripts"]:
        if s.get("source_url") == source_url:
            return s
    return None


def add_script(registry: dict, script_meta: dict) -> None:
    registry["scripts"].append(script_meta)
    save_registry(registry)


def remove_script(registry: dict, script_id: str) -> bool:
    script = find_script(registry, script_id)
    if not script:
        return False
    registry["scripts"] = [s for s in registry["scripts"] if s["id"] != script_id]
    save_registry(registry)
    return True


def update_script(registry: dict, script_id: str, updates: dict) -> bool:
    script = find_script(registry, script_id)
    if not script:
        return False
    script.update(updates)
    save_registry(registry)
    return True
