from django.db import models
from django.utils import timezone

from app.models.auth import BaseModel


class GalleryPost(BaseModel):
    """Frontend gallery-page.js kontraktiga mos galereya/yangilik posti."""

    category = models.JSONField(
        help_text='{"uz":"Tadbir","ru":"Событие","en":"Event"}',
        verbose_name="Toifasi",
    )
    icon = models.CharField(max_length=16, default="📰", verbose_name="Belgisi")
    date = models.CharField(max_length=20, help_text="Masalan: 12.07.2026", verbose_name="Sanasi")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Ko‘rishlar soni")
    views_display = models.CharField(max_length=20, blank=True, default="", verbose_name="Ko‘rishlar (matn)")

    cover_image = models.CharField(max_length=500, blank=True, default="", verbose_name="Muqova rasmi")
    cover_contain = models.BooleanField(default=False, verbose_name="Muqovani to‘liq ko‘rsatish")
    cover_bg = models.CharField(max_length=200, blank=True, default="", verbose_name="Muqova foni")

    title = models.JSONField(verbose_name="Sarlavhasi")
    description = models.JSONField(verbose_name="Tavsifi")
    media = models.JSONField(default=list, blank=True, verbose_name="Media fayllar")

    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Faol")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    class Meta:
        db_table = "gallery_posts"
        verbose_name = "Galereya posti"
        verbose_name_plural = "Galereya postlari"
        ordering = ["sort_order", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.date:
            when = self.created_at or timezone.now()
            self.date = timezone.localtime(when).strftime("%d.%m.%Y")
        super().save(*args, **kwargs)

    def __str__(self):
        title = self.title or {}
        return title.get("uz") or title.get("en") or str(self.id)

    @property
    def views(self):
        if self.views_display:
            return self.views_display
        count = self.views_count or 0
        if count >= 1000:
            return f"{count / 1000:.1f}K".replace(".0K", "K")
        return str(count)
