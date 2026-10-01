// ==UserScript==
// @name         Bilibili 清爽增强
// @namespace    https://github.com/ACG-Q/userscript-manager
// @version      1.0.0
// @description  隐藏推荐位与浮层广告，还原干净的观看页面
// @author       ACG-Q
// @match        *://www.bilibili.com/*
// @grant        none
// @downloadURL  https://ACG-Q.github.io/userscript-manager/dist/7520c86c-4b77-4587-a71d-82d4b0ff9c72.user.js
// @updateURL    https://ACG-Q.github.io/userscript-manager/dist/7520c86c-4b77-4587-a71d-82d4b0ff9c72.user.js
// ==/UserScript==
(function () {
  'use strict';
  document.querySelectorAll('.recommended-swipe, .bili-ad').forEach(el => el.remove());
})();