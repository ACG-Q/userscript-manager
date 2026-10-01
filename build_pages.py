#!/usr/bin/env python3
"""从 registry 生成 Pages 站点：index 列表页 + scripts/<id>.html 详情页。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import markdown as md

from userscript_manager.config import CONFIG, get_install_url
from userscript_manager.escaping import escape_html
from userscript_manager.registry import load_registry

PAGE_STYLE = """
body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; }
h1 { border-bottom: 2px solid #eee; padding-bottom: 12px; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; }
th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; }
th { background: #f5f5f5; }
tr:hover { background: #fafafa; }
a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }
.footer { margin-top: 30px; font-size: 13px; color: #999; }
.install { display: inline-block; padding: 8px 16px; background: #2ea44f; color: #fff; border-radius: 6px; text-decoration: none; }
"""


def render_markdown(text: str) -> str:
    return md.markdown(text or "", extensions=["fenced_code", "tables"])


def page(title: str, body_html: str) -> str:
    repo = escape_html(CONFIG["github_repo"])
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(title)}</title>
<style>{PAGE_STYLE}</style>
</head>
<body>
{body_html}
<div class="footer">由 <a href="https://github.com/{repo}">仓库</a> 自动生成 · 管理入口 <a href="https://github.com/{repo}/issues/1">Issue #1</a></div>
</body>
</html>"""


def build_index(registry: dict) -> str:
    rows = []
    for s in registry["scripts"]:
        name = escape_html(s.get("name", s["id"]))
        version = escape_html(s.get("version", ""))
        status = "启用" if s.get("enabled", True) else "已禁用"
        script_type = "自写" if s["type"] == "self" else "同步"
        links = [f'<a href="scripts/{escape_html(s["id"])}.html">详情</a>']
        links.append(f'<a href="{escape_html(get_install_url(s["id"]))}">安装</a>')
        discussion_url = (s.get("discussion") or {}).get("url")
        if discussion_url:
            links.append(f'<a href="{escape_html(discussion_url)}">讨论</a>')
        rows.append(
            f"<tr><td>{name}</td><td>{script_type}</td><td>{version}</td>"
            f"<td>{status}</td><td>{' · '.join(links)}</td></tr>"
        )
    rows_html = "\n".join(rows) if rows else (
        '<tr><td colspan="5" style="text-align:center;color:#888;">'
        "暂无脚本，请在命令面板 Issue #1 中使用 /add 添加。</td></tr>"
    )
    body = f"""<h1>油猴脚本管理器</h1>
<p>此页面由 GitHub Actions 构建，安装链接指向本站部署的脚本文件。</p>
<table>
<thead><tr><th>名称</th><th>类型</th><th>版本</th><th>状态</th><th>操作</th></tr></thead>
<tbody>
{rows_html}
</tbody>
</table>"""
    return page("油猴脚本管理器", body)


def build_detail(script: dict) -> str:
    name = escape_html(script.get("name", script["id"]))
    version = escape_html(script.get("version", ""))
    author = escape_html(script.get("author", "") or "-")
    description = escape_html(script.get("description", ""))
    matches = "<br>".join(f"<code>{escape_html(m)}</code>" for m in script.get("match") or [])
    install_url = escape_html(get_install_url(script["id"]))

    extra = ""
    discussion_url = (script.get("discussion") or {}).get("url")
    if discussion_url:
        extra = f' · <a href="{escape_html(discussion_url)}">讨论与反馈</a>'

    rows = [
        ("<tr><th>版本</th><td>" + version + "</td></tr>"),
        ("<tr><th>作者</th><td>" + author + "</td></tr>"),
        ("<tr><th>匹配规则</th><td>" + (matches or "-") + "</td></tr>"),
        ("<tr><th>描述</th><td>" + (description or "-") + "</td></tr>"),
    ]
    changelog = script.get("changelog") or []
    if changelog:
        ch_rows = "".join(
            f"<tr><td>{escape_html(r.get('version', ''))}</td>"
            f"<td>{escape_html(r.get('date', ''))}</td>"
            f"<td>{escape_html(r.get('note', ''))}</td></tr>"
            for r in changelog
        )
        changelog_html = (
            "<table><thead><tr><th>版本</th><th>日期</th><th>说明</th></tr></thead>"
            f"<tbody>{ch_rows}</tbody></table>"
        )
    else:
        changelog_html = "<p>暂无更新记录。</p>"

    body = f"""<h1>{name}</h1>
<p><a class="install" href="{install_url}">安装脚本</a>{extra}</p>
<table><tbody>{''.join(rows)}</tbody></table>
<h2>文档</h2>
{render_markdown(script.get("documentation") or "_暂无文档_")}
<h2>更新历史</h2>
{changelog_html}"""
    return page(script.get("name", script["id"]), body)


def build_site(registry: dict) -> list[Path]:
    dist = Path(CONFIG["dist_dir"])
    (dist / "scripts").mkdir(parents=True, exist_ok=True)
    written = []
    index_path = dist / "index.html"
    index_path.write_text(build_index(registry), encoding="utf-8")
    written.append(index_path)
    for s in registry["scripts"]:
        detail_path = dist / "scripts" / f"{s['id']}.html"
        detail_path.write_text(build_detail(s), encoding="utf-8")
        written.append(detail_path)
    return written


def main() -> int:
    written = build_site(load_registry())
    print(f"已生成 {len(written)} 个页面 -> {CONFIG['dist_dir']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
