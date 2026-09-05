"""
Database maintenance: faqat ortiqcha yoki muddati o'tgan ma'lumotlarni tozalaydi.

Muhim: StudentQuestionReward, coin buyurtmalar, to'lovlar va modul progress
uchun kerakli canonical test session saqlanadi.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.db.models import Case, Count, F, IntegerField, When
from django.utils import timezone


def _detail_cutoff():
    return timezone.now() - timedelta(days=settings.TEST_DETAIL_RETENTION_DAYS)


def _unfinished_cutoff():
    return timezone.now() - timedelta(days=settings.TEST_UNFINISHED_RETENTION_DAYS)


def _dedupe_cutoff():
    return timezone.now() - timedelta(days=settings.TEST_DEDUPE_SESSIONS_AFTER_DAYS)


def expire_stale_test_sessions(*, batch_size=500, max_batches=20):
    from app.models.test import TestSession

    now = timezone.now()
    finalized = 0

    for _ in range(max_batches):
        expired_ids = list(
            TestSession.objects.filter(
                is_finished=False,
                expires_at__lt=now,
            ).values_list("id", flat=True)[:batch_size]
        )
        if not expired_ids:
            break

        for session_id in expired_ids:
            with transaction.atomic():
                session = (
                    TestSession.objects.select_for_update(skip_locked=True)
                    .filter(pk=session_id, is_finished=False)
                    .select_related("lesson", "student")
                    .first()
                )
                if session and session.is_expired():
                    session.finish()
                    finalized += 1

    return {"expired_finalized": finalized}


def cleanup_abandoned_test_sessions():
    """Tashlab ketilgan va uzoq vaqt ochiq qolgan sessionlarni o'chiradi."""
    from app.models.test import TestSession

    deleted, _ = TestSession.objects.filter(
        is_finished=False,
        expires_at__lt=_unfinished_cutoff(),
    ).delete()
    return {"abandoned_deleted": deleted}


def finalize_unfinalized_old_sessions(*, batch_size=200):
    """Eski lekin finalize qilinmagan sessionlarning summary sini saqlaydi."""
    from app.models.test import TestSession

    finalized = 0
    qs = TestSession.objects.filter(
        is_finished=True,
        finished_at__lt=_detail_cutoff(),
        finalized_at__isnull=True,
    )
    for session in qs.iterator(chunk_size=batch_size):
        with transaction.atomic():
            locked = TestSession.objects.select_for_update().get(pk=session.pk)
            if not locked.finalized_at:
                locked.finalize()
                finalized += 1
    return {"sessions_finalized": finalized}


def purge_old_test_session_details(*, batch_size=500, max_batches=200):
    """
    Eski test javob/savol detailini o'chiradi.
    TestSession summary (percent, correct_count, ...) saqlanadi.

    ILGARI BU SIKL HECH QACHON TUGAMASDI: tanlash sharti `TestSession`
    ustida edi, o'chirish esa faqat bolalarini (javob va savollarni)
    olib tashlardi. Sessiya o'zi na o'chirilardi, na belgilanardi, ya'ni
    keyingi aylanishda aynan o'sha ID'lar qaytardi va `break` hech qachon
    ishlamasdi. Celery uni har 6 soatda timeout bilan o'ldirar, detallar
    esa tozalanmasdi.

    Endi sikl faqat **hali detali bor** sessiyalarni tanlaydi
    (`items__isnull=False`), shuning uchun har aylanishda to'plam
    kichrayadi va sikl tabiiy tugaydi. `max_batches` — qo'shimcha
    xavfsizlik cheklovi.
    """
    from app.models.test import TestSession, TestSessionAnswer, TestSessionQuestion

    answers_deleted = 0
    questions_deleted = 0
    batches = 0

    while batches < max_batches:
        batches += 1
        old_session_ids = list(
            TestSession.objects.filter(
                is_finished=True,
                finished_at__lt=_detail_cutoff(),
                finalized_at__isnull=False,
                items__isnull=False,
            )
            .values_list("id", flat=True)
            .distinct()[:batch_size]
        )
        if not old_session_ids:
            break

        deleted_answers, _ = TestSessionAnswer.objects.filter(
            session_id__in=old_session_ids,
        ).delete()
        deleted_questions, _ = TestSessionQuestion.objects.filter(
            session_id__in=old_session_ids,
        ).delete()
        answers_deleted += deleted_answers
        questions_deleted += deleted_questions

        if not deleted_questions:
            # Savollari yo'q, faqat javoblari bor holat — takrorlanmasin.
            break

    return {
        "answers_deleted": answers_deleted,
        "session_questions_deleted": questions_deleted,
        "batches": batches,
    }


