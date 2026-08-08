from rest_framework import serializers

from app.models.payment import StudentPaymentHistory


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