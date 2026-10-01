# 油猴脚本自动化管理系统

基于 GitHub Issues + Actions 的全自动油猴脚本管理方案。支持自写脚本全生命周期管理，以及从 GreasyFork、Userscript.zone、GitHub Gist 等站点同步第三方脚本。

## 特性

- **命令行式管理**：在 Issue 评论中用 `/命令` 管理脚本，手机电脑通用
- **自写脚本**：完整的增删改查、版本自增、代码格式化、元数据管理
- **Markdown 文档**：自写脚本支持 Markdown 文档，代码块自动提取为脚本代码，其余内容保存为 README.md
- **第三方同步**：支持 GreasyFork、Userscript.zone、GitHub Gist、直接链接，可插拔适配器架构
- **GitHub Pages 分发**：安装链接走 Pages/CDN，国内可访问，支持自动更新检测
- **每脚本独立页**：每个脚本自动拥有 Discussions 页面（元数据 + 文档 + 更新历史），评论区供用户反馈；Pages 列表站提供安装入口
- **定时同步**：可选的 GitHub Actions 定时任务，自动检查第三方脚本更新
- **单仓库管理**：所有脚本统一在一个仓库，`dist/` 目录直接部署到 Pages
- **权限控制**：仅 Issue #1 作为命令面板，仅仓库拥有者可执行命令，其他人评论自动删除

## 快速开始

### 1. 创建仓库

Fork 或新建一个仓库，将本项目代码推送上去。

### 2. 启用 GitHub Pages

仓库 Settings → Pages → Source 选择 "GitHub Actions"。

### 3. 启用 Discussions（脚本独立页）

仓库 Settings → Features → 勾选 **Discussions**（API 无法代办，仅此一次）。分类保持默认 `General`，或用仓库变量 `DISCUSSION_CATEGORY` 指定。

### 4. 初始化命令面板

推送代码后，在 Actions 选项卡中手动运行 **"Init Command Panel"** 工作流（或等待 push 触发），它会自动创建 Issue #1 作为命令面板。重复运行是安全的——已存在时会跳过创建。

### 5. 配置作者信息（可选）

修改 `userscript_manager/config.py` 中的作者信息：

```python
"author": {
    "name": "你的名字",
    "namespace": "https://your-namespace.com",
},
```

或通过 GitHub 仓库 Settings → Secrets and variables → Actions 添加环境变量：

- `AUTHOR_NAME`
- `AUTHOR_NAMESPACE`

### 6. 开始使用

在 Issue #1（命令面板）下评论命令即可：

**添加自写脚本（支持 Markdown 文档）：**

````
/add
# 我的去广告脚本

这是一个去除百度广告的脚本。

## 功能
- 移除首页广告
- 移除搜索结果推广

## 使用方法
安装后自动生效，无需配置。

```javascript
// ==UserScript==
// @name 我的去广告脚本
// @version 1.0.0
// @match *://www.baidu.com/*
// @grant none
// ==/UserScript==
(function() {
    // 移除广告逻辑
    console.log('广告已移除');
})();
```
````

**从网页同步脚本：**

```
/add https://greasyfork.org/zh-CN/scripts/12345
```

## 命令大全

| 命令 | 说明 | 示例 | 详细文档 |
|------|------|------|----------|
| `/list` | 列出所有脚本 | `/list` | [list.md](docs/commands/list.md) |
| `/add` | 添加自写脚本（Markdown 代码块中提供代码） | `/add` + Markdown 内容 | [add.md](docs/commands/add.md) |
| `/add <url>` | 从网页同步脚本 | `/add https://greasyfork.org/zh-CN/scripts/12345` | [add.md](docs/commands/add.md) |
| `/up <id>` | 更新自写脚本（支持更新文档） | `/up abc123` + Markdown 内容 | [up.md](docs/commands/up.md) |
| `/sync <id>` | 手动同步单个第三方脚本 | `/sync abc123` | [sync.md](docs/commands/sync.md) |
| `/sync-all` | 批量同步所有启用自动同步的脚本 | `/sync-all` | [sync.md](docs/commands/sync.md) |
| `/rm <id>` | 删除自写脚本 | `/rm abc123` | [rm.md](docs/commands/rm.md) |
| `/rm <url>` | 删除同步脚本（按原始 URL） | `/rm https://greasyfork.org/...` | [rm.md](docs/commands/rm.md) |
| `/info <id>` | 查看脚本详情 | `/info abc123` | [info.md](docs/commands/info.md) |
| `/enable <id>` | 启用脚本 | `/enable abc123` | [toggle.md](docs/commands/toggle.md) |
| `/disable <id>` | 禁用脚本 | `/disable abc123` | [toggle.md](docs/commands/toggle.md) |
| `/export [json\|md]` | 导出安装列表 | `/export md` | [export.md](docs/commands/export.md) |

完整命令文档见 [docs/index.md](docs/index.md) 或 [docs/commands/](docs/commands/) 目录；系统架构与设计决策见 [docs/design.md](docs/design.md)。

## Markdown 文档格式说明

