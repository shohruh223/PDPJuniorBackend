#!/bin/sh
set -e
python manage.py migrate --noinput
exec gunicorn root.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-4}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout 60 \
  --max-requests 1000 \
  --max-requests-jitter 50
