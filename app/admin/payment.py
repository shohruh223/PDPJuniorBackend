from django.contrib import admin

from app.admin.resources import (
    PrettyImportExportModelAdmin,
    StudentInvoiceResource,
    StudentPaymentHistoryResource,
)
from app.models.payment import StudentInvoice, StudentPaymentHistory


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


@admin.register(StudentInvoice)
class StudentInvoiceAdmin(PrettyImportExportModelAdmin):
    resource_class = StudentInvoiceResource

    list_display = [
        "invoice_number",
        "student_profile",
        "invoice_status",
        "invoice_amount",
        "paid_invoice_amount",
        "debt_amount",
        "group_name",
        "time_table_name",
        "time_table_position",
    ]

    list_filter = [
        "invoice_status",
        "time_table_position",
        "group_name",
    ]

    search_fields = [
        "external_id",
        "invoice_number",
        "group_name",
        "time_table_name",
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
        "-updated_at",
        "-created_at",
    ]
