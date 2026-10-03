# 代码审查与语言替换评估报告

- **日期**：2026-10-03
- **范围**：28 个生产 `.py`（3,612 行，其中 `pages_assets.py` 617 行为站点 CSS/JS 资产）、19 个测试文件（263 用例）、6 个 GitHub Actions 工作流、README + docs
- **方法**：两路并行子代理审查（核心库 / 测试与 CI）→ 主会话逐条复核关键结论 → 本地与 CI 门禁实测
- **状态**：审查结论按「路径 A」完成 12 项加固（提交 `93dcff2`），本报告同时记录修复前后

---

## 0. TL;DR

| 维度 | 审查时 | 现在 |
|---|---|---|
| 静态检查 | 无 lint、无类型检查 | **ruff（规则锁定）+ mypy 全标注，均为 CI 硬门禁** |
| 测试保护 | 258 用例；幂等契约「同源比较」无真保护 | **263 用例 + 4 个 golden 基线**，覆盖率 **92.3%** 且 **≥90% 硬门禁** |
| API 正确性 | 假客户端按子串路由，字段名写错照样全绿 | **+ 官方 schema 校验**（能在 CI 拦住 `Query.discussion` 类 bug） |
| 严重问题 | 3 个 | **0 个** |
| CI 缺陷 | 3 条流水线权限/逻辑问题 | **0 个** |
| 语言替换 | 当时有 3 条支持理由 | **只剩「团队主语言是 TS」1 条** → 不建议重写 |

**一句话结论：不建议整体换语言。** 代码量小（约 3,000 行纯 Python 逻辑）、只在 CI/本地运行、语言不是瓶颈；重写的主要风险（契约漂移、字段错误、类型退化）已被门禁结构性堵住，而 263 个用例需要全部重做一遍。

---

## 1. 代码现状盘点

### 1.1 模块地图

| 层 | 文件 | 说明 |
|---|---|---|
| 入口 | `manager.py` | Actions 命令入口：env → 面板/权限校验 → 解析 → 分发 → `_finish` 统一落盘 |
|  | `project_issues.py` | Issue/版本帖幂等对账投影器（GraphQL） |
|  | `build_pages.py` | Pages 站点生成器（列表/详情/命令归档页） |
|  | `panel_cleanup.py` | 命令面板定期清理与归档（本次会话新增） |
| 核心库 | `userscript_manager/` | `issue_parser` 评论解析、`issue_page` 正文唯一生成器、`registry` 原子读写、`utils` 头部/版本/文件、`escaping` 转义、`config` 配置、`discussions` 版本帖、`issue_stats` 讨论统计 |
|  | `commands/` | 9 个命令模块 + 注册表（统一异常边界） |
|  | `sources/` | 4 个来源适配器 + 域名白名单匹配 |
| 资产 | `pages_assets.py` | TOKEN/组件/预览 CSS + 筛选/懒加载/版本切换 JS |
| CI | `.github/workflows/` | test / issue-commands / deploy-pages / sync-scheduled / cleanup-panel / init-command-panel |

### 1.2 度量

- **生产代码**：3,612 行 / 28 文件；核心库 102 个函数、修复前 75% 全注解、92% docstring
- **测试**：19 文件、263 用例、`unittest` 风格、`ConfigIsolation` 统一路径隔离
- **覆盖率**：92.3%（1,752 语句，未覆盖 135）
- **依赖**：运行时 5（requests / beautifulsoup4 / jsbeautifier / markdown / nh3）+ 开发 4（ruff / mypy / coverage / graphql-core）
- **CI**：6 个 workflow，action 全部按 commit SHA 锁定、均设 timeout

---

## 2. 值得保留的设计

1. **幂等对账投影**：Issue 标题/正文逐字符一致才更新 + `script-id` 标记 + 墓碑不带标记（`issue_page.py`），使投影可重入、孤儿可识别。
2. **原子落盘 + 加载即校验**（`registry.py`）：临时文件 + `os.replace`；结构错误提示直接指向 Git 恢复。
3. **统一异常边界**（`commands/__init__.py`）：命令异常降级为回帖文本而非炸流水线；`manager.py` 所有早退路径强制经 `_finish`，Actions 不会误报成功。
4. **安全细节**：hostname 后缀匹配防 `evil.com/path/greasyfork.org` 绕过（`sources/base.py`）；入库前校验 `==UserScript==` 头；"纯代码块不算文档"防覆盖；`nh3` 消毒 + 集中转义；bash + Python **双重权限门禁**。
5. **软删除可恢复**、`sync` 无变化短路、GreasyFork 多级回退并汇总 attempts 便于排障。
6. **分层原则**：命令核心不直接调 GitHub API，读/回/删评论由 workflow 的 `gh` 完成 → 业务层可在本地完整测试。

---

## 3. 问题清单（严重度分级）