自写脚本的 `/add` 和 `/up` 命令支持完整的 Markdown 格式：

- **代码块**：使用 `javascript` 或 `js` 语言标注的代码块会被提取为脚本代码（仅取第一个代码块）
- **其余内容**：作为脚本文档保存，自动生成 `scripts/self/<id>/README.md`
- **元数据提取**：脚本代码中的 `// @name`、`// @version` 等油猴头部信息会自动解析

示例：

````
/add
# 脚本标题

脚本描述和使用说明...

## 功能
- 移除页面广告
- 屏蔽推广弹窗

```javascript
// ==UserScript==
// @name 脚本名称
// @version 1.0.0
// @match *://*/*
// @grant GM_xmlhttpRequest
// ==/UserScript==
(function() {
    // 代码逻辑
})();
```
````

## 支持的同步来源

| 来源 | 适配器 | 示例 URL |
|------|--------|----------|
| GreasyFork | `GreasyForkAdapter` | `https://greasyfork.org/zh-CN/scripts/12345` |
| Userscript.zone | `UserscriptZoneAdapter` | `https://userscript.zone/scripts/12345` |
| GitHub Gist | `GitHubGistAdapter` | `https://gist.github.com/user/abc123` |
| 直接链接 | `DirectUrlAdapter` | `https://raw.githubusercontent.com/.../script.user.js` |

## 安装脚本

生成的安装链接格式：

- **GitHub Pages**：`https://<user>.github.io/<repo>/dist/<id>.user.js`
- **Raw GitHub**：`https://raw.githubusercontent.com/<user>/<repo>/master/dist/<id>.user.js`
- **jsDelivr CDN**：`https://cdn.jsdelivr.net/gh/<user>/<repo>@master/dist/<id>.user.js`

在油猴扩展中点击"从 URL 安装"即可。脚本的 `@updateURL` 已指向同一链接，油猴会自动检查更新。

## 权限说明

- **仅 Issue #1（命令面板）接受命令**，其他 Issue 的评论被忽略
- **仅仓库拥有者**可执行命令（通过 `COMMENT_USER == REPO_OWNER` 校验）
- **非拥有者在命令面板评论命令会被机器人自动删除**
- 仓库可以是 Private，不影响使用
- 同步的第三方脚本仅供个人使用，请遵守原作者许可协议

## 进阶配置

### 启用定时同步

在 `.github/workflows/issue-commands.yml` 中添加 schedule（或单独建一个 workflow）：

```yaml
on:
  schedule:
    - cron: '0 3 * * 1'  # 每周一 UTC 3 点
  workflow_dispatch:
```

### 自定义域名

在仓库 Settings → Pages → Custom domain 设置自定义域名，然后在 `userscript_manager/config.py` 中设置：

```python
"github_pages": {
    "enabled": True,
    "base_url": "https://your-domain.com",
},
```

### 添加新的源适配器

1. 在 `userscript_manager/sources/` 下创建 `xxx.py`
2. 继承 `BaseSourceAdapter` 实现 `name`、`domains`、`fetch()` 方法
3. 在 `userscript_manager/sources/__init__.py` 中注册

### GitHub Actions 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AUTHOR_NAME` | 脚本作者名 | "Your Name" |
| `AUTHOR_NAMESPACE` | 命名空间 | "https://your-namespace.com" |
| `GITHUB_PAGES_URL` | Pages 基础 URL | 自动推导 |
| `DISCUSSION_CATEGORY` | Discussion 分类名 | `General` |

## 目录结构

```
.
├── .github/workflows/
│   ├── init-command-panel.yml  # 初始化命令面板
│   ├── issue-commands.yml      # 命令处理与 Discussion 投影
│   ├── deploy-pages.yml        # 构建站点并部署 Pages
│   └── test.yml                # 单元测试 CI
├── userscript_manager/
│   ├── config.py               # 配置
│   ├── registry.py             # 注册表读写（原子写入）
│   ├── utils.py                # 工具函数（头部构建 / 版本 / 安装地址）
│   ├── issue_parser.py         # 评论解析（Markdown 支持）
│   ├── discussion_page.py      # Discussion 正文生成
│   ├── escaping.py             # HTML / Markdown 转义
│   ├── sources/                # 源适配器（base / greasyfork / userscript_zone / github_gist / direct_url）
│   └── commands/               # 命令模块（list / add / remove / update / sync / info / toggle / export）
├── tests/                      # 单元与回归测试（python -m unittest discover）
├── docs/
│   ├── index.md                # 文档索引
│   ├── design.md               # 系统设计文档
│   └── commands/               # 各命令详细说明
├── scripts/
│   ├── self/                   # 自写脚本源码（按 UUID）
│   └── synced/                 # 同步脚本源码
├── dist/                       # .user.js 安装包（HTML 页面部署时生成，不入库）
├── manager.py                  # 命令入口
├── project_discussions.py      # Discussions 投影器（幂等对账）
├── build_pages.py              # Pages 站点生成器
├── registry.json               # 脚本注册表（真源）
└── requirements.txt
```

## 许可证

MIT License
