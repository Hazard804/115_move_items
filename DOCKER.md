# 115网盘文件移动工具 - Docker使用指南

## 快速开始

### 方法1: 使用docker-compose（推荐）

#### 1. 编辑配置文件
编辑 `docker-compose.yml`，填入你的配置：

```yaml
environment:
  - COOKIE=你的115网盘Cookie
  - SOURCE_PATH=/待处理/下载
  - TARGET_PATH=/已完成/视频
  - CHECK_INTERVAL=5
  - MIN_FILE_SIZE=200MB
  - LOG_RETENTION_DAYS=7
```

#### 2. 启动容器
```bash
docker-compose up -d
```

#### 3. 查看日志
```bash
docker-compose logs -f
```

#### 4. 停止容器
```bash
docker-compose down
```

### 方法2: 使用启动脚本

```bash
chmod +x docker-start.sh
./docker-start.sh
```

脚本会交互式地引导你输入所有配置参数。

### 方法3: 直接使用Docker命令

```bash
# 构建镜像
docker build -t 115-move-items .

# 运行容器
docker run -d \
  --name 115_move_items \
  --restart unless-stopped \
  -e COOKIE='你的Cookie' \
  -e SOURCE_PATH='/待处理/下载' \
  -e TARGET_PATH='/已完成/视频' \
  -e CHECK_INTERVAL=5 \
  -e MIN_FILE_SIZE='200MB' \
  -e LOG_RETENTION_DAYS=7 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  115-move-items

# 查看日志
docker logs -f 115_move_items

# 停止容器
docker stop 115_move_items

# 删除容器
docker rm 115_move_items
```

## 环境变量说明

### 必填参数

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `COOKIE` | 115网盘的Cookie | `UID=...; CID=...; SEID=...` |
| `SOURCE_PATH` | 源目录路径（待检查） | `/待处理/下载` |
| `TARGET_PATH` | 目标目录路径（移动到此） | `/已完成/视频` |

### 可选参数

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `CHECK_INTERVAL` | 检查间隔（分钟） | 5 | `10` |
| `MIN_FILE_SIZE` | 最小文件大小 | 200MB | `1GB`, `500MB` |
| `LOG_RETENTION_DAYS` | 日志保留天数 | 7 | `30` |
| `MODE` | 运行模式 | auto | `auto` |

### 文件大小格式

支持以下格式：
- `200MB` 或 `200M` - 200兆字节
- `1.5GB` 或 `1.5G` - 1.5吉字节
- `500KB` 或 `500K` - 500千字节
- `1TB` 或 `1T` - 1太字节

## 数据持久化

### 日志目录
```bash
-v ./logs:/app/logs
```
将容器内的日志目录映射到宿主机，方便查看和备份日志。

### 数据目录
```bash
-v ./data:/app/data
```
保存Cookie等配置信息，容器重启后无需重新输入。

## 常用操作

### 查看实时日志
```bash
# docker-compose
docker-compose logs -f

# docker
docker logs -f 115_move_items
```

### 重启容器
```bash
# docker-compose
docker-compose restart

# docker
docker restart 115_move_items
```

### 修改配置
1. 停止容器
2. 修改 `docker-compose.yml` 或删除 `data/115-cookies.txt`
3. 重新启动容器

### 查看容器状态
```bash
# docker-compose
docker-compose ps

# docker
docker ps | grep 115_move_items
```

### 进入容器调试
```bash
docker exec -it 115_move_items /bin/bash
```

## 获取Cookie

1. 打开浏览器访问 https://115.com
2. 登录你的账号
3. 按 F12 打开开发者工具
4. 切换到 Network（网络）标签
5. 刷新页面
6. 点击任意请求
7. 在请求头中找到 `Cookie` 字段
8. 复制完整的Cookie值

Cookie格式示例：
```
UID=12345_A1B2C3D4; CID=E5F6G7H8; SEID=I9J0K1L2M3N4O5P6
```

## 路径输入规则

