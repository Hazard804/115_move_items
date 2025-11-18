# 115网盘文件移动工具

一个功能强大的115网盘文件自动移动工具，支持手动和自动两种模式。

## 功能特性

### 手动模式
- 浏览指定目录的文件
- 支持路径或ID方式指定目录
- 交互式选择文件进行移动
- 实时显示文件信息（大小、路径等）

### 自动模式
- 定期自动检查指定目录
- 根据文件大小自动移动符合条件的文件
- 遍历子目录，支持深度扫描
- 可自定义检查间隔和文件大小阈值
- 完整的日志记录

## 使用方法

### 直接使用可执行文件（推荐）

#### Linux系统
```bash
# 赋予执行权限
chmod +x move_items_linux

# 运行程序
./move_items_linux
```

#### Windows系统
直接双击 `move_items_windows.exe` 运行

### 从源码运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python move_items.py
```

## 打包说明

### 在Linux上打包
```bash
chmod +x build_linux.sh
./build_linux.sh
```

### 在Windows上打包
```powershell
.\build_windows.ps1
```

### 使用Docker跨平台打包
```bash
chmod +x build_docker.sh
./build_docker.sh
```

## 首次运行

1. 程序会要求输入115网盘的Cookie
2. Cookie获取方法：
   - 访问 https://115.com 并登录
   - 按F12打开开发者工具
   - 在Network标签找到任意请求
   - 复制请求头中的Cookie值
3. Cookie验证成功后会自动保存
4. 后续运行会询问是否复用已保存的Cookie

## 配置说明

### 日志配置
- 日志按天保存在 `logs/` 目录
- 可自定义日志保留天数（默认7天）
- 自动清理过期日志

### 路径输入规则
- 路径必须以 `/` 开头
- 路径严格区分大小写
- 示例：`/我的文件/视频/电影`

### 自动模式配置
- 源目录：待检查的目录（包含子目录）
- 目标目录：文件移动的目标位置
- 检查间隔：最少2分钟
- 最小文件大小：支持KB、MB、GB、TB单位

## 注意事项

⚠️ **重要提示**
1. 路径输入时请仔细检查大小写
2. 自动模式会遍历源目录的所有子目录
3. 移动操作不可逆，请谨慎操作
4. 建议先在测试目录验证功能
5. 按Ctrl+C可随时停止自动模式

## 依赖项

- p115client：115网盘API客户端
- blacksheep：Web框架（API依赖）
- Python 3.8+

## 文件说明

- `move_items.py`：主程序
- `115-cookies.txt`：Cookie存储文件（首次运行后生成）
- `logs/`：日志目录（运行后自动创建）
- `requirements.txt`：Python依赖列表
- `build_*.sh/ps1`：打包脚本
- `Dockerfile`：Docker打包配置

## 技术支持

如遇问题，请检查：
1. Cookie是否有效
2. 路径格式是否正确
3. 网络连接是否正常
4. 查看日志文件获取详细信息

## 许可证

本项目仅供学习交流使用，请勿用于商业用途。
