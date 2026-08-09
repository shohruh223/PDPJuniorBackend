from django.contrib import admin
from django.utils import timezone
from app.admin.mixins import RowActionsAdminMixin
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
class CoinOrderAdmin(RowActionsAdminMixin, admin.ModelAdmin):
    def get_model_perms(self, request):
        return {}

    list_display = [
        "product_title",
        "student_name",
        "branch_name",
        "price",
        "balance_after",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "product_title",
        "student_name",
        "student_phone",
        "branch_name",
        "group_name",
    ]
    readonly_fields = [
        "id",
        "student_profile",
        "product",
        "product_title",
        "price",
        "student_name",
        "student_phone",
        "course_name",
        "branch_name",
        "group_name",
        "balance_before",
        "balance_after",
        "telegram_sent_at",
        "telegram_error",
        "is_admin_read",
        "admin_read_at",
        "created_at",
        "updated_at",
    ]

    def change_view(self, request, object_id, form_url="", extra_context=None):
        CoinOrder.objects.filter(
            pk=object_id,
            is_admin_read=False,
        ).update(
            is_admin_read=True,
            admin_read_at=timezone.now(),
        )
        return super().change_view(request, object_id, form_url, extra_context)