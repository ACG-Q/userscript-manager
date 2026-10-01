#!/usr/bin/env python3
"""从 registry 生成 Pages 站点：index 列表页 + scripts/<id>.html 详情页。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import markdown as md

from userscript_manager.config import CONFIG, get_install_url
from userscript_manager.escaping import escape_html
from userscript_manager.registry import load_registry

BRAND = "油猴脚本管理器"

TOKEN_CSS = """
:root, [data-theme="github-light"] {
  --brand: #0969da;
  --brand-hover: #0860ca;
  --brand-fade: #0969da66;
  --primary: #1f883d;
  --primary-hover: #1a7f37;
  --bg: #ffffff;
  --bg-subtle: #f6f8fa;
  --page-bg: #f6f8fa;
  --text: #1f2328;
  --text-muted: #57606a;
  --border: #d8dee4;
  --border-strong: #b1b9c1;
  --success: #1a7f37;
  --success-bg: #dafbe1;
  --danger: #cf222e;
  --info-bg: #ddf4ff;
  --info-text: #0969da;
  --warn-bg: #fff8c5;
  --warn-text: #9a6700;
  --neutral-bg: #eaeef2;
  --radius-card: 12px;
  --radius-btn: 8px;
  --radius-pill: 999px;
  --font-ui: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
  --font-mono: ui-monospace, "Cascadia Code", Consolas, monospace;
}
[data-theme="terminal-dark"] { /* 预留：硬核绿（开发者暗色）token 待填 */ }
[data-theme="vivid-purple"] { /* 预留：表达紫（现代 SaaS）token 待填 */ }
"""

COMPONENT_CSS = """
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; padding: 40px 16px; font-family: var(--font-ui); background: var(--page-bg); color: var(--text); }
code { font-family: var(--font-mono); }
a { color: var(--brand); text-decoration: none; }
a:hover { text-decoration: underline; }

.frame { max-width: 1060px; margin: 0 auto; background: var(--bg); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }

.nav { display: flex; align-items: center; gap: 20px; padding: 14px 28px; border-bottom: 1px solid var(--border); }
.brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 16px; }
.brand svg { color: var(--brand); display: block; }
.nav .spacer { flex: 1; }
.nav a.link { color: var(--text); font-size: 14px; font-weight: 500; padding: 10px 6px; min-height: 44px; display: inline-flex; align-items: center; }
.nav a.link:hover { color: var(--brand); text-decoration: none; }

.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 44px; padding: 0 18px; border-radius: var(--radius-btn); font-size: 14px; font-weight: 600; text-decoration: none; cursor: pointer; border: 1px solid transparent; white-space: nowrap; transition: background .15s ease, border-color .15s ease; }
.btn:hover { text-decoration: none; }
.btn:focus-visible, .chip:focus-visible, .nav a.link:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }
.btn.nav-btn { background: var(--brand); color: #fff; }
.btn.nav-btn:hover { background: var(--brand-hover); }
.btn.primary { background: var(--primary); color: #fff; }
.btn.primary:hover { background: var(--primary-hover); }
.btn.ghost { background: var(--bg-subtle); border-color: var(--border); color: var(--text); }
.btn.ghost:hover { background: var(--neutral-bg); border-color: var(--border-strong); }
.btn.big { min-height: 48px; padding: 0 24px; font-size: 15px; }

.hero { padding: 36px 28px 28px; background: var(--bg-subtle); border-bottom: 1px solid var(--border); }
.hero h1 { margin: 0 0 8px; font-size: 28px; letter-spacing: -.01em; }
.hero .sub { margin: 0 0 20px; font-size: 15px; line-height: 1.6; max-width: 640px; color: var(--text-muted); }
.stats { display: flex; gap: 12px; flex-wrap: wrap; }
.stat { flex: 1; min-width: 150px; padding: 14px 16px; border-radius: 10px; background: var(--bg); border: 1px solid var(--border); }
.stat b { display: block; font-size: 24px; line-height: 1.2; color: var(--brand); }
.stat span { font-size: 13px; color: var(--text-muted); }

main { padding: 8px 28px 36px; }
.sec { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin: 26px 0 14px; font-size: 18px; }
.filters { display: inline-flex; gap: 6px; }
.chip { font-size: 13px; padding: 7px 14px; border-radius: var(--radius-pill); cursor: pointer; border: 1px solid var(--border); background: var(--bg); color: var(--text-muted); font-family: var(--font-ui); min-height: 34px; }
.chip:hover { border-color: var(--border-strong); }
.chip.active { background: var(--brand); border-color: var(--brand); color: #fff; }

.script-card { display: grid; grid-template-columns: 1.3fr 1fr auto; gap: 18px; padding: 18px; border-radius: var(--radius-card); margin-bottom: 12px; align-items: start; background: var(--bg); border: 1px solid var(--border); }
.script-card:hover { border-color: var(--brand-fade); }
.sc-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.sc-title h3 { margin: 0; font-size: 16px; }
.pill { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: var(--radius-pill); }
.pill.type-self { background: var(--info-bg); color: var(--info-text); }
.pill.type-sync { background: var(--warn-bg); color: var(--warn-text); }
.pill.ver { background: var(--bg-subtle); color: var(--text-muted); border: 1px solid var(--border); }
.status { font-size: 13px; display: inline-flex; align-items: center; gap: 6px; color: var(--success); }
.status.off { color: var(--danger); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); display: inline-block; }
.status.off .dot { background: var(--danger); }
.sc-desc { margin: 0 0 6px; font-size: 14px; line-height: 1.55; }
.sc-meta { margin: 0; font-size: 12.5px; color: var(--text-muted); }
.sc-meta code { padding: 2px 6px; border-radius: 5px; font-size: 12px; background: var(--bg-subtle); border: 1px solid var(--border); }

.sc-disc { border-radius: 10px; padding: 12px 14px; font-size: 13px; background: var(--bg-subtle); border: 1px solid var(--border); }
.disc-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-weight: 600; font-size: 13px; margin-bottom: 8px; }
.disc-head svg { flex: none; color: var(--brand); }
.disc-head .grow { flex: 1; }
.disc-head a { font-size: 13px; font-weight: 600; }
.badge { font-size: 12px; font-weight: 600; padding: 2px 9px; border-radius: var(--radius-pill); display: inline-flex; align-items: center; gap: 4px; background: var(--success-bg); color: var(--success); }
.badge.plain { background: var(--neutral-bg); color: var(--text-muted); }
.disc-latest { margin: 0; line-height: 1.55; }
.disc-who { display: block; margin-top: 4px; font-size: 12px; color: var(--text-muted); }
.disc-empty { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 0; color: var(--text-muted); }
.disc-empty a { font-weight: 600; font-size: 13px; }

.sc-actions { display: flex; flex-direction: column; gap: 8px; }
.empty { text-align: center; color: var(--text-muted); padding: 32px 0; }

.detail-card { border-radius: 14px; padding: 24px; background: var(--bg); border: 1px solid var(--border); }
.d-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.d-head h3 { margin: 0 0 8px; font-size: 22px; }
.d-pills { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.d-meta { display: flex; gap: 18px; flex-wrap: wrap; font-size: 13.5px; margin: 16px 0; padding: 12px 0; border-bottom: 1px solid var(--border); color: var(--text-muted); }
.d-meta i { font-style: normal; opacity: .7; margin-right: 4px; }
.d-meta code { background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 5px; padding: 1px 6px; font-size: 12.5px; }

.d-doc h1, .d-doc h2, .d-doc h3, .d-doc h4 { margin: 18px 0 8px; font-size: 17px; }
.d-doc h4 { font-size: 15px; }
.d-doc p, .d-doc li { font-size: 14.5px; line-height: 1.65; }
.d-doc p { margin: 0 0 10px; }
.d-doc ul, .d-doc ol { padding-left: 24px; }
.d-doc code { padding: 1px 6px; border-radius: 5px; font-size: 13px; background: var(--bg-subtle); border: 1px solid var(--border); }
.d-doc pre { background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 8px; padding: 12px; overflow-x: auto; }
.d-doc pre code { background: none; border: none; padding: 0; }
.d-doc table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; }
.d-doc th, .d-doc td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; }
.d-doc th { background: var(--bg-subtle); }
.d-doc blockquote { margin: 12px 0; padding: 2px 14px; border-left: 3px solid var(--border); color: var(--text-muted); }
.d-doc img { max-width: 100%; }

