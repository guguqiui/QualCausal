# Dockerfile
FROM python:3.9-slim

# 环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 设置工作目录
WORKDIR /app

# 安装 psycopg2 所需的系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    dos2unix && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 复制代码
COPY . /app/

# 设置入口脚本权限
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 启动服务
ENTRYPOINT ["/app/entrypoint.sh"]
