from pathlib import Path
import os
import sys
from datetime import timedelta

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------
# Env helperlar
# ---------------------------------------------------------------------

def env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def env_int(name, default):
    try:
        return int(os.getenv(name, "") or default)
    except (TypeError, ValueError):
        return default


def env_list(name, default=""):
    raw = os.getenv(name, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


# DEBUG endi env orqali boshqariladi. Production'da u YOQILMASLIGI kerak:
# Django DEBUG=True holatida har bir SQL so'rovni xotirada saqlaydi va
# uzoq ishlaydigan worker sekin-asta xotirani to'ldirib boradi.
DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-development-only"
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY env o'zgaruvchisi majburiy (DEBUG=0 holatida)."
        )

# Vergul bilan ajratilgan ro'yxat: ALLOWED_HOSTS=api.pdp.uz,www.pdp.uz
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS") or (["*"] if DEBUG else [])
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS env o'zgaruvchisi majburiy (DEBUG=0 holatida)."
    )

# Render/Heroku kabi platformalar tashqi hostni env orqali beradi.
_external_host = os.getenv("RENDER_EXTERNAL_HOSTNAME") or os.getenv("EXTERNAL_HOSTNAME")
if _external_host and _external_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_external_host)

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
# Qo'shimcha originlarni env orqali bering: CORS_ALLOWED_ORIGINS=https://a.uz,https://b.uz
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS") + [
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
# Preflight javobini brauzer 24 soat keshlaydi — har so'rovdan oldingi
# ortiqcha OPTIONS chaqiruvlari yo'qoladi.
CORS_PREFLIGHT_MAX_AGE = env_int("CORS_PREFLIGHT_MAX_AGE", 86400)

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS") or [
    origin for origin in CORS_ALLOWED_ORIGINS if origin.startswith("https://")
]

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

# DB_CONN_MAX_AGE — ulanishni necha soniya qayta ishlatish. Har so'rovda yangi
# TCP+TLS ulanish ochish 5-30 ms turadi; 500 foydalanuvchida bu sezilarli.
# Ammo juda katta qiymat Postgres'ning max_connections limitini yeb qo'yadi:
#   kerakli ulanishlar = worker soni x thread soni (+ celery worker'lari)
# Render Starter Postgres'da limit past, shuning uchun default 120 soniya.
DB_CONN_MAX_AGE = env_int("DB_CONN_MAX_AGE", 120)

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=DB_CONN_MAX_AGE,
            conn_health_checks=True,
            ssl_require=env_bool("DB_SSL_REQUIRE", True),
        )
    }
    DATABASES["default"].setdefault("OPTIONS", {})
    # Bitta so'rov 15 soniyadan ko'p ishlasa uziladi — sekin so'rov butun
    # worker'ni ushlab turmasligi uchun.
    DATABASES["default"]["OPTIONS"].setdefault(
        "options", f"-c statement_timeout={env_int('DB_STATEMENT_TIMEOUT_MS', 15000)}"
    )
    DATABASES["default"]["OPTIONS"].setdefault(
        "connect_timeout", env_int("DB_CONNECT_TIMEOUT", 10)
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {"timeout": 20},
        }
    }

# ---------------------------------------------------------------------
# Redis / Celery / Cache
# ---------------------------------------------------------------------
# REDIS_URL berilgan bo'lsa kesh, throttle va Celery o'shanga ulanadi.
# Berilmasa — mahalliy xotira keshi (faqat development uchun): u har bir
# gunicorn worker'ida alohida bo'lgani uchun productionda kesh ham,
# rate limiting ham ishonchsiz bo'ladi.
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL") or ""
REDIS_AVAILABLE = bool(REDIS_URL)

if not REDIS_URL and DEBUG:
    REDIS_URL = "redis://127.0.0.1:6379/0"


def _redis_db(url: str, index: int) -> str:
    """Bitta Redis instansiyasining turli DB raqamlariga bo'ladi."""
    if not url:
        return ""
    base, _, tail = url.rpartition("/")
    if base and tail.isdigit():
        return f"{base}/{index}"
    return f"{url.rstrip('/')}/{index}"


