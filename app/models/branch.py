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
        (OPENED, "Ochiq"),
        (CLOSED, "Yopiq"),
    )

    name = models.CharField(max_length=120, verbose_name="Filial nomi")
    address = models.CharField(max_length=255, verbose_name="Manzil")
    phone = models.CharField(max_length=20, verbose_name="Telefon")
    hours = models.CharField(max_length=50, blank=True, default="09:00–18:00", verbose_name="Ish vaqti")
    image_url = models.CharField(max_length=500, blank=True, default="", verbose_name="Rasm havolasi")
    district = models.CharField(max_length=120, blank=True, default="", verbose_name="Tuman")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, verbose_name="Kenglik")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True, verbose_name="Uzunlik")

    map_url = models.URLField(max_length=500, verbose_name="Xarita havolasi")
    is_opened = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=OPENED,
        db_index=True,
        verbose_name="Holati",
    )

    album = models.JSONField(default=list, blank=True, validators=[validate_album], verbose_name="Rasmlar albomi")

    is_active = models.BooleanField(default=True, verbose_name="Faol")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

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