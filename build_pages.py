#!/usr/bin/env python3
"""从 registry 生成 Pages 站点：index 列表页 + scripts/<id>.html 详情页。"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import markdown as md
import nh3

from userscript_manager.config import CONFIG, get_install_url
from userscript_manager.discussions import fetch_discussion_comments
from userscript_manager.issue_stats import clip, fetch_stats, relative_time
from userscript_manager.escaping import escape_html
from userscript_manager.registry import load_registry
from pages_assets import (
    COMPONENT_CSS,
    DISC_JS,
    FILTER_JS,
    LIST_JS,
    PREVIEW_CSS,
    TOKEN_CSS,
)

BRAND = "油猴脚本管理器"
BRAND_SHORT = "脚本管理器"
NAV_BTN_FULL = "管理入口 · Issue #1"
NAV_BTN_SHORT = "管理"

# 首页首屏服务端渲染的卡片数，其余由 scripts.json 滚动追加
LIST_BATCH = 10
# 命令归档页每页条数（一条 = 命令 + 其执行结果）
COMMANDS_PER_PAGE = 5

PAGE_STYLE = TOKEN_CSS + COMPONENT_CSS + PREVIEW_CSS

# 外链（GitHub / 安装地址）统一新标签打开；站内页面导航保持当前标签
NEW_TAB = ' target="_blank" rel="noopener noreferrer"'


def render_markdown(text: str) -> str:
    """把文档 Markdown 渲染为安全 HTML（nh3 消毒、禁脚本与事件属性）。"""
    html = md.markdown(text or "", extensions=["fenced_code", "tables"])
    return nh3.clean(html)


def _theme_row(theme: str, label: str, suffix: str) -> str:
    return (
        f'<li><button type="button" data-theme="{theme}" aria-pressed="false">'
        f'<span class="tl-preview pv-{suffix}" aria-hidden="true">'
        '<span class="pv-bar"><i class="pv-brand"></i><i class="pv-link"></i>'
        '<i class="pv-link"></i><i class="pv-pill"></i></span>'
        '<span class="pv-hero"><i class="pv-title"></i><i class="pv-sub"></i>'
        '<span class="pv-stats"><i></i><i></i><i></i></span></span>'
        '<span class="pv-body"><i class="pv-card"></i><i class="pv-card"></i></span>'
        "</span>"
        f'<span class="tl-label"><span class="swatch swatch-{suffix}" '
        f'aria-hidden="true"></span>{label}'
        '<span class="check" aria-hidden="true">✓</span></span>'
        "</button></li>"
    )


GEAR_ICON = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83'
    "l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0"
    "v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83"
    "-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4"
    "h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83"
    "-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0"
    "v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 "
    "2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 "
    '4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'
)

THEME_MARKUP = f"""<button type="button" class="theme-rail" id="themeRail" aria-expanded="false" aria-controls="settingsDrawer" aria-label="打开设置">
{GEAR_ICON}
<span class="rail-text">设置</span>
</button>
<div class="sd-overlay" id="sdOverlay"></div>
<aside class="settings-drawer" id="settingsDrawer" aria-hidden="true" aria-label="设置面板">
<div class="sd-head">
<h3>设置</h3>
<button type="button" class="sd-close" aria-label="关闭设置">&times;</button>
</div>
<div class="sd-group">
<h4>主题</h4>
<ul class="theme-list">
{_theme_row("github-light", "清爽蓝", "a")}
{_theme_row("terminal-dark", "硬核绿", "b")}
{_theme_row("vivid-purple", "表达紫", "c")}
</ul>
</div>
<div class="sd-group">
<h4>更多功能</h4>
<p class="sd-soon">规划中</p>
</div>
</aside>
"""


THEME_JS = """<script>
(function () {
  var KEY = 'asm-theme';
  var root = document.documentElement;
  var rail = document.getElementById('themeRail');
  var drawer = document.getElementById('settingsDrawer');
  var overlay = document.getElementById('sdOverlay');
  var closeBtn = drawer.querySelector('.sd-close');
  var rows = drawer.querySelectorAll('.theme-list button[data-theme]');

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    rows.forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.theme === theme));
    });
    try {
      localStorage.setItem(KEY, theme);
    } catch (e) {
      console.warn('无法保存主题偏好', e);
    }
  }

  rows.forEach(function (b) {
    b.setAttribute('aria-pressed', String(b.dataset.theme === root.getAttribute('data-theme')));
    b.addEventListener('click', function () { applyTheme(b.dataset.theme); });
  });

  function setDrawer(open) {
    drawer.classList.toggle('open', open);
    overlay.classList.toggle('open', open);
    rail.setAttribute('aria-expanded', String(open));
    drawer.setAttribute('aria-hidden', String(!open));
    if (open) {
      document.body.style.overflow = 'hidden';
      drawer.querySelector('.theme-list button').focus();
    } else {
      document.body.style.overflow = '';
      rail.focus();
    }
  }

  rail.addEventListener('click', function () {
    setDrawer(!drawer.classList.contains('open'));
  });
  overlay.addEventListener('click', function () { setDrawer(false); });
  closeBtn.addEventListener('click', function () { setDrawer(false); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && drawer.classList.contains('open')) setDrawer(false);
  });
})();
</script>"""


def page(title: str, body_html: str, extra_js: str = "", root_href: str = "index.html") -> str:
    """包裹完整 HTML 壳：主题预载脚本、导航、主题抽屉与页脚。

    root_href 决定站内相对前缀（详情页为 ../index.html → ../），命令归档等
    二级页据此生成正确的站内链接。"""
    repo = escape_html(CONFIG["github_repo"])
    issue = CONFIG["control_issue_number"]
    rel = root_href.rsplit("/", 1)[0] + "/" if "/" in root_href else ""
    archive_href = f"{rel}commands/page-1.html"
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="github-light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>{escape_html(title)}</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22><text y=%2215%22 font-size=%2224%22 text-anchor=%22middle%22 fill=%22%233b82f6%22>📜</text></svg>">
<style>{PAGE_STYLE}</style>
<script>try {{ var t = localStorage.getItem('asm-theme'); if (t === 'github-light' || t === 'terminal-dark' || t === 'vivid-purple') {{ document.documentElement.setAttribute('data-theme', t); }} }} catch (e) {{ console.warn('无法读取主题偏好', e); }}</script>
</head>
<body>
<div class="frame">
<header class="nav">
<a class="brand" href="{root_href}"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg><span class="brand-full">{BRAND}</span><span class="brand-short">{BRAND_SHORT}</span></a>
<span class="spacer"></span>
<a class="link" href="https://github.com/{repo}/blob/master/docs/index.md"{NEW_TAB}>文档</a>
<a class="link" href="https://github.com/{repo}"{NEW_TAB}>GitHub 仓库</a>
<a class="link" href="{archive_href}">命令归档</a>
<a class="btn nav-btn" href="https://github.com/{repo}/issues/{issue}"{NEW_TAB}><span class="btn-label-full">管理入口 · Issue #{issue}</span><span class="btn-label-short">管理</span></a>
</header>
{body_html}
<footer class="foot">
<span>由 <a href="https://github.com/{repo}"{NEW_TAB}>{repo}</a> 自动生成</span>
<a href="{archive_href}">命令归档</a>
<a href="https://github.com/{repo}/issues/{issue}"{NEW_TAB}>管理入口 · Issue #{issue}</a>
<a href="https://github.com/{repo}"{NEW_TAB}>GitHub 仓库</a>
</footer>
</div>
{extra_js}
{THEME_MARKUP}
{THEME_JS}
</body>
</html>"""


