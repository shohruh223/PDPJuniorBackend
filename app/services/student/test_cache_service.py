"""Modul qulfi (progress) keshi.

Ikki muammo tuzatildi:

1. **Kesh backendi.** Ilgari standart holatda `LocMemCache` ishlatilardi —
   u har gunicorn worker'ining shaxsiy xotirasida. Test yakunlanganda
   kesh faqat javob bergan workerda tozalanardi, qolgan uchtasi eski
   qulf ro'yxatini bir soatgacha ushlab turardi va modul goh ochiq, goh
   yopiq ko'rinardi. Endi `REDIS_URL` berilsa kesh Redis'da, ya'ni
   barcha worker'lar uchun yagona.

2. **Kontent o'zgarishi.** Kesh faqat test yakunlanganda tozalanardi.
   Bo'sh darsga savol qo'shilsa yoki yangi modul yaratilsa, o'quvchi
   TTL tugagunicha eski holatni ko'rardi. Endi "avlod" (generation)
   raqami bor: kurs tarkibi o'zgarganda u oshiriladi va barcha eski
   kalitlar bir zumda yaroqsiz bo'ladi (`app/signals.py`).
"""

from django.conf import settings
from django.core.cache import cache

_DEFAULT_TTL = 60 * 60

UNLOCKED_MODULES_CACHE_TTL = int(getattr(settings, "CACHE_TTL_PROGRESS", _DEFAULT_TTL) or _DEFAULT_TTL)
COMPLETED_LESSONS_CACHE_TTL = UNLOCKED_MODULES_CACHE_TTL

_GENERATION_KEY = "progress:generation"


def progress_generation() -> int:
    """Joriy avlod raqami. Kesh yiqilsa 0 qaytadi — bu ham to'g'ri ishlaydi."""
    try:
        value = cache.get(_GENERATION_KEY)
    except Exception:
        return 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def bump_progress_generation() -> int:
    """Kurs tarkibi o'zgarganda chaqiriladi — barcha progress keshini eskirtiradi."""
    try:
        try:
            return int(cache.incr(_GENERATION_KEY))
        except ValueError:
            # Kalit hali yo'q edi.
            cache.set(_GENERATION_KEY, 1, None)
            return 1
    except Exception:
        return 0


def unlocked_modules_cache_key(user_id, course_id):
    return f"unlocked_modules:{progress_generation()}:{user_id}:{course_id}"


def completed_lessons_cache_key(user_id, course_id):
    return f"completed_lessons:{progress_generation()}:{user_id}:{course_id}"


def invalidate_unlocked_modules_cache(user, course=None, *, course_id=None):
    """Test yakunlanganda progress keshini yangilash uchun."""
    if course_id is None and course is not None:
        course_id = course.id
    if course_id is None and hasattr(user, "student_profile"):
        profile_course = getattr(user.student_profile, "course", None)
        if profile_course:
            course_id = profile_course.id
    if not course_id:
        return
    try:
        cache.delete_many([
            unlocked_modules_cache_key(user.id, course_id),
            completed_lessons_cache_key(user.id, course_id),
        ])
    except Exception:
        pass


def invalidate_user_progress_cache(user, *, course_id=None):
    invalidate_unlocked_modules_cache(user, course_id=course_id)
