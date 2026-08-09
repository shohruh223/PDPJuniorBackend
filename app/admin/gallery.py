from django.contrib import admin

from app.admin.mixins import RowActionsAdminMixin
from app.models.gallery import GalleryPost


@admin.register(GalleryPost)
class GalleryPostAdmin(RowActionsAdminMixin, admin.ModelAdmin):
    list_display = ("title_preview", "date", "icon", "views_count", "is_active", "sort_order", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("date",)
    ordering = ("sort_order", "-created_at")

    @admin.display(description="Sarlavha")
    def title_preview(self, obj):
        title = obj.title or {}
        return title.get("uz") or title.get("en") or str(obj.id)
