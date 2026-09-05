#!/bin/sh
set -e
exec celery -A root beat -l info
