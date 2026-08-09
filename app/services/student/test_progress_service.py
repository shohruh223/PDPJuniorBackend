from django.db.models import Count, F

from app.models.question import Module
from app.models.test import TestSession


def is_module_completed(user, module):
    testable_lesson_ids = list(
        module.lessons.annotate(question_count=Count("questions"))
        .filter(question_count__gt=0)
        .values_list("id", flat=True)
    )

    if not testable_lesson_ids:
        return False

    completed_lesson_ids = set(
        TestSession.objects.filter(
            student=user,
            lesson_id__in=testable_lesson_ids,
            is_finished=True,
        )
        .annotate(answered_count=Count("answers", distinct=True))
        .filter(answered_count__gte=F("total_questions"))
        .values_list("lesson_id", flat=True)
    )

    return set(testable_lesson_ids).issubset(completed_lesson_ids)


def get_unlocked_module_ids(user, course):
    unlocked_ids = []

    for module in (
        Module.objects.filter(course=course)
        .order_by("order", "id")
    ):
        unlocked_ids.append(module.pk)

        if not is_module_completed(user, module):
            break

    return unlocked_ids


def is_module_unlocked(user, course, module_id):
    return module_id in get_unlocked_module_ids(user, course)
