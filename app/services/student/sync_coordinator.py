"""Tashqi PDP API bilan sinxronizatsiyani boshqaruvchi qatlam.

Muammo. Ilgari `GET /api/student/dashboard`, `/payment-histories` va
`/invoices` endpointlari **har chaqirilganda** `adminapi.pdp.uz` ga
bloklovchi HTTP so'rov yuborardi. Bu 500 foydalanuvchida quyidagini
anglatadi:

* har bir so'rov gunicorn thread'ini tashqi servis javob bergunicha
  ushlab turadi (timeout 15 s edi);
* PDP sekinlashsa yoki javob bermasa — bizning saytimiz ham to'xtaydi,
  garchi barcha ma'lumot allaqachon bazada bo'lsa ham;
* 500 o'quvchi bir vaqtda kirsa PDP ga 500 ta bir xil so'rov ketadi.

Yechim uch qatlamli:

1. **Yangilik oynasi.** Ma'lumot `PDP_SYNC_MIN_INTERVAL` (default 5 daqiqa)
   ichida sinxronlangan bo'lsa, tashqi so'rov umuman yuborilmaydi.
2. **Fon rejimi.** Celery yoqilgan bo'lsa sinxronizatsiya vazifa sifatida
   navbatga qo'yiladi; foydalanuvchi bazadagi nusxani darhol oladi.
3. **Bitta yuguruvchi (single-flight).** Sinxron bajarish kerak bo'lsa ham,
   bitta o'quvchi uchun bir vaqtda faqat bitta so'rov tashqariga chiqadi —
   qolganlari bazadagi nusxa bilan javob beradi.

Natijada tashqi servis bizning javob vaqtimizga ta'sir qilmaydi.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

DASHBOARD = "dashboard"
INVOICES = "invoices"
PAYMENTS = "payments"

_KINDS = (DASHBOARD, INVOICES, PAYMENTS)


def _min_interval() -> int:
    return int(getattr(settings, "PDP_SYNC_MIN_INTERVAL", 300) or 0)


def _async_enabled() -> bool:
    return bool(getattr(settings, "PDP_SYNC_ASYNC", True)) and bool(
        getattr(settings, "CELERY_ENABLED", False)
    )


def stamp_key(profile_id, kind: str) -> str:
    return f"pdpsync:ts:{kind}:{profile_id}"


def lock_key(profile_id, kind: str) -> str:
    return f"pdpsync:lock:{kind}:{profile_id}"


def warning_key(profile_id, kind: str) -> str:
    return f"pdpsync:warn:{kind}:{profile_id}"


def mark_synced(profile_id, kind: str, *, warning: str | None = None) -> None:
    """Sinxronizatsiya tugadi deb belgilaydi (muvaffaqiyatli yoki xato bilan)."""
    ttl = max(_min_interval(), 60)
    cache.set(stamp_key(profile_id, kind), timezone.now().timestamp(), ttl * 4)
    if warning:
        cache.set(warning_key(profile_id, kind), warning, ttl)
    else:
        cache.delete(warning_key(profile_id, kind))


def last_warning(profile_id, kind: str):
    return cache.get(warning_key(profile_id, kind))


def is_fresh(profile, kind: str) -> bool:
    """Ma'lumot yaqinda sinxronlanganmi?"""
    interval = _min_interval()
    if interval <= 0:
        return False

    stamp = cache.get(stamp_key(profile.pk, kind))
    if stamp:
        return (timezone.now().timestamp() - float(stamp)) < interval

    # Kesh bo'sh bo'lsa (restart, Redis yiqilishi) dashboard uchun
    # bazadagi last_synced_at zaxira manba bo'lib xizmat qiladi.
    if kind == DASHBOARD and getattr(profile, "last_synced_at", None):
        age = (timezone.now() - profile.last_synced_at).total_seconds()
        return age < interval

    return False


def _acquire_lock(profile_id, kind: str, ttl: int = 30) -> bool:
    """Bitta o'quvchi uchun bir vaqtda bitta tashqi so'rov."""
    try:
        return bool(cache.add(lock_key(profile_id, kind), "1", ttl))
    except Exception:
        # Kesh ishlamasa qulf ham ishlamaydi — so'rovni o'tkazamiz.
        return True


def _release_lock(profile_id, kind: str) -> None:
    try:
        cache.delete(lock_key(profile_id, kind))
    except Exception:
        pass


