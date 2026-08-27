web: python manage.py migrate --noinput && gunicorn root.wsgi:application --bind 0.0.0.0:$PORT --workers ${GUNICORN_WORKERS:-4} --threads ${GUNICORN_THREADS:-2} --timeout 60 --max-requests 1000 --max-requests-jitter 50
worker: celery -A root worker -l info -Q pdp-junior --concurrency ${CELERY_CONCURRENCY:-2}
beat: celery -A root beat -l info
