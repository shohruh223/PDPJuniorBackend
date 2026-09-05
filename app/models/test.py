from datetime import timedelta
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from app.models.question import Lesson, Question


class TestSession(models.Model):
    id = models.BigAutoField(primary_key=True)

    # tashqi API va endpointlar uchun UUID
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True, verbose_name="Sessiya ID")

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="test_sessions",
        verbose_name="O‘quvchi",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="test_sessions",
        verbose_name="Dars",
    )

    total_questions = models.PositiveIntegerField(default=0, verbose_name="Savollar soni")
    answered_count = models.PositiveIntegerField(default=0, verbose_name="Javob berilgan")
    duration_minutes = models.PositiveIntegerField(default=0, verbose_name="Davomiyligi (daq.)")

    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan vaqt")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugash vaqti")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Yakunlangan vaqt")

    is_finished = models.BooleanField(default=False, verbose_name="Yakunlangan")
    # Natija yakunlanganda bir marta hisoblanadi. Shunday qilib keyinchalik
    # savol kontenti o'zgarsa ham sessionning asosiy statistikasi saqlanadi.
    correct_count = models.PositiveIntegerField(default=0, verbose_name="To‘g‘ri javoblar")
    wrong_count = models.PositiveIntegerField(default=0, verbose_name="Xato javoblar")
    unanswered_count = models.PositiveIntegerField(default=0, verbose_name="Javobsiz")
    percent = models.PositiveSmallIntegerField(default=0, verbose_name="Foiz")
    finalized_at = models.DateTimeField(null=True, blank=True, verbose_name="Hisoblangan vaqt")

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Test sessiyasi"
        verbose_name_plural = "Test sessiyalari"
        indexes = [
            models.Index(
                fields=["student", "lesson", "is_finished", "started_at"],
                name="test_session_lookup_idx",
            ),
            models.Index(
                fields=["is_finished", "finished_at"],
                name="test_session_cleanup_idx",
            ),
            models.Index(
                fields=["is_finished", "expires_at"],
                name="test_session_expire_idx",
            ),
            models.Index(
                fields=["student", "lesson", "is_finished"],
                name="test_session_st_lesson_idx",
            ),
        ]
        constraints = [
            # Parallel start requestlar bitta student uchun ikki ochiq test
            # session hosil qilmasligini database darajasida kafolatlaydi.
            models.UniqueConstraint(
                fields=["student", "lesson"],
                condition=Q(is_finished=False),
                name="uniq_active_test_per_student_lesson",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.total_questions and not self.duration_minutes:
            self.duration_minutes = self.total_questions + 1

        if not self.expires_at and self.duration_minutes:
            base_time = self.started_at or timezone.now()
            self.expires_at = base_time + timedelta(minutes=self.duration_minutes)

        super().save(*args, **kwargs)

    @property
    def remaining_seconds(self):
        if not self.expires_at:
            return None
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))

    @property
    def spent_seconds(self):
        end = self.finished_at or timezone.now()
        return max(0, int((end - self.started_at).total_seconds()))

    def is_expired(self):
        return bool(self.expires_at and timezone.now() >= self.expires_at)

    def finalize(self):
        """Sessionning tarixiy summary sini saqlaydi."""
        if self.finalized_at:
            if not self.is_finished:
                self.is_finished = True
                self.finished_at = self.finished_at or timezone.now()
                self.save(update_fields=["is_finished", "finished_at"])
            self._invalidate_progress_cache()
            return

        items = list(self.items.all())
        answers = {answer.question_id: answer for answer in self.answers.all()}
        correct = sum(
            1
            for item in items
            if (answer := answers.get(item.question_id)) and answer.is_correct
        )
        answered = self.answered_count or len(answers)
        total = self.total_questions or len(items) or self.items.count()

        self.correct_count = correct
        self.wrong_count = max(0, answered - correct)
        self.unanswered_count = max(0, total - answered)
        self.percent = int((correct * 100) / total) if total else 0
        self.answered_count = answered
        if not self.is_finished:
            self.is_finished = True
            self.finished_at = timezone.now()
        self.finalized_at = self.finished_at or timezone.now()
        self.save(
            update_fields=[
                "is_finished",
                "finished_at",
                "correct_count",
                "wrong_count",
                "unanswered_count",
                "answered_count",
                "percent",
                "finalized_at",
            ]
        )
        self._invalidate_progress_cache()

    def finish(self):
        if not self.is_finished or not self.finalized_at:
            self.finalize()

    def _invalidate_progress_cache(self):
        from app.models.question import Lesson
        from app.services.student.test_cache_service import invalidate_unlocked_modules_cache

        course_id = None
        if hasattr(self, "lesson") and getattr(self.lesson, "course_id", None):
            course_id = self.lesson.course_id
        elif self.lesson_id:
            course_id = (
                Lesson.objects.filter(pk=self.lesson_id)
                .values_list("course_id", flat=True)
                .first()
            )
        invalidate_unlocked_modules_cache(self.student, course_id=course_id)

    def __str__(self):
        # Ilgari uchta xom ID qaytarardi: "UUID | 12 | UUID". Bu matn
        # admin jadvallarida FK ustuni sifatida ko'rinadi, shuning uchun
        # odam o'qiy oladigan bo'lishi kerak. Qo'shimcha SQL so'rov
        # bo'lmasligi uchun faqat shu jadvaldagi maydonlar ishlatiladi.
        when = self.started_at.strftime("%d.%m.%Y %H:%M") if self.started_at else "—"
        return f"Test · {when} · {str(self.session_id)[:8]}"


