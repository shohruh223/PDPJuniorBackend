from django.core.cache import cache
from django.db.models import Count, F

from app.models.question import Module
from app.models.test import TestSession
from app.services.student.test_cache_service import (
    COMPLETED_LESSONS_CACHE_TTL,
    completed_lessons_cache_key,
    unlocked_modules_cache_key,
    UNLOCKED_MODULES_CACHE_TTL,
)


def _get_completed_lesson_ids(user, course):
    cache_key = completed_lessons_cache_key(user.id, course.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return set(cached)

    completed = set(
        TestSession.objects.filter(
            student=user,
            lesson__course=course,
            is_finished=True,
            answered_count__gte=F("total_questions"),
        )
        .values_list("lesson_id", flat=True)
        .distinct()
    )
    cache.set(cache_key, list(completed), COMPLETED_LESSONS_CACHE_TTL)
    return completed


def is_module_completed(user, module, *, completed_lesson_ids=None):
    testable_lesson_ids = list(
        module.lessons.annotate(question_count=Count("questions"))
        .filter(question_count__gt=0)
        .values_list("id", flat=True)
    )

    if not testable_lesson_ids:
        # DIQQAT: ilgari bu yerda `False` qaytarilardi va chaqiruvchi sikl
        # birinchi "tugallanmagan" modulda to'xtardi. Ya'ni admin savol
        # qo'shishga ulgurmagan bitta bo'sh modul BUTUN KURSNI barcha
        # o'quvchilar uchun doimiy qulflab qo'yardi.
        #
        # Testga yaroqli darsi yo'q modulda o'quvchi qiladigan ish yo'q,
        # shuning uchun uni "o'tilgan" deb hisoblaymiz va keyingi modul
        # ochiladi.
        return True

    if completed_lesson_ids is None:
        course = module.course
        completed_lesson_ids = _get_completed_lesson_ids(user, course)

    return set(testable_lesson_ids).issubset(completed_lesson_ids)


def _compute_unlocked_module_ids(user, course, completed_lesson_ids):
    unlocked_ids = []

    for module in (
        Module.objects.filter(course=course)
        .select_related("course")
        .order_by("order", "id")
    ):
        unlocked_ids.append(module.pk)

        if not is_module_completed(
            user,
            module,
            completed_lesson_ids=completed_lesson_ids,
        ):
            break

    return unlocked_ids


def get_unlocked_module_ids(user, course):
    cache_key = unlocked_modules_cache_key(user.id, course.id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    completed_lesson_ids = _get_completed_lesson_ids(user, course)
    unlocked_ids = _compute_unlocked_module_ids(user, course, completed_lesson_ids)
    cache.set(cache_key, unlocked_ids, UNLOCKED_MODULES_CACHE_TTL)
    return unlocked_ids


def is_module_unlocked(user, course, module_id):
    return module_id in get_unlocked_module_ids(user, course)
