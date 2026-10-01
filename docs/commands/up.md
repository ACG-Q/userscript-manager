# /up - 更新自写脚本

## 语法

```
/up <script_id>
[Markdown 内容，包含代码块]
```

## 说明

- 仅支持**自写脚本**（type=self），同步脚本请使用 `/sync`
- 必须在 Markdown 代码块中提供完整的新脚本代码
- 版本号自动递增（补丁版本 +1：1.0.0 → 1.0.1）
- 代码块中的油猴头部信息会更新脚本元数据
- 代码块外的 Markdown 内容会更新文档（`README.md`）
- 重新生成格式化后的 `.user.js` 到 `dist/` 目录

## 示例

### 示例 1：更新代码和文档

````
/up f9076f78-e878-4095-b53c-71d63e7ff556
# 百度去广告脚本 v2

新增对百度新版页面的支持。

## 更新内容
- 修复新版首页广告选择器
- 新增对搜索建议广告的移除

```javascript
// ==UserScript==
// @name         百度去广告
// @namespace    https://github.com/yourname/userscripts
// @version      1.0.0
// @description  移除百度页面广告（支持新版）
// @author       Your Name
// @match        *://www.baidu.com/*
// @match        *://www.so.com/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    const selectors = [
        '#content_left .result-op',
        '.ec_tuiguang_pannel',
        '.sug-wrap .ad-item'
    ];
    const removeAds = () => {
        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => el.remove());
        });
    };
    removeAds();
    new MutationObserver(removeAds).observe(document.body, { childList: true, subtree: true });
})();
```
````

### 示例 2：仅更新代码（保留原文档）

````
/up f9076f78-e878-4095-b53c-71d63e7ff556
```javascript
// ==UserScript==
// @name 百度去广告
// @version 1.0.0
// @match *://www.baidu.com/*
// @grant none
// ==/UserScript==
console.log('Updated');
```
````

## 输出示例

```
✅ 脚本 f9076f78-e878-4095-b53c-71d63e7ff556 更新成功！新版本 1.0.1
安装链接: https://yourname.github.io/repo/dist/f9076f78-e878-4095-b53c-71d63e7ff556.user.js
```

## 注意事项

- 代码块中的 `@version` 会被忽略，系统自动递增版本号
- 如果代码块中没有 `@name`，将保留原有名称
- 文档内容会完全替换原有的 `README.md`