from datetime import timedelta

from celery import shared_task
from django.conf import settings

from app.services.maintenance.cleanup_service import (
    cleanup_django_sessions,
    cleanup_jwt_blacklist,
    dedupe_finished_test_sessions,
    expire_stale_test_sessions,
    run_full_maintenance,
    run_test_data_maintenance,
)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def send_shop_order_notification_task(order_id):
    """Telegram xabarini web requestdan tashqarida jo'natadi."""
    from app.services.portal.shop_notification_service import send_shop_order_notification

    return send_shop_order_notification(order_id)


@shared_task
def expire_stale_test_sessions_task():
    return expire_stale_test_sessions()


@shared_task
def cleanup_test_sessions_task():
    return run_test_data_maintenance()


@shared_task
def dedupe_test_sessions_task():
    return dedupe_finished_test_sessions(group_batch_size=200)


@shared_task
def cleanup_jwt_blacklist_task():
    return cleanup_jwt_blacklist()


@shared_task
def cleanup_django_sessions_task():
    return cleanup_django_sessions()


@shared_task
def run_full_maintenance_task():
    return run_full_maintenance()


# Eski task nomlari bilan moslik.
expire_stale_test_sessions = expire_stale_test_sessions_task
cleanup_test_sessions = cleanup_test_sessions_task
