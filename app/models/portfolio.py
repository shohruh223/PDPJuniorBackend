from django.db import models
from django.core.exceptions import ValidationError


def validate_portfolio_image(value):
    if value in [None, ""]:
        return

    if not isinstance(value, dict):
        raise ValidationError("image object bo‘lishi kerak.")

    file_path = value.get("url")

    if file_path and not isinstance(file_path, str):
        raise ValidationError("image ichidagi url string bo‘lishi kerak.")


class Portfolio(models.Model):
    name = models.CharField(max_length=120, verbose_name="Loyiha nomi")
    url = models.URLField(max_length=500, verbose_name="Havolasi")
    image = models.JSONField(default=dict, blank=True, validators=[validate_portfolio_image], verbose_name="Rasmi")
    desc = models.CharField(max_length=255, verbose_name="Tavsifi")
    student = models.CharField(max_length=120, blank=True, default="", verbose_name="Muallifi")
    category = models.CharField(max_length=80, blank=True, default="", verbose_name="Toifasi")
    year = models.CharField(max_length=4, blank=True, default="", verbose_name="Yili")

    is_active = models.BooleanField(default=True, verbose_name="Faol")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    def clean(self):
        validate_portfolio_image(self.image)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "portfolios"
        verbose_name = "Portfolio"
        verbose_name_plural = "Portfoliolar"
        ordering = ["id"]