#!/bin/bash
set -e  # 遇到任何错误立即退出脚本

# 等待 PostgreSQL 启动
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 2
done
echo "✅ PostgreSQL is up."

# 等待 Redis 启动（如果你确实用到它）
echo "⏳ Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 2
done
echo "✅ Redis is up."

# 数据库迁移
echo "🔧 Running database migrations..."
python manage.py migrate

# 收集静态资源
echo "📦 Collecting static files..."
rm -rf /app/staticfiles/*
#python manage.py collectstatic --noinput
if python manage.py collectstatic --noinput; then
  echo "✅ Static files collected successfully."
else
  echo "❌ collectstatic failed. Exiting."
  exit 1
fi

# 创建超级用户（如不存在）
echo "👤 Creating superuser if needed..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="qpn").exists():
    User.objects.create_superuser("qpn", "12@3.com", "123")
    print("✅ Superuser created.")
else:
    print("ℹ️  Superuser already exists.")
EOF

# 启动 Gunicorn（WSGI）
echo "🚀 Starting Gunicorn..."
exec gunicorn visualizationBackendProject.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 1000
