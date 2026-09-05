from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from app.models.auth import StudentProfile
from app.models.payment import StudentInvoice, StudentPaymentHistory
from app.pagination import paginate_iterable
from app.permissions import IsStudentUserRole
from app.services.student import sync_coordinator
from app.throttling import SyncThrottle
from app.serializers.payment import (
    StudentInvoiceSerializer,
    StudentPaymentHistorySerializer,
)


class StudentPaymentHistoryListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]
    throttle_classes = [SyncThrottle]

    @swagger_auto_schema(
        tags=["Student / Payments"],
        operation_summary="Student to'lovlari tarixi",
        operation_description=(
            "Autentifikatsiya qilingan studentning to'lov tarixini tashqi manba bilan sinxronlashtiradi va "
            "eng yangi yozuvdan boshlab qaytaradi. Bearer token yuboring; query parametrlari kerak emas. "
            "`sync_warning` sinxronlashdagi ogohlantirishni saqlashi mumkin, ammo lokal tarix baribir qaytariladi."
        ),
        responses={
            200: openapi.Response(
                "To'lov tarixi olindi.",
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
                            description="Sinxronlash muvaffaqiyatli bo'lsa null.",
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

        # Tashqi PDP so'rovi endi so'rovni bloklamaydi: u fon rejimida
        # (Celery) bajariladi, javob esa bazadagi nusxadan quriladi.
        _, sync_warning = sync_coordinator.ensure_fresh(
            student_profile,
            sync_coordinator.PAYMENTS,
            force=sync_coordinator.wants_refresh(request),
        )

        payment_histories = StudentPaymentHistory.objects.filter(
            student_profile=student_profile,
        ).order_by(
            "-created_date",
            "-date",
            "-created_at",
        )

        page, meta = paginate_iterable(request, payment_histories)
        serializer = StudentPaymentHistorySerializer(page, many=True)

        body = {
            "success": True,
            "message": "Payment history ma'lumotlari",
            "data": serializer.data,
            "sync_warning": sync_warning,
        }
        if meta:
            body["meta"] = meta
        return Response(body, status=status.HTTP_200_OK)


class StudentInvoiceListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]
    throttle_classes = [SyncThrottle]

    @swagger_auto_schema(
        tags=["Student / Payments"],
        operation_summary="Student invoyslari",
        operation_description=(
            "Autentifikatsiya qilingan studentning joriy/pending invoyslarini tashqi PDP "
            "`student-invoices` manbasi bilan sinxronlashtiradi va qaytaradi. "
            "Qaysi oyga to'lash (`timeTableName`), invoys raqami, status va qarz summasi shu yerda. "
            "`sync_warning` sinxronlashdagi ogohlantirishni saqlashi mumkin, ammo lokal data baribir qaytariladi."
        ),
        responses={
            200: openapi.Response(
                "Invoyslar olindi.",
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
                                    "timeTableName": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="Time table 3",
                                    ),
                                    "groupName": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="P-18",
                                    ),
                                    "timeTablePosition": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="CURRENT",
                                    ),
                                    "invoiceId": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="8b4b32fe-9bd1-43a7-af11-8a61858c59a9",
                                    ),
                                    "invoiceNumber": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="INV-A0126130",
                                    ),
                                    "invoiceStatus": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="PENDING",
                                    ),
                                    "invoiceAmount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER,
                                        example=1090000.0,
                                    ),
                                    "paidInvoiceAmount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER,
                                        example=0.0,
                                    ),
                                    "debtAmount": openapi.Schema(
                                        type=openapi.TYPE_NUMBER,
                                        example=1090000.0,
                                    ),
                                },
                            ),
                        ),
                        "sync_warning": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            x_nullable=True,
                            description="Sinxronlash muvaffaqiyatli bo'lsa null.",
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

        _, sync_warning = sync_coordinator.ensure_fresh(
            student_profile,
            sync_coordinator.INVOICES,
            force=sync_coordinator.wants_refresh(request),
        )

        invoices = StudentInvoice.objects.filter(
            student_profile=student_profile,
        ).order_by(
            "-updated_at",
            "-created_at",
        )

        page, meta = paginate_iterable(request, invoices)
        serializer = StudentInvoiceSerializer(page, many=True)

        body = {
            "success": True,
            "message": "Student invoices ma'lumotlari",
            "data": serializer.data,
            "sync_warning": sync_warning,
        }
        if meta:
            body["meta"] = meta
        return Response(body, status=status.HTTP_200_OK)
