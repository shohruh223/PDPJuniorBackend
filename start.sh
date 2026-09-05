#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn root.wsgi:application -c gunicorn.conf.py