CELERY_ENABLED = env_bool("CELERY_ENABLED", REDIS_AVAILABLE)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_DEFAULT_QUEUE = "pdp-junior"
CELERY_TASK_ROUTES = {
    # Uzoq davom etadigan maintenance vazifalari alohida navbatda —
    # ular tez sinxronizatsiya vazifalarini kutdirib qo'ymasin.
    "app.tasks.run_full_maintenance_task": {"queue": "pdp-junior-maintenance"},
    "app.tasks.cleanup_test_sessions_task": {"queue": "pdp-junior-maintenance"},
    "app.tasks.dedupe_test_sessions_task": {"queue": "pdp-junior-maintenance"},
}
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = False
CELERY_TASK_TIME_LIMIT = env_int("CELERY_TASK_TIME_LIMIT", 300)
CELERY_TASK_SOFT_TIME_LIMIT = env_int("CELERY_TASK_SOFT_TIME_LIMIT", 240)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = env_int("CELERY_WORKER_MAX_TASKS_PER_CHILD", 200)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_POOL_LIMIT = env_int("CELERY_BROKER_POOL_LIMIT", 10)
CELERY_RESULT_EXPIRES = env_int("CELERY_RESULT_EXPIRES", 3600)
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
    "refresh-ranking-cache": {
        "task": "app.tasks.warm_public_caches_task",
        "schedule": 60 * 5,
    },
}

# Test retention (env orqali sozlanadi, mavjud summary/progress saqlanadi):
# 1) Tashlab ketilgan ochiq sessionlar -> o'chiriladi
# 2) Eski javob/savol detaili -> o'chiriladi, TestSession summary qoladi
# 3) Takroriy test sessionlar -> eng yaxshi bittasi qoldiriladi
TEST_UNFINISHED_RETENTION_DAYS = env_int("TEST_UNFINISHED_RETENTION_DAYS", 7)
TEST_DETAIL_RETENTION_DAYS = env_int("TEST_DETAIL_RETENTION_DAYS", 30)
TEST_DEDUPE_SESSIONS_AFTER_DAYS = env_int("TEST_DEDUPE_SESSIONS_AFTER_DAYS", 45)
JWT_BLACKLIST_CLEANUP_ENABLED = env_bool("JWT_BLACKLIST_CLEANUP_ENABLED", True)
DJANGO_SESSION_CLEANUP_ENABLED = env_bool("DJANGO_SESSION_CLEANUP_ENABLED", True)

REDIS_CACHE_ENABLED = env_bool("REDIS_CACHE_ENABLED", REDIS_AVAILABLE)
REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL") or _redis_db(REDIS_URL, 1)

if REDIS_CACHE_ENABLED and REDIS_CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_CACHE_URL,
            "TIMEOUT": env_int("CACHE_DEFAULT_TIMEOUT", 300),
            "KEY_PREFIX": os.getenv("CACHE_KEY_PREFIX", "pdpj"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 3,
                "SOCKET_TIMEOUT": 3,
                # Redis vaqtincha yiqilsa sayt ishlashda davom etsin —
                # kesh o'qishlari None qaytaradi, xato ko'tarilmaydi.
                "IGNORE_EXCEPTIONS": True,
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": env_int("REDIS_MAX_CONNECTIONS", 50),
                    "retry_on_timeout": True,
                },
            },
        }
    }
    DJANGO_REDIS_IGNORE_EXCEPTIONS = True
    DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "pdp-junior-local",
            "TIMEOUT": env_int("CACHE_DEFAULT_TIMEOUT", 300),
            "OPTIONS": {"MAX_ENTRIES": 5000},
        }
    }

# Kesh TTL'lari (soniya) — barchasi env orqali sozlanadi.
CACHE_TTL_PUBLIC = env_int("CACHE_TTL_PUBLIC", 300)        # katalog, filial, mentor
CACHE_TTL_RANKING = env_int("CACHE_TTL_RANKING", 120)      # reyting
CACHE_TTL_HEROES = env_int("CACHE_TTL_HEROES", 300)        # oy qahramonlari
CACHE_TTL_GALLERY = env_int("CACHE_TTL_GALLERY", 300)      # galereya
CACHE_TTL_SHOP = env_int("CACHE_TTL_SHOP", 120)            # do'kon katalogi
CACHE_TTL_PROGRESS = env_int("CACHE_TTL_PROGRESS", 900)    # modul qulfi

