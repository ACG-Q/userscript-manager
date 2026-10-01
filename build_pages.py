#!/usr/bin/env python3
"""从 registry 生成 Pages 站点：index 列表页 + scripts/<id>.html 详情页。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import markdown as md

from userscript_manager.config import CONFIG, get_install_url
from userscript_manager.discussion_stats import clip, fetch_stats, relative_time
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
[hidden] { display: none !important; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; padding: 40px 16px; font-family: var(--font-ui); background: var(--page-bg); color: var(--text); }
code { font-family: var(--font-mono); }
a { color: var(--brand); text-decoration: none; }
a:hover { text-decoration: underline; }

.frame { max-width: 1060px; margin: 0 auto; background: var(--bg); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }

.nav { display: flex; align-items: center; gap: 20px; padding: 14px 28px; border-bottom: 1px solid var(--border); }
.brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 16px; }
.brand svg { color: var(--brand); display: block; }
a.brand { color: var(--text); }
a.brand:hover { text-decoration: none; color: var(--brand); }
.back { display: inline-flex; align-items: center; gap: 6px; min-height: 44px; font-size: 14px; font-weight: 600; margin-bottom: 6px; }
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
.empty-state { text-align: center; color: var(--text-muted); padding: 36px 16px; }
.empty-state svg { display: block; margin: 0 auto 12px; }
.empty-state p { margin: 0; font-size: 14.5px; line-height: 1.6; }
.empty-state p a { font-weight: 600; font-size: 13.5px; }
.empty-state .es-doc { fill: var(--bg); stroke: var(--border-strong); stroke-width: 2; }
.empty-state .es-line { fill: var(--border); }
.empty-state .es-tray, .empty-state .es-lip { fill: var(--border); }
.empty-state .es-bub rect, .empty-state .es-bub path { fill: var(--border-strong); }
.empty-state .es-bub circle { fill: var(--bg); }
.empty-state.sm { padding: 14px 8px; }
.empty-state.sm svg { width: 56px; height: auto; margin-bottom: 8px; }
.empty-state.sm p { font-size: 13px; }

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


def page(title: str, body_html: str, extra_js: str = "", root_href: str = "index.html") -> str:
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
<a class="brand" href="{root_href}"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>{BRAND}</a>
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


ICON_COMMENT = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
ICON_CHECK = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>'

FILTER_JS = """<script>
document.querySelectorAll('.chip').forEach(function (btn) {
  btn.addEventListener('click', function () {
    document.querySelectorAll('.chip').forEach(function (b) { b.classList.toggle('active', b === btn); });
    var cards = document.querySelectorAll('.script-card');
    var visible = 0;
    cards.forEach(function (card) {
      var show = btn.dataset.filter === 'all' || card.dataset.type === btn.dataset.filter;
      card.hidden = !show;
      if (show) visible += 1;
    });
    var empty = document.getElementById('filter-empty');
    if (empty) empty.hidden = !(cards.length > 0 && visible === 0);
  });
});
</script>"""


EMPTY_SVG = (
    '<svg width="104" height="88" viewBox="0 0 104 88" aria-hidden="true">'
    '<rect class="es-doc" x="30" y="6" width="38" height="46" rx="4"/>'
    '<rect class="es-line" x="37" y="16" width="24" height="4" rx="2"/>'
    '<rect class="es-line" x="37" y="25" width="24" height="4" rx="2"/>'
    '<rect class="es-line" x="37" y="34" width="15" height="4" rx="2"/>'
    '<path class="es-tray" d="M16 50 h72 a6 6 0 0 1 6 6 v10 H10 v-10 '
    'a6 6 0 0 1 6 -6 z"/>'
    '<rect class="es-lip" x="6" y="66" width="92" height="10" rx="5"/>'
    '<g class="es-bub"><rect x="76" y="2" width="26" height="18" rx="6"/>'
    '<path d="M82 18 l1 8 l7 -6 z"/>'
    '<circle cx="83" cy="11" r="1.8"/><circle cx="89" cy="11" r="1.8"/>'
    '<circle cx="95" cy="11" r="1.8"/></g>'
    "</svg>"
)


def empty_state(text: str, small: bool = False, link_html: str = "",
                elem_id: str = "", hidden: bool = False) -> str:
    cls = "empty-state sm" if small else "empty-state"
    attrs = f' id="{elem_id}"' if elem_id else ""
    if hidden:
        attrs += " hidden"
    link = f"<p>{link_html}</p>" if link_html else ""
    return (f'<div class="{cls}"{attrs} role="status">{EMPTY_SVG}'
            f"<p>{text}</p>{link}</div>")


def discussions_list_url() -> str:
    return f"https://github.com/{CONFIG['github_repo']}/discussions"


def discussion_badges(stats) -> str:
    if stats.is_answered:
        return (
            f'<span class="badge" title="讨论已被标记为已解决">'
            f"{ICON_CHECK}已解决</span>"
            f'<span class="badge plain" title="讨论回复总数">'
            f"{stats.reply_count} 条回复</span>"
        )
    if not stats.reply_count:
        return (
            '<span class="badge plain" title="该讨论还没有回复">'
            "0 条回复</span>"
        )
    return (
        f'<span class="badge plain" title="讨论尚未标记为已解决">'
        f"{stats.reply_count} 条回复 · 待解决</span>"
    )


def script_discussion_panel(script: dict, stats) -> str:
    url = (script.get("discussion") or {}).get("url")
    if not url:
        return (
            f'<div class="sc-disc"><div class="disc-head">{ICON_COMMENT}讨论</div>'
            f'<p class="disc-empty"><span>还没有讨论</span>'
            f'<a href="{escape_html(discussions_list_url())}">发起讨论 →</a></p></div>'
        )
    if stats is None:
        return (
            f'<div class="sc-disc"><div class="disc-head">{ICON_COMMENT}讨论</div>'
            f'<p class="disc-empty"><span>摘要暂不可用</span>'
            f'<a href="{escape_html(url)}">在 GitHub 打开 →</a></p></div>'
        )
    head = f'<div class="sc-disc"><div class="disc-head">{ICON_COMMENT}讨论{discussion_badges(stats)}'
    if stats.replies:
        latest = stats.replies[-1]
        who = "仓库所有者" if latest.is_owner else latest.author
        quote = (
            f'<p class="disc-latest">“{escape_html(clip(latest.body, 80))}”'
            f'<span class="disc-who">{escape_html(who)} · '
            f'{escape_html(relative_time(latest.created_at))}</span></p>'
        )
    else:
        quote = ""
    return f"{head}</div>{quote}</div>"


def script_card(script: dict, stats) -> str:
    sid = escape_html(script["id"])
    name = escape_html(script.get("name", script["id"]))
    script_type = script["type"]
    enabled = script.get("enabled", True)
    match = script.get("match") or []
    match_html = f"<code>{escape_html(match[0])}</code>" if match else "<code>—</code>"
    if script_type == "sync":
        when = (script.get("last_synced_at") or script.get("updated_at") or "")[:10]
        time_label = f"同步于 {when}" if when else "同步"
    else:
        when = (script.get("updated_at") or "")[:10]
        time_label = f"更新于 {when}" if when else ""
    desc = escape_html(script.get("description") or "")
    desc_html = f'<p class="sc-desc">{desc}</p>' if desc else ""
    version = escape_html(script.get("version", ""))
    version_html = (
        f'<span class="pill ver" title="当前版本">v{version}</span>' if version else ""
    )
    if script_type == "self":
        type_html = '<span class="pill type-self" title="本仓库自主编写的脚本">自写</span>'
    else:
        source = escape_html(script.get("source_type") or "")
        label = f"同步 · {source}" if source else "同步"
        type_html = (
            f'<span class="pill type-sync" title="从外部来源自动同步的脚本">'
            f"{label}</span>"
        )
    if enabled:
        status_cls = ""
        status_title = "脚本已启用，安装链接可用"
        status_text = "启用"
    else:
        status_cls = " off"
        status_title = "脚本已禁用，暂不可安装"
        status_text = "已禁用"
    install = escape_html(get_install_url(script["id"]))
    disc_href = escape_html(
        (script.get("discussion") or {}).get("url") or discussions_list_url()
    )
    panel = script_discussion_panel(script, stats)
    return f"""<article class="script-card" data-type="{script_type}">
