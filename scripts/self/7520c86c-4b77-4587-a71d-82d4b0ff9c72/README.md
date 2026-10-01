# Bilibili 清爽增强

隐藏推荐位与浮层广告，还原干净的观看页面。

## 功能
- 首页推荐位降噪
- 悬浮广告与浮层弹窗隐藏

```javascript
// ==UserScript==
// @name         Bilibili 清爽增强
// @namespace    https://github.com/ACG-Q/userscript-manager
// @version      1.0.0
// @description  隐藏推荐位与浮层广告，还原干净的观看页面
// @author       ACG-Q
// @match        *://www.bilibili.com/*
// @grant        none
// ==/UserScript==
(function () {
  'use strict';
  document.querySelectorAll('.recommended-swipe, .bili-ad').forEach(el => el.remove());
})();
```