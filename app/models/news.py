from django.db import models
from django.core.validators import RegexValidator
from app.models.auth import BaseModel


class News(BaseModel):
    class TypeChoices(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        ANNOUNCEMENT = "announcement", "Announcement"
        EVENT = "event", "Event"

    title = models.CharField(
        max_length=255,
        verbose_name="Sarlavha",
    )

    date = models.CharField(
        max_length=50,
        verbose_name="Sana",
        help_text="Masalan: 15-may, 20-iyun, 01-avgust",
    )

    type = models.CharField(
        max_length=30,
        choices=TypeChoices.choices,
        verbose_name="Turi",
    )

    description = models.TextField(
        verbose_name="Tavsif",
    )

    color = models.CharField(
        max_length=7,
        default="#01E0EE",
        validators=[
            RegexValidator(
                regex=r"^#[0-9A-Fa-f]{6}$",
                message="Rang HEX formatda bo‘lishi kerak. Masalan: #01E0EE",
            )
        ],
        verbose_name="Rang",
    )

    icon = models.CharField(
        max_length=50,
        default="zap",
        verbose_name="Icon",
        help_text="Masalan: zap, calendar, megaphone, trophy",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Faolmi?",
    )

    class Meta:
        db_table = "news"
        verbose_name = "Yangilik"
        verbose_name_plural = "Yangiliklar"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["type"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.title