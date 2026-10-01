from ..registry import load_registry, save_registry, find_script
from ..commands import register

@register("enable")
def execute_enable(registry, args, code, markdown, has_code_block):
    if not args:
        return "❌ 请提供脚本 ID，例如 /enable <script_id>"
    
    script = find_script(registry, args)
    if not script:
        return f"❌ 未找到 ID 为 {args} 的脚本。"
    
    if script.get("enabled", True):
        return f"ℹ️ 脚本 {args} 已经是启用状态。"
    
    script["enabled"] = True
    save_registry(registry)
    return f"✅ 已启用脚本 {args}"

@register("disable")
def execute_disable(registry, args, code, markdown, has_code_block):
    if not args:
        return "❌ 请提供脚本 ID，例如 /disable <script_id>"
    
    script = find_script(registry, args)
    if not script:
        return f"❌ 未找到 ID 为 {args} 的脚本。"
    
    if not script.get("enabled", True):
        return f"ℹ️ 脚本 {args} 已经是禁用状态。"
    
    script["enabled"] = False
    save_registry(registry)
    return f"⏸️ 已禁用脚本 {args}"