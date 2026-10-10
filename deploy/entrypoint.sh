#!/bin/sh
# Konteyner kirish nuqtasi.
# RUN_MIGRATIONS=1 faqat `web` xizmatida qo'yiladi — worker/beat bir vaqtda
# migratsiya qilib poyga holatini yaratmasligi uchun.
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "[entrypoint] migrate..."
    python manage.py migrate --noinput
fi

exec "$@"