<div class="sc-main">
<div class="sc-title"><h3>{name}</h3>{type_html}{version_html}<span class="status{status_cls}" title="{status_title}"><span class="dot" aria-hidden="true"></span>{status_text}</span></div>
{desc_html}
<p class="sc-meta">{match_html}{(' · ' + time_label) if time_label else ''}</p>
</div>
{panel}
<div class="sc-actions">
<a class="btn primary" href="{install}">安装</a>
<a class="btn ghost" href="scripts/{sid}.html">详情</a>
<a class="btn ghost" href="{disc_href}">讨论</a>
</div>
</article>"""


def build_index(registry: dict, stats_by_id: dict | None = None) -> str:
    degraded = stats_by_id is None
    stats_map = stats_by_id or {}
    scripts = registry["scripts"]
    cards = "\n".join(script_card(s, stats_map.get(s["id"])) for s in scripts)
    if not cards:
        cards = ('<p class="empty">暂无脚本，请在命令面板 Issue #1 '
                 "中使用 /add 添加。</p>")
        filter_empty = ""
    else:
        filter_empty = (
            '<p class="empty" id="filter-empty" hidden>'
            "没有符合筛选条件的脚本</p>"
        )
    if degraded:
        replies_html = answered_html = "—"
    else:
        replies_html = str(sum(st.reply_count for st in stats_map.values()))
        answered_html = str(sum(1 for st in stats_map.values() if st.is_answered))
    body = f"""<section class="hero">
