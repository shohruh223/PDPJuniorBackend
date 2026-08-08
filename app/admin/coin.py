from django.contrib import admin
from app.admin.resources import PrettyImportExportModelAdmin, CoinProductResource
from app.models.coin import CoinProduct, CoinOrder


@admin.register(CoinProduct)
class CoinProductAdmin(PrettyImportExportModelAdmin):
    resource_class = CoinProductResource

    list_display = ["name", "category", "price", "stock", "emoji", "is_active", "created_at"]
    list_filter = ["category", "is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CoinOrder)
class CoinOrderAdmin(admin.ModelAdmin):
    list_display = ["product_title", "student_profile", "price", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["product_title"]
    readonly_fields = ["id", "created_at", "updated_at"]