ICON_COMMENT = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>'
ICON_CHECK = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>'


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
    """统一空态组件：SVG + 文案，可带链接、隐藏属性与元素 id。"""
    cls = "empty-state sm" if small else "empty-state"
    attrs = f' id="{elem_id}"' if elem_id else ""
    if hidden:
        attrs += " hidden"
    link = f"<p>{link_html}</p>" if link_html else ""
    return (f'<div class="{cls}"{attrs} role="status">{EMPTY_SVG}'
            f"<p>{text}</p>{link}</div>")


def issues_list_url() -> str:
    """带 script 标签过滤的 Issues 列表页 URL。"""
    return f"https://github.com/{CONFIG['github_repo']}/issues?q=is%3Aissue+label%3Ascript"


def discussion_href(script: dict) -> str:
    """卡片「讨论」入口：最新版本帖优先，其次脚本 Issue，最后 Issue 列表。"""
    for entry in reversed(script.get("discussions") or []):  # 账本旧→新
        url = _safe_url(entry.get("url"))
        if url:
            return url
    return _safe_url((script.get("issue") or {}).get("url")) or issues_list_url()


def issue_badges(stats) -> str:
    """渲染讨论统计徽标（回复数/已解决）；stats 缺失时为空串。"""
    if stats.is_closed:
        return (
            f'<span class="badge" data-tip="讨论已被标记为已解决">'
            f"{ICON_CHECK}已解决</span>"
            f'<span class="badge plain" data-tip="讨论回复总数">'
            f"{stats.reply_count} 条回复</span>"
        )
    if not stats.reply_count:
        return (
            '<span class="badge plain" data-tip="该讨论还没有回复">'
            "0 条回复</span>"
        )
    return (
        f'<span class="badge plain" data-tip="讨论尚未标记为已解决">'
        f"{stats.reply_count} 条回复 · 待解决</span>"
    )


