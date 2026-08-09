from django.contrib import admin

from app.admin.resources import (
    PrettyImportExportModelAdmin,
    StudentPaymentHistoryResource,
)
from app.models.payment import StudentPaymentHistory


@admin.register(StudentPaymentHistory)
class StudentPaymentHistoryAdmin(PrettyImportExportModelAdmin):
    resource_class = StudentPaymentHistoryResource

    list_display = [
        "invoice_number",
        "student_profile",
        "amount",
        "aim",
        "group_name",
        "payment_type",
        "date",
        "created_date",
        "cashier",
        "canceled",
    ]

    list_filter = [
        "payment_type",
        "group_name",
        "canceled",
        "date",
        "created_date",
    ]

    search_fields = [
        "external_id",
        "invoice_number",
        "aim",
        "group_name",
        "time_table_name",
        "cashier",
        "student_profile__user__phone_number",
        "student_profile__user__first_name",
        "student_profile__user__last_name",
    ]

    autocomplete_fields = ["student_profile"]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-created_date",
        "-date",
        "-created_at",
    ]