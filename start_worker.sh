#!/bin/sh
set -e
exec celery -A root worker -l info -Q pdp-junior \
  --concurrency "${CELERY_CONCURRENCY:-4}" \
  --max-tasks-per-child 200
