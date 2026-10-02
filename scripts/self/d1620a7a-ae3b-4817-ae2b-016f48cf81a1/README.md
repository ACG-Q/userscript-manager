# 我的去广告脚本

移除百度首页和搜索结果广告，支持信息流与推广链接过滤。

## 功能
- 首页右侧广告位
- 搜索结果推广链接
- 信息流广告卡片

```javascript
// ==UserScript==
// @name         我的去广告脚本
// @namespace    https://github.com/ACG-Q/userscript-manager
// @version      1.0.1
// @description  移除百度首页和搜索结果广告，支持信息流与推广链接过滤
// @author       ACG-Q
// @match        *://www.baidu.com/*
// @grant        none
// ==/UserScript==
(function () {
  'use strict';
  const kill = () => document.querySelectorAll('#content_right, .ec_tuiguang_pannel').forEach(el => el.remove());
  kill();
  new MutationObserver(kill).observe(document.body, { childList: true, subtree: true });
})();
```