<h1>{BRAND}</h1>
<p class="sub">基于 GitHub Issues + Discussions 的全自动脚本管理：在命令面板里用 <code>/add</code>、<code>/up</code> 管理脚本，每个脚本拥有独立讨论区，安装即可用。</p>
<div class="stats">
<div class="stat" title="注册表中的脚本总数"><b>{len(scripts)}</b><span>脚本总数</span></div>
<div class="stat" title="全部脚本讨论的回复总数"><b>{replies_html}</b><span>讨论回复</span></div>
<div class="stat" title="已被标记为已解决的讨论数"><b>{answered_html}</b><span>已解决反馈</span></div>
</div>
</section>
<main>
<h2 class="sec">脚本列表
<span class="filters">
<button class="chip active" type="button" data-filter="all">全部</button>
<button class="chip" type="button" data-filter="self">自写</button>
<button class="chip" type="button" data-filter="sync">同步</button>
</span>
</h2>
{cards}
{filter_empty}
</main>"""
    return page(BRAND, body, extra_js=FILTER_JS)


def detail_discussion_panel(script: dict, stats) -> str:
    url = (script.get("discussion") or {}).get("url")
    if not url:
        return (
            '<section class="d-disc"><div class="disc-head">'
            f'{ICON_COMMENT}讨论</div>'
            f'<p class="disc-empty"><span>还没有讨论</span>'
            f'<a href="{escape_html(discussions_list_url())}">发起讨论 →</a>'
            "</p></section>"
        )
    if stats is None:
        return (
            '<section class="d-disc"><div class="disc-head">'
            f'{ICON_COMMENT}讨论</div>'
            f'<p class="disc-empty"><span>摘要暂不可用</span>'
            f'<a href="{escape_html(url)}">在 GitHub 打开 →</a>'
            "</p></section>"
        )
    head = (
        f'<div class="disc-head">{ICON_COMMENT}讨论{discussion_badges(stats)}'
        f'<span class="grow"></span>'
        f'<a href="{escape_html(url)}">在 GitHub 打开 →</a></div>'
    )
    if stats.replies:
        comments = "".join(
            f'<div class="cmt{" owner" if r.is_owner else ""}">'
            f"<b>{escape_html(r.author)}</b>"
            f"<time>{escape_html(relative_time(r.created_at))}</time>"
            f"<p>{escape_html(clip(r.body, 400))}</p></div>"
            for r in stats.replies
        )
    else:
        comments = '<p class="disc-empty"><span>还没有回复</span></p>'
    return f'<section class="d-disc">{head}{comments}</section>'


def build_detail(script: dict, stats=None) -> str:
    name = escape_html(script.get("name", script["id"]))
    version = escape_html(script.get("version", ""))
    author = escape_html(script.get("author", "") or "-")
    description = escape_html(script.get("description", ""))
    matches = " ".join(f"<code>{escape_html(m)}</code>" for m in script.get("match") or [])
    install_url = escape_html(get_install_url(script["id"]))

    if script["type"] == "self":
        type_html = '<span class="pill type-self" title="本仓库自主编写的脚本">自写</span>'
    else:
        source = escape_html(script.get("source_type") or "")
        type_html = (
            f'<span class="pill type-sync" title="从外部来源自动同步的脚本">'
            f"同步 · {source}</span>"
        ) if source else (
            '<span class="pill type-sync" title="从外部来源自动同步的脚本">'
            "同步</span>"
        )
    enabled = script.get("enabled", True)
    if enabled:
        status_cls = ""
        status_title = "脚本已启用，安装链接可用"
        status_text = "启用"
    else:
        status_cls = " off"
        status_title = "脚本已禁用，暂不可安装"
        status_text = "已禁用"
    version_html = (
        f'<span class="pill ver" title="当前版本">v{version}</span>' if version else ""
    )
    when = (script.get("updated_at") or script.get("last_synced_at") or "")[:10]
    when_html = f"<span><i>更新</i>{escape_html(when)}</span>" if when else ""
    desc_html = f'<p class="sc-desc">{description}</p>' if description else ""

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

    body = f"""<main>
