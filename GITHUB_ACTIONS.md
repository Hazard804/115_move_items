# 使用 GitHub Actions 自动构建和发布 Docker 镜像

## 优势

相比在本地构建，使用 GitHub Actions 有以下优势：
- ✅ **无需本地网络环境**：在 GitHub 服务器上构建，速度快且稳定
- ✅ **自动化流程**：推送代码即可自动构建发布
- ✅ **多平台支持**：自动构建 linux/amd64 和 linux/arm64 架构
- ✅ **版本管理**：通过 Git Tag 轻松管理版本
- ✅ **免费额度**：GitHub Actions 对公开仓库完全免费

## 配置步骤

### 1. 在 GitHub 仓库中设置 Secrets

前往你的 GitHub 仓库：`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

添加以下两个 secrets：

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `DOCKER_USERNAME` | Docker Hub 用户名 | 你的 Docker Hub 登录用户名 |
| `DOCKER_PASSWORD` | Docker Hub 访问令牌 | 在 Docker Hub 创建 Access Token (推荐) 或使用密码 |

#### 如何创建 Docker Hub Access Token（推荐）：

1. 登录 [Docker Hub](https://hub.docker.com/)
2. 点击右上角头像 → `Account Settings`
3. 选择 `Security` → `New Access Token`
4. 输入描述（如：`GitHub Actions`），权限选择 `Read, Write, Delete`
5. 点击 `Generate`，复制生成的 token
6. 将这个 token 作为 `DOCKER_PASSWORD` 的值

### 2. 推送代码到 GitHub

确保你的代码已推送到 GitHub 仓库，并且包含以下文件：
- `.github/workflows/docker-publish.yml` （已创建）
- `Dockerfile`
- `move_items_docker.py`
- 其他必要文件

## 使用方式

### 方式一：通过 Git Tag 发布版本（推荐）

这种方式适合发布正式版本：

```powershell
# 1. 确保代码已提交
git add .
git commit -m "准备发布 v1.0.0"

# 2. 创建并推送 tag
git tag v1.0.0
git push origin v1.0.0

# 3. GitHub Actions 会自动触发构建和发布
```

版本标签说明：
- `v1.0.0` → 生成 tags: `1.0.0`, `1.0`, `1`, `latest`
- `v1.2.3` → 生成 tags: `1.2.3`, `1.2`, `1`, `latest`

### 方式二：推送到 main 分支

这种方式适合测试：

```powershell
# 1. 提交并推送到 main 分支
git add .
git commit -m "更新代码"
git push origin main

# 2. GitHub Actions 会自动触发构建
# 生成的镜像标签为: main
```

### 方式三：手动触发

1. 前往 GitHub 仓库的 `Actions` 标签
2. 选择 `Build and Publish Docker Image`
3. 点击 `Run workflow` → `Run workflow`

## 查看构建状态

### 1. 在 GitHub Actions 页面查看

前往仓库的 `Actions` 标签，可以看到：
- ✅ 构建成功（绿色勾）
- ❌ 构建失败（红色叉）
- 🟡 构建中（黄色圆圈）

点击具体的 workflow run 可以查看详细日志。

### 2. 构建完成后

构建成功后，你可以在 [Docker Hub](https://hub.docker.com/) 上找到你的镜像。

## 使用发布的镜像

### 用户使用方式

发布成功后，任何人都可以使用你的镜像：

```yaml
# docker-compose.yml
version: '3.8'

services:
  move_items:
    image: 你的用户名/115-move-items:latest
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

或直接运行：

```bash
docker pull 你的用户名/115-move-items:latest
docker run -d \
  --name 115_move_items \
  -e COOKIE='xxx' \
  -e SOURCE_PATH='/xxx' \
  -e TARGET_PATH='/xxx' \
  -v ./logs:/app/logs \
  -v ./data:/app/data \
  你的用户名/115-move-items:latest
```

## 版本管理最佳实践

### 语义化版本号

遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)：

```
v主版本号.次版本号.修订号

例如：v1.2.3
- 1：主版本号（重大变更）
- 2：次版本号（新功能）
- 3：修订号（bug 修复）
```

### 发布流程示例

