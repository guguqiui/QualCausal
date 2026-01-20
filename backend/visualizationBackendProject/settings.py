# """
#  @file: settings.py
#  @Time    : 2025/4/30
#  @Author  : Peinuan qin
#  """
# import os
# from pathlib import Path
# import dj_database_url
# from dotenv import load_dotenv, find_dotenv
#
# load_dotenv()  # 加载 .env 文件（本地开发用）
#
# BASE_DIR = Path(__file__).resolve().parent.parent
# env = os.environ.copy()
#
# # 判断是否在 Heroku 上运行
# IS_HEROKU_APP = "DYNO" in os.environ and "CI" not in os.environ
# DEBUG = not IS_HEROKU_APP
#
# SECRET_KEY = os.getenv("SECRET_KEY", 'django-insecure-m#-8j@rwfijyuxmc)wa5dbr$3h0zavu5$)4@k4_byljmgkfhm-')
# ALLOWED_HOSTS = ["*"]
#
# # Application definition
# INSTALLED_APPS = [
#     "daphne",  # 若你需要 WebSocket 支持
#     "whitenoise.runserver_nostatic",
#     "django.contrib.admin",
#     "django.contrib.auth",
#     "django.contrib.contenttypes",
#     "django.contrib.sessions",
#     "django.contrib.messages",
#     "django.contrib.staticfiles",
#     "rest_framework",
#     "corsheaders",
#     "channels",
#     "core",
# ]
#
# MIDDLEWARE = [
#     "corsheaders.middleware.CorsMiddleware",
#     "django.middleware.security.SecurityMiddleware",
#     "whitenoise.middleware.WhiteNoiseMiddleware",
#     "django.contrib.sessions.middleware.SessionMiddleware",
#     "django.middleware.common.CommonMiddleware",
#     "django.middleware.csrf.CsrfViewMiddleware",
#     "django.contrib.auth.middleware.AuthenticationMiddleware",
#     "django.contrib.messages.middleware.MessageMiddleware",
#     "django.middleware.clickjacking.XFrameOptionsMiddleware",
# ]
#
# ROOT_URLCONF = "visualizationBackendProject.urls"
#
# TEMPLATES = [
#     {
#         "BACKEND": "django.template.backends.django.DjangoTemplates",
#         "DIRS": [Path(BASE_DIR, 'templates')],
#         "APP_DIRS": True,
#         "OPTIONS": {
#             "context_processors": [
#                 "django.template.context_processors.debug",
#                 "django.template.context_processors.request",
#                 "django.contrib.auth.context_processors.auth",
#                 "django.contrib.messages.context_processors.messages",
#             ],
#         },
#     },
# ]
#
# WSGI_APPLICATION = "visualizationBackendProject.wsgi.application"
# ASGI_APPLICATION = "visualizationBackendProject.asgi.application"
#
# # Database
# if DEBUG:
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.sqlite3",
#             "NAME": BASE_DIR / "db.sqlite3",
#         }
#     }
# else:
#     DATABASES = {
#         "default": dj_database_url.config(
#             env="DATABASE_URL",
#             conn_max_age=600,
#             ssl_require=True,
#         )
#     }
#
# # Channels
# if DEBUG:
#     CHANNEL_LAYERS = {
#         "default": {
#             "BACKEND": "channels.layers.InMemoryChannelLayer",
#         }
#     }
# else:
#     CHANNEL_LAYERS = {
#         "default": {
#             "BACKEND": "channels_redis.core.RedisChannelLayer",
#             "CONFIG": {
#                 "hosts": [(os.getenv("REDIS_URL", "redis://localhost:6379"))],
#             },
#         }
#     }
#
# # Static files
# STATIC_URL = "/static/"
# STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]  # 让 Django 识别 static 目录
# STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")  # 用于 collectstatic
#
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
#
# # Default primary key field
# DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
#
# # CORS settings
# # CORS_ALLOW_ALL_ORIGINS = True
#
#
# # CSRF_TRUSTED_ORIGINS = [
# #     "https://visualization-django-backend-53b841bdee5f.herokuapp.com"
# # ]
#
# # CORS_ALLOWED_ORIGINS = [
# #     "https://visualization-frontend-menghan-a9837b9f84a9.herokuapp.com",
# #     "https://visualization-django-backend-53b841bdee5f.herokuapp.com",
# #     "http://localhost:8080",
# # ]
# #
# # CORS_ALLOW_CREDENTIALS = True
#
# CORS_ALLOW_ALL_ORIGINS = True
# CORS_ALLOW_CREDENTIALS = True
#
# # Logging
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "handlers": {
#         "console": {"class": "logging.StreamHandler"},
#     },
#     "root": {
#         "handlers": ["console"],
#         "level": "INFO",
#     },
# }



"""
 @file: aws_settings_template.py
 @Time    : 2025/6/14
 @Author  : Peinuan qin
 """
"""
 @file: settings.py
 @Time    : 2025/4/30
 @Author  : Peinuan qin
 """
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv, find_dotenv

load_dotenv()  # 加载 .env 文件（本地开发用）

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv_path = find_dotenv(str(BASE_DIR / ".env"))
if load_dotenv(dotenv_path):
    print(f"✅ Successfully loaded .env from {dotenv_path}")
else:
    print("⚠️ No .env file found or failed to load.")

env = os.environ.copy()

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# API_BASE = "http://ec2-13-213-43-132.ap-southeast-1.compute.amazonaws.com"  # large
# API_BASE = "http://13.214.211.82" # larger for 7.7 data collection (big)
# API_BASE = "http://13.213.50.213"  # 小的，for paper writing
API_BASE = "http://13.250.111.20"  # 小的，for paper revision

SECRET_KEY = os.getenv("SECRET_KEY", 'django-insecure-m#-8j@rwfijyuxmc)wa5dbr$3h0zavu5$)4@k4_byljmgkfhm-')
ALLOWED_HOSTS = ["*"]

# Application definition
INSTALLED_APPS = [
    "daphne",  # 若你需要 WebSocket 支持
    "whitenoise.runserver_nostatic",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "channels",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "visualizationBackendProject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [Path(BASE_DIR, 'templates')],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "visualizationBackendProject.wsgi.application"
ASGI_APPLICATION = "visualizationBackendProject.asgi.application"

# Database
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            env="DATABASE_URL",
            conn_max_age=600,
            ssl_require=False,  # ✅ 改为 False
        )
    }