### 3.1 严重（3 个，**全部已修复**）

| # | 位置 | 问题 | 状态 |
|---|---|---|---|
| S1 | `commands/add.py` + `registry.py` | **软删复活路径断裂**：`remove/sync/update` 三处承诺「重新 `/add` 复活」，但按 `source_url` 查重不跳过 `deleted` 条目 → 永远回「脚本已存在」，软删同步脚本锁死 | ✅ `93dcff2`：软删条目走复活（复用原 ID、就地清 `deleted`、回写文件），+3 回归测试 |
| S2 | `sync-scheduled.yml` | **缺 `discussions: write`**：定时同步执行 `project_issues` 时 `createDiscussion` 403，被 `except` 吞掉只打警告 → **新版本的版本帖创建失败** | ✅ `93dcff2` 补权限 |
| S3 | `cleanup-panel.yml` | **缺 `actions: write`**：`gh workflow run` 必 403 → 清理归档后站点不自动刷新 | ✅ `93dcff2` 补权限 |

### 3.2 中（8 个，1 个已修复）

| # | 位置 | 问题 | 状态 |
|---|---|---|---|
| M1 | `manager.py` | 权限检查 fail-open：`COMMENT_USER` 与 `REPO_OWNER` 同为空串时通过（后续 `parse_comment("")` 无命令，实际不会执行 → 校准为中） | ⬜ 待办 |
| M2 | `manager.py` | `ISSUE_NUMBER` 缺失即跳过面板校验（fail-open），应缺失即拒绝 | ⬜ 待办 |
| M3 | `issue-commands.yml` | 回帖步骤无 `always()`：`Run manager` 失败则**用户收不到任何回帖**（静默失败） | ✅ `93dcff2`：改 `!cancelled()` + 携带 `manager`/`commit` 步骤状态，失败也会回帖说明 |
| M4 | `commands/toggle.py` | `/disable` 只改 registry、**不删 dist** → `/dist/<id>.user.js` 仍可直接安装，与回帖「安装链接停用」不符 | ⬜ 待办 |
| M5 | `commands/add.py`、`update.py` | 先写源码/dist 后 `save_registry`，中途异常会留孤儿文件或版本不一致 | ⬜ 待办 |
| M6 | `sources/base.py` | `requests` 默认跟随重定向，白名单域名 302 → 内网地址无二次校验（SSRF 面） | ⬜ 待办 |
| M7 | `registry.py` | 固定 `.tmp` 文件名，并发运行互踩同一临时文件 | ⬜ 待办 |
| M8 | `tests/test_projector.py` | **幂等契约无真保护**：noop 断言两侧都调 `build_issue_body`（同源比较）——builder 一变测试仍绿，线上会全量重写所有 Issue | ✅ `93dcff2`：`tests/golden/` 4 个基线文件逐字符对拍（`UPDATE_GOLDEN=1` 再生成） |

### 3.3 低（代表项）

- `manager.py` Windows stdout 重包装 → **✅ 已根修**（改 `reconfigure`；重包会提前关闭 pytest 捕获文件，导致整目录收集崩溃）
- `test.yml` 缺 `concurrency` → ✅ 已补（同分支新提交取消旧跑）
- 文档漂移：`design.md`「仅三处例外调 API」、README 架构目录缺 `panel_cleanup.py` → ✅ 已同步
- `list.py` `last_synced_at=None` 时 `None[:10]` TypeError → ✅ 顺带修复（`or "从未"`）
- ⬜ `config.py` repo 多斜杠解包 `ValueError`
- ⬜ `escaping.py` 未处理 `)]`，可破 Issue 正文表格
- ⬜ `github_gist.py` 未带 token，受 api.github.com 共享 IP 60 次/时限额
- ⬜ `registry.json` 无结尾换行 → 编辑器易产生噪音 diff
- ⬜ `sync-scheduled.yml:72` 写 `GITHUB_OUTPUT` 但步骤无 `id`（死代码）
- ⬜ `deploy-pages.yml`：`issue_comment` 未排除 PR 评论（会白跑构建）；`mv dist/*` 遇空目录会失败
- ⬜ 类型风格历史混用（`str | None` vs `Optional`）——已被 mypy 全标注收敛

---

## 4. 测试与 CI 评估

### 4.1 测试盘点

19 个 `test_*.py` / 263 用例，全部 `unittest.TestCase`；隔离设施 `tests/_helpers.py` 的 `ConfigIsolation`（路径键重定向到独立临时目录）。CI 用 `python -m unittest discover`。

**零覆盖**（仍待办）：`sources/userscript_zone.py`（覆盖率 43.5%）、`project_issues.main()`、**6 个 workflow 的全部 shell 逻辑**（权限门禁、`init-command-panel` 的 404 判定——该文件注释自证曾因此重复建面板）、GraphQL 限流/错误路径。

