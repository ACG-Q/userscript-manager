# /export - 导出安装列表

## 语法

```
/export [json|md]
```

## 说明

导出所有脚本的安装信息列表，支持两种格式：

- **Markdown** (默认) - 表格格式，适合阅读和分享
- **JSON** - 结构化数据，适合程序处理

包含信息：状态、类型、ID、名称、版本、安装链接

## 示例

### 导出 Markdown（默认）

```
/export
```
/export md
```

### 导出 JSON

```
/export json
```

## 输出示例

### Markdown 格式

```
# 油猴脚本安装列表

| 状态 | 类型 | ID | 名称 | 版本 | 安装链接 |
|------|------|----|------|------|----------|
| ✅ | 📝 | f9076f78-e878-4095-b53c-71d63e7ff556 | 百度去广告 | v1.0.2 | [安装](https://yourname.github.io/repo/dist/f9076f78-e878-4095-b53c-71d63e7ff556.user.js) |
| ✅ | 📝 | 5eb89853-6306-4684-8705-777c9b501d8b | 带文档的脚本 v2 | v1.0.1 | [安装](https://yourname.github.io/repo/dist/5eb89853-6306-4684-8705-777c9b501d8b.user.js) |
| ✅ | 🔄 | a1b2c3d4e5f6 | GreasyFork 脚本 | v2.1.0 | [安装](https://yourname.github.io/repo/dist/a1b2c3d4e5f6.user.js) |
```

### JSON 格式

```json
{
  "scripts": [
    {
      "id": "f9076f78-e878-4095-b53c-71d63e7ff556",
      "type": "self",
      "name": "百度去广告",
      "version": "1.0.2",
      "enabled": true,
      "install_url": "https://yourname.github.io/repo/dist/f9076f78-e878-4095-b53c-71d63e7ff556.user.js"
    },
    {
      "id": "5eb89853-6306-4684-8705-777c9b501d8b",
      "type": "self",
      "name": "带文档的脚本 v2",
      "version": "1.0.1",
      "enabled": true,
      "install_url": "https://yourname.github.io/repo/dist/5eb89853-6306-4684-8705-777c9b501d8b.user.js"
    },
    {
      "id": "a1b2c3d4e5f6",
      "type": "synced",
      "name": "GreasyFork 脚本",
      "version": "2.1.0",
      "enabled": true,
      "install_url": "https://yourname.github.io/repo/dist/a1b2c3d4e5f6.user.js"
    }
  ]
}
```

## 使用场景

- 备份脚本列表
- 分享给他人安装
- 程序化处理（配合 JSON 格式）
- 生成个人脚本导航页面