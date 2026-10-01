# /rm - 删除脚本

## 语法

```
/rm <script_id>
```

```
/rm <source_url>
```

## 说明

支持两种删除方式：

1. **按 ID 删除** - 可删除自写脚本和同步脚本
2. **按原始 URL 删除** - 仅用于同步脚本，通过来源 URL 定位

删除操作会：
- 删除源码目录（`scripts/self/<id>/` 或 `scripts/synced/<id>/`）
- 删除生成的 `.user.js` 文件（`dist/<id>.user.js`）
- 从 `registry.json` 中移除记录

## 示例

### 示例 1：按 ID 删除自写脚本

```
/rm f9076f78-e878-4095-b53c-71d63e7ff556
```

### 示例 2：按 ID 删除同步脚本

```
/rm a1b2c3d4e5f6
```

### 示例 3：按原始 URL 删除同步脚本

```
/rm https://greasyfork.org/zh-CN/scripts/123456
```

## 输出示例

### 删除自写脚本

```
🗑️ 已删除脚本 f9076f78-e878-4095-b53c-71d63e7ff556
```

### 删除同步脚本（按 URL）

```
🗑️ 已删除同步脚本 a1b2c3d4e5f6（来源 https://greasyfork.org/zh-CN/scripts/123456）
```

## 注意事项

- 删除操作不可恢复，请谨慎操作
- 同步脚本建议使用 URL 删除，避免 ID 记错
- 删除后，已安装该脚本的用户将无法再收到更新