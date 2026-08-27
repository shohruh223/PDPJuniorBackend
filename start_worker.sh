#!/bin/sh
set -e
celery -A root worker -l info -Q pdp-junior --concurrency "${CELERY_CONCURRENCY:-2}"
