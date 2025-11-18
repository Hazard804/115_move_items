# 115网盘文件移动工具 - Docker版本
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# 最终镜像
FROM python:3.12-slim

WORKDIR /app

# 从构建阶段复制已安装的包
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制源代码（只复制必要的文件）
COPY move_items_docker.py .

# 创建日志目录和数据目录
RUN mkdir -p /app/logs /app/data

# 设置环境变量默认值
ENV COOKIE="" \
    SOURCE_PATH="" \
    TARGET_PATH="" \
    CHECK_INTERVAL=5 \
    MIN_FILE_SIZE="200MB" \
    LOG_RETENTION_DAYS=7 \
    MODE="auto"

# 数据卷
VOLUME ["/app/logs", "/app/data"]

# 运行程序
CMD ["python", "-u", "move_items_docker.py"]
