# 115网盘文件移动工具 - Docker版本

自动监控115网盘指定目录，按文件大小自动移动文件到目标目录。

## 特性

- ✅ 自动定期检查源目录
- ✅ 根据文件大小筛选
- ✅ 遍历子目录深度扫描
- ✅ 完整的日志记录
- ✅ 支持多平台（amd64/arm64）
- ✅ 持久化配置和日志

## 快速开始

### 使用docker-compose（推荐）

1. 创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  move_items:
    image: yourusername/115-move-items:latest
    container_name: 115_move_items
    restart: unless-stopped
    environment:
      - COOKIE=你的115网盘Cookie
      - SOURCE_PATH=/待处理/下载
      - TARGET_PATH=/已完成/视频
      - CHECK_INTERVAL=5
      - MIN_FILE_SIZE=200MB
      - LOG_RETENTION_DAYS=7
      - TZ=Asia/Shanghai
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
```

2. 启动容器：
```bash
docker-compose up -d
```

3. 查看日志：
```bash
docker-compose logs -f
```

### 使用Docker命令

```bash
docker run -d \
  --name 115_move_items \
  --restart unless-stopped \
  -e COOKIE='你的Cookie' \
  -e SOURCE_PATH='/待处理/下载' \
  -e TARGET_PATH='/已完成/视频' \
  -e CHECK_INTERVAL=5 \
  -e MIN_FILE_SIZE='200MB' \
  -e LOG_RETENTION_DAYS=7 \
  -e TZ=Asia/Shanghai \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  yourusername/115-move-items:latest
```

## 环境变量

### 必填参数

| 变量 | 说明 | 示例 |
|------|------|------|
| `COOKIE` | 115网盘Cookie | `UID=...; CID=...; SEID=...` |
| `SOURCE_PATH` | 源目录路径 | `/待处理/下载` |
| `TARGET_PATH` | 目标目录路径 | `/已完成/视频` |

### 可选参数

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CHECK_INTERVAL` | 检查间隔（分钟） | 5 |
| `MIN_FILE_SIZE` | 最小文件大小 | 200MB |
| `LOG_RETENTION_DAYS` | 日志保留天数 | 7 |
| `TZ` | 时区 | Asia/Shanghai |

## 获取Cookie

1. 访问 https://115.com 并登录
2. 按F12打开开发者工具
3. 切换到Network标签
4. 刷新页面，找到任意请求
5. 复制请求头中的Cookie字段

Cookie格式：`UID=xxx; CID=xxx; SEID=xxx`

## 路径规则

⚠️ **重要提示**
- 路径必须以 `/` 开头
- 路径严格区分大小写
- 确保路径与115网盘实际文件夹名称完全一致

✅ 正确：`/我的文件/视频`
❌ 错误：`我的文件/视频`（缺少开头的 `/`）

## 文件大小格式

支持：`200MB`, `1.5GB`, `500KB`, `1TB`

## 常用命令

```bash
# 查看日志
docker-compose logs -f

# 停止容器
docker-compose down

# 重启容器
docker-compose restart

# 更新镜像
docker-compose pull
docker-compose up -d
```

## 数据持久化

- `/app/logs` - 日志文件
- `/app/data` - Cookie等配置

映射到宿主机保证数据不丢失。

## 故障排查

### 容器启动后立即退出
```bash
# 查看错误日志
docker logs 115_move_items

# 常见原因：
# 1. Cookie格式错误或已过期
# 2. 必填环境变量未设置
# 3. 路径格式错误
```

### 找不到目录
检查：
1. 路径是否以 `/` 开头
2. 大小写是否正确
3. 目录在115网盘中是否存在

## 更多文档

- [完整使用指南](DOCKER.md)
- [发布到Docker Hub](PUBLISH.md)

## 支持

- 查看日志文件：`logs/move_items.log`
- 进入容器调试：`docker exec -it 115_move_items /bin/bash`

## 许可证

仅供学习交流使用。