### 4.2 脆弱点（重写时最先红的）

- 整段 HTML 字面量断言（如安装按钮整串、`<html lang=...>` 整标签）
- Markdown 表格逐字断言（文案/emoji 变更即断）
- 断言 GraphQL 查询文本本身

> 这类断言**是有意的**（它们锁定幂等契约），但依赖 `tests/golden/` 提供的独立锚点，改模板必须显式 `UPDATE_GOLDEN=1`。

### 4.3 系统性假阳性（本次审查最有价值的发现）

**13 处假客户端按「查询子串」路由**（`test_projector`、`test_discussions`、`test_panel_cleanup` 等）：不校验 variables、不模拟 cursor 与 GraphQL errors → **字段名写错照样全绿**。线上事故 `Query.discussion`（字段不存在）通过了当时全部 234 个测试，只在真实请求时暴露。

**修复**：`tools/validate_graphql.py` 用 GitHub 官方 schema 校验仓库内全部 14 个查询，作为 CI 硬门禁；负向验证确认可捕获该类 bug。variables 一致性与假件真实性仍属待办。

### 4.4 CI 盘点（修复后）

| Workflow | 权限 | 触发 | 状态 |
|---|---|---|---|
| `test.yml` | `contents: read` | push/PR，带 concurrency | ✅ **4 道门禁**：ruff → mypy → GraphQL schema → 测试+覆盖率≥90% |
| `issue-commands.yml` | contents/issues/actions/discussions write | 仅 Issue #1 | ✅ 回帖 `!cancelled()` 且携带步骤状态 |
| `deploy-pages.yml` | 含 `discussions: read` | push/issues/issue_comment/**discussion_comment(created)**/dispatch | ✅（低危项见 3.3） |
| `sync-scheduled.yml` | contents/issues/actions/discussions write | 手动/定时 | ✅ 已补 `discussions: write` |
| `cleanup-panel.yml` | contents/issues/actions write | 每天 UTC 03:00 + 手动 | ✅ 已补 `actions: write` |
| `init-command-panel.yml` | `issues: write` | 手动 | ✅（404 判定用 grep 文本仍偏脆） |

---

## 5. 语言替换评估

### 5.1 为什么值得评估

项目只在 GitHub Actions 与本地开发运行、没有线上服务器；JSON/HTTP/HTML 是主体；团队若主语言是 JS/TS，换语言能降低维护门槛、去掉 pip 安装步骤、获得类型系统。

### 5.2 候选对比

| | **TypeScript/Node** | **Go** | **Rust** | **Bash + gh/jq** |
|---|---|---|---|---|
| Actions 免安装 | ✅ Node 预装（6 条流水线各省 3–8s） | ❌ 需 setup+build | ❌ 需 setup+build | ✅ |
| 依赖等价物 | ✅ fetch / cheerio / js-beautify / marked+sanitize-html | ⚠️ goquery、无 js-beautify 等价 | ❌（`nh3` 本就是 Rust） | ❌ 业务逻辑写不了 |
| 类型拦错 | ✅ 需 **graphql-codegen** 才能拦 schema 字段错 | ✅ 强 | ✅ 强 | ❌ |
| 修 Windows stdout 崩溃 | ✅ | ✅ | ✅ | — |
| 构建步骤 | ⚠️ tsc/tsx，或退化为带 JSDoc 的 JS | ❌ 必须 | ❌ 必须 | — |
| 与站点前端同语言 | ✅（`DISC_JS`/`LIST_JS` 已是 JS） | ❌ | ❌ | — |

**若换，选 TypeScript**；Go/Rust/Bash 均不如它。

### 5.3 迁移面（逐模块）

- **约 80% 纯逻辑直接平移**：`issue_parser`、`escaping`、`issue_page`（字符串模板）、`registry`（JSON + `os.replace`）、`config`、`commands/*` 全部编排、`panel_cleanup` 分组/归档。
- **必须替换的绑定**：`requests`→`fetch`（超时/UA 语义不同）；`bs4`→`cheerio`（**选择器语义需回归**，GreasyFork/Userscript.zone 两个解析器）；`jsbeautifier`→`js-beautify`；`markdown`+`nh3`→`marked`+`sanitize-html`（**安全关键，XSS 用例必须重跑**）；`pkgutil` 动态注册→显式注册表（漏列=漏命令）。
- **零成本**：`pages_assets.py` 617 行本质是 CSS/JS，直接搬文件。
- **测试 2,800+ 行**：约 60% 可机械转换；30% 需重写（GraphQL 假件、monkeypatch 用例、80+ 条 HTML 字面量需重生成 golden）；workflow shell 需 act/bats 另写；`ConfigIsolation` 这类全局可变 CONFIG 在静态语言无对应物，要先做依赖注入。

### 5.4 成本与收益

