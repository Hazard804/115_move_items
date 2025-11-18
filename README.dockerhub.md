# 115网盘文件移动工具

[![Docker Image Size](https://img.shields.io/docker/image-size/hazard084/115-move-items/latest)](https://hub.docker.com/r/hazard084/115-move-items)
[![Docker Pulls](https://img.shields.io/docker/pulls/hazard084/115-move-items)](https://hub.docker.com/r/hazard084/115-move-items)

一个功能强大的115网盘文件自动移动工具，支持 Docker 部署，可自动监控和移动文件。

## ✨ 功能特性

- 🔄 **自动监控**：定期检查指定目录，自动移动符合条件的文件
- 📏 **智能筛选**：根据文件大小自动筛选，避免误操作小文件
- 📁 **递归扫描**：自动遍历子目录，无需手动处理
- ⏰ **可配置间隔**：自定义检查间隔时间
- 📝 **完整日志**：详细的操作日志，支持自动清理
- 🐳 **Docker 部署**：开箱即用，无需配置环境

## 🚀 快速开始

### 使用 Docker Compose（推荐）

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  move_items:
    image: hazard084/115-move-items:latest
    container_name: 115_move_items
    restart: unless-stopped
    network_mode: host  # 使用宿主机网络（解决代理问题）
    environment:
      # 必填：115网盘的Cookie
      - COOKIE=你的115网盘Cookie
      
      # 多组路径映射（推荐）
      - PATH_MAPPINGS=/待处理/下载->/已完成/视频,/临时/缓存->/归档/2024
      
      # 排除特定后缀的文件
      - EXCLUDE_EXTENSIONS=.txt,.nfo,.jpg,.png,.srt
      
      # 可选：检查间隔（分钟），默认5分钟
      - CHECK_INTERVAL=5
      
      # 可选：最小文件大小，默认200MB
      - MIN_FILE_SIZE=200MB
      
      # 可选：日志保留天数，默认7天
      - LOG_RETENTION_DAYS=7
      
      # 可选：时区设置
      - TZ=Asia/Shanghai
    
    volumes:
      # 日志目录映射
      - ./logs:/app/logs
      
      # 数据目录映射
      - ./data:/app/data
```

启动服务：

```bash
docker-compose up -d
```

### 使用 Docker 命令

```bash
docker run -d \
  --name 115_move_items \
  --restart unless-stopped \
  --network host \
  -e COOKIE='你的115网盘Cookie' \
  -e PATH_MAPPINGS='/待处理/下载->/已完成/视频,/临时/缓存->/归档/2024' \
  -e EXCLUDE_EXTENSIONS='.txt,.nfo,.jpg,.png' \
  -e CHECK_INTERVAL=5 \
  -e MIN_FILE_SIZE=200MB \
  -e LOG_RETENTION_DAYS=7 \
  -e TZ=Asia/Shanghai \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  hazard084/115-move-items:latest
```

## 📋 配置说明

### 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|-------|------|--------|------|
| `COOKIE` | ✅ | - | 115网盘的Cookie |
| `PATH_MAPPINGS` | ⭐ | - | 多组路径映射（推荐） |
| `SOURCE_PATH` | ⭐ | - | 源目录路径（单组） |
| `TARGET_PATH` | ⭐ | - | 目标目录路径（单组） |
| `EXCLUDE_EXTENSIONS` | ❌ | - | 排除的文件后缀 |
| `CHECK_INTERVAL` | ❌ | 5 | 检查间隔（分钟） |
| `MIN_FILE_SIZE` | ❌ | 200MB | 最小文件大小 |
| `LOG_RETENTION_DAYS` | ❌ | 7 | 日志保留天数 |
| `API_TIMEOUT` | ❌ | 120 | API超时（秒） |
| `API_RETRY_TIMES` | ❌ | 3 | API重试次数 |
| `BARK_URL` | ❌ | - | Bark通知URL |
| `TZ` | ❌ | Asia/Shanghai | 时区 |

### 🆕 多组路径映射

配置多组源目录到目标目录的映射：

```yaml
environment:
  # 格式: 源路径1->目标路径1,源路径2->目标路径2
  - PATH_MAPPINGS=/待处理/下载->/已完成/视频,/临时/缓存->/归档/2024
```

### 🆕 排除文件后缀

排除特定后缀的文件不进行移动：

```yaml
environment:
  - EXCLUDE_EXTENSIONS=.txt,.nfo,.jpg,.png
```

### 🆕 Bark 失败通知

在操作失败时接收 iPhone 推送通知：

```yaml
environment:
  - BARK_URL=https://api.day.app/你的Bark密钥
```

**说明**: 仅在 API 超时、请求失败或 Cookie 失效时发送通知，正常运行不打扰。

### 获取 115网盘 Cookie

1. 访问 https://115.com 并登录
2. 按 `F12` 打开开发者工具
3. 切换到 `Network`（网络）标签
4. 刷新页面，选择任意请求
5. 在请求头中找到 `Cookie` 字段
6. 复制完整的 Cookie 值

Cookie 格式示例：
```
UID=12345_A1B2C3D4; CID=E5F6G7H8; SEID=I9J0K1L2M3N4O5P6; KID=...
```

### 路径规则

- 路径必须以 `/` 开头
- 路径严格区分大小写
- 示例：`/我的文件/视频/电影`

## 🔧 管理命令

```bash
# 查看日志
docker logs -f 115_move_items

# 停止服务
docker stop 115_move_items

# 重启服务
docker restart 115_move_items

# 更新镜像
docker pull hazard084/115-move-items:latest
docker stop 115_move_items
docker rm 115_move_items
# 然后重新运行 docker run 或 docker-compose up -d
```

## 📊 日志查看

日志文件保存在映射的 `logs/` 目录，按天分割：

```bash
# 查看实时日志
docker logs -f 115_move_items

# 查看历史日志文件
ls -lh logs/
cat logs/move_items_20241118.log
```

## ⚠️ 注意事项

1. **路径检查**：路径输入时请仔细检查大小写
2. **递归扫描**：程序会遍历源目录的所有子目录
3. **操作不可逆**：移动操作不可逆，请谨慎配置
4. **先行测试**：建议先在测试目录验证功能
5. **Cookie 有效期**：Cookie 可能过期，需要定期更新
6. **网络配置**：建议使用 `network_mode: host` 避免网络问题

## 🔍 故障排查

### Cookie 验证卡住

如果容器启动后卡在 "正在验证Cookie..." 步骤：

**原因**：使用了全局代理，Docker 容器无法正确访问网络

**解决方案**：添加 `network_mode: host` 或 `--network host`

### API 请求超时

**现象**：扫描目录时卡住或频繁超时

**解决方案**：调整超时和重试配置

```yaml
environment:
  - API_TIMEOUT=180        # 增加超时时间（默认120秒）
  - API_RETRY_TIMES=5     # 增加重试次数（默认3次）
```

**说明**：
- 程序会在每次重试之间自动增加等待时间
- 超时的操作会跳过，不会中断整个程序

### Cookie 失效

程序会**自动检测 Cookie 失效**并提示更新：

**更新步骤**：
1. 重新登录 115.com 获取新 Cookie
2. 修改 docker-compose.yml 中的 COOKIE
3. 重启容器：`docker-compose restart`

### 文件没有移动

1. 检查路径是否正确（大小写敏感）
2. 检查文件大小是否满足 `MIN_FILE_SIZE`
3. 查看日志了解详细信息

## 🔒 安全提醒

- Cookie 相当于登录凭证，请妥善保管
- 不要在公开场合分享包含真实 Cookie 的配置
- 建议定期更新 Cookie

## 📦 支持的平台

- `linux/amd64` - x86_64 架构
- `linux/arm64` - ARM64 架构（树莓派等）

## 🤝 技术支持

- GitHub 仓库：https://github.com/Hazard804/115_move_items
- 提交 Issue：https://github.com/Hazard804/115_move_items/issues

## 📄 许可证

本项目仅供学习交流使用，请勿用于商业用途。
