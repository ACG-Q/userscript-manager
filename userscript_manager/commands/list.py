from ..commands import register

@register("list")
def execute(registry, args, code, markdown, has_code_block):
    """/list：列出全部未软删的脚本及启用/同步状态。"""
    visible = [s for s in registry["scripts"] if not s.get("deleted")]
    if not visible:
        return "📭 当前没有脚本。"

    lines = ["📋 脚本列表："]
    for s in visible:
        status = "✅" if s.get("enabled", True) else "⏸️"
        script_type = "📝" if s["type"] == "self" else "🔄"
        sync_status = ""
        if s["type"] == "synced":
            last_sync = s.get("last_synced_at", "从未")
            if last_sync != "从未":
                sync_status = f" (上次同步: {last_sync[:10]})"
            else:
                sync_status = " (未同步)"
        lines.append(
            f"  {status} {script_type} {s['id']} | {s['name']} "
            f"(v{s['version']}){sync_status}"
        )
    return "\n".join(lines)