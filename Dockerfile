# syntax=docker/dockerfile:1
# PDP Junior backend — production image (runtime.txt dagi Python 3.12 bilan bir xil).
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl: diagnostika; gettext: tarjimalarni (.po -> .mo) kompilyatsiya qilish uchun; libpq kerak emas (psycopg2-binary).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Root bo'lmagan foydalanuvchi. /app/media oldindan yaratiladi, shunda unga
# ulangan nomli volume yozish uchun ochiq bo'ladi (R2 ishlatilmasa).
RUN useradd --system --create-home --uid 10001 app \
    && mkdir -p /app/media /app/static \
    && chmod +x /app/deploy/entrypoint.sh \
    && chown -R app:app /app

# Tarjimalar: .mo fayllar git'da yo'q (.gitignore), shuning uchun build vaqtida yig'iladi.
RUN SECRET_KEY=build-only ALLOWED_HOSTS=localhost REDIS_URL=redis://localhost:6379/0 \
    DATABASE_URL=postgres://u:p@localhost:5432/d \
    python manage.py compilemessages

# Statik fayllarni build vaqtida yig'amiz. Bu qiymatlar FAQAT shu qadam uchun
# (sirlar image ichida qolmaydi; haqiqiy qiymatlar ish vaqtida beriladi).
RUN SECRET_KEY=build-only ALLOWED_HOSTS=localhost REDIS_URL=redis://localhost:6379/0 \
    DATABASE_URL=postgres://u:p@localhost:5432/d \
    python manage.py collectstatic --noinput \
    && chown -R app:app /app/static

USER app
EXPOSE 8000

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "root.wsgi:application", "-c", "gunicorn.conf.py"]
