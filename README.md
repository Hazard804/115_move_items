# 115网盘文件移动工具

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

1. **创建 `docker-compose.yml` 文件**：

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
      
      # 方式1：多组路径映射（推荐）
      - PATH_MAPPINGS=/待处理/下载->/已完成/视频,/临时/缓存->/归档/2024
      
      # 方式2：单组映射（二选一，兼容旧版）
      # - SOURCE_PATH=/待处理/下载
      # - TARGET_PATH=/已完成/视频
      
      # 可选：排除特定后缀的文件
      - EXCLUDE_EXTENSIONS=.txt,.nfo,.jpg,.png,.srt
      
      # 可选：检查间隔（分钟），默认5分钟
      - CHECK_INTERVAL=5
      
      # 可选：最小文件大小，支持 KB/MB/GB/TB，默认200MB
      - MIN_FILE_SIZE=200MB
      
      # 可选：日志保留天数，默认7天
      - LOG_RETENTION_DAYS=7
      
      # 可选：时区设置
      - TZ=Asia/Shanghai
    
    volumes:
      # 日志目录映射（可选）
      - ./logs:/app/logs
      
      # 数据目录映射（持久化cookie）
      - ./data:/app/data
```

2. **启动服务**：

```bash
docker-compose up -d
```

3. **查看日志**：

```bash
# 查看实时日志
docker-compose logs -f

# 查看历史日志
ls logs/
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
| `PATH_MAPPINGS` | ⭐ | - | 多组路径映射（推荐）格式: `源1->目标1,源2->目标2` |
| `SOURCE_PATH` | ⭐ | - | 源目录路径（单组映射，兼容旧版） |
| `TARGET_PATH` | ⭐ | - | 目标目录路径（单组映射，兼容旧版） |
| `EXCLUDE_EXTENSIONS` | ❌ | - | 排除的文件后缀，如: `.txt,.tmp,.log` |
| `CHECK_INTERVAL` | ❌ | 5 | 检查间隔（分钟），最少2分钟 |
| `MIN_FILE_SIZE` | ❌ | 200MB | 最小文件大小（KB/MB/GB/TB） |
| `LOG_RETENTION_DAYS` | ❌ | 7 | 日志保留天数 |
| `API_TIMEOUT` | ❌ | 120 | API请求超时时间（秒），最少10秒 |
| `API_RETRY_TIMES` | ❌ | 3 | API请求失败重试次数（1-10次） |
| `BARK_URL` | ❌ | - | Bark通知URL，仅失败时通知，格式: `https://api.day.app/你的key` |
| `MODE` | ❌ | auto | 运行模式（目前只支持 auto） |
| `TZ` | ❌ | Asia/Shanghai | 时区设置 |

> **注意**：`PATH_MAPPINGS` 和 `SOURCE_PATH`/`TARGET_PATH` 二选一即可。推荐使用 `PATH_MAPPINGS` 支持多组映射。

### 🆕 多组路径映射

使用 `PATH_MAPPINGS` 可以配置多组源目录到目标目录的映射：

```yaml
environment:
  - PATH_MAPPINGS=/待处理/下载->/已完成/视频,/临时/缓存->/归档/2024,/新增/测试->/备份/测试
```

**格式说明**：
- 使用 `->` 分隔源路径和目标路径
- 使用 `,` 分隔多组映射
- 示例：`源路径1->目标路径1,源路径2->目标路径2`

**Docker Compose 完整示例**：

```yaml
version: '3.8'

services:
  move_items:
    image: hazard084/115-move-items:latest
    container_name: 115_move_items
    restart: unless-stopped
    network_mode: host
    environment:
      - COOKIE=你的115网盘Cookie
      
      # 多组路径映射（推荐）
      - PATH_MAPPINGS=/待处理/下载->/已完成/视频,/临时/缓存->/归档/2024
      
      # 排除特定后缀的文件
      - EXCLUDE_EXTENSIONS=.txt,.nfo,.jpg,.png
      
      - CHECK_INTERVAL=5
      - MIN_FILE_SIZE=200MB
      - LOG_RETENTION_DAYS=7
      - TZ=Asia/Shanghai
    
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
```

### 🆕 排除文件后缀

使用 `EXCLUDE_EXTENSIONS` 可以排除特定后缀的文件不进行移动：

```yaml
environment:
  # 排除文本文件和临时文件
  - EXCLUDE_EXTENSIONS=.txt,.tmp,.log
  
  # 排除图片和字幕文件
  - EXCLUDE_EXTENSIONS=.jpg,.png,.nfo,.srt
  
  # 也可以不带点号
  - EXCLUDE_EXTENSIONS=txt,tmp,log
```

### 🆕 Bark 失败通知

使用 `BARK_URL` 可以在操作失败时接收推送通知（仅失败时通知）：

```yaml
environment:
  # 配置 Bark 通知 URL
  - BARK_URL=https://api.day.app/你的Bark密钥
```

