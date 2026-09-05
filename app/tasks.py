"""Celery vazifalari.

DIQQAT — ilgari shu faylning oxirida quyidagi ikki qator bor edi:

    expire_stale_test_sessions = expire_stale_test_sessions_task
    cleanup_test_sessions = cleanup_test_sessions_task

Birinchisi `cleanup_service` dan import qilingan nomni vazifaning o'ziga
qayta bog'lardi. Python global nomni **chaqiruv paytida** aniqlagani uchun
vazifa tanasi servis funksiyasini emas, o'zini chaqirardi — ya'ni har 5
daqiqada `RecursionError`. Shu sababli muddati tugagan test sessiyalari
hech qachon avtomatik yakunlanmasdi.

Endi servis funksiyalari **modul orqali** chaqiriladi, shuning uchun nom
to'qnashuvi qaytadan yuzaga kelmaydi.
"""

import logging

from celery import shared_task

from app.services.maintenance import cleanup_service

logger = logging.getLogger(__name__)


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


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_jitter=True,
    retry_kwargs={"max_retries": 2},
    acks_late=True,
)
def sync_student_external_data_task(self, profile_id, kind):
    """Bitta o'quvchining PDP ma'lumotini fon rejimida yangilaydi.

    Web so'rovi endi tashqi API'ni kutmaydi — u shu vazifani navbatga
    qo'yadi va bazadagi nusxa bilan javob beradi.
    """
    from app.models.auth import StudentProfile
    from app.services.student import sync_coordinator

    try:
        profile = StudentProfile.objects.select_related("user", "course").get(pk=profile_id)
    except StudentProfile.DoesNotExist:
        logger.info("PDP sync: profil topilmadi (%s)", profile_id)
        return {"profile": str(profile_id), "kind": kind, "status": "profil yo'q"}

    warning = sync_coordinator._run_inline(profile, kind)
    sync_coordinator.mark_synced(profile.pk, kind, warning=warning)
    sync_coordinator._release_lock(profile.pk, kind)
    return {"profile": str(profile_id), "kind": kind, "warning": warning}


@shared_task
def expire_stale_test_sessions_task():
    return cleanup_service.expire_stale_test_sessions()


@shared_task
def cleanup_test_sessions_task():
    return cleanup_service.run_test_data_maintenance()


@shared_task
def dedupe_test_sessions_task():
    return cleanup_service.dedupe_finished_test_sessions(group_batch_size=200)


@shared_task
def cleanup_jwt_blacklist_task():
    return cleanup_service.cleanup_jwt_blacklist()


@shared_task
def cleanup_django_sessions_task():
    return cleanup_service.cleanup_django_sessions()


@shared_task
def run_full_maintenance_task():
    return cleanup_service.run_full_maintenance()


@shared_task
def warm_public_caches_task():
    """Ommaviy endpointlar keshini oldindan to'ldiradi.

    Reyting va oy qahramonlari eng qimmat so'rovlar. Ular kesh muddati
    tugashi bilan birinchi kelgan foydalanuvchi tomonidan qayta
    hisoblanardi ("cache stampede"). Endi buni beat qiladi, ya'ni
    foydalanuvchi hech qachon sovuq keshga tushmaydi.
    """
    from app.services.portal import cache_warmer

    return cache_warmer.warm_all()
