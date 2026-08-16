from django.db import models
from django.utils import timezone

from app.models.auth import BaseModel


class GalleryPost(BaseModel):
    """Frontend gallery-page.js kontraktiga mos galereya/yangilik posti."""

    category = models.JSONField(
        help_text='{"uz":"Tadbir","ru":"Событие","en":"Event"}',
    )
    icon = models.CharField(max_length=16, default="📰")
    date = models.CharField(max_length=20, help_text="Masalan: 12.07.2026")
    views_count = models.PositiveIntegerField(default=0)
    views_display = models.CharField(max_length=20, blank=True, default="")

    cover_image = models.CharField(max_length=500, blank=True, default="")
    cover_contain = models.BooleanField(default=False)
    cover_bg = models.CharField(max_length=200, blank=True, default="")

    title = models.JSONField()
    description = models.JSONField()
    media = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

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