def script_issue_panel(script: dict, stats) -> str:
    """卡片右栏的讨论面板：最近回复摘要或降级 GitHub 链接。"""
    url = (script.get("issue") or {}).get("url")
    if not url:
        return (f'<div class="sc-disc"><div class="disc-head">{ICON_COMMENT}讨论</div>'
                + empty_state(
                    "还没有讨论", small=True,
                    link_html=f'<a href="{escape_html(issues_list_url())}"{NEW_TAB}>'
                              "发起讨论 →</a>")
                + "</div>")
    if stats is None:
        return (f'<div class="sc-disc"><div class="disc-head">{ICON_COMMENT}讨论</div>'
                + empty_state(
                    "摘要暂不可用", small=True,
                    link_html=f'<a href="{escape_html(url)}"{NEW_TAB}>在 GitHub 打开 →</a>')
                + "</div>")
    head = f'<div class="sc-disc"><div class="disc-head">{ICON_COMMENT}讨论{issue_badges(stats)}'
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


def install_button(script: dict, label: str = "安装") -> str:
    """安装按钮：启用时为可点击链接，禁用时为无 href 的灰色禁用态。"""
    if not script.get("enabled", True):
        return (f'<span class="btn primary disabled" aria-disabled="true" '
                f'data-tip="脚本已禁用，暂不可安装">{label}</span>')
    url = escape_html(get_install_url(script["id"]))
    return f'<a class="btn primary" href="{url}"{NEW_TAB}>{label}</a>'


def type_pill(script: dict) -> str:
    """脚本类型 pill（自写/同步），带悬浮说明。"""
    if script.get("type") == "self":
        return '<span class="pill type-self" data-tip="本仓库自主编写的脚本">自写</span>'
    source = escape_html(script.get("source_type") or "")
    label = f"同步 · {source}" if source else "同步"
    return (
        '<span class="pill type-sync" data-tip="从外部来源自动同步的脚本">'
        f"{label}</span>"
    )


def version_pill(script: dict) -> str:
    """当前版本 pill；缺少版本号时返回空串。"""
    version = escape_html(script.get("version", ""))
    if not version:
        return ""
    return f'<span class="pill ver" data-tip="当前版本">v{version}</span>'


def status_badge(script: dict) -> str:
    """启用/禁用状态徽标（含悬浮说明）。"""
    if script.get("enabled", True):
        cls, title, text = "", "脚本已启用，安装链接可用", "启用"
    else:
        cls, title, text = " off", "脚本已禁用，暂不可安装", "已禁用"
    return (
        f'<span class="status{cls}" data-tip="{title}">'
        f'<span class="dot" aria-hidden="true"></span>{text}</span>'
    )


def script_card(script: dict, stats) -> str:
    """渲染列表页单个脚本卡片（标题/pill/元数据/讨论/操作）。"""
    sid = escape_html(script["id"])
    name = escape_html(script.get("name", script["id"]))
    script_type = script["type"]
    match = script.get("match") or []
    match_html = f"<code>{escape_html(match[0])}</code>" if match else "<code>—</code>"
    if script_type == "synced":
        when = (script.get("last_synced_at") or script.get("updated_at") or "")[:10]
        time_label = f"同步于 {when}" if when else "同步"
    else:
        when = (script.get("updated_at") or "")[:10]
        time_label = f"更新于 {when}" if when else ""
    desc = escape_html(script.get("description") or "")
    desc_html = f'<p class="sc-desc">{desc}</p>' if desc else ""
    disc_href = escape_html(discussion_href(script))
    panel = script_issue_panel(script, stats)
    return f"""<article class="script-card" data-type="{script_type}">
<div class="sc-main">
<div class="sc-title"><h3>{name}</h3>{type_pill(script)}{version_pill(script)}{status_badge(script)}</div>
{desc_html}
<p class="sc-meta">{match_html}{(' · ' + time_label) if time_label else ''}</p>
</div>
{panel}
<div class="sc-actions">
{install_button(script)}
<a class="btn ghost" href="scripts/{sid}.html">详情</a>
<a class="btn ghost" href="{disc_href}"{NEW_TAB}>讨论</a>
</div>
</article>"""


