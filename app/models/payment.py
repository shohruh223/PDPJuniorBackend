from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import models
from django.utils import timezone

from app.models.auth import BaseModel, StudentProfile


class StudentPaymentHistory(BaseModel):
    student_profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="payment_histories",
        verbose_name="O‘quvchi",
    )

    external_id = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name="Tashqi ID",
    )

    invoice_number = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Invoys raqami",
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Summasi",
    )

    aim = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Maqsadi",
    )

    time_table_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Dars jadvali",
    )

    group_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Guruh",
    )

    payment_type = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="To‘lov turi",
    )

    date = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name="To‘lov sanasi",
    )

    created_date = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Yaratilgan sana",
    )

    cashier = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Kassir",
    )

    canceled = models.BooleanField(default=False, verbose_name="Bekor qilingan")

    raw_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Xom ma’lumot",
    )

    class Meta:
        db_table = "student_payment_histories"
        ordering = ["-created_date", "-date", "-created_at"]
        verbose_name = "To‘lov tarixi"
        verbose_name_plural = "To‘lovlar tarixi"

        constraints = [
            models.UniqueConstraint(
                fields=["student_profile", "external_id"],
                name="unique_student_payment_history_external_id",
            ),
        ]

        indexes = [
            models.Index(fields=["student_profile", "invoice_number"]),
            models.Index(fields=["student_profile", "created_date"]),
            models.Index(fields=["student_profile", "date"]),
        ]

    def __str__(self):
        return self.invoice_number or self.external_id

    @staticmethod
    def to_decimal(value) -> Decimal:
        try:
            return Decimal(str(value if value not in (None, "") else 0)).quantize(
                Decimal("0.01")
            )
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0.00")

    @staticmethod
    def timestamp_ms_to_datetime(value):
        """
        PDP API dan keladigan timestamp milliseconds qiymatini
        Django DateTimeField uchun datetime formatiga o'tkazadi.

        Misol:
        1776419579595 -> datetime
        """

        if value in (None, ""):
            return None

        try:
            timestamp = int(value) / 1000

            return datetime.fromtimestamp(
                timestamp,
                tz=timezone.get_current_timezone(),
            )
        except (ValueError, TypeError, OSError, OverflowError):
            return None


class StudentInvoice(BaseModel):
    student_profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="invoices",
        verbose_name="O‘quvchi profili",
    )

    external_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="PDP invoiceId",
        verbose_name="Tashqi ID",
    )

    invoice_number = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Invoys raqami",
    )

    invoice_status = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Invoys holati",
    )

    invoice_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Invoys summasi",
    )

    paid_invoice_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="To‘langan summa",
    )

    debt_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Qarz summasi",
    )

    time_table_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Dars jadvali",
    )

    time_table_position = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Jadval o‘rni",
    )

    group_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Guruh nomi",
    )

    raw_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Xom ma’lumot",
    )

    class Meta:
        db_table = "student_invoices"
        ordering = ["-updated_at", "-created_at"]
        verbose_name = "O‘quvchi invoysi"
        verbose_name_plural = "O‘quvchi invoyslari"

        constraints = [
            models.UniqueConstraint(
                fields=["student_profile", "external_id"],
                name="unique_student_invoice_external_id",
            ),
        ]

        indexes = [
            models.Index(fields=["student_profile", "invoice_number"]),
            models.Index(fields=["student_profile", "invoice_status"]),
            models.Index(fields=["student_profile", "time_table_position"]),
        ]

    def __str__(self):
        return self.invoice_number or self.external_id

    @staticmethod
    def to_decimal(value) -> Decimal:
        return StudentPaymentHistory.to_decimal(value)
