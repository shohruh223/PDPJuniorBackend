from django.core.exceptions import ValidationError
from django.db import models


class StudentMark(models.Model):
    class AttendanceChoices(models.TextChoices):
        PRESENT = "present", "Qatnashgan"
        ABSENT = "absent", "Qatnashmagan"
        LATE = "late", "Kechikkan"

    student_profile = models.ForeignKey(
        "app.StudentProfile",
        on_delete=models.CASCADE,
        related_name="marks",
    )
    course = models.ForeignKey(
        "app.Course",
        on_delete=models.CASCADE,
        related_name="student_marks",
    )
    lesson = models.ForeignKey(
        "app.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_marks",
    )
    record_date = models.DateField(db_index=True)
    attendance = models.CharField(
        max_length=10,
        choices=AttendanceChoices.choices,
        default=AttendanceChoices.PRESENT,
    )
    grade = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(value, str(value)) for value in range(1, 6)],
    )
    verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = "O‘quvchi bahosi"
        verbose_name_plural = "O‘quvchi baholari"
        ordering = ["-record_date", "student_profile__user__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student_profile", "course", "record_date"],
                name="unique_student_mark_per_course_date",
            )
        ]
        indexes = [
            models.Index(fields=["course", "record_date"]),
            models.Index(fields=["student_profile", "record_date"]),
        ]

    def clean(self):
        super().clean()
        if self.lesson_id and self.lesson.course_id != self.course_id:
            raise ValidationError(
                {"lesson": "Dars tanlangan kursga tegishli bo‘lishi kerak."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.student_profile} | {self.course} | "
            f"{self.record_date:%Y-%m-%d}"
        )
