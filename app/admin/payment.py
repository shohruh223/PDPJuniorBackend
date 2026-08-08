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

    readonly_fields = [
        "id",
        "student_profile",
        "external_id",
        "invoice_number",
        "amount",
        "aim",
        "time_table_name",
        "group_name",
        "payment_type",
        "date",
        "created_date",
        "cashier",
        "canceled",
        "raw_data",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "-created_date",
        "-date",
        "-created_at",
    ]