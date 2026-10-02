from ..registry import save_registry, find_script
from ..utils import now_iso
from ..commands import register


@register("enable")
def execute_enable(registry, args, code, markdown, has_code_block):
    """/enable <id>：重新启用已禁用的脚本，并记录 updated_at。"""
    if not args:
        return "❌ 请提供脚本 ID，例如 /enable <script_id>"

    script = find_script(registry, args)
    if not script:
        return f"❌ 未找到 ID 为 {args} 的脚本。"

    if script.get("enabled", True):
        return f"ℹ️ 脚本 {args} 已经是启用状态。"

    script["enabled"] = True
    script["updated_at"] = now_iso()
    save_registry(registry)
    return f"✅ 已启用脚本 {args}"


@register("disable")
def execute_disable(registry, args, code, markdown, has_code_block):
    """/disable <id>：禁用脚本（安装链接停用），并记录 updated_at。"""
    if not args:
        return "❌ 请提供脚本 ID，例如 /disable <script_id>"

    script = find_script(registry, args)
    if not script:
        return f"❌ 未找到 ID 为 {args} 的脚本。"

    if not script.get("enabled", True):
        return f"ℹ️ 脚本 {args} 已经是禁用状态。"

    script["enabled"] = False
    script["updated_at"] = now_iso()
    save_registry(registry)
    return f"⏸️ 已禁用脚本 {args}"
