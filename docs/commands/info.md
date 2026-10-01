# /info - 查看脚本详情

## 语法

```
/info <script_id>
```

## 说明

显示指定脚本的完整元数据信息，包括：
- 基本信息：ID、名称、类型、版本、状态
- 作者信息：作者、命名空间、描述
- 技术配置：匹配规则、权限
- 时间信息：创建时间、更新时间
- 同步脚本特有：来源 URL、来源类型、上次同步时间、自动同步状态
- 自写脚本特有：文档状态
- 安装链接

## 示例

```
/info f9076f78-e878-4095-b53c-71d63e7ff556
```

## 输出示例

### 自写脚本

```
📄 脚本详情: f9076f78-e878-4095-b53c-71d63e7ff556
  名称: 百度去广告
  类型: 自写
  版本: 1.0.2
  状态: 启用
  作者: Your Name
  命名空间: https://github.com/yourname/userscripts
  描述: 移除百度页面广告
  匹配规则: *://www.baidu.com/*, *://www.so.com/*
  权限: none
  创建时间: 2026-01-15T10:30:00.000000Z
  更新时间: 2026-01-20T14:22:11.000000Z
  文档: 有 (README.md)
  安装链接: https://yourname.github.io/repo/dist/f9076f78-e878-4095-b53c-71d63e7ff556.user.js
```

### 同步脚本

```
📄 脚本详情: a1b2c3d4e5f6
  名称: GreasyFork 热门脚本
  类型: 同步
  版本: 2.1.0
  状态: 启用
  作者: Original Author
  命名空间: https://greasyfork.org
  描述: 来自 GreasyFork 的热门脚本
  匹配规则: *://*/*
  权限: GM_xmlhttpRequest, GM_setValue
  创建时间: 2026-01-10T08:00:00.000000Z
  更新时间: 2026-01-18T12:00:00.000000Z
  来源: https://greasyfork.org/zh-CN/scripts/123456
  来源类型: greasyfork
  上次同步: 2026-01-18T12:00:00.000000Z
  自动同步: 是
  安装链接: https://yourname.github.io/repo/dist/a1b2c3d4e5f6.user.js
```