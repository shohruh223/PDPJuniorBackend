from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.models.auth import BaseModel, StudentProfile


def current_period():
    now = timezone.now()
    return now.date().replace(day=1)


class MonthHero(BaseModel):
    student_profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="month_heroes",
        verbose_name="O‘quvchi",
    )

    period = models.DateField(
        default=current_period,
        db_index=True,
        help_text="Oy/yil filter uchun. Masalan: 2026-04-01",
        verbose_name="Oy",
    )
    points = models.PositiveIntegerField(
        default=0,
        help_text="Shu oyda to'plangan ball. 0 bo'lsa student umumiy bali ishlatiladi.",
        verbose_name="Ballari",
    )

    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Faol")

    class Meta:
        db_table = "month_heroes"
        verbose_name = "Oy qahramoni"
        verbose_name_plural = "Oy qahramonlari"
        ordering = [
            "-period",
            "-points",
            "-student_profile__total_score",
        ]
        indexes = [
            models.Index(fields=["period"]),
            models.Index(fields=["is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student_profile", "period"],
                name="unique_month_hero_per_student_period",
            ),
        ]

    def clean(self):
        super().clean()

        if self.period:
            self.period = self.period.replace(day=1)

        student_profile = getattr(self, "student_profile", None)

        if student_profile and not student_profile.user.is_student:
            raise ValidationError({
                "student_profile": "MonthHero faqat student role uchun bo‘lishi kerak."
            })

    def save(self, *args, **kwargs):
        if self.period:
            self.period = self.period.replace(day=1)

        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        student_profile = getattr(self, "student_profile", None)

        if not student_profile:
            return "Oy qahramoni"

        full_name = student_profile.user.full_name
        score = student_profile.total_score
        period = self.period.strftime("%m/%Y") if self.period else "-"

        return f"{full_name} | {score} score | {period}"