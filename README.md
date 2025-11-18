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
    image: hazard804/115-move-items:latest
    container_name: 115_move_items
    restart: unless-stopped
    environment:
      # 必填：115网盘的Cookie
      - COOKIE=你的115网盘Cookie
      
      # 必填：源目录路径（待检查的目录）
      - SOURCE_PATH=/待处理/下载
      
      # 必填：目标目录路径（文件移动到此目录）
      - TARGET_PATH=/已完成/视频
      
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
  -e COOKIE='你的115网盘Cookie' \
  -e SOURCE_PATH='/待处理/下载' \
  -e TARGET_PATH='/已完成/视频' \
  -e CHECK_INTERVAL=5 \
  -e MIN_FILE_SIZE=200MB \
  -e LOG_RETENTION_DAYS=7 \
  -e TZ=Asia/Shanghai \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  hazard804/115-move-items:latest
```

## 📋 配置说明

### 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|-------|------|--------|------|
| `COOKIE` | ✅ | - | 115网盘的Cookie |
| `SOURCE_PATH` | ✅ | - | 源目录路径（待检查的目录） |
| `TARGET_PATH` | ✅ | - | 目标目录路径（移动目标） |
| `CHECK_INTERVAL` | ❌ | 5 | 检查间隔（分钟），最少2分钟 |
| `MIN_FILE_SIZE` | ❌ | 200MB | 最小文件大小（KB/MB/GB/TB） |
| `LOG_RETENTION_DAYS` | ❌ | 7 | 日志保留天数 |
| `MODE` | ❌ | auto | 运行模式（目前只支持 auto） |
| `TZ` | ❌ | Asia/Shanghai | 时区设置 |

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
docker pull hazard804/115-move-items:latest

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

### Cookie 失效

如果出现认证错误：
1. 重新获取 Cookie
2. 更新环境变量
3. 重启容器

```bash
# 修改 docker-compose.yml 中的 COOKIE
# 然后重启
docker-compose restart
```

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
