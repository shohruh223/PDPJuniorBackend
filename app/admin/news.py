from django.contrib import admin

from app.admin.resources import PrettyImportExportModelAdmin, NewsResource
from app.models.news import News


@admin.register(News)
class NewsAdmin(PrettyImportExportModelAdmin):
    resource_class = NewsResource

    list_display = (
        "title",
        "date",
        "type",
        "color",
        "icon",
        "is_active",
        "created_at",
    )
    list_filter = (
        "type",
        "is_active",
        "created_at",
    )
    search_fields = (
        "title",
        "description",
        "date",
    )
    ordering = ("-created_at",)