⚠️ **重要提示**
- 路径必须以 `/` 开头
- 路径严格区分大小写
- 确保路径与115网盘中的实际文件夹名称完全一致

✅ 正确示例：
- `/我的文件/视频`
- `/待处理/下载/电影`
- `/已完成/归档/2024`

❌ 错误示例：
- `我的文件/视频` （缺少开头的 `/`）
- `/我的文件/Video` （大小写不匹配）
- `/我的文件/视频/` （不要以 `/` 结尾）

## 监控和维护

### 检查程序运行状态
```bash
# 查看容器是否在运行
docker ps | grep 115_move_items

# 查看最近的日志
docker-compose logs --tail 50

# 查看日志文件
tail -f logs/move_items.log
```

### 性能优化
- 如果文件很多，可以适当增加 `CHECK_INTERVAL` 减少扫描频率
- 对于大文件，移动过程会有延迟，这是正常现象
- 网络不稳定时可能出现移动失败，程序会记录错误日志

### 故障排查

**问题：容器启动后立即退出**
```bash
# 查看错误日志
docker logs 115_move_items

# 常见原因：
# 1. Cookie格式错误或已过期
# 2. 必填环境变量未设置
# 3. 路径格式错误
```

**问题：找不到目录**
```bash
# 检查路径是否正确
# 1. 确认以 / 开头
# 2. 检查大小写
# 3. 登录115网盘确认目录是否存在
```

**问题：文件移动失败**
```bash
# 查看详细错误信息
docker-compose logs | grep "失败"

# 可能原因：
# 1. 目标目录不存在
# 2. 网络问题
# 3. Cookie已过期
```

## 更新程序

```bash
# 停止并删除旧容器
docker-compose down

# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

## 安全建议

1. **不要将包含Cookie的配置文件提交到Git仓库**
2. **定期检查日志，确保程序正常运行**
3. **备份重要文件，虽然只是移动操作，但仍需谨慎**
4. **使用只读Cookie（如果115支持），降低安全风险**

## 示例配置

### 场景1：自动整理下载文件
```yaml
environment:
  - COOKIE=你的Cookie
  - SOURCE_PATH=/下载
  - TARGET_PATH=/已整理/视频
  - CHECK_INTERVAL=10
  - MIN_FILE_SIZE=500MB
  - LOG_RETENTION_DAYS=30
```

### 场景2：转移大文件到归档目录
```yaml
environment:
  - COOKIE=你的Cookie
  - SOURCE_PATH=/待处理
  - TARGET_PATH=/归档/2024
  - CHECK_INTERVAL=60
  - MIN_FILE_SIZE=5GB
  - LOG_RETENTION_DAYS=7
```

### 场景3：监控临时目录
```yaml
environment:
  - COOKIE=你的Cookie
  - SOURCE_PATH=/临时文件/缓存
  - TARGET_PATH=/备份/自动归档
  - CHECK_INTERVAL=5
  - MIN_FILE_SIZE=100MB
  - LOG_RETENTION_DAYS=3
```

## 高级用法

### 运行多个实例
创建多个 `docker-compose.yml` 文件，监控不同的目录对：

```bash
# 实例1
docker-compose -f docker-compose-task1.yml up -d

# 实例2
docker-compose -f docker-compose-task2.yml up -d
```

### 使用环境变量文件
创建 `.env` 文件：
```env
COOKIE=你的Cookie
SOURCE_PATH=/待处理/下载
TARGET_PATH=/已完成/视频
CHECK_INTERVAL=5
MIN_FILE_SIZE=200MB
LOG_RETENTION_DAYS=7
```

然后简化 `docker-compose.yml`：
```yaml
services:
  move_items:
    build: .
    env_file: .env
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
```

## 技术支持

遇到问题？
1. 查看日志文件：`logs/move_items.log`
2. 检查容器状态：`docker-compose ps`
3. 查看实时日志：`docker-compose logs -f`
4. 进入容器调试：`docker exec -it 115_move_items /bin/bash`