def build_index(registry: dict, stats_by_id: dict | None = None) -> str:
    """渲染首页：hero 统计、筛选 chips 与全部脚本卡片。"""
    degraded = stats_by_id is None
    stats_map = stats_by_id or {}
    scripts = registry["scripts"]
    cards = [(s["type"], script_card(s, stats_map.get(s["id"]))) for s in scripts]
    total = len(cards)
    shown = cards[:LIST_BATCH]
    if not shown:
        list_html = empty_state(
            "暂无脚本，请在命令面板 Issue #1 中使用 /add 添加。")
        filter_empty = ""
    else:
        list_html = "\n".join(html for _type, html in shown)
        filter_empty = empty_state("没有符合筛选条件的脚本",
                                   elem_id="filter-empty", hidden=True)
    # 首屏之后的卡片由 scripts.json 懒加载（滚动到底或点「加载更多」）
    if total > LIST_BATCH:
        tail = ('<div id="listSentinel" aria-hidden="true"></div>'
                '<button class="btn ghost" type="button" id="loadMore">'
                "加载更多</button>"
                f'<p class="list-end" id="listEnd" hidden>已全部加载（共 {total} 个）</p>')
    else:
        tail = ""
    if degraded:
        replies_html = answered_html = "—"
    else:
        replies_html = str(sum(st.reply_count for st in stats_map.values()))
        answered_html = str(sum(1 for st in stats_map.values() if st.is_closed))
    body = f"""<section class="hero">
<h1>{BRAND}</h1>
<p class="sub">基于 GitHub Issues 的全自动脚本管理：在命令面板里用 <code>/add</code>、<code>/up</code> 管理脚本，每个脚本拥有独立讨论区，安装即可用。</p>
<div class="stats">
<div class="stat" data-tip="注册表中的脚本总数"><b>{len(scripts)}</b><span>脚本总数</span></div>
<div class="stat" data-tip="全部脚本讨论的回复总数"><b>{replies_html}</b><span>讨论回复</span></div>
<div class="stat" data-tip="已被标记为已解决的讨论数"><b>{answered_html}</b><span>已解决反馈</span></div>
</div>
</section>
<main>
<h2 class="sec">脚本列表
<span class="filters">
<button class="chip active" type="button" data-filter="all">全部</button>
<button class="chip" type="button" data-filter="self">自写</button>
        <button class="chip" type="button" data-filter="synced">同步</button>
</span>
</h2>
<div id="scriptList" data-batch="{LIST_BATCH}" data-total="{total}">
{list_html}
{tail}
</div>
{filter_empty}
</main>"""
    extra = FILTER_JS + (LIST_JS if total > LIST_BATCH else "")
    return page(BRAND, body, extra_js=extra)


def build_scripts_json(registry: dict, stats_by_id: dict | None = None) -> str:
    """全量脚本卡片 → scripts.json：[{type, html}]，供首页滚动时追加渲染。"""
    stats_map = stats_by_id or {}
    items = [{"type": s["type"], "html": script_card(s, stats_map.get(s["id"]))}
             for s in registry["scripts"]]
    return json.dumps(items, ensure_ascii=False)


