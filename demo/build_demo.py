#!/usr/bin/env python3
"""设计确认用静态 Demo 生成器：详情页（含版本帖下拉评论区）、Issue 样式、版本帖样式。

仅用于视觉与交互确认，不属于生产代码。运行：python demo/build_demo.py
生成的 demo/*.html 可直接在浏览器打开。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build_pages as bp  # noqa: E402

DEMO_DIR = ROOT / "demo"
REPO = "ACG-Q/userscript-manager"
ISSUE_URL = f"https://github.com/{REPO}/issues/2"
DISC_LIST_URL = f"https://github.com/{REPO}/discussions"

SAMPLE = {
    "id": "d1620a7a-ae3b-4817-ae2b-016f48cf81a1",
    "type": "self",
    "name": "我的去广告脚本",
    "version": "1.0.1",
    "description": "移除百度首页和搜索结果广告，支持信息流与推广链接过滤",
    "author": "ACG-Q",
    "namespace": "https://github.com/ACG-Q/userscript-manager",
    "match": ["*://www.baidu.com/*"],
    "grant": ["none"],
    "enabled": True,
    "created_at": "2026-08-20T14:18:57Z",
    "updated_at": "2026-10-02T02:41:47Z",
    "source_url": None,
    "source_type": None,
    "last_synced_at": None,
    "sync_enabled": False,
    "documentation": "# 我的去广告脚本\n\n移除百度首页和搜索结果广告，支持信息流与推广链接过滤。",
    "changelog": [
        {"version": "1.0.1", "date": "2026-10-01", "note": "手动更新"},
        {"version": "1.0.0", "date": "2026-08-20", "note": "初始版本"},
    ],
    "issue": {"number": 2, "node_id": "I_kwDOU4CvsM8AAAABUhVjEg", "url": ISSUE_URL},
    "discussions": [
        {
            "version": "1.0.0",
            "number": 7,
            "node_id": "D_demo0007",
            "url": f"https://github.com/{REPO}/discussions/7",
            "created_at": "2026-08-20",
        },
        {
            "version": "1.0.1",
            "number": 9,
            "node_id": "D_demo0009",
            "url": f"https://github.com/{REPO}/discussions/9",
            "created_at": "2026-10-01",
        },
    ],
    "deleted": False,
}

COMMENTS_101 = [
    {
        "author": "user123",
        "is_owner": False,
        "time": "2 天前",
        "html": "<p>首页右侧广告没了，但<strong>搜索结果页底部</strong>还有推广链接卡片，是还没适配吗？</p>",
        "replies": [
            {
                "author": "ACG-Q",
                "is_owner": True,
                "time": "2 天前",
                "answer": True,
                "html": "<p>是的，v1.0.1 已修复该问题。升级到最新版本刷新页面即可生效。</p>",
                "replies": [],
            }
        ],
    },
    {
        "author": "reader9527",
        "is_owner": False,
        "time": "1 天前",
        "html": "<p>能不能加个快捷键临时开关去广告？有时要对比原页面。</p>",
        "replies": [],
    },
]

DISC_DATA = [
    {
        "version": "1.0.1",
        "number": 9,
        "url": SAMPLE["discussions"][1]["url"],
        "is_answered": True,
        "comments": COMMENTS_101,
    },
    {
        "version": "1.0.0",
        "number": 7,
        "url": SAMPLE["discussions"][0]["url"],
        "is_answered": False,
        "comments": [],
    },
]

NEW_CSS = """
.disc-ver { position: relative; }
.disc-ver-btn { display: inline-flex; align-items: center; gap: 5px; border: none;
  background: transparent; color: var(--brand); font: inherit; font-size: 13.5px;
  font-weight: 600; cursor: pointer; padding: 6px 4px; border-radius: 8px; }
.disc-ver-btn:hover { color: var(--brand-hover); }
.disc-ver-btn .chev { transition: transform .15s ease; }
.disc-ver-btn[aria-expanded="true"] .chev { transform: rotate(180deg); }
.disc-ver-menu { position: absolute; right: 0; top: calc(100% + 8px); z-index: 30;
  min-width: 200px; padding: 6px; border-radius: 12px; background: var(--bg);
  box-shadow: 0 12px 32px rgba(0, 0, 0, .16), 0 2px 8px rgba(0, 0, 0, .06); }
