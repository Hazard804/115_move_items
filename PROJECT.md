# 项目文件说明

## Docker相关文件（发布用）

### 核心文件
- **Dockerfile** - Docker镜像构建文件
- **move_items_docker.py** - Docker版本主程序（环境变量配置）
- **requirements.txt** - Python依赖列表
- **.dockerignore** - Docker构建忽略文件

### 配置文件
- **docker-compose.yml** - 开发环境配置（本地构建）
- **docker-compose.user.yml** - 用户版本（使用Docker Hub镜像）

### 脚本
- **publish-docker.sh** - 发布镜像到Docker Hub
- **docker-start.sh** - 交互式启动脚本

### 文档
- **README.docker.md** - Docker版本使用说明（简洁版）
- **DOCKER.md** - 完整的Docker使用指南
- **PUBLISH.md** - 发布到Docker Hub的完整指南

## 本地运行文件（可选）

- **move_items.py** - 本地运行版本（交互式配置）
- **README.md** - 本地运行说明

## 其他文件

- **.gitignore** - Git忽略文件配置
- **logs/** - 日志目录（运行时生成）

## 发布到Docker Hub的步骤

1. **准备工作**
   ```bash
   # 登录Docker Hub
   docker login
   ```

2. **发布镜像**
   ```bash
   chmod +x publish-docker.sh
   ./publish-docker.sh
   ```

3. **分享给用户**
   - 提供 `docker-compose.user.yml` 文件
   - 提供 `README.docker.md` 使用说明
   - 告知Docker Hub镜像地址

## 用户使用流程

1. 用户下载 `docker-compose.user.yml`
2. 修改其中的配置（Cookie、路径等）
3. 运行 `docker-compose up -d`
4. 完成！

## 文件清理说明

已删除的非Docker构建文件：
- ~~build_linux.sh~~ - Linux打包脚本（PyInstaller）
- ~~build_windows.ps1~~ - Windows打包脚本
- ~~build_docker.sh~~ - 旧的Docker构建脚本
- ~~move_items.spec~~ - PyInstaller配置
- ~~BUILD.md~~ - PyInstaller构建说明

保留理由：
- 专注于Docker部署方式
- 简化项目结构
- 方便用户理解和使用

## 目录结构

```
test_move_items/
├── Dockerfile                    # Docker镜像构建
├── docker-compose.yml            # 开发用配置
├── docker-compose.user.yml       # 用户版配置
├── move_items_docker.py          # Docker版程序
├── move_items.py                 # 本地运行版本
├── requirements.txt              # 依赖列表
├── publish-docker.sh             # 发布脚本
├── docker-start.sh               # 启动脚本
├── README.docker.md              # 使用说明（简洁）
├── DOCKER.md                     # 使用指南（详细）
├── PUBLISH.md                    # 发布指南
├── README.md                     # 项目说明
├── .dockerignore                 # Docker忽略
├── .gitignore                    # Git忽略
└── logs/                         # 日志目录
```
