from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-development-only")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
AUTH_USER_MODEL = "app.User"

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'drf_yasg',
    'corsheaders',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    'app.apps.AppConfig',

    'import_export',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    "django.middleware.locale.LocaleMiddleware",
    "app.middleware.AdminUzbekLocaleMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'root.urls'

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    'https://pdp-junior-test.netlify.app'
]
CORS_ALLOW_CREDENTIALS = False

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'root.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "600")),
            ssl_require=os.getenv("DB_SSL_REQUIRE", "1") == "1",
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------
# Redis / Celery / Cache
# Productionda CELERY_ENABLED=1 qilib worker va beat processlarini ishga tushiring.
REDIS_URL = os.getenv("REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0"))
CELERY_ENABLED = os.getenv("CELERY_ENABLED", "0") == "1"
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_DEFAULT_QUEUE = "pdp-junior"
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TIME_LIMIT = 120
CELERY_TASK_SOFT_TIME_LIMIT = 90
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_RESULT_EXPIRES = int(os.getenv("CELERY_RESULT_EXPIRES", "3600"))
CELERY_BEAT_SCHEDULE = {
    "expire-stale-test-sessions": {
        "task": "app.tasks.expire_stale_test_sessions_task",
        "schedule": 60 * 5,
    },
    "cleanup-test-sessions": {
        "task": "app.tasks.cleanup_test_sessions_task",
        "schedule": 60 * 60 * 6,
    },
    "dedupe-test-sessions": {
        "task": "app.tasks.dedupe_test_sessions_task",
        "schedule": 60 * 60 * 24,
    },
    "cleanup-jwt-blacklist": {
        "task": "app.tasks.cleanup_jwt_blacklist_task",
        "schedule": 60 * 60 * 24,
    },
    "cleanup-django-sessions": {
        "task": "app.tasks.cleanup_django_sessions_task",
        "schedule": 60 * 60 * 24 * 7,
    },
}

# Test retention (env orqali sozlanadi, mavjud summary/progress saqlanadi):
# 1) Tashlab ketilgan ochiq sessionlar -> o'chiriladi
# 2) Eski javob/savol detaili -> o'chiriladi, TestSession summary qoladi
# 3) Takroriy test sessionlar -> eng yaxshi bittasi qoldiriladi
TEST_UNFINISHED_RETENTION_DAYS = int(os.getenv("TEST_UNFINISHED_RETENTION_DAYS", "7"))
TEST_DETAIL_RETENTION_DAYS = int(os.getenv("TEST_DETAIL_RETENTION_DAYS", "30"))
TEST_DEDUPE_SESSIONS_AFTER_DAYS = int(os.getenv("TEST_DEDUPE_SESSIONS_AFTER_DAYS", "45"))
JWT_BLACKLIST_CLEANUP_ENABLED = os.getenv("JWT_BLACKLIST_CLEANUP_ENABLED", "1") == "1"
DJANGO_SESSION_CLEANUP_ENABLED = os.getenv("DJANGO_SESSION_CLEANUP_ENABLED", "1") == "1"

REDIS_CACHE_ENABLED = os.getenv("REDIS_CACHE_ENABLED", "1" if CELERY_ENABLED else "0") == "1"
REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", REDIS_URL.rsplit("/", 1)[0] + "/1")

if REDIS_CACHE_ENABLED:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_CACHE_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "IGNORE_EXCEPTIONS": True,
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "pdp-junior-local",
        }
    }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGES = [
    ("uz", "O‘zbek"),
    ("ru", "Русский"),
    ("en", "english"),
]

QUESTION_LANGS = ("uz", "ru", "en")

TIME_ZONE = 'Asia/Tashkent'
LANGUAGE_CODE = 'uz'
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/admin'

LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
        }
    }
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

APPEND_SLASH = False

ESKIZ_EMAIL = os.getenv("ESKIZ_EMAIL", "test@gmail.com")
ESKIZ_PASSWORD = os.getenv("ESKIZ_PASSWORD", "")
ESKIZ_SENDER = os.getenv("ESKIZ_SENDER", "4546")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_SHOP_CHAT_ID = os.getenv("TELEGRAM_SHOP_CHAT_ID", "-5326868544")

# ---------------------------------------------------------------------
# MEDIA STORAGE: Local yoki Cloudflare R2 (S3-compatible)
# Yoqish: USE_R2=1 + R2_* env o'zgaruvchilari (.env / hosting)
USE_R2 = os.getenv("USE_R2") == "1"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

if USE_R2:
    from django.core.exceptions import ImproperlyConfigured

    required_r2 = {
        "R2_ACCOUNT_ID": os.getenv("R2_ACCOUNT_ID"),
        "R2_ACCESS_KEY_ID": os.getenv("R2_ACCESS_KEY_ID"),
        "R2_SECRET_ACCESS_KEY": os.getenv("R2_SECRET_ACCESS_KEY"),
        "R2_BUCKET_NAME": os.getenv("R2_BUCKET_NAME"),
    }
    missing = [key for key, value in required_r2.items() if not value]
    if missing:
        raise ImproperlyConfigured(
            "USE_R2=1, lekin yetishmayotgan env: " + ", ".join(missing)
        )

    if "storages" not in INSTALLED_APPS:
        INSTALLED_APPS += ["storages"]

    R2_ACCOUNT_ID = required_r2["R2_ACCOUNT_ID"]
    AWS_ACCESS_KEY_ID = required_r2["R2_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = required_r2["R2_SECRET_ACCESS_KEY"]
    AWS_STORAGE_BUCKET_NAME = required_r2["R2_BUCKET_NAME"]

    AWS_S3_ENDPOINT_URL = os.getenv(
        "R2_ENDPOINT",
        f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    ).rstrip("/")
    AWS_S3_REGION_NAME = "auto"
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_ADDRESSING_STYLE = "path"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_LOCATION = os.getenv("R2_LOCATION", "media").strip("/") or "media"

    R2_PUBLIC_BASE_URL = os.getenv("R2_PUBLIC_BASE_URL", "").rstrip("/")
    AWS_S3_CUSTOM_DOMAIN = (
        R2_PUBLIC_BASE_URL.replace("https://", "").replace("http://", "")
        if R2_PUBLIC_BASE_URL
        else None
    )
    AWS_S3_URL_PROTOCOL = "https:"

    storage_options = {
        "bucket_name": AWS_STORAGE_BUCKET_NAME,
        "location": AWS_LOCATION,
        "endpoint_url": AWS_S3_ENDPOINT_URL,
        "region_name": AWS_S3_REGION_NAME,
        "addressing_style": AWS_S3_ADDRESSING_STYLE,
        "signature_version": AWS_S3_SIGNATURE_VERSION,
        "default_acl": None,
        "querystring_auth": False,
        "file_overwrite": False,
    }
    if AWS_S3_CUSTOM_DOMAIN:
        storage_options["custom_domain"] = AWS_S3_CUSTOM_DOMAIN
        storage_options["url_protocol"] = AWS_S3_URL_PROTOCOL

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": storage_options,
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    if R2_PUBLIC_BASE_URL:
        MEDIA_URL = f"{R2_PUBLIC_BASE_URL}/{AWS_LOCATION}/"
    else:
        # Public URL yo'q — API endpoint orqali URL chiqadi (brauzerda ochilmasligi mumkin).
        # Cloudflare R2 bucket Settings > Public access dan R2_PUBLIC_BASE_URL qo'ying.
        MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/{AWS_LOCATION}/"
