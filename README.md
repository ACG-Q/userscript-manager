<div align="center">

# 油猴脚本控制台

**Write · Sync · Ship —— 像管理代码一样管理你的油猴脚本**

在 GitHub Issue 里敲命令，把自写脚本与第三方脚本统一收进一个可安装、可更新、可反馈的脚本仓库。

[![License](https://img.shields.io/badge/license-MIT-7C3AED?style=for-the-badge)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Actions](https://img.shields.io/badge/GitHub%20Actions-CI-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](../../actions)
[![Pages](https://img.shields.io/badge/Pages-deploy-222?style=for-the-badge&logo=githubpages&logoColor=white)](../../deployments)

[快速开始](#30-秒上手) · [命令速查](#命令速查) · [使用场景](#三种使用场景) · [设计文档](docs/design.md)

</div>

---

## 它解决什么问题？

| 痛点 | 传统做法 | 本方案 |
|------|----------|--------|
| 自写脚本散落各处 | 本地文件夹 + 手动上传 | 一条 `/add` 命令入库，自动生成安装链接 |
| 第三方脚本更新要手动盯 | 定期访问 GreasyFork 检查 | 定时任务自动同步，版本号自动比对 |
| 用户反馈没有归口 | 分散在评论区/私信 | 每个脚本独立 Issue 页，评论即反馈 |
| 国内安装 GitHub Raw 慢 | 挂梯子 / 手动下载 | Pages + jsDelivr 双通道分发 |

---

## 核心特性

<table>
<tr>
<td width="50%" valign="top">

### 命令行式管理
在 Issue 评论中用 `/命令` 管理脚本，**手机电脑通用**，无需本地环境。

</td>
<td width="50%" valign="top">

### 自写脚本全生命周期
增删改查 · 版本自增 · 代码格式化 · 元数据管理 · Markdown 文档。

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 多源同步
GreasyFork · Userscript.zone · GitHub Gist · 直链，**可插拔适配器架构**。

</td>
<td width="50%" valign="top">

### Pages 分发
安装链接走 Pages/CDN，**国内可访问**，`@updateURL` 支持自动更新检测。

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 每脚本独立页
自动生成独立 Issue（元数据 + 文档 + 更新历史），评论区供用户反馈。

</td>
<td width="50%" valign="top">

### 定时同步
可选 GitHub Actions 定时任务，自动检查第三方脚本更新。

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 单仓库管理
所有脚本统一入库，`dist/` 目录直接部署到 Pages。

</td>
<td width="50%" valign="top">

### 权限控制
仅 Issue #1 为命令面板，仅仓库拥有者可执行，越权评论自动删除。

</td>
</tr>
</table>

---

## 30 秒上手

> 三步走：**建仓库 → 开 Pages → 敲命令**

### ① 创建仓库
Fork 或新建一个仓库，将本项目代码推送上去。

### ② 启用 GitHub Pages
`Settings → Pages → Source` 选择 **GitHub Actions**。

### ③ 初始化命令面板
推送代码后，在 **Actions** 选项卡手动运行 **"Init Command Panel"** 工作流（或等待 push 触发）。
它会自动创建 **Issue #1** 作为命令面板；重复运行安全——已存在时会跳过。

### ④ 配置作者信息（可选）

修改 `userscript_manager/config.py`：

```python
"author": {
    "name": "你的名字",
    "namespace": "https://your-namespace.com",
},
```

或通过 `Settings → Secrets and variables → Actions` 添加：

- `AUTHOR_NAME`
- `AUTHOR_NAMESPACE`

### ⑤ 开始使用

在 **Issue #1** 下评论命令即可。

---

## 命令速查

| 命令 | 说明 | 详细文档 |
|------|------|----------|
| `/list` | 列出所有脚本 | [list.md](docs/commands/list.md) |
| `/add` | 添加自写脚本（Markdown 代码块中提供代码） | [add.md](docs/commands/add.md) |
| `/add <url>` | 从网页同步脚本 | [add.md](docs/commands/add.md) |
| `/up <id>` | 更新自写脚本（支持更新文档） | [up.md](docs/commands/up.md) |
| `/sync <id>` | 手动同步单个第三方脚本 | [sync.md](docs/commands/sync.md) |
| `/sync-all` | 批量同步所有启用自动同步的脚本 | [sync.md](docs/commands/sync.md) |
| `/rm <id>` | 删除自写脚本 | [rm.md](docs/commands/rm.md) |
| `/rm <url>` | 删除同步脚本（按原始 URL） | [rm.md](docs/commands/rm.md) |
| `/info <id>` | 查看脚本详情 | [info.md](docs/commands/info.md) |
| `/enable <id>` | 启用脚本 | [toggle.md](docs/commands/toggle.md) |
| `/disable <id>` | 禁用脚本 | [toggle.md](docs/commands/toggle.md) |
| `/export [json\|md]` | 导出安装列表 | [export.md](docs/commands/export.md) |

> 完整命令文档见 [docs/index.md](docs/index.md)；系统架构与设计决策见 [docs/design.md](docs/design.md)。

---

## 三种使用场景

<details>
<summary><b>场景一：添加自写脚本（带 Markdown 文档）</b></summary>

在 Issue #1 评论：

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

**系统会**：提取代码块为脚本 · 其余内容存为 `README.md` · 解析 `@name/@version` 等头部 · 生成独立 Issue 页 · 输出安装链接。

</details>

<details>
<summary><b>场景二：从网页同步第三方脚本</b></summary>

```
/add https://greasyfork.org/zh-CN/scripts/12345
```

系统会调用对应适配器抓取脚本，存入 `scripts/synced/`，并在独立 Issue 页展示元数据与来源。

</details>

<details>
<summary><b>场景三：用户反馈</b></summary>

每个脚本自动拥有独立 Issue 页（元数据 + 文档 + 更新历史），用户可直接在该 Issue 下评论反馈；Pages 列表站提供安装入口。

</details>

---

## 安装脚本

生成三种安装链接：

| 通道 | 格式 | 适用 |
|------|------|------|
| **GitHub Pages** | `https://<user>.github.io/<repo>/dist/<id>.user.js` | 国内友好 |
| **Raw GitHub** | `https://raw.githubusercontent.com/<user>/<repo>/master/dist/<id>.user.js` | 备用 |
| **jsDelivr CDN** | `https://cdn.jsdelivr.net/gh/<user>/<repo>@master/dist/<id>.user.js` | 全球加速 |

在油猴扩展中点击 **"从 URL 安装"** 即可。脚本的 `@updateURL` 已指向同一链接，油猴会自动检查更新。

---

## Markdown 文档格式说明

自写脚本的 `/add` 和 `/up` 命令支持完整 Markdown：

- **代码块**：使用 `javascript` 或 `js` 标注的代码块会被提取为脚本代码（**仅取第一个**）
- **其余内容**：作为脚本文档保存，自动生成 `scripts/self/<id>/README.md`
- **元数据提取**：脚本代码中的 `// @name`、`// @version` 等油猴头部信息会自动解析

---

## 支持的同步来源

| 来源 | 适配器 | 示例 URL |
|------|--------|----------|
| GreasyFork | `GreasyForkAdapter` | `https://greasyfork.org/zh-CN/scripts/12345` |
| Userscript.zone | `UserscriptZoneAdapter` | `https://userscript.zone/scripts/12345` |
| GitHub Gist | `GitHubGistAdapter` | `https://gist.github.com/user/abc123` |
| 直接链接 | `DirectUrlAdapter` | `https://raw.githubusercontent.com/.../script.user.js`<br>`https://github.com/<user>/<repo>/raw/<branch>/script.user.js` |

---

## 进阶玩法

<details>
<summary><b>启用定时同步</b></summary>

仓库自带可选工作流 `.github/workflows/sync-scheduled.yml`：

- 默认**仅手动触发**（Actions → Scheduled Sync → Run workflow）
- 要**每周自动同步**，取消 `schedule` 注释：

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: '0 3 * * 1'  # 每周一 UTC 3 点
```

</details>

<details>
<summary><b>自定义域名</b></summary>

`Settings → Pages → Custom domain` 设置域名，然后在 `userscript_manager/config.py`：

```python
"github_pages": {
    "enabled": True,
    "base_url": "https://your-domain.com",
},
```

</details>

<details>
<summary><b>添加新的源适配器</b></summary>

1. 在 `userscript_manager/sources/` 下创建 `xxx.py`
2. 继承 `BaseSourceAdapter`，实现 `name`、`domains`、`fetch()`
3. 在 `userscript_manager/sources/__init__.py` 中注册

</details>

<details>
<summary><b>GitHub Actions 环境变量</b></summary>

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AUTHOR_NAME` | 脚本作者名 | `"Your Name"` |
| `AUTHOR_NAMESPACE` | 命名空间 | `"https://your-namespace.com"` |
| `GITHUB_PAGES_URL` | Pages 基础 URL | 自动推导 |

</details>

---

## 架构与目录

```
.
├── .github/workflows/
│   ├── init-command-panel.yml  # 初始化命令面板
│   ├── issue-commands.yml      # 命令处理与 Issue 投影
│   ├── deploy-pages.yml        # 构建站点并部署 Pages
│   └── test.yml                # 单元测试 CI
├── userscript_manager/
│   ├── config.py               # 配置
│   ├── registry.py             # 注册表读写（原子写入）
│   ├── utils.py                # 工具函数（头部构建 / 版本 / 安装地址）
│   ├── issue_parser.py         # 评论解析（Markdown 支持）
│   ├── issue_page.py           # Issue 正文生成
│   ├── escaping.py             # HTML / Markdown 转义
│   ├── sources/                # 源适配器
│   └── commands/               # 命令模块
├── tests/                      # 单元与回归测试
├── docs/
│   ├── index.md                # 文档索引
│   ├── design.md               # 系统设计文档
│   └── commands/               # 各命令详细说明
├── scripts/
│   ├── self/                   # 自写脚本源码（按 UUID）
│   └── synced/                 # 同步脚本源码
├── dist/                       # .user.js 安装包（部署时生成，不入库）
├── manager.py                  # 命令入口
├── project_issues.py           # Issues 投影器（幂等对账）
├── build_pages.py              # Pages 站点生成器
├── registry.json               # 脚本注册表（真源）
└── requirements.txt
```

---

## 安全与权限

- **仅 Issue #1（命令面板）接受命令**，其他 Issue 的评论被忽略
- **仅仓库拥有者可执行命令**（通过 `COMMENT_USER == REPO_OWNER` 校验）
- **非拥有者在命令面板评论命令会被机器人自动删除**
- 管理功能（命令、真源存储、Issues 面板）可在 **Private 仓库**运行；但 GitHub Pages 免费账户仅 Public 仓库可启用，需经 Pages 安装分发时仓库必须 Public
- 同步的第三方脚本**仅供个人使用**，请遵守原作者许可协议

---

## Roadmap

- [x] 命令面板 + 命令解析
- [x] 自写脚本 CRUD + Markdown 文档
- [x] 四大源适配器
- [x] Pages 分发 + `@updateURL`
- [x] 定时同步工作流
- [ ] Pages 列表站个性化主题
- [ ] 脚本安装量统计（通过 CDN 日志）
- [ ] 脚本代码 ESLint 校验
- [ ] 更多适配器（OpenUserJS / GitHub Repo 直读）
- [ ] 移动端命令补全提示

---

## License

[MIT License](./LICENSE)

<div align="center">

**如果这个项目对你有帮助，欢迎 Star 支持一下。**

Made with care by [@your-name](https://github.com/your-name)

</div>