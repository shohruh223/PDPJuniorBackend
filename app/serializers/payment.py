from rest_framework import serializers

from app.models.payment import StudentInvoice, StudentPaymentHistory


class StudentPaymentHistorySerializer(serializers.ModelSerializer):
    invoiceNumber = serializers.CharField(
        source="invoice_number",
        read_only=True,
    )

    timeTableName = serializers.CharField(
        source="time_table_name",
        read_only=True,
    )

    groupName = serializers.CharField(
        source="group_name",
        read_only=True,
    )

    paymentType = serializers.CharField(
        source="payment_type",
        read_only=True,
    )

    createdDate = serializers.DateTimeField(
        source="created_date",
        format="%Y-%m-%d %H:%M:%S",
        read_only=True,
    )

    date = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True,
    )

    class Meta:
        model = StudentPaymentHistory
        fields = [
            "id",
            "amount",
            "aim",
            "invoiceNumber",
            "timeTableName",
            "groupName",
            "paymentType",
            "date",
            "createdDate",
            "cashier",
            "canceled",
        ]
        read_only_fields = fields


class StudentInvoiceSerializer(serializers.ModelSerializer):
    timeTableName = serializers.CharField(
        source="time_table_name",
        read_only=True,
    )

    groupName = serializers.CharField(
        source="group_name",
        read_only=True,
    )

    timeTablePosition = serializers.CharField(
        source="time_table_position",
        read_only=True,
    )

    invoiceId = serializers.CharField(
        source="external_id",
        read_only=True,
    )

    invoiceNumber = serializers.CharField(
        source="invoice_number",
        read_only=True,
    )

    invoiceStatus = serializers.CharField(
        source="invoice_status",
        read_only=True,
    )

    invoiceAmount = serializers.DecimalField(
        source="invoice_amount",
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )

    paidInvoiceAmount = serializers.DecimalField(
        source="paid_invoice_amount",
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )

    debtAmount = serializers.DecimalField(
        source="debt_amount",
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = StudentInvoice
        fields = [
            "id",
            "timeTableName",
            "groupName",
            "timeTablePosition",
            "invoiceId",
            "invoiceNumber",
            "invoiceStatus",
            "invoiceAmount",
            "paidInvoiceAmount",
            "debtAmount",
        ]
        read_only_fields = fields