# Tashqi PDP API bilan ishlash
PDP_API_TIMEOUT = env_int("PDP_API_TIMEOUT", 8)
PDP_SYNC_MIN_INTERVAL = env_int("PDP_SYNC_MIN_INTERVAL", 300)
PDP_SYNC_ASYNC = env_bool("PDP_SYNC_ASYNC", True)

# Django sessiyalari keshda saqlansin — admin panel har so'rovda
# bazaga bormaydi.
if REDIS_CACHE_ENABLED and REDIS_CACHE_URL:
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

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
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}
WHITENOISE_MAX_AGE = env_int("WHITENOISE_MAX_AGE", 31536000)


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
    # Qisqa access token + rotatsiyalanadigan refresh: o'g'irlangan token
    # bir oy emas, bir necha soat amal qiladi.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 120)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 30)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": False,
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    # Orqaga mos paginatsiya: ?page= yoki ?limit= yuborilmasa javob shakli
    # o'zgarmaydi, lekin qattiq maksimal chegara har doim qo'llanadi.
    "DEFAULT_PAGINATION_CLASS": "app.pagination.OptionalPageNumberPagination",
    "PAGE_SIZE": env_int("API_PAGE_SIZE", 50),
    "DEFAULT_THROTTLE_CLASSES": (
        "app.throttling.BurstAnonThrottle",
        "app.throttling.BurstUserThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "90/min"),
        "user": os.getenv("THROTTLE_USER", "600/min"),
        # Login/SMS: qimmat va tashqi servisga bog'liq — qattiq cheklanadi.
        "auth": os.getenv("THROTTLE_AUTH", "10/min"),
        "sms": os.getenv("THROTTLE_SMS", "4/min"),
        "password": os.getenv("THROTTLE_PASSWORD", "6/min"),
        # Test topshirish oqimi: 500 o'quvchi bir vaqtda yozadi, shuning
        # uchun keng, lekin cheksiz emas.
        "test_write": os.getenv("THROTTLE_TEST_WRITE", "180/min"),
        "shop_write": os.getenv("THROTTLE_SHOP_WRITE", "20/min"),
        "sync": os.getenv("THROTTLE_SYNC", "20/min"),
    },
}

if not DEBUG:
    # BrowsableAPIRenderer HTML sahifa render qiladi — u sekin va
    # productionda keraksiz. Faqat JSON qoldiramiz.
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
        "rest_framework.renderers.JSONRenderer",
    )

# Testlar va yuk sinovlarida throttle o'chiriladi (THROTTLE_ENABLED=0).
THROTTLE_ENABLED = env_bool("THROTTLE_ENABLED", True)
if "test" in sys.argv or os.getenv("PYTEST_CURRENT_TEST"):
    THROTTLE_ENABLED = env_bool("THROTTLE_ENABLED", False)
if not THROTTLE_ENABLED:
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
        key: None for key in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    }

APPEND_SLASH = False

# ---------------------------------------------------------------------
# HTTPS / xavfsizlik sarlavhalari (proxy ortidagi deploy uchun)
# ---------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", not DEBUG)

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"

# So'rov tanasining maksimal hajmi — kutilmagan katta payload worker'ni
# band qilib qo'ymasin.
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024)
DATA_UPLOAD_MAX_NUMBER_FIELDS = env_int("DATA_UPLOAD_MAX_NUMBER_FIELDS", 1000)
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024)

# ---------------------------------------------------------------------
# Loglash — ilgari umuman sozlanmagan edi.
# ---------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(levelname)s %(asctime)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        # SQL loglari faqat ataylab yoqilganda
        "django.db.backends": {
            "handlers": ["console"],
            "level": os.getenv("SQL_LOG_LEVEL", "WARNING").upper(),
            "propagate": False,
        },
        "app": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "celery": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

ESKIZ_EMAIL = os.getenv("ESKIZ_EMAIL", "test@gmail.com")
ESKIZ_PASSWORD = os.getenv("ESKIZ_PASSWORD", "")
ESKIZ_SENDER = os.getenv("ESKIZ_SENDER", "4546")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_SHOP_CHAT_ID = os.getenv("TELEGRAM_SHOP_CHAT_ID", "")

# ---------------------------------------------------------------------
# MEDIA STORAGE: Local yoki Cloudflare R2 (S3-compatible)
# Yoqish: USE_R2=1 + R2_* env o'zgaruvchilari (.env / hosting)
USE_R2 = os.getenv("USE_R2") == "1"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

if USE_R2:
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
