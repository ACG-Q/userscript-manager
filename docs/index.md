# 命令文档索引

本目录包含每个命令的详细使用说明和示例。

> 想了解系统整体设计（架构分层、数据模型、工作流机制）？见 [设计文档](design.md)。
> 想了解代码质量、已知问题与「是否值得换语言重写」的评估？见 [代码审查与语言替换评估报告](code-review-2026-10-03.md)。

## 命令列表

| 命令 | 说明 | 文档 |
|------|------|------|
| [`/list`](commands/list.md) | 列出所有脚本 | [list.md](commands/list.md) |
| [`/add`](commands/add.md) | 添加自写脚本 / 同步第三方脚本 | [add.md](commands/add.md) |
| [`/up`](commands/up.md) | 更新自写脚本 | [up.md](commands/up.md) |
| [`/sync`](commands/sync.md) | 同步第三方脚本 | [sync.md](commands/sync.md) |
| [`/rm`](commands/rm.md) | 删除脚本 | [rm.md](commands/rm.md) |
| [`/info`](commands/info.md) | 查看脚本详情 | [info.md](commands/info.md) |
| [`/enable` / `/disable`](commands/toggle.md) | 启用/禁用脚本 | [toggle.md](commands/toggle.md) |
| [`/export`](commands/export.md) | 导出安装列表 | [export.md](commands/export.md) |

## 快速参考

### 自写脚本管理

```
/add + Markdown(含代码块)     # 创建
/up <id> + Markdown(含代码块)  # 更新
/rm <id>                       # 删除
/info <id>                     # 查看详情
/enable <id>                   # 启用
/disable <id>                  # 禁用
```

### 同步脚本管理

```
/add <url>                     # 添加
/sync <id>                     # 手动同步
/sync-all                      # 批量同步
/rm <url>                      # 删除（按原始 URL）
```

### 通用

```
/list                          # 列出所有
/export [json|md]              # 导出列表
```

## Markdown 文档格式

自写脚本的 `/add` 和 `/up` 支持完整 Markdown：

````markdown
# 脚本标题

脚本描述...

## 功能
- 移除页面广告
- 屏蔽推广弹窗

```javascript
// ==UserScript==
// @name 脚本名
// @version 1.0.0
// @match *://*/*
// ==/UserScript==
(function() { ... })();
```
````

- **代码块**（`javascript`）提取为脚本代码
- **其余内容**保存为 `README.md` 文档
- **油猴头部**（@name 等）自动解析为元数据

## 支持的同步来源

| 来源 | 适配器 | 示例 |
|------|--------|------|
| GreasyFork | GreasyForkAdapter | `https://greasyfork.org/zh-CN/scripts/12345` |
| Userscript.zone | UserscriptZoneAdapter | `https://userscript.zone/scripts/abc` |
| GitHub Gist | GitHubGistAdapter | `https://gist.github.com/user/abc123` |
| 直接链接 | DirectUrlAdapter | `https://raw.githubusercontent.com/.../script.user.js`、`https://github.com/<user>/<repo>/raw/<branch>/script.user.js` |