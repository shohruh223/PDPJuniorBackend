web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn root.wsgi:application -c gunicorn.conf.py
worker: celery -A root worker -l info -Q pdp-junior --concurrency ${CELERY_CONCURRENCY:-4} --max-tasks-per-child 200
maintenance: celery -A root worker -l info -Q pdp-junior-maintenance --concurrency 1 --max-tasks-per-child 20
beat: celery -A root beat -l info