class TestSessionQuestion(models.Model):
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Sessiya",
    )
    question = models.ForeignKey(
        Question,
        # Test tarixi bilan bog'langan savol o'chib ketmasin. Session paytidagi
        # snapshot esa keyingi tahrirlardan tarixni himoya qiladi.
        on_delete=models.PROTECT,
        related_name="in_test_sessions",
        verbose_name="Savol",
    )
    order = models.PositiveSmallIntegerField(verbose_name="Tartibi")
    question_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Savol nusxasi")
    correct_option_snapshot = models.CharField(
        max_length=1,
        choices=Question.OPTION_CHOICES,
        blank=True,
        default="",
        verbose_name="To‘g‘ri javob nusxasi",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Test savoli"
        verbose_name_plural = "Test savollari"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "order"],
                name="uniq_test_session_order",
            ),
            models.UniqueConstraint(
                fields=["session", "question"],
                name="uniq_test_session_question",
            ),
        ]

    def __str__(self):
        # `self.session.session_id` har bir qator uchun alohida SQL
        # so'rov qilardi; `session_id` esa shu jadvalning o'z ustuni.
        return f"{self.order}-savol · {str(self.session_id)[:8]}"


class TestSessionAnswer(models.Model):
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Test sessiyasi",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="test_answers",
        verbose_name="Savol",
    )
    selected_option = models.CharField(max_length=1, choices=Question.OPTION_CHOICES, verbose_name="Tanlangan variant")
    is_correct = models.BooleanField(default=False, verbose_name="To‘g‘ri")

    class Meta:
        verbose_name = "Test javobi"
        verbose_name_plural = "Test javoblari"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question"],
                name="uniq_test_session_answer",
            )
        ]

    def __str__(self):
        return f"Javob «{self.selected_option}» · {str(self.session_id)[:8]}"


class StudentQuestionReward(models.Model):
    """Bir savol uchun coin/score faqat bir marta berilganini qayd etadi."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_rewards",
        verbose_name="O‘quvchi",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
        related_name="student_rewards",
        verbose_name="Savol",
    )
    session = models.ForeignKey(
        TestSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="awarded_rewards",
        verbose_name="Test sessiyasi",
    )
    awarded_at = models.DateTimeField(auto_now_add=True, verbose_name="Berilgan vaqt")

    class Meta:
        verbose_name = "Savol mukofoti"
        verbose_name_plural = "Savol mukofotlari"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "question"],
                name="uniq_student_question_reward",
            )
        ]

    def __str__(self):
        return f"Mukofot · savol {self.question_id}"
