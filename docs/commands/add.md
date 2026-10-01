# /add - 添加脚本

## 语法

```
/add
[Markdown 内容，包含代码块]
```

```
/add <URL>
```

## 说明

支持两种模式：

1. **添加自写脚本** - 不带参数，在 Markdown 代码块中提供脚本代码
2. **同步第三方脚本** - 带 URL 参数，自动从支持的站点抓取脚本

### 自写脚本模式

- 评论体必须包含一个 JavaScript 代码块（```javascript 或 ```js）
- 代码块中的油猴头部（`// @name` 等）会自动解析为元数据
- 代码块外的 Markdown 内容会保存为 `scripts/self/<id>/README.md` 文档
- 自动生成 UUID 作为脚本 ID
- 版本号从 1.0.0 开始，后续 `/up` 自动递增
- 自动生成格式化后的 `.user.js` 到 `dist/` 目录

### 同步脚本模式

- 支持的来源：GreasyFork、Userscript.zone、GitHub Gist、直接链接
- 使用 URL 的 MD5 哈希（前12位）作为脚本 ID
- 仅修改 `@downloadURL` 和 `@updateURL` 指向本仓库 Pages
- 原始代码保持不变，保存到 `scripts/synced/<id>/`
- 自动启用定时同步（可通过 `/sync` 手动触发）

## 示例

### 示例 1：添加自写脚本（带完整文档）

````
/add
# 百度去广告脚本

这是一个移除百度首页和搜索结果广告的脚本。

## 功能
- 移除首页右侧广告
- 移除搜索结果中的推广链接
- 移除信息流广告

## 适用页面
- www.baidu.com
- www.so.com

## 更新日志
### v1.0.0 (2026-01-15)
- 初始版本

```javascript
// ==UserScript==
// @name         百度去广告
// @namespace    https://github.com/yourname/userscripts
// @version      1.0.0
// @description  移除百度页面广告
// @author       Your Name
// @match        *://www.baidu.com/*
// @match        *://www.so.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    // 移除广告逻辑
    const removeAds = () => {
        document.querySelectorAll('#content_left .result-op, .ec_tuiguang_pannel').forEach(el => el.remove());
    };
    removeAds();
    new MutationObserver(removeAds).observe(document.body, { childList: true, subtree: true });
})();
```
````

### 示例 2：添加简单自写脚本（无文档）

````
/add
```javascript
// ==UserScript==
// @name 简单脚本
// @version 1.0.0
// @match *://*/*
// @grant none
// ==/UserScript==
console.log('Hello World');
```
````

### 示例 3：从 GreasyFork 同步

```
/add https://greasyfork.org/zh-CN/scripts/123456
```

### 示例 4：从 Userscript.zone 同步

```
/add https://userscript.zone/scripts/abcdef
```

### 示例 5：从 GitHub Gist 同步

```
/add https://gist.github.com/username/abc123def456
```

### 示例 6：从直接链接同步

```
/add https://raw.githubusercontent.com/user/repo/main/script.user.js
```

## 输出示例

### 自写脚本成功

```
✅ 自写脚本添加成功！
ID: f9076f78-e878-4095-b53c-71d63e7ff556
安装链接: https://yourname.github.io/repo/dist/f9076f78-e878-4095-b53c-71d63e7ff556.user.js
```

### 同步脚本成功

```
✅ 同步脚本添加成功！
ID: a1b2c3d4e5f6
来源: GreasyFork
安装链接: https://yourname.github.io/repo/dist/a1b2c3d4e5f6.user.js
```