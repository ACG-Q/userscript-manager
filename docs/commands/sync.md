# /sync - 同步第三方脚本

## 语法

```
/sync <script_id>
```

```
/sync-all
```

## 说明

- `/sync <id>`：手动触发单个同步脚本的更新检查
- `/sync-all`：批量同步所有启用了 `sync_enabled=true` 的同步脚本
- 从原始 URL 重新抓取脚本代码
- 对比代码内容，仅在有变化时更新
- 更新时会同步元数据（版本、描述、匹配规则等）
- 重新生成 `.user.js`（更新 `@downloadURL`/`@updateURL`）
- 更新 `last_synced_at` 时间戳

## 示例

### 示例 1：同步单个脚本

```
/sync a1b2c3d4e5f6
```

### 示例 2：批量同步所有

```
/sync-all
```

## 输出示例

### 单个同步 - 有更新

```
✅ a1b2c3d4e5f6 (GreasyFork 脚本): 已更新到 v2.1.0
```

### 单个同步 - 无变化

```
✅ a1b2c3d4e5f6 (GreasyFork 脚本): 无变化
```

### 批量同步

```
🔄 批量同步完成：
  ✅ a1b2c3d4e5f6 (GreasyFork 脚本): 已更新到 v2.1.0
  ✅ b2c3d4e5f6a7 (Userscript 脚本): 无变化
  ❌ c3d4e5f6a7b8 (GitHub Gist): 获取失败: 404 Not Found
```

## 注意事项

- 仅适用于 `type=synced` 的脚本
- 同步失败不会中断其他脚本的同步（`/sync-all`）
- 原始代码保存到 `scripts/synced/<id>/script.user.js`
- 仅修改 `@downloadURL` 和 `@updateURL` 指向本仓库