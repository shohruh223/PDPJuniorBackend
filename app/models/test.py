from datetime import timedelta
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from app.models.question import Lesson, Question


class TestSession(models.Model):
    id = models.BigAutoField(primary_key=True)

    # tashqi API va endpointlar uchun UUID
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="test_sessions",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="test_sessions",
    )

    total_questions = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    is_finished = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Test sessiyasi"
        verbose_name_plural = "Test sessiyalari"

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

    def finish(self):
        if not self.is_finished:
            self.is_finished = True
            self.finished_at = timezone.now()
            self.save(update_fields=["is_finished", "finished_at"])

    def __str__(self):
        return f"{self.student_id} | {self.lesson_id} | {self.session_id}"


class TestSessionQuestion(models.Model):
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name="items",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="in_test_sessions",
    )
    order = models.PositiveSmallIntegerField()

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
        return f"{self.session.session_id} #{self.order} -> Q{self.question_id}"


class TestSessionAnswer(models.Model):
    session = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="test_answers",
    )
    selected_option = models.CharField(max_length=1, choices=Question.OPTION_CHOICES)
    is_correct = models.BooleanField(default=False)

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
        return f"{self.session.session_id} | Q{self.question_id} | {self.selected_option}"