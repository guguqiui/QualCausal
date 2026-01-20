#!/bin/bash
set -e  # 遇到错误就退出

# 等待 PostgreSQL 启动
echo "Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 2
done
echo "PostgreSQL is up."

# 等待 Redis 启动
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 2
done
echo "Redis is up."

# 数据库迁移
echo "Running migrations..."
python manage.py migrate

# 收集静态文件

#rm -rf /app/staticfiles/

echo "Collecting static files..."
python manage.py collectstatic --noinput

# 创建超级用户（若不存在）
echo "Creating superuser if needed..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="qpn").exists():
    User.objects.create_superuser("qpn", "12@3.com", "123")
    print("Superuser created.")
else:
    print("Superuser already exists.")
EOF

# 启动 Daphne（ASGI）
echo "Starting Daphne..."
#exec daphne -b 0.0.0.0 -p 8000 automaticExtractionBackend.asgi:application
exec gunicorn automaticExtractionBackend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 16 \
    --timeout 300