def _can_sync(profile) -> bool:
    return bool(getattr(profile, "external_id", None) and getattr(profile, "pdp_access_token", None))


def _enqueue(profile_id, kind: str) -> bool:
    """Celery vazifasini navbatga qo'yadi. Muvaffaqiyat bo'lsa True."""
    try:
        from app.tasks import sync_student_external_data_task

        sync_student_external_data_task.delay(str(profile_id), kind)
        return True
    except Exception:
        logger.warning("PDP sync vazifasini navbatga qo'yib bo'lmadi", exc_info=True)
        return False


def _run_inline(profile, kind: str) -> str | None:
    """Sinxron bajarish — faqat qulfni olgan so'rov chaqiradi."""
    from app.services.student.external_student_api import PDPStudentAPIClient, PDPStudentAPIError

    try:
        client = PDPStudentAPIClient(token=profile.pdp_access_token)
        if kind == DASHBOARD:
            from app.services.student.student_dashboard_service import sync_student_dashboard_data

            payload = client.get_student_info(str(profile.external_id))
            sync_student_dashboard_data(student_profile=profile, external_payload=payload)
        elif kind == INVOICES:
            from app.services.student.invoice_service import sync_student_invoices

            payload = client.get_student_invoices(str(profile.external_id))
            sync_student_invoices(student_profile=profile, external_payload=payload)
        elif kind == PAYMENTS:
            from app.services.student.payment_history_service import sync_student_payment_histories

            payload = client.get_student_payment_history(str(profile.external_id))
            sync_student_payment_histories(student_profile=profile, external_payload=payload)
        else:
            return f"Noma'lum sinxronizatsiya turi: {kind}"
    except PDPStudentAPIError as exc:
        logger.info("PDP sync xatosi (%s, profil %s): %s", kind, profile.pk, exc)
        return "Tashqi servisdan ma'lumot olinmadi. Ko'rsatilgan ma'lumot oxirgi saqlangan holat."
    except Exception:
        logger.exception("PDP sync kutilmagan xato (%s, profil %s)", kind, profile.pk)
        return "Ma'lumotni yangilashda kutilmagan xatolik. Oxirgi saqlangan holat ko'rsatilmoqda."
    return None


def ensure_fresh(profile, kind: str, *, force: bool = False, allow_inline: bool | None = None):
    """Kerak bo'lsa sinxronizatsiyani ishga tushiradi.

    Qaytaradi `(sinxronlandi_mi, ogohlantirish)`. Endpoint hech qachon
    tashqi servisni kutib qolmasligi uchun default holatda vazifa fon
    rejimiga uzatiladi.
    """
    if kind not in _KINDS:
        raise ValueError(f"Noma'lum sinxronizatsiya turi: {kind}")

    if not _can_sync(profile):
        return False, None

    if not force and is_fresh(profile, kind):
        return False, last_warning(profile.pk, kind)

    # Birinchi marta: hali hech qachon sinxronlanmagan va ko'rsatadigan
    # ma'lumot yo'q. Bunda fon rejimini kutish o'quvchiga bo'sh ekran
    # ko'rsatadi, shuning uchun bir marta sinxron bajaramiz.
    never_synced = kind == DASHBOARD and not (
        getattr(profile, "last_synced_at", None) or getattr(profile, "external_snapshot", None)
    )

    if _async_enabled() and not force and not never_synced:
        if _acquire_lock(profile.pk, kind, ttl=60) and _enqueue(profile.pk, kind):
            return False, last_warning(profile.pk, kind)
        _release_lock(profile.pk, kind)
        return False, last_warning(profile.pk, kind)

    # Sinxron yo'l: Celery yo'q, yoki mijoz ataylab yangilashni so'radi.
    if allow_inline is None:
        allow_inline = True
    if not allow_inline:
        return False, last_warning(profile.pk, kind)

    if not _acquire_lock(profile.pk, kind):
        # Boshqa so'rov allaqachon yangilamoqda — kutmaymiz.
        return False, last_warning(profile.pk, kind)

    try:
        warning = _run_inline(profile, kind)
    finally:
        _release_lock(profile.pk, kind)

    mark_synced(profile.pk, kind, warning=warning)
    return True, warning


def wants_refresh(request) -> bool:
    """`?refresh=1` — mijoz ataylab yangilashni so'radi."""
    params = getattr(request, "query_params", None) or {}
    return str(params.get("refresh", "")).lower() in ("1", "true", "yes")
