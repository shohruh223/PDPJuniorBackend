from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from app.models.auth import StudentProfile
from app.models.payment import StudentPaymentHistory
from app.permissions import IsStudentUserRole
from app.serializers.payment import StudentPaymentHistorySerializer
from app.services.student.payment_history_service import (
    fetch_and_sync_student_payment_histories,
)


class StudentPaymentHistoryListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Student / Payments"],
        operation_summary="Student to‘lovlari tarixi",
        operation_description=(
            "Autentifikatsiya qilingan studentning to‘lov tarixini tashqi manba bilan sinxronlashtiradi va "
            "eng yangi yozuvdan boshlab qaytaradi. Bearer token yuboring; query parametrlari kerak emas. "
            "`sync_warning` sinxronlashdagi ogohlantirishni saqlashi mumkin, ammo lokal tarix baribir qaytariladi."
        ),
        responses={
            200: openapi.Response(
                "To‘lov tarixi olindi.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=["success", "message", "data", "sync_warning"],
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_STRING),
                                    "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                                    "aim": openapi.Schema(type=openapi.TYPE_STRING),
                                    "invoiceNumber": openapi.Schema(type=openapi.TYPE_STRING),
                                    "timeTableName": openapi.Schema(type=openapi.TYPE_STRING),
                                    "groupName": openapi.Schema(type=openapi.TYPE_STRING),
                                    "paymentType": openapi.Schema(type=openapi.TYPE_STRING),
                                    "date": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="2026-08-08 14:30:00",
                                    ),
                                    "createdDate": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="2026-08-08 14:31:00",
                                    ),
                                    "cashier": openapi.Schema(type=openapi.TYPE_STRING),
                                    "canceled": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                },
                            ),
                        ),
                        "sync_warning": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            x_nullable=True,
                            description="Sinxronlash muvaffaqiyatli bo‘lsa null.",
                        ),
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
            404: openapi.Response(
                "Student profil topilmadi.",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Student profile topilmadi.",
                    }
                },
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        try:
            student_profile = StudentProfile.objects.get(user=request.user)
        except StudentProfile.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Student profile topilmadi.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        _, sync_warning = fetch_and_sync_student_payment_histories(student_profile)

        payment_histories = StudentPaymentHistory.objects.filter(
            student_profile=student_profile,
        ).order_by(
            "-created_date",
            "-date",
            "-created_at",
        )

        serializer = StudentPaymentHistorySerializer(
            payment_histories,
            many=True,
        )

        return Response(
            {
                "success": True,
                "message": "Payment history ma'lumotlari",
                "data": serializer.data,
                "sync_warning": sync_warning,
            },
            status=status.HTTP_200_OK,
        )