def detail_issue_panel(script: dict, stats) -> str:
    """详情页讨论区面板：徽标、最近回复与跳转链接。"""
    url = (script.get("issue") or {}).get("url")
    if not url:
        return ('<section class="d-disc"><div class="disc-head">'
                f'{ICON_COMMENT}讨论</div>'
                + empty_state(
                    "还没有讨论", small=True,
                    link_html=f'<a href="{escape_html(issues_list_url())}"{NEW_TAB}>'
                              "发起讨论 →</a>")
                + "</section>")
    if stats is None:
        return ('<section class="d-disc"><div class="disc-head">'
                f'{ICON_COMMENT}讨论</div>'
                + empty_state(
                    "摘要暂不可用", small=True,
                    link_html=f'<a href="{escape_html(url)}"{NEW_TAB}>在 GitHub 打开 →</a>')
                + "</section>")
    head = (
        f'<div class="disc-head">{ICON_COMMENT}讨论{issue_badges(stats)}'
        f'<span class="grow"></span>'
        f'<a href="{escape_html(url)}"{NEW_TAB}>在 GitHub 打开 →</a></div>'
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
        comments = empty_state("还没有回复", small=True)
    return f'<section class="d-disc">{head}{comments}</section>'


def fetch_discussion_posts(client, scripts: list[dict],
                           problems: list[str] | None = None
                           ) -> dict[str, list[dict]] | None:
    """构建时拉取各版本帖评论，返回 {sid: [post, ...]}，每组按版本新→旧排列。

    post 结构：{version, number, url, is_answered, reply_count, comments}，
    comments 是渲染与嵌入共用的展示载荷（相对时间已算好、正文已折叠）。
    无版本帖的脚本不占位也不发请求；整体失败返回 None（详情页回退 Issue 评论）。
    problems 非 None 时逐条记录失败原因，供 build-warnings.txt 暴露到部署现场。"""
    note = problems.append if problems is not None else (lambda _msg: None)
    targets = [(s["id"], s.get("discussions") or []) for s in scripts]
    targets = [(sid, ledger) for sid, ledger in targets if ledger]
    if not targets:
        return {}
    out: dict[str, list[dict]] = {}
    try:
        for sid, ledger in targets:
            posts = []
            for entry in reversed(ledger):  # 账本旧→新，倒序后最新版本在前
                node_id = entry.get("node_id")
                if not node_id:
                    note(f"{sid} v{entry.get('version') or '-'} 缺少 node_id，跳过")
                    continue
                data = fetch_discussion_comments(client, node_id)
                if not data:
                    # 版本帖已删除或令牌无权读取：跳过该版本，不阻断其余
                    note(f"{sid} v{entry.get('version') or '-'} (#{entry.get('number')}) "
                         "拉取为空：discussion 返回 null（节点不存在或无读取权限）")
                    continue
                payload = _comment_payload(data.get("comments") or [])
                posts.append({
                    "version": entry.get("version") or "",
                    "number": entry.get("number") or 0,
                    "url": data.get("url") or entry.get("url") or "",
                    "is_answered": bool(data.get("is_answered")),
                    "reply_count": _count_replies(payload),
                    "comments": payload,
                })
            if posts:
                out[sid] = posts
    except Exception as e:
        note(f"版本帖评论整体拉取失败，详情页回退 Issue 评论渲染：{e}")
        print(f"警告: 版本帖评论拉取失败，详情页回退 Issue 评论渲染：{e}",
              file=sys.stderr)
        return None
    return out


def _comment_payload(comments: list[dict]) -> list[dict]:
    """把 discussion 评论规范化为展示结构（递归处理嵌套回复）。"""
    out = []
    for c in comments or []:
        out.append({
            "author": c.get("author") or "未知用户",
            "is_owner": bool(c.get("is_owner")),
            "is_answer": bool(c.get("is_answer")),
            "time": relative_time(c.get("created_at") or ""),
            "body": clip(c.get("body") or "", 400),
            "replies": _comment_payload(c.get("replies") or []),
        })
    return out


def _count_replies(comments: list[dict]) -> int:
    """载荷内评论总数（含嵌套回复），用作徽标的回复计数。"""
    return sum(1 + _count_replies(c.get("replies") or []) for c in comments)


def _safe_url(url) -> str:
    """仅放行 http(s) 外链，其余返回空串（拒绝 javascript: 等协议）。"""
    url = url or ""
    return url if url.startswith(("https://", "http://")) else ""


def _comment_html(c: dict) -> str:
    """单条评论（含嵌套回复）：作者 + 已解决标记 + 相对时间 + 正文。"""
    author = escape_html(c.get("author") or "未知用户")
    owner = " owner" if c.get("is_owner") else ""
    answer = '<span class="answer-tag">✓ 已解决</span>' if c.get("is_answer") else ""
    replies = c.get("replies") or []
    replies_html = (
        '<div class="cmt-replies">'
        + "".join(_comment_html(r) for r in replies)
        + "</div>"
        if replies else ""
    )
    return (f'<div class="cmt{owner}">'
            f'<span class="cmt-who"><b>{author}</b>{answer}</span>'
            f'<time>{escape_html(c.get("time") or "—")}</time>'
            f'<p>{escape_html(c.get("body") or "")}</p>{replies_html}</div>')


def post_badges(post: dict) -> str:
    """版本帖讨论徽标：已解决 / 回复数 · 待解决（与 Issue 徽标同一套视觉）。"""
    count = int(post.get("reply_count") or 0)
    if post.get("is_answered"):
        return (
            f'<span class="badge" data-tip="该版本帖已被标记为已解决">'
            f"{ICON_CHECK}已解决</span>"
            f'<span class="badge plain" data-tip="讨论回复总数">'
            f"{count} 条回复</span>"
        )
    if not count:
        return ('<span class="badge plain" data-tip="该版本帖还没有评论">'
                "0 条回复</span>")
    return (
        f'<span class="badge plain" data-tip="讨论尚未标记为已解决">'
        f"{count} 条回复 · 待解决</span>"
    )


def _ver_label(post: dict, index: int) -> str:
    """版本下拉文案：首项（账本最新版本）追加「（最新）」。"""
    label = f"v{post['version']}" if post.get("version") else "未知版本"
    return f"{label}（最新）" if index == 0 else label


def _disc_payload(posts: list[dict]) -> str:
    """版本帖载荷 → 可安全内嵌的 JSON 文本（转义 & < >，防 </script> 逃逸）。

    url 在此统一过一遍协议白名单：载荷里只可能携带 http(s) 链接。"""
    safe = [{**p, "url": _safe_url(p.get("url"))} for p in posts]
    raw = json.dumps(safe, ensure_ascii=False)
    return raw.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def detail_version_panel(posts: list[dict], fallback_html: str) -> str:
    """版本帖评论面板：版本下拉切换各帖评论与跳转链接。

    posts 为空时原样返回 fallback_html（回退 Issue 评论面板）。"""
    if not posts:
        return fallback_html
    first = posts[0]
    items = []
    for i, p in enumerate(posts):
        selected = "true" if i == 0 else "false"
        cls = "disc-ver-item active" if i == 0 else "disc-ver-item"
        num = f"#{p['number']}" if p.get("number") else ""
        num_html = f'<span class="num">{escape_html(num)}</span>' if num else ""
        items.append(
            f'<button type="button" class="{cls}" role="option" '
            f'aria-selected="{selected}" data-i="{i}">'
            f"{escape_html(_ver_label(p, i))}{num_html}</button>"
        )
    url = _safe_url(first.get("url"))
    link = (
        f'<a id="discLink" href="{escape_html(url)}"{NEW_TAB}>'
        "在 GitHub 打开本帖 →</a>"
    ) if url else ""
    head = (
        f'<div class="disc-head">{ICON_COMMENT}讨论'
        f'<span class="disc-badges" id="discBadges">{post_badges(first)}</span>'
        f'<span class="grow"></span>{link}'
        '<div class="disc-ver">'
        '<button type="button" class="disc-ver-btn" id="discVerBtn" '
        'aria-haspopup="listbox" aria-expanded="false" aria-label="切换讨论版本">'
        f'<span id="discVerLabel">{escape_html(_ver_label(first, 0))}</span>'
        '<svg class="chev" width="12" height="12" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<polyline points="6 9 12 15 18 9"/></svg></button>'
        '<div class="disc-ver-menu" id="discVerMenu" role="listbox" '
        'aria-label="选择版本帖" hidden>'
        + "".join(items) +
        "</div></div></div>"
    )
    comments = (
        empty_state("该版本帖还没有评论", small=True)
        if not first.get("comments")
        else "".join(_comment_html(c) for c in first["comments"])
    )
    return (
        f'<section class="d-disc">{head}'
        f'<div id="discComments">{comments}</div>'
        f'<template id="discEmpty">'
        f'{empty_state("该版本帖还没有评论", small=True)}</template>'
        f'<script type="application/json" id="discData">{_disc_payload(posts)}</script>'
        "</section>"
    )


def build_detail(script: dict, stats=None,
                 disc_posts: list[dict] | None = None) -> str:
    """渲染脚本详情页：元数据、文档、更新历史与讨论面板。

    disc_posts 为该脚本各版本帖的拉取结果（新→旧）；为空回退 Issue 评论面板。"""
    name = escape_html(script.get("name", script["id"]))
    author = escape_html(script.get("author", "") or "-")
    description = escape_html(script.get("description", ""))
    matches = " ".join(f"<code>{escape_html(m)}</code>" for m in script.get("match") or [])

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
        changelog_html = empty_state("暂无更新记录。")

    body = f"""<main>
<section class="detail-card">
<a class="back" href="../index.html">← 返回列表</a>
<div class="d-head">
<div>
<div class="d-pills">{type_pill(script)}{version_pill(script)}{status_badge(script)}</div>
<h3>{name}</h3>
</div>
{install_button(script, "安装脚本")}
</div>
<div class="d-meta"><span><i>作者</i>{author}</span>{when_html}<span><i>匹配规则</i>{matches or "-"}</span></div>
{desc_html}
<section class="d-doc">
{render_markdown(script.get("documentation") or "_暂无文档_")}
</section>
{detail_version_panel(disc_posts or [], detail_issue_panel(script, stats))}
<section class="d-doc">
<h2>更新历史</h2>
{changelog_html}
</section>
</section>
</main>"""
    return page(script.get("name", script["id"]), body,
                extra_js=DISC_JS if disc_posts else "",
                root_href="../index.html")


def load_command_archive() -> list[dict]:
    """读命令面板归档账本；缺失或损坏返回空列表（不阻断建站）。"""
    path = Path(CONFIG["archive_file"])
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    commands = data.get("commands") if isinstance(data, dict) else None
    return commands if isinstance(commands, list) else []


def _cmd_time(iso: str) -> str:
    """归档时间戳 → `YYYY-MM-DD HH:MM`；空值/非法值原样或占位。"""
    if not iso:
        return "—"
    try:
        moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    return moment.strftime("%Y-%m-%d %H:%M")


def command_entry_html(entry: dict, serial: int) -> str:
    """归档条目 → 命令 + 其执行结果的展示块。"""
    author = escape_html(entry.get("author") or "未知用户")
    when = escape_html(_cmd_time(entry.get("created_at") or ""))
    command = escape_html(entry.get("command") or "")
    results = entry.get("results") or []
    if results:
        res_html = "".join(
            f'<div class="cmd-res"><div class="cmd-line">'
            f"<b>{escape_html(r.get('author') or '未知用户')}</b>"
            f"<time>{escape_html(_cmd_time(r.get('created_at') or ''))}</time>"
            f"</div><pre>{escape_html(r.get('body') or '')}</pre></div>"
            for r in results
        )
    else:
        res_html = '<p class="cmd-none">没有执行结果</p>'
    return (f'<article class="cmd-item">'
            f'<div class="cmd-line"><b>{author}</b><time>{when}</time>'
            f'<span class="cmd-no">#{serial}</span></div>'
            f"<pre>{command}</pre>{res_html}</article>")


def _pager(current: int, pages: int) -> str:
    """静态分页控件：上一页 / 当前页码 / 下一页。"""
    if pages <= 1:
        return ""
    parts = []
    if current > 1:
        parts.append(f'<a class="btn ghost" href="page-{current - 1}.html">上一页</a>')
    parts.append(f'<span class="pager-now">第 {current} / {pages} 页</span>')
    if current < pages:
        parts.append(f'<a class="btn ghost" href="page-{current + 1}.html">下一页</a>')
    return f'<nav class="pager" aria-label="分页">{" ".join(parts)}</nav>'


def build_command_pages() -> list[Path]:
    """生成 dist/commands/page-N.html（每页 COMMANDS_PER_PAGE 条）与跳转页。

    归档账本为旧→新，展示按新→旧；同时清理页数变少后的陈旧分页文件。"""
    dist = Path(CONFIG["dist_dir"])
    out_dir = dist / "commands"
    out_dir.mkdir(parents=True, exist_ok=True)
    ordered = list(reversed(load_command_archive()))
    chunks = [ordered[i:i + COMMANDS_PER_PAGE]
              for i in range(0, len(ordered), COMMANDS_PER_PAGE)] or [[]]
    written = []
    issue_url = (f"https://github.com/{CONFIG['github_repo']}"
                 f"/issues/{CONFIG['control_issue_number']}")
    for index, chunk in enumerate(chunks, start=1):
        if chunk:
            entries = "".join(command_entry_html(entry, n)
                              for n, entry in enumerate(chunk, start=1))
        else:
            entries = empty_state(
                "还没有归档的命令记录。",
                link_html=f'<a href="{escape_html(issue_url)}"{NEW_TAB}>'
                          "去命令面板发一条命令 →</a>")
        total_note = (f"<p class=\"cmd-sub\">共 {len(ordered)} 条历史命令，"
                      "清理自命令面板 Issue #1，按时间新→旧排列，"
                      f"每页 {COMMANDS_PER_PAGE} 条。</p>"
                      if ordered else
                      "<p class=\"cmd-sub\">命令面板中更早的「命令 + 执行结果」"
                      "清理后会自动归档到这里。</p>")
        body = f"""<main>
<section class="detail-card">
<h3 class="cmd-title">命令归档</h3>
{total_note}
{entries}
{_pager(index, len(chunks))}
</section>
</main>"""
        page_path = out_dir / f"page-{index}.html"
        page_path.write_text(
            page(f"命令归档 · 第 {index} 页", body, root_href="../index.html"),
            encoding="utf-8")
        written.append(page_path)

    keep = {f"page-{i}.html" for i in range(1, len(chunks) + 1)}
    for stale in out_dir.glob("page-*.html"):
        if stale.name not in keep:
            stale.unlink()

    redirect = out_dir / "index.html"
    redirect.write_text(
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta http-equiv=\"refresh\" content=\"0; url=page-1.html\">\n"
        "<title>命令归档</title>\n</head>\n<body>\n"
        '<p><a href="page-1.html">进入命令归档第 1 页 →</a></p>\n'
        "</body>\n</html>\n",
        encoding="utf-8")
    written.append(redirect)
    return written


def build_site(registry: dict, stats_by_id: dict | None = None,
               disc_map: dict | None = None) -> list[Path]:
    """生成列表页与各脚本详情页，并清理已删除脚本遗留的陈旧详情页。

    disc_map 为 fetch_discussion_posts 的结果：{sid: [post, ...]} 或 None（降级）。"""
    dist = Path(CONFIG["dist_dir"])
    (dist / "scripts").mkdir(parents=True, exist_ok=True)
    written = []
    index_path = dist / "index.html"
    index_path.write_text(build_index(registry, stats_by_id), encoding="utf-8")
    written.append(index_path)
    json_path = dist / "scripts.json"
    json_path.write_text(build_scripts_json(registry, stats_by_id), encoding="utf-8")
    written.append(json_path)
    keep = set()
    for s in registry["scripts"]:
        detail_stats = stats_by_id.get(s["id"]) if stats_by_id else None
        detail_posts = disc_map.get(s["id"]) if disc_map else None
        detail_path = dist / "scripts" / f"{s['id']}.html"
        detail_path.write_text(build_detail(s, detail_stats, detail_posts),
                               encoding="utf-8")
        written.append(detail_path)
        keep.add(detail_path.name)
    for stale in (dist / "scripts").glob("*.html"):
        if stale.name not in keep:
            stale.unlink()
    written.extend(build_command_pages())
    return written


def main() -> int:
    """构建入口：拉取讨论统计与版本帖评论（无 token 降级）并生成全部页面。

    拉取失败的原因会落到 dist/build-warnings.txt（部署后可在站点根目录看到）。"""
    registry = load_registry()
    stats_by_id = None
    disc_map = None
    problems: list[str] = []
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        from project_issues import GraphQLClient

        owner, sep, name = os.environ.get("GITHUB_REPOSITORY", "").partition("/")
        if not sep:
            owner, _, name = CONFIG["github_repo"].partition("/")
        client = GraphQLClient(token)
        stats_by_id = fetch_stats(client, owner, name, registry["scripts"])
        if stats_by_id is None:
            problems.append("讨论统计（Issue）拉取失败，首页与详情页降级渲染")
        disc_map = fetch_discussion_posts(client, registry["scripts"], problems)
    else:
        print(
            "警告: 未设置 GITHUB_TOKEN，跳过讨论统计拉取，页面降级渲染",
            file=sys.stderr,
        )
    written = build_site(registry, stats_by_id, disc_map)
    warnings = Path(CONFIG["dist_dir"]) / "build-warnings.txt"
    if problems:
        warnings.write_text("\n".join(problems) + "\n", encoding="utf-8")
        print("\n".join(f"警告: {p}" for p in problems), file=sys.stderr)
    elif warnings.exists():
        warnings.unlink()
    print(f"已生成 {len(written)} 个页面 -> {CONFIG['dist_dir']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())