def _keeper_session_queryset(student_id, lesson_id):
    from app.models.test import TestSession

    return (
        TestSession.objects.filter(
            student_id=student_id,
            lesson_id=lesson_id,
            is_finished=True,
            finalized_at__isnull=False,
            finished_at__lt=_dedupe_cutoff(),
        )
        .annotate(item_count=Count("items"))
        .filter(item_count=0)
        .annotate(
            is_complete=Case(
                When(answered_count__gte=F("total_questions"), then=1),
                default=0,
                output_field=IntegerField(),
            )
        )
        .order_by("-is_complete", "-percent", "-answered_count", "-finished_at")
    )


def dedupe_finished_test_sessions(*, group_batch_size=100):
    """
    Bir xil lesson bo'yicha takroriy test sessionlardan eng yaxshisini qoldiradi.
    Modul progress buzilmasligi uchun to'liq yakunlangan session ustunlik oladi.
    """
    from app.models.test import TestSession

    duplicate_groups = (
        TestSession.objects.filter(
            is_finished=True,
            finalized_at__isnull=False,
            finished_at__lt=_dedupe_cutoff(),
        )
        .annotate(item_count=Count("items"))
        .filter(item_count=0)
        .values("student_id", "lesson_id")
        .annotate(session_count=Count("id"))
        .filter(session_count__gt=1)
        .order_by("student_id", "lesson_id")[:group_batch_size]
    )

    deleted_sessions = 0
    for group in duplicate_groups:
        keeper = _keeper_session_queryset(
            group["student_id"],
            group["lesson_id"],
        ).first()
        if not keeper:
            continue

        deleted, _ = (
            TestSession.objects.filter(
                student_id=group["student_id"],
                lesson_id=group["lesson_id"],
                is_finished=True,
                finalized_at__isnull=False,
                # MUHIM: keeper faqat retention oynasidan o'tgan
                # sessiyalar orasidan tanlanadi, shuning uchun o'chirish
                # ham aynan shu oyna bilan cheklanishi shart. Aks holda
                # o'quvchining kechagi (eng yangi va eng yaxshi) urinishi
                # eski dublikatlar sababli o'chib ketardi.
                finished_at__lt=_dedupe_cutoff(),
            )
            .annotate(item_count=Count("items"))
            .filter(item_count=0)
            .exclude(pk=keeper.pk)
            .delete()
        )
        deleted_sessions += deleted

    return {"duplicate_sessions_deleted": deleted_sessions}


def cleanup_jwt_blacklist():
    if not getattr(settings, "JWT_BLACKLIST_CLEANUP_ENABLED", True):
        return {"jwt_tokens_flushed": 0}

    call_command("flushexpiredtokens", verbosity=0)
    return {"jwt_tokens_flushed": "ok"}


def cleanup_django_sessions():
    if not getattr(settings, "DJANGO_SESSION_CLEANUP_ENABLED", True):
        return {"django_sessions_cleared": 0}

    call_command("clearsessions", verbosity=0)
    return {"django_sessions_cleared": "ok"}


def run_test_data_maintenance():
    """Test bilan bog'liq barcha xavfsiz cleanup bosqichlari."""
    results = {}
    results.update(cleanup_abandoned_test_sessions())
    results.update(finalize_unfinalized_old_sessions())
    results.update(purge_old_test_session_details())

    # Detail tozalangandan keyin takroriy sessionlarni qisqartirish.
    for _ in range(5):
        dedupe_result = dedupe_finished_test_sessions()
        results["duplicate_sessions_deleted"] = (
            results.get("duplicate_sessions_deleted", 0)
            + dedupe_result["duplicate_sessions_deleted"]
        )
        if dedupe_result["duplicate_sessions_deleted"] == 0:
            break

    return results


def run_full_maintenance():
    """Barcha ruxsat etilgan maintenance tasklar."""
    results = {"tests": run_test_data_maintenance()}
    results["jwt"] = cleanup_jwt_blacklist()
    results["sessions"] = cleanup_django_sessions()
    return results
