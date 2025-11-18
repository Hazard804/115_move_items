# 115网盘文件移动工具 - Docker版本
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc g++

# 复制源代码
COPY move_items.py .
COPY move_items_docker.py .
COPY README.md .

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