**成本（1 人全职）**：基线固化 1–2 天 → 命令层 5–8 天 → 投影/站点 4–6 天 → sources 2–3 天 → 切 workflow + 双跑对拍 2–3 天 ≈ **14–22 人日（3–4 周）+ 1–2 周观察**，且测试迁移占其中约一半。

**收益**（更新后）：

| 当初支持重写的理由 | 现状 |
|---|---|
| Python 有 Windows stdout 崩溃问题 | ✅ 已用 `reconfigure` 根修 |
| 无类型安全、API 字段错测不出来 | ✅ mypy 全标注 + **GraphQL schema 校验**（注意：**TS 类型同样拦不住 schema 字段名**，除非上 graphql-codegen，成本与本方案相当） |
| 团队主语言是 JS/TS | ❌ 仍是唯一剩余的实质理由 |
| CI 更快 | ⚠️ 收益约 3–8s/次，量级太小 |

**风险**：263 个用例是唯一安全网，迁移期保护力必然下降；双语言过渡期维护翻倍；最易翻车的三处是**幂等投影的逐字符契约**、**Markdown+消毒的 XSS 面**、**bash+Python 双重权限门禁**。

### 5.5 决策

| 方案 | 结论 |
|---|---|
| **A. 不换语言，按门禁持续加固** | ✅ **推荐**——门禁已落地，重写的主要理由被消解 |
| B. 分四阶段换 TypeScript | ⚠️ 仅在触发条件满足时 |
| C. Go / Rust / Bash | ❌ 不建议 |

**重启重写的触发条件**（满足其一）：
1. 团队多人协作且主语言为 JS/TS；
2. 要给它加真正的服务端（当前无服务器，语言无关紧要）；
3. 新能力持续被 Python 生态拖后腿（当前 5 个依赖都有等价物，不构成拖累）。

**若届时重写**：走「**固化基线 → 命令层 → 投影/站点 → sources → 切 workflow**」四阶段，双跑对拍通过前不切 workflow。`tests/golden/` 就是现成的迁移验收资产。

---

## 6. 审查后的执行记录（12/12，提交 `93dcff2`）

1. `cleanup-panel.yml` 补 `actions: write`
2. `sync-scheduled.yml` 补 `discussions: write`
3. `/add <url>` 软删复活 + 3 条回归测试
4. `manager.py` 改 `reconfigure`（根修 Windows pytest 崩溃）
5. `issue-commands.yml` 回帖 `!cancelled()` + 步骤状态感知
6. `tests/golden/` 4 个 golden 基线（修「同源比较」假保护）
7. `tools/validate_graphql.py` schema 校验（负向验证可抓 `Query.discussion`）
8. `ruff.toml` 门禁 + 71 处修复
9. 命令注册改**惰性自加载**（ruff 清掉的"未用导入"实为 `@register` 副作用）→ 19 个测试文件单跑全过
10. `mypy.ini` + `userscript_manager` 全量标注
11. `.coveragerc` + 覆盖率 ≥90% 门禁（实测 92.3%）
12. 文档同步（`design.md` API 例外清单、README 架构目录）

**验证**：本地一次性四门禁全绿 → 提交推送 → **CI Tests run #13 `success`**。

**顺带修掉的两个真实缺陷**：`tests/_helpers.py` 的 `setUp` 只重定向写死的四个路径键（`archive_file` 被保存却从未重定向，测试数据写进了真实 `archive/`）；`.gitignore` 补 `dist/scripts.json`、`dist/commands/`。

---

## 7. 后续建议（按性价比排序）

1. **修 M1/M2 fail-open**（`manager.py` 权限与面板校验）——安全面，10 分钟
2. **`/disable` 同步移除 dist**（M4）——与回帖文案一致，10 分钟
3. **补 `userscript_zone.py` 测试**（当前 43.5%）与 `project_issues.main()`
4. **假件升级为变量校验**：schema 校验已覆盖 query 侧，补一份「假客户端校验 variables 与 query 别名一致」的工具
5. M5 事务性、M6 SSRF 重定向、M7 并发 `.tmp`
6. deploy-pages 排除 PR 评论、`registry.json` 补结尾换行
7. 覆盖率按模块分层设阈值（`userscript_manager` 已 90%+，可单独提到 95%）

---

## 8. 附录：本次相关提交

| 提交 | 内容 |
|---|---|
| `df3ad56` | 详情页评论区版本帖切换 |
| `bfa4987` | 外链统一新标签 + `discussions: read` |
| `f4f91c3` | 版本帖拉取失败原因落盘 `build-warnings.txt` |
| `92db3b5` | 版本帖查询改走 `node(id)` + 内联片段（修线上 undefinedField） |
| `9bcc94f` | 版本帖评论触发重建、列表懒加载、命令归档页 |
| `93dcff2` | **本报告对应的 12 项加固与四道门禁** |