.d-disc { margin-top: 20px; border-radius: 12px; padding: 16px; background: var(--bg-subtle); border: 1px solid var(--border); }
.d-disc .disc-head { font-size: 14px; margin-bottom: 12px; }
.cmt { display: grid; grid-template-columns: auto 1fr; gap: 4px 10px; padding: 10px 0; border-top: 1px solid var(--border); font-size: 14px; }
.cmt:first-of-type { border-top: none; }
.cmt b { font-size: 13.5px; }
.cmt time { font-size: 12px; align-self: center; color: var(--text-muted); }
.cmt p { grid-column: 1 / -1; margin: 2px 0 0; line-height: 1.6; }
.cmt.owner b::after { content: "· 仓库所有者"; color: var(--success); font-weight: 600; margin-left: 6px; font-size: 12px; }
.d-disc .btn { margin-top: 12px; }

footer.foot { padding: 18px 28px; font-size: 13px; display: flex; gap: 14px; flex-wrap: wrap; align-items: center; color: var(--text-muted); border-top: 1px solid var(--border); }
footer.foot a { font-weight: 600; }

@media (max-width: 760px) {
  body { padding: 16px 8px; }
  .script-card { grid-template-columns: 1fr; }
  .sc-actions { flex-direction: row; }
  .hero h1 { font-size: 24px; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""

PAGE_STYLE = TOKEN_CSS + COMPONENT_CSS


def render_markdown(text: str) -> str:
    return md.markdown(text or "", extensions=["fenced_code", "tables"])


def page(title: str, body_html: str, extra_js: str = "") -> str:
    repo = escape_html(CONFIG["github_repo"])
    issue = CONFIG["control_issue_number"]
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="github-light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(title)}</title>
<style>{PAGE_STYLE}</style>
</head>
<body>
<div class="frame">
<header class="nav">
<span class="brand"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>{BRAND}</span>
<span class="spacer"></span>
<a class="link" href="https://github.com/{repo}/blob/master/docs/index.md">文档</a>
<a class="link" href="https://github.com/{repo}">GitHub 仓库</a>
<a class="btn nav-btn" href="https://github.com/{repo}/issues/{issue}">管理入口 · Issue #{issue}</a>
</header>
{body_html}
<footer class="foot">
<span>由 <a href="https://github.com/{repo}">{repo}</a> 自动生成</span>
<a href="https://github.com/{repo}/issues/{issue}">管理入口 · Issue #{issue}</a>
<a href="https://github.com/{repo}">GitHub 仓库</a>
</footer>
</div>
{extra_js}
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