```powershell
# 修复 bug - 增加修订号
git tag v1.0.1
git push origin v1.0.1

# 添加新功能 - 增加次版本号
git tag v1.1.0
git push origin v1.1.0

# 重大更新 - 增加主版本号
git tag v2.0.0
git push origin v2.0.0
```

### 查看现有标签

```powershell
# 查看所有标签
git tag

# 查看远程标签
git ls-remote --tags origin

# 删除本地标签
git tag -d v1.0.0

# 删除远程标签
git push origin :refs/tags/v1.0.0
```

## 构建配置说明

### Workflow 配置文件：`.github/workflows/docker-publish.yml`

关键配置：

```yaml
# 触发条件
on:
  push:
    tags:
      - 'v*'        # 推送 v* 标签时触发
    branches:
      - main        # 推送到 main 分支时触发
  workflow_dispatch: # 允许手动触发

# 支持的平台
platforms: linux/amd64,linux/arm64
```

### 自动生成的镜像标签

Workflow 会根据不同情况生成不同标签：

| Git 操作 | 生成的 Docker 标签 |
|---------|------------------|
| `git push origin v1.2.3` | `1.2.3`, `1.2`, `1`, `latest` |
| `git push origin main` | `main` |
| Pull Request #123 | `pr-123` |

## 常见问题

### Q1: 构建失败，提示 "secrets.DOCKER_USERNAME not found"

**原因**：未在 GitHub 仓库中配置 Secrets。

**解决**：按照上面的步骤在仓库设置中添加 `DOCKER_USERNAME` 和 `DOCKER_PASSWORD`。

### Q2: 构建成功但推送失败

**原因**：Docker Hub 认证失败。

**解决**：
1. 检查 `DOCKER_USERNAME` 是否正确
2. 检查 `DOCKER_PASSWORD` 是否有效（建议使用 Access Token）
3. 确认 Docker Hub 账户状态正常

### Q3: 构建时间过长

**原因**：GitHub Actions 需要下载依赖和构建多平台镜像。

**解决**：
- Workflow 已配置构建缓存，第二次构建会快很多
- 首次构建预计 5-10 分钟
- 后续构建预计 2-3 分钟

### Q4: 如何只构建特定平台？

修改 `.github/workflows/docker-publish.yml`：

```yaml
# 只构建 amd64
platforms: linux/amd64

# 或只构建 arm64
platforms: linux/arm64
```

### Q5: 如何构建私有镜像？

在 Docker Hub 上将仓库设置为 Private（需要付费账户），Workflow 配置不需要更改。

## 进阶配置

### 添加构建徽章

在你的 `README.md` 中添加：

```markdown
![Docker Build](https://github.com/你的用户名/仓库名/actions/workflows/docker-publish.yml/badge.svg)
```

### 自动更新 Docker Hub 描述

在 workflow 中添加步骤：

```yaml
- name: Update Docker Hub Description
  uses: peter-evans/dockerhub-description@v3
  with:
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_PASSWORD }}
    repository: ${{ secrets.DOCKER_USERNAME }}/115-move-items
    readme-filepath: ./README.md
```

### 构建通知

可以添加构建成功/失败的通知，比如发送到 Telegram、Discord、邮件等。

## 对比：本地构建 vs GitHub Actions

| 特性 | 本地构建 | GitHub Actions |
|-----|---------|----------------|
| 网络要求 | 需要稳定的网络 | 使用 GitHub 服务器网络 |
| 构建速度 | 取决于本地网络 | 通常更快更稳定 |
| 多平台支持 | 需要配置 buildx | 自动支持 |
| 自动化程度 | 手动执行脚本 | 全自动 |
| 版本管理 | 手动管理 tag | Git tag 自动关联 |
| 成本 | 使用本地资源 | 公开仓库免费 |

## 下一步

1. ✅ 配置好 GitHub Secrets
2. ✅ 推送代码并创建第一个版本标签
3. ✅ 观察 GitHub Actions 构建过程
4. ✅ 在 Docker Hub 验证镜像
5. ✅ 分享给用户使用

## 参考链接

- [GitHub Actions 文档](https://docs.github.com/cn/actions)
- [Docker Hub](https://hub.docker.com/)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [语义化版本](https://semver.org/lang/zh-CN/)
