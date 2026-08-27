#!/bin/sh
set -e
celery -A root beat -l info
