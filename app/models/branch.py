from django.db import models
from django.core.exceptions import ValidationError


def validate_album(value):
    if not isinstance(value, list):
        raise ValidationError("album list bo‘lishi kerak.")

    allowed_types = {"image", "video"}

    for item in value:
        if not isinstance(item, dict):
            raise ValidationError("album ichidagi har bir element object bo‘lishi kerak.")

        media_type = item.get("type")
        url = item.get("url")

        if media_type not in allowed_types:
            raise ValidationError("album type faqat image yoki video bo‘lishi kerak.")

        if not isinstance(url, str) or not url.strip():
            raise ValidationError("album url bo‘sh bo‘lmagan string bo‘lishi kerak.")


class Branch(models.Model):
    OPENED = "opened"
    CLOSED = "closed"

    STATUS_CHOICES = (
        (OPENED, "Opened"),
        (CLOSED, "Closed"),
    )

    name = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    hours = models.CharField(max_length=50, blank=True, default="09:00–18:00")
    image_url = models.CharField(max_length=500, blank=True, default="")
    district = models.CharField(max_length=120, blank=True, default="")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)

    map_url = models.URLField(max_length=500)
    is_opened = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=OPENED,
        db_index=True,
    )

    album = models.JSONField(default=list, blank=True, validators=[validate_album])

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        validate_album(self.album)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "branches"
        verbose_name = "Filial"
        verbose_name_plural = "Filiallar"
        ordering = ["id"]