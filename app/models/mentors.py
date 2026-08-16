from django.db import models
from django.core.exceptions import ValidationError


def validate_socials(value):
    """Eski migratsiyalar uchun saqlangan; yangi kodda ishlatilmaydi."""
    return


def validate_avatar(value):
    if value in [None, ""]:
        return

    if not isinstance(value, dict):
        raise ValidationError("avatar object bo‘lishi kerak.")

    file_path = value.get("url")

    if file_path and not isinstance(file_path, str):
        raise ValidationError("avatar ichidagi url string bo‘lishi kerak.")


class Mentor(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=80)
    bio = models.TextField(blank=True, default="")

    branch = models.ForeignKey(
        "app.Branch",
        on_delete=models.PROTECT,
        related_name="mentors",
    )

    exp = models.CharField(max_length=50)
    students_count = models.CharField(max_length=50)

    working_period_start = models.DateField()

    avatar = models.JSONField(default=dict, blank=True, validators=[validate_avatar])

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        validate_avatar(self.avatar)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} | {self.role}"

    class Meta:
        db_table = "mentors"
        verbose_name = "Mentor"
        verbose_name_plural = "Mentorlar"
        ordering = ["id"]