**如何获取 Bark URL**：
1. 在 iPhone/iPad 上下载安装 [Bark App](https://apps.apple.com/cn/app/bark/id1403753865)
2. 打开 App，复制顶部显示的推送 URL
3. URL 格式如: `https://api.day.app/xxxxxxxxxxxxx`

**通知时机**：
- ✅ 仅在以下情况发送通知：
  - API 请求超时（重试3次后仍失败）
  - API 请求错误（重试3次后仍失败）
  - Cookie 失效检测
- ❌ 正常运行时不会发送通知

### 单组映射（兼容旧版）

如果只需要一组映射，可以继续使用旧的配置方式：

```yaml
environment:
  - SOURCE_PATH=/待处理/下载
  - TARGET_PATH=/已完成/视频
```

### 获取 115网盘 Cookie

1. 访问 https://115.com 并登录
2. 按 `F12` 打开开发者工具
3. 切换到 `Network`（网络）标签
4. 刷新页面，选择任意请求
5. 在请求头中找到 `Cookie` 字段
6. 复制完整的 Cookie 值

### 路径输入规则

- 路径必须以 `/` 开头
- 路径严格区分大小写
- 示例：`/我的文件/视频/电影`

## 📂 目录结构

```
.
├── logs/              # 日志文件目录（映射到宿主机）
│   ├── move_items_20241118.log
│   └── move_items_20241117.log
└── data/              # 数据目录（持久化 cookie）
    └── cookies.txt
```

## 🔧 管理命令

### 查看运行状态

```bash
docker ps | grep 115_move_items
```

### 停止服务

```bash
docker-compose stop
# 或
docker stop 115_move_items
```

### 重启服务

```bash
docker-compose restart
# 或
docker restart 115_move_items
```

### 更新镜像

```bash
# 拉取最新镜像
docker pull hazard084/115-move-items:latest

# 重新创建容器
docker-compose up -d
```

### 删除服务

```bash
docker-compose down
# 或
docker rm -f 115_move_items
```

## 📊 日志查看

### 实时日志

```bash
# 使用 docker-compose
docker-compose logs -f

# 使用 docker
docker logs -f 115_move_items

# 查看最近100行
docker logs --tail 100 115_move_items
```

### 历史日志文件

日志文件保存在 `logs/` 目录，按天分割：

```bash
# 查看日志文件列表
ls -lh logs/

# 查看特定日期的日志
cat logs/move_items_20241118.log
```

## ⚠️ 注意事项

1. **路径检查**：路径输入时请仔细检查大小写
2. **递归扫描**：程序会遍历源目录的所有子目录
3. **操作不可逆**：移动操作不可逆，请谨慎配置
4. **先行测试**：建议先在测试目录验证功能
5. **Cookie 有效期**：Cookie 可能过期，需要定期更新
6. **网络要求**：需要能够访问 115.com

## 🔍 故障排查

### 容器无法启动

```bash
# 查看容器日志
docker logs 115_move_items

# 检查环境变量配置
docker inspect 115_move_items | grep -A 20 Env
```

### Cookie 验证卡住或网络问题

如果容器启动后卡在 "正在验证Cookie..." 步骤：

**原因**：使用了全局代理（VPN/TUN），Docker 容器无法正确使用代理

**解决方案**：使用宿主机网络模式（已在上面的示例中包含）

```yaml
# docker-compose.yml 中添加
network_mode: host
```

或在 docker run 命令中添加：
```bash
--network host
```

### API 请求超时或频繁卡住

**现象**：扫描目录时卡住，或者频繁出现超时错误

**解决方案**：调整超时和重试配置

```yaml
environment:
  # 增加超时时间（默认120秒）
  - API_TIMEOUT=180
  
  # 增加重试次数（默认3次）
  - API_RETRY_TIMES=5
```

**说明**：
- `API_TIMEOUT`: 单次API请求的最大等待时间（秒），建议范围 10-120
- `API_RETRY_TIMES`: API失败后的重试次数，建议范围 1-10
- 程序会在每次重试之间自动增加等待时间
- 超时的操作不会中断整个程序，会跳过继续处理下一个

**注意**：
- Windows 系统下超时机制基于网络库自身超时，可能不够精确
- Linux/Unix 系统使用信号机制，超时控制更准确

### Cookie 失效

程序会**自动检测 Cookie 是否失效**：
- 每10轮检查会验证一次 Cookie 状态
- 移动文件时如果遇到认证错误会立即提醒
- 发现 Cookie 失效后程序会停止并提示更新步骤

**更新 Cookie 的步骤**：

1. 重新获取 Cookie（见上面的获取方法）
2. 更新配置（选择其中一种方式）：

```bash
# 方式1：修改环境变量（推荐）
# 编辑 docker-compose.yml，更新 COOKIE 环境变量
vim docker-compose.yml
docker-compose restart
# 新 Cookie 会自动覆盖持久化文件中的旧 Cookie

# 方式2：删除持久化文件
rm data/115-cookies.txt
# 然后修改 docker-compose.yml 并重启
docker-compose restart
```

**Cookie 优先级**：
- ✅ 优先使用环境变量中的 Cookie
- ✅ 环境变量为空时，从 `data/115-cookies.txt` 读取
- ✅ Cookie 验证成功后会自动保存/更新到文件

### 文件没有移动

1. 检查源目录和目标目录路径是否正确
2. 检查文件大小是否满足 `MIN_FILE_SIZE` 条件
3. 查看日志文件了解详细信息

## 🛠️ 从源码构建

如果你想自己构建 Docker 镜像：

```bash
# 克隆仓库
git clone https://github.com/Hazard804/115_move_items.git
cd 115_move_items

# 构建镜像
docker build -t 115-move-items:custom .

# 运行
docker run -d \
  --name 115_move_items \
  -e COOKIE='xxx' \
  -e SOURCE_PATH='/xxx' \
  -e TARGET_PATH='/xxx' \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  115-move-items:custom
```

## 📦 技术栈

- **Python 3.12**：运行环境
- **p115client**：115网盘 API 客户端
- **Docker**：容器化部署

## 📄 许可证

本项目仅供学习交流使用，请勿用于商业用途。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 技术支持

如遇问题，请：
1. 查看日志文件获取详细信息
2. 检查 Cookie 是否有效
3. 验证路径格式是否正确
4. 确认网络连接正常
5. 提交 GitHub Issue 寻求帮助
