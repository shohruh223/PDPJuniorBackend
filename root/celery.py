import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")

app = Celery("pdp_junior")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
