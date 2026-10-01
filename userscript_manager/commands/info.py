from ..registry import find_script
from ..config import get_install_url
from ..commands import register

@register("info")
def execute(registry, args, code, markdown, has_code_block):
    if not args:
        return "❌ 请提供脚本 ID，例如 /info <script_id>"
    
    script = find_script(registry, args)
    if not script:
        return f"❌ 未找到 ID 为 {args} 的脚本。"
    
    install_url = get_install_url(script['id'])
    
    lines = [f"📄 脚本详情: {script['id']}"]
    lines.append(f"  名称: {script['name']}")
    lines.append(f"  类型: {'自写' if script['type'] == 'self' else '同步'}")
    lines.append(f"  版本: {script['version']}")
    lines.append(f"  状态: {'启用' if script.get('enabled', True) else '禁用'}")
    lines.append(f"  作者: {script.get('author', '未知')}")
    lines.append(f"  命名空间: {script.get('namespace', '未设置')}")
    lines.append(f"  描述: {script.get('description', '无')}")
    lines.append(f"  匹配规则: {', '.join(script.get('match', ['*://*/*']))}")
    lines.append(f"  权限: {', '.join(script.get('grant', ['none']))}")
    lines.append(f"  创建时间: {script.get('created_at', '未知')}")
    lines.append(f"  更新时间: {script.get('updated_at', '未知')}")
    
    if script["type"] == "synced":
        lines.append(f"  来源: {script.get('source_url', '未知')}")
        lines.append(f"  来源类型: {script.get('source_type', '未知')}")
        lines.append(f"  上次同步: {script.get('last_synced_at', '从未')}")
        lines.append(f"  自动同步: {'是' if script.get('sync_enabled', True) else '否'}")
    else:
        if script.get("documentation"):
            lines.append(f"  文档: 有 (README.md)")
    
    lines.append(f"  安装链接: {install_url}")
    
    return "\n".join(lines)