.disc-ver-menu[hidden] { display: none; }
.disc-ver-item { display: flex; width: 100%; align-items: center; gap: 8px;
  border: none; background: transparent; font: inherit; font-size: 13.5px;
  color: var(--text); padding: 9px 10px; border-radius: 8px; cursor: pointer;
  text-align: left; }
.disc-ver-item:hover { background: var(--neutral-bg); }
.disc-ver-item.active { color: var(--brand); font-weight: 600; }
.disc-ver-item .num { margin-left: auto; font-size: 12px; color: var(--text-muted);
  font-weight: 400; }
.disc-ver-foot { display: block; margin-top: 4px; padding: 9px 10px 7px;
  font-size: 12.5px; font-weight: 600; border-top: 1px solid var(--border);
  border-radius: 0 0 8px 8px; }
.cmt-item { padding: 12px 0 10px; border-top: 1px solid var(--border); }
.cmt-meta { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.cmt-avatar { width: 26px; height: 26px; border-radius: 50%; flex: none;
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; font-size: 13px; font-weight: 600; }
.cmt-meta b { color: var(--text); }
.cmt-meta time { color: var(--text-muted); font-size: 12px; }
.cmt-body { margin: 6px 0 0 34px; font-size: 14px; line-height: 1.6; }
.cmt-body p { margin: 0 0 8px; }
.cmt-body p:last-child { margin-bottom: 0; }
.cmt-body code { padding: 1px 6px; border-radius: 5px; font-size: 13px;
  background: var(--bg-subtle); border: 1px solid var(--border); }
.cmt-replies { margin: 4px 0 0 34px; border-left: 2px solid var(--border);
  padding-left: 12px; }
.cmt-replies .cmt-item:first-child { border-top: none; padding-top: 8px; }
.disc-empty { text-align: center; padding: 26px 12px 16px;
  border-top: 1px solid var(--border); color: var(--text-muted); font-size: 13.5px; }
.disc-empty p { margin: 0 0 6px; }
"""

NEW_JS = """
(function () {
  var data = JSON.parse(document.getElementById('discData').textContent);
  var btn = document.getElementById('discVerBtn');
  var label = document.getElementById('discVerLabel');
  var menu = document.getElementById('discVerMenu');
  var foot = document.getElementById('discLink');
  var box = document.getElementById('discComments');
  var items = menu.querySelectorAll('.disc-ver-item');
  var colors = ['#0969da', '#1a7f37', '#bc4c00', '#8250df', '#cf222e', '#bf3989'];
  var current = 0;
  function color(name) {
    var n = 0;
    for (var i = 0; i < name.length; i++) { n = (n + name.charCodeAt(i)) % 997; }
    return colors[n % colors.length];
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function setOpen(open) {
    menu.hidden = !open;
    btn.setAttribute('aria-expanded', String(open));
  }
  function cmtHtml(c) {
    var answer = c.answer ? '<span class="badge">✓ 已标记为答案</span>' : '';
    var head =
      '<div class="cmt-meta"><span class="cmt-avatar" style="background:' +
      color(c.author) + '">' + esc(c.author.charAt(0).toUpperCase()) + '</span>' +
      '<b>' + esc(c.author) + (c.is_owner ? ' <span class="badge plain">作者</span>' : '') +
      '</b>' + answer + '<time>' + esc(c.time) + '</time></div>';
    var replies = '';
    if (c.replies && c.replies.length) {
      replies = '<div class="cmt-replies">' +
        c.replies.map(cmtHtml).join('') + '</div>';
    }
    return '<div class="cmt-item">' + head +
      '<div class="cmt-body">' + c.html + '</div></div>' + replies;
  }
  function render() {
    var d = data[current];
    foot.href = d.url;
    if (!d.comments.length) {
      box.innerHTML =
        '<div class="disc-empty"><p>该版本帖还没有评论</p>' +
        '<a href="' + d.url + '" target="_blank" rel="noopener noreferrer">' +
        '去帖子留言 →</a></div>';
      return;
    }
    box.innerHTML = d.comments.map(cmtHtml).join('');
  }
  function select(i) {
    current = i;
    label.textContent = 'v' + data[i].version + (i === 0 ? '（最新）' : '');
    items.forEach(function (el, j) { el.classList.toggle('active', i === j); });
    render();
  }
  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    setOpen(menu.hidden);
  });
  items.forEach(function (el) {
    el.addEventListener('click', function () {
      select(Number(el.dataset.i));
      setOpen(false);
    });
  });
  document.addEventListener('click', function (e) {
    if (!menu.hidden && !menu.contains(e.target)) { setOpen(false); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { setOpen(false); }
  });
  select(0);
})();
"""


def new_panel(script, stats):
    """详情页新版讨论面板原型：头部版本浮层菜单 + 构建期烘焙的评论。"""
    latest = DISC_DATA[0]
    items = []
    for i, d in enumerate(DISC_DATA):
        mark = "（最新）" if i == 0 else ""
        active = " active" if i == 0 else ""
        items.append(
            f'<button type="button" class="disc-ver-item{active}" data-i="{i}" '
            f'role="option">v{d["version"]}{mark}'
            f'<span class="num">#{d["number"]}</span></button>'
        )
    total = sum(len(d["comments"]) for d in DISC_DATA)
    if latest["is_answered"]:
        badge = '<span class="badge">✓ 已解决</span>'
    else:
        badge = f'<span class="badge plain">{total} 条评论 · 待解决</span>'
    payload = json.dumps(DISC_DATA, ensure_ascii=False)
    chevron = (
        '<svg class="chev" width="12" height="12" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<polyline points="6 9 12 15 18 9"/></svg>'
    )
    return f"""<section class="d-disc">
<div class="disc-head">{bp.ICON_COMMENT}讨论{badge}<span class="grow"></span>
<div class="disc-ver">
<button type="button" class="disc-ver-btn" id="discVerBtn" aria-haspopup="listbox"
aria-expanded="false"><span id="discVerLabel">v{latest['version']}（最新）</span>{chevron}</button>
<div class="disc-ver-menu" id="discVerMenu" role="listbox" aria-label="选择版本帖" hidden>
{''.join(items)}
<a class="disc-ver-foot" id="discLink" href="{latest['url']}">在 GitHub 打开本帖 →</a>
</div>
</div>
<a href="{DISC_LIST_URL}">全部版本帖 →</a></div>
<div id="discComments"></div>
<script type="application/json" id="discData">{payload}</script>
<style>{NEW_CSS}</style>
<script>{NEW_JS}</script>
</section>"""


_ANCHOR_RE = re.compile(r"<a\s+([^>]*href=\"https://[^\"]+\"[^>]*)>")


def open_external_links(html: str) -> str:
    """外链锚点统一新标签页打开（demo 范围；实现阶段同步进 build_pages）。"""
    def repl(m: re.Match) -> str:
        attrs = m.group(1)
        if "target=" in attrs:
            return m.group(0)
        return f'<a target="_blank" rel="noopener noreferrer" {attrs}>'

    return _ANCHOR_RE.sub(repl, html)


def gh_shell(title, body, state_html=""):
    """仿 GitHub 页面外壳（ Discussions / Issues 通用简化版）。"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI",
  Helvetica, Arial, sans-serif, "Apple Color Emoji"; color: #1f2328; background: #ffffff; }}
a {{ color: #0969da; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.gh-top {{ background: #f6f8fa; border-bottom: 1px solid #d1d9e0; }}
.gh-top-in {{ max-width: 1012px; margin: 0 auto; padding: 14px 24px;
  display: flex; align-items: center; gap: 8px; font-size: 14px; }}
.gh-top-in .sep {{ color: #59636e; }}
.gh-count {{ border: 1px solid #d1d9e0; border-radius: 999px; padding: 0 8px;
  font-size: 12px; color: #59636e; background: #ffffff; }}
.gh-wrap {{ max-width: 1012px; margin: 0 auto; padding: 24px; }}
.gh-title {{ font-size: 32px; font-weight: 400; line-height: 1.25; margin: 0 0 12px; }}
.gh-sub {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  margin-bottom: 16px; font-size: 12px; color: #59636e; }}
.gh-state {{ display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px;
  border-radius: 999px; font-weight: 600; font-size: 12px; }}
.gh-state.open {{ background: #1a7f37; color: #ffffff; }}
.gh-state.done {{ background: #8250df; color: #ffffff; }}
.gh-label {{ padding: 2px 10px; border-radius: 999px; font-weight: 600; font-size: 12px;
  color: #0969da; background: #ddf4ff; border: 1px solid #54aeff66; }}
.gh-cat {{ padding: 2px 10px; border-radius: 999px; font-weight: 600; font-size: 12px;
  color: #8250df; background: #fbefff; border: 1px solid #d8b9ff; }}
.gh-card {{ border: 1px solid #d1d9e0; border-radius: 6px; margin-bottom: 16px; }}
.gh-card-head {{ padding: 10px 16px; background: #f6f8fa;
  border-bottom: 1px solid #d1d9e0; border-radius: 6px 6px 0 0;
  font-size: 12px; color: #59636e; display: flex; align-items: center; gap: 8px; }}
.gh-card-head b {{ color: #1f2328; }}
.gh-avatar {{ width: 24px; height: 24px; border-radius: 50%; background: #bc4c00;
  color: #fff; display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; flex: none; }}
.gh-content {{ padding: 16px; font-size: 14px; line-height: 1.6; }}
.gh-content h2 {{ font-size: 16px; margin: 16px 0 8px; }}
.gh-content h2:first-child {{ margin-top: 0; }}
.gh-content p {{ margin: 0 0 10px; }}
.gh-content code {{ padding: 1px 6px; border-radius: 5px; font-size: 90%;
  background: #f6f8fa; border: 1px solid #d1d9e0; }}
.gh-content table {{ border-collapse: collapse; width: auto; margin: 4px 0 12px;
  font-size: 13.5px; }}
.gh-content th, .gh-content td {{ border: 1px solid #d1d9e0; padding: 6px 13px;
  text-align: left; }}
.gh-content th {{ background: #f6f8fa; font-weight: 600; }}
.gh-content blockquote {{ margin: 10px 0; padding: 2px 14px;
  border-left: 3px solid #d1d9e0; color: #59636e; }}
.gh-answer {{ display: inline-flex; align-items: center; gap: 5px; padding: 2px 10px;
  border-radius: 999px; font-weight: 600; font-size: 12px;
  color: #1a7f37; background: #dafbe1; border: 1px solid #4ac26b66; }}
.gh-comment {{ padding: 16px 0 0; margin-top: 16px; border-top: 1px solid #d1d9e0; }}
.gh-comment:first-child {{ border-top: none; margin-top: 0; padding-top: 0; }}
.gh-comment .c-head {{ display: flex; align-items: center; gap: 8px; font-size: 13px; }}
.gh-comment .c-body {{ margin: 8px 0 0 32px; }}
.gh-comment .c-replies {{ margin: 8px 0 0 32px; padding-left: 16px;
  border-left: 2px solid #d1d9e0; }}
.gh-note {{ font-size: 12px; color: #59636e; margin: 12px 0 0; }}
.gh-back {{ font-size: 13px; display: inline-block; margin-bottom: 14px; }}
</style>
</head>
<body>
<header class="gh-top"><div class="gh-top-in">
<b>{REPO}</b><span class="sep">/</span>{state_html}
</div></header>
<main class="gh-wrap">
<a class="gh-back" href="index.html">← 返回 Demo 导航</a>
{body}
</main>
</body>
</html>
"""


def build_issue_html():
    """Issue 正文样式 demo：活字段表 + 版本帖索引（对账器维护）。"""
    install = f"https://acg-q.github.io/userscript-manager/scripts/{SAMPLE['id']}.user.js"
    rows = [
        ("状态", "✅ 已启用"),
        ("最新版本", "1.0.1"),
        ("名称", "我的去广告脚本"),
        ("安装链接", f'<a href="{install}">安装脚本</a>'),
        ("来源", "自写（本仓库）"),
    ]
    table = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows
    )
    idx_rows = "".join(
        f'<tr><td>v{d["version"]}</td><td>{d["created_at"]}</td>'
        f'<td><a href="{d["url"]}">讨论 #{d["number"]} →</a></td></tr>'
        for d in reversed(SAMPLE["discussions"])
    )
    body = f"""<h1 class="gh-title">📝 我的去广告脚本</h1>
<div class="gh-sub">
<span class="gh-state open">● Open</span>
<span class="gh-label">script</span>
<span>#2 · 由 ACG-Q 创建于 2026-08-20 · 对账器自动维护</span>
</div>
<div class="gh-card">
<div class="gh-card-head"><span class="gh-avatar">A</span><b>ACG-Q</b>
<span>commented on 2026-08-20</span></div>
<div class="gh-content">
<!-- script-id: d1620a7a-ae3b-4817-ae2b-016f48cf81a1 -->
<h2>我的去广告脚本</h2>
<table>
<tr><th>字段</th><th>值</th></tr>
{table}
</table>
<h2>版本讨论帖</h2>
<p>每个版本一个讨论帖，按版本参与讨论：</p>
<table>
<tr><th>版本</th><th>日期</th><th>讨论</th></tr>
{idx_rows}
</table>
<p class="gh-note">字段与索引由对账器每轮刷新；状态、版本等实时值以本页为准，
完整信息与历史讨论见对应版本帖。</p>
</div>
</div>
<div class="gh-card">
<div class="gh-card-head"><span class="gh-avatar">A</span><b>ACG-Q</b>
<span>commented · 命令执行结果留在本面板</span></div>
<div class="gh-content">
<p>✅ <code>/sync</code> 完成：已是最新版本 v1.0.1。</p>
</div>
</div>"""
    return gh_shell("Issue #2 · 我的去广告脚本 (Demo)", body)


def build_discussion_html():
    """版本帖样式 demo：全量信息快照 + 评论（含已标记为答案）。"""
    install = f"https://acg-q.github.io/userscript-manager/scripts/{SAMPLE['id']}.user.js"
    snap = [
        ("名称", "我的去广告脚本"),
        ("版本", "1.0.1"),
        ("作者", "ACG-Q"),
        ("命名空间", "<code>https://github.com/ACG-Q/userscript-manager</code>"),
        ("匹配规则", "<code>*://www.baidu.com/*</code>"),
        ("授权", "<code>none</code>"),
        ("来源类型", "自写"),
        ("创建时间", "2026-08-20"),
        ("最后同步", "-"),
        ("安装链接", f'<a href="{install}">安装脚本</a>'),
    ]
    snap_table = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in snap)
    answer_badge = '<span class="gh-answer">✓ 已标记为答案</span>'
    body = f"""<h1 class="gh-title">[v1.0.1] 我的去广告脚本 2026-10-01</h1>
<div class="gh-sub">
<span class="gh-state done">✓ 已解决</span>
<span class="gh-cat">💬 Q&amp;A</span>
<span>讨论 #{9} · 由机器人发布于 2026-10-01 · 创建后不再修改</span>
</div>
<div class="gh-card">
<div class="gh-card-head"><span class="gh-avatar">A</span><b>ACG-Q</b>
<span>发布于 2026-10-01</span></div>
<div class="gh-content">
<h2>脚本信息（发帖时快照）</h2>
<table>
<tr><th>字段</th><th>值</th></tr>
{snap_table}
</table>
<h2>本次更新</h2>
<p>自 v1.0.0 更新至 <strong>v1.0.1</strong>：手动更新。</p>
<p>描述：移除百度首页和搜索结果广告，支持信息流与推广链接过滤。</p>
<blockquote>回链：<a href="{ISSUE_URL}">Issue #2（状态与索引）</a> ·
<a href="detail.html">脚本详情页</a> ·
<a href="index.html">Demo 导航</a></blockquote>
</div>
</div>
<div class="gh-card">
<div class="gh-card-head"><span class="gh-avatar">U</span><b>user123</b>
<span>commented 2 天前</span></div>
<div class="gh-content">
<div class="gh-comment">
<div class="c-head"><span class="gh-avatar" style="background:#0969da">U</span>
<b>user123</b><span>commented 2 天前</span></div>
<div class="c-body"><p>首页右侧广告没了，但<strong>搜索结果页底部</strong>还有推广链接卡片，是还没适配吗？</p></div>
<div class="c-replies">
<div class="gh-comment">
<div class="c-head"><span class="gh-avatar" style="background:#bc4c00">A</span>
<b>ACG-Q</b>{answer_badge}<span>commented 2 天前</span></div>
<div class="c-body"><p>是的，v1.0.1 已修复该问题。升级到最新版本刷新页面即可生效。</p></div>
</div>
</div>
</div>
<div class="gh-comment">
<div class="c-head"><span class="gh-avatar" style="background:#8250df">R</span>
<b>reader9527</b><span>commented 1 天前</span></div>
<div class="c-body"><p>能不能加个快捷键临时开关去广告？有时要对比原页面。</p></div>
</div>
</div>
</div>"""
    return gh_shell("Discussion #9 · [v1.0.1] 我的去广告脚本 (Demo)", body)


def build_index_html():
    """Demo 导航页：三个样例入口与确认要点。"""
    cards = [
        ("detail.html", "① 脚本详情页（站内样式）",
         "头部版本浮层菜单（默认最新），切换 v1.0.0 查看空态；徽标跟随最新帖 isAnswered。"),
        ("issue.html", "② Issue 正文样式（GitHub）",
         "活字段表（状态/版本/安装/来源）+ 版本帖索引累积列表；marker 首行。"),
        ("discussion.html", "③ 版本帖样式（GitHub Q&amp;A）",
         "全量信息快照、自 vX 至 vY、回链、评论与「已标记为答案」。"),
    ]
    lis = "".join(
        f'<div class="card"><h3><a href="{href}">{title}</a></h3><p>{desc}</p></div>'
        for href, title, desc in cards
    )
    body = f"""<main>
<h1>设计 Demo · 三页样式确认</h1>
<p class="lead">样例脚本：我的去广告脚本 v1.0.1（账本：v1.0.0 #7 → v1.0.1 #9）。
确认三页后进入规格与实现阶段。</p>
{lis}
<p class="tip">详情页可试：右上「设置」切换三套主题，验证新面板在暗色/紫色主题下的表现。</p>
</main>"""
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Demo 导航 · 设计确认</title>
<style>
body {{ margin: 0; padding: 48px 16px; font-family: -apple-system, "Segoe UI",
  Helvetica, Arial, sans-serif; background: #f6f8fa; color: #1f2328; }}
main {{ max-width: 760px; margin: 0 auto; }}
h1 {{ font-size: 24px; margin: 0 0 8px; }}
.lead {{ color: #59636e; margin: 0 0 24px; line-height: 1.6; }}
.card {{ background: #fff; border: 1px solid #d1d9e0; border-radius: 10px;
  padding: 18px 20px; margin-bottom: 14px; }}
.card h3 {{ margin: 0 0 6px; font-size: 16px; }}
.card p {{ margin: 0; font-size: 14px; color: #59636e; line-height: 1.6; }}
.tip {{ font-size: 13px; color: #59636e; }}
</style>
</head>
<body>
{body}
</body>
</html>"""
    return html


def main() -> int:
    """生成 demo/*.html 四个文件。"""
    DEMO_DIR.mkdir(exist_ok=True)
    bp.detail_issue_panel = new_panel
    detail = bp.build_detail(SAMPLE, None).replace("../index.html", "index.html")
    files = {
        "detail.html": detail,
        "issue.html": build_issue_html(),
        "discussion.html": build_discussion_html(),
        "index.html": build_index_html(),
    }
    for name, content in files.items():
        if name != "index.html":
            content = open_external_links(content)
        (DEMO_DIR / name).write_text(content, encoding="utf-8", newline="\n")
    print(f"已生成 {len(files)} 个 demo 页面 -> {DEMO_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
