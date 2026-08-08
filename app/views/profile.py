from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.permissions import IsStudentUserRole
from app.serializers.profile import (
    StudentProfileSerializer,
    StudentProfileImageUpdateSerializer,
    StudentPasswordChangeSerializer,
)


class StudentProfileAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Student / Profil"],
        operation_summary="Joriy student profilini olish",
        operation_description=(
            "Login qilingan studentning profil ma’lumotlarini qaytaradi. Avval login "
            "endpointidan olingan access tokenni `Authorization: Bearer <access_token>` "
            "sarlavhasida yuboring. Frontend profil sahifasi, ism, telefon, rasm va "
            "rasm bo‘lmagandagi `avatar` initsiallarini shu javobdan chizadi."
        ),
        responses={
            200: openapi.Response(
                description="Student profili olindi.",
                examples={"application/json": {
                    "success": True,
                    "message": "Student profile ma'lumotlari.",
                    "data": {
                        "id": "c97a5d85-2d93-4f0d-b6c4-8d9d3a7d4e33",
                        "full_name": "Ali Valiyev",
                        "first_name": "Ali",
                        "last_name": "Valiyev",
                        "phone_number": "+998901234567",
                        "image": "https://example.uz/media/profiles/ali.webp",
                        "avatar": "AV",
                    },
                }},
            ),
            401: openapi.Response(description="Access token yuborilmagan yoki yaroqsiz."),
            403: openapi.Response(description="Autentifikatsiyalangan foydalanuvchi student emas."),
        },
    )
    def get(self, request, *args, **kwargs):
        serializer = StudentProfileSerializer(
            request.user,
            context={"request": request},
        )

        return Response(
            {
                "success": True,
                "message": "Student profile ma'lumotlari.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class StudentProfileImageUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        tags=["Student / Profil"],
        operation_summary="Student profil rasmini yangilash",
        operation_description=(
            "Profil rasmini `multipart/form-data` formatida yangilaydi. Avval profilni "
            "GET orqali olish mumkin; keyin `image` maydoniga JPG, PNG yoki WEBP fayl "
            "yuboring (maksimal 5 MB). Muvaffaqiyatli javob to‘liq yangilangan profilni "
            "qaytaradi, shuning uchun frontend lokal profil holatini `data` bilan almashtirishi mumkin."
        ),
        manual_parameters=[
            openapi.Parameter(
                name="image",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="Student profile rasmi. JPG, PNG yoki WEBP. Maksimal 5MB.",
            ),
        ],
        responses={
            200: openapi.Response(
                description="Rasm yangilandi va to‘liq profil qaytarildi.",
                examples={"application/json": {
                    "success": True,
                    "message": "Profile rasmi muvaffaqiyatli yangilandi.",
                    "data": {
                        "id": "c97a5d85-2d93-4f0d-b6c4-8d9d3a7d4e33",
                        "full_name": "Ali Valiyev",
                        "first_name": "Ali",
                        "last_name": "Valiyev",
                        "phone_number": "+998901234567",
                        "image": "https://example.uz/media/profiles/ali.webp",
                        "avatar": "AV",
                    },
                }},
            ),
            400: openapi.Response(
                description="Fayl yo‘q, 5 MB dan katta yoki JPG/PNG/WEBP formatida emas."
            ),
            401: openapi.Response(description="Access token yuborilmagan yoki yaroqsiz."),
            403: openapi.Response(description="Foydalanuvchida student roli yo‘q."),
        },
    )
    def patch(self, request, *args, **kwargs):
        serializer = StudentProfileImageUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        response_serializer = StudentProfileSerializer(
            user,
            context={"request": request},
        )

        return Response(
            {
                "success": True,
                "message": "Profile rasmi muvaffaqiyatli yangilandi.",
                "data": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class StudentPasswordChangeAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]
    parser_classes = [JSONParser]

    @swagger_auto_schema(
        tags=["Student / Profil"],
        operation_summary="Student parolini almashtirish",
        operation_description=(
            "Login qilingan student parolini almashtiradi. `old_password` ga amaldagi "
            "lokal yoki PDP parolini, `new_password` va `confirm_password` ga bir xil "
            "yangi parolni yuboring. Yangi parol Django xavfsizlik talablaridan o‘tishi "
            "va eski paroldan farq qilishi shart. Muvaffaqiyatdan keyin frontend "
            "foydalanuvchini qayta login qilishga yo‘naltirishi tavsiya etiladi."
        ),
        request_body=StudentPasswordChangeSerializer,
        responses={
            200: openapi.Response(
                description="Parol muvaffaqiyatli o‘zgartirildi.",
                examples={"application/json": {
                    "success": True,
                    "message": "Parol muvaffaqiyatli o‘zgartirildi.",
                    "data": None,
                }},
            ),
            400: openapi.Response(
                description="Eski parol noto‘g‘ri, yangi parollar mos emas yoki yangi parol xavfsizlik talabiga javob bermaydi."
            ),
            401: openapi.Response(description="Access token yuborilmagan yoki yaroqsiz."),
            403: openapi.Response(description="Foydalanuvchida student roli yo‘q."),
        },
    )
    def patch(self, request, *args, **kwargs):
        serializer = StudentPasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Parol muvaffaqiyatli o‘zgartirildi.",
                "data": None,
            },
            status=status.HTTP_200_OK,
        )