# Channels
if DEBUG:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [(os.getenv("REDIS_URL", "redis://localhost:6379"))],
            },
        }
    }


# Static files
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]  # 让 Django 识别 static 目录
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")  # 用于 collectstatic

# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# Default primary key field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# CORS_ALLOW_ALL_ORIGINS = True
# CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "https://13.214.211.82",
    "http://localhost:8080",
    "http://47.129.207.110",
]

CORS_ALLOW_CREDENTIALS = True


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}



# Service Connection Check Logs (only for initial debugging, safe to remove later)
import psycopg2
import redis
from urllib.parse import urlparse

if not DEBUG:
    print("🧪 [PRODUCTION MODE] Checking container-based PostgreSQL and Redis connections...")

    # PostgreSQL 连接检查
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            parsed = urlparse(db_url)
            conn = psycopg2.connect(
                dbname=parsed.path.lstrip("/"),
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port,
            )
            print("✅ Successfully connected to PostgreSQL via DATABASE_URL!")
            conn.close()
        except Exception as e:
            print(f"❌ PostgreSQL Connection Error via DATABASE_URL: {e}")
    else:
        print("❌ DATABASE_URL is not set!")

    # Redis 连接检查
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")  # 👈 默认是 localhost，容易出错
        parsed_redis = urlparse(redis_url)
        redis_client = redis.Redis(
            host=parsed_redis.hostname,
            port=parsed_redis.port,
            db=0,
            decode_responses=True,
        )
        redis_client.ping()
        print(f"✅ Successfully connected to Redis at {parsed_redis.hostname}:{parsed_redis.port}!")
    except Exception as e:
        print(f"❌ Redis Connection Error (production): {e}")