<section class="detail-card">
<a class="back" href="../index.html">← 返回列表</a>
<div class="d-head">
<div>
<div class="d-pills">{type_html}{version_html}<span class="status{status_cls}" title="{status_title}"><span class="dot" aria-hidden="true"></span>{status_text}</span></div>
<h3>{name}</h3>
</div>
<a class="btn primary" href="{install_url}">安装脚本</a>
</div>
<div class="d-meta"><span><i>作者</i>{author}</span>{when_html}<span><i>匹配规则</i>{matches or "-"}</span></div>
{desc_html}
<section class="d-doc">
{render_markdown(script.get("documentation") or "_暂无文档_")}
</section>
{detail_discussion_panel(script, stats)}
<section class="d-doc">
<h2>更新历史</h2>
{changelog_html}
</section>
</section>
</main>"""
    return page(script.get("name", script["id"]), body, root_href="../index.html")


def build_site(registry: dict, stats_by_id: dict | None = None) -> list[Path]:
    dist = Path(CONFIG["dist_dir"])
    (dist / "scripts").mkdir(parents=True, exist_ok=True)
    written = []
    index_path = dist / "index.html"
    index_path.write_text(build_index(registry, stats_by_id), encoding="utf-8")
    written.append(index_path)
    for s in registry["scripts"]:
        detail_stats = stats_by_id.get(s["id"]) if stats_by_id else None
        detail_path = dist / "scripts" / f"{s['id']}.html"
        detail_path.write_text(build_detail(s, detail_stats), encoding="utf-8")
        written.append(detail_path)
    return written


def main() -> int:
    registry = load_registry()
    stats_by_id = None
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        from project_discussions import GraphQLClient

        owner, sep, name = os.environ.get("GITHUB_REPOSITORY", "").partition("/")
        if not sep:
            owner, _, name = CONFIG["github_repo"].partition("/")
        stats_by_id = fetch_stats(GraphQLClient(token), owner, name, registry["scripts"])
    else:
        print(
            "警告: 未设置 GITHUB_TOKEN，跳过讨论统计拉取，页面降级渲染",
            file=sys.stderr,
        )
    written = build_site(registry, stats_by_id)
    print(f"已生成 {len(written)} 个页面 -> {CONFIG['dist_dir']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
