from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from app.serializers.auth import (
    CheckPhoneSerializer,
    EnterPasswordSerializer,
    CheckSMSCodeSerializer,
    ForgotPasswordSerializer,
    VerifySMSCodeSerializer,
    SetNewPasswordSerializer,
)
from app.services.auth_service import (
    check_phone_via_external_api,
    enter_password_via_external_api,
    check_sms_code_and_sync_user,
    forgot_password_via_external_api,
    verify_sms_code_via_external_api,
    set_new_password_via_external_api, verify_sms_code_for_password_reset, set_new_password_with_pre_token,
)
from app.services.password_reset_token import PreResetTokenError
from app.services.auth_external_api import PDPAPIError


class CheckPhoneAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Autentifikatsiya"],
        operation_summary="Telefon raqamni tekshirish",
        operation_description="""
    Login flow'ning 1-bosqichi.

    Frontend foydalanuvchi telefon raqamini kiritgandan keyin shu endpointni chaqiradi.
    Endpoint raqam tizimda mavjudligini va foydalanuvchida oldindan parol bor yoki yo‘qligini tekshiradi.

    Frontend uchun:
    - agar `hasPassword = true` bo‘lsa, keyingi qadamda parol kiritish oynasiga o‘ting
    - agar `hasPassword = false` bo‘lsa, login flow boshqa ssenariy bo‘yicha davom etishi mumkin

    Request:
    - `phone_number`: foydalanuvchi telefon raqami

    Response:
    - `success`: so‘rov holati
    - `data.hasPassword`: foydalanuvchida parol mavjud yoki yo‘qligi

    Eslatma:
    bu endpoint login qilmaydi, faqat keyingi ekranni tanlashga yordam beradi.
    """,
        request_body=CheckPhoneSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Telefon muvaffaqiyatli tekshirildi",
                examples={
                    "application/json": {
                        "success": True,
                        "data": {
                            "hasPassword": True
                        }
                    }
                },
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Noto‘g‘ri so‘rov"
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = CheckPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = check_phone_via_external_api(
            phone_number=serializer.validated_data["phone_number"]
        )
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class EnterPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Autentifikatsiya"],
        operation_summary="Parolni yuborish",
        operation_description="""
    Login flow'ning 2-bosqichi.

    Frontend foydalanuvchi telefon raqami va parolni yuboradi.
    Agar parol to‘g‘ri bo‘lsa, backend tashqi tizimdan SMS tasdiqlash jarayonini boshlaydi va `smsCodeId` qaytaradi.

    Frontend uchun:
    - muvaffaqiyatli bo‘lsa, SMS kod kiritish sahifasiga o‘ting
    - `smsCodeId` va `phoneNumber` ni keyingi endpoint uchun saqlab turing

    Request:
    - `phone_number`: foydalanuvchi telefon raqami
    - `password`: foydalanuvchi paroli

    Response:
    - `success`: so‘rov holati
    - `message`: foydalanuvchiga ko‘rsatish mumkin bo‘lgan izoh
    - `data.smsCodeId`: SMS tasdiqlash uchun identifikator
    - `data.phoneNumber`: tasdiqlanadigan telefon raqami
    - `data.reliableDevice`: tashqi tizimdan kelgan qo‘shimcha flag

    Xatolik:
    - parol noto‘g‘ri bo‘lsa 400 qaytadi
    - bu endpoint hali lokal JWT token bermaydi
    """,
        request_body=EnterPasswordSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Parol qabul qilindi",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "SMS kodni tasdiqlang!",
                        "data": {
                            "smsCodeId": "291b3c96-1d95-4013-9ad8-ef24849a37c5",
                            "phoneNumber": "+998901234567",
                            "reliableDevice": False
                        }
                    }
                },
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Telefon raqam yoki parol xato"
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Kutilmagan ichki server xatoligi.",
                examples={"application/json": {
                    "success": False,
                    "message": "Ichki server xatoligi yuz berdi.",
                }},
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = EnterPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = enter_password_via_external_api(
                phone_number=serializer.validated_data["phone_number"],
                password=serializer.validated_data["password"],
            )
            return Response(
                {
                    "success": True,
                    "message": "SMS kodni tasdiqlang!",
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )

        except PDPAPIError as e:
            error_text = str(e)

            if "WRONG_PASSWORD" in error_text:
                return Response(
                    {
                        "success": False,
                        "message": "Telefon raqam yoki parol xato kiritildi.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "success": False,
                    "message": "Parolni tekshirishda xatolik yuz berdi.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "Ichki server xatoligi yuz berdi.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CheckSMSCodeAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Autentifikatsiya"],
        operation_summary="SMS kodni tekshirish va userni login qilish",
        operation_description="""
    Login flow'ning 3-bosqichi va asosiy yakuniy bosqichi.

    Frontend foydalanuvchi kiritgan SMS kodni, oldingi bosqichdan kelgan `smsCodeId`
    va telefon raqami bilan birga yuboradi.
    Agar SMS kod to‘g‘ri bo‘lsa:
    - foydalanuvchi tashqi tizim bo‘yicha tasdiqlanadi
    - lokal user sinxron qilinadi
    - lokal access/refresh tokenlar qaytariladi

    Frontend uchun:
    - shu endpoint muvaffaqiyatli o'tsa foydalanuvchini login bo‘lgan deb hisoblang
    - `access` va `refresh` tokenlarni saqlang
    - `student` obyektidan profil ma’lumotlarini oling

    Request:
    - `phone_number`: foydalanuvchi telefon raqami
    - `sms_code_id`: oldingi bosqichdan qaytgan identifikator
    - `sms_code`: foydalanuvchi kiritgan SMS kod

    Response:
    - `success`: so‘rov holati
    - `data.pdp_token`: tashqi tizim tokeni
    - `data.access`: lokal access token
    - `data.refresh`: lokal refresh token
    - `data.student`: foydalanuvchi profili

    Muhim:
    frontend uchun asosiy login muvaffaqiyati shu endpointdan keyin boshlanadi.
    """,

        request_body=CheckSMSCodeSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Login muvaffaqiyatli bajarildi",
                examples={
                    "application/json": {
                        "success": True,
                        "data": {
                            "pdp_token": "Bearer eyJhbGciOiJIUzI1NiJ9...",
                            "access": "local_access_token",
                            "refresh": "local_refresh_token",
                            "student": {
                                "id": "c97a5d85-2d93-4f0d-b6c4-8d9d3a7d4e33",
                                "external_id": "49687357-f9a9-4642-a946-81ce67b633bd",
                                "first_name": "Ali",
                                "last_name": "Valiyev",
                                "full_name": "Ali Valiyev",
                                "phone_number": "+998901234567",
                                "patron": "Karim o‘g‘li",
                                "role": "student",
                            },
                        },
                    }
                },
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Noto‘g‘ri SMS kod yoki noto‘g‘ri so‘rov"
            ),
            status.HTTP_502_BAD_GATEWAY: openapi.Response(
                description="Tashqi PDP auth servisi javob bermadi.",
                examples={"application/json": {
                    "success": False,
                    "message": "Tashqi PDP auth servisida xatolik bor. Birozdan keyin qayta urinib ko‘ring.",
                }},
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Kutilmagan ichki server xatoligi."
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = CheckSMSCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = check_sms_code_and_sync_user(
                sms_code_id=serializer.validated_data["sms_code_id"],
                sms_code=serializer.validated_data["sms_code"],
                phone_number=serializer.validated_data["phone_number"],
            )

            return Response(
                {
                    "success": True,
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )

        except PDPAPIError:
            return Response(
                {
                    "success": False,
                    "message": "Tashqi PDP auth servisida xatolik bor. Birozdan keyin qayta urinib ko‘ring.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:

            return Response(
                {
                    "success": False,
                    "message": "Ichki server xatoligi yuz berdi.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Parolni tiklash"],
        operation_summary="Parolni tiklashni boshlash",
        operation_description="""
    Parolni unutgan foydalanuvchi uchun reset flow'ning 1-bosqichi.

    Frontend foydalanuvchi telefon raqamini yuboradi.
    Backend tashqi tizim orqali parolni tiklash uchun SMS yuboradi va `smsCodeId` qaytaradi.

    Frontend uchun:
    - muvaffaqiyatli bo‘lsa, SMS kod kiritish bosqichiga o‘ting
    - `smsCodeId` va `phoneNumber` ni keyingi reset bosqichi uchun saqlang

    Request:
    - `phone_number`: foydalanuvchi telefon raqami

    Response:
    - `success`: so‘rov holati
    - `data.smsCodeId`: reset SMS kodi uchun identifikator
    - `data.phoneNumber`: tasdiqlanadigan telefon raqami

    Eslatma:
    bu endpoint yangi parol o‘rnatmaydi, faqat reset jarayonini boshlaydi.
    """,
        request_body=ForgotPasswordSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Parolni tiklash uchun SMS yuborildi",
                examples={
                    "application/json": {
                        "success": True,
                        "data": {
                            "smsCodeId": "291b3c96-1d95-4013-9ad8-ef24849a37c5",
                            "phoneNumber": "+998901234567"
                        }
                    }
                },
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Noto‘g‘ri so‘rov"
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = forgot_password_via_external_api(
            phone_number=serializer.validated_data["phone_number"]
        )
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class VerifySMSCodeAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Parolni tiklash"],
        operation_summary="Parol tiklash uchun SMS kodni tasdiqlash",
        operation_description="""
    Parol reset flow'ning 2-bosqichi.

    Frontend foydalanuvchi kiritgan SMS kodni yuboradi.
    Backend yuborilgan qiymatlarni parolni yangilashga ruxsat beruvchi qisqa muddatli
    `pre_reset_token` ichiga xavfsiz joylaydi.

    Frontend uchun:
    - muvaffaqiyatli response'dan keyin yangi parol kiritish ekraniga o‘ting
    - response ichidagi `data.pre_reset_token` ni saqlang
    - tokenni `SetNewPasswordAPIView` so‘rovidagi `pre_reset_token` maydoniga yuboring

    Request:
    - `phone_number`: foydalanuvchi telefon raqami
    - `sms_code_id`: reset bosqichida olingan identifikator
    - `sms_code`: foydalanuvchi kiritgan SMS kod

    Response:
    - `success`: so‘rov holati
    - `data.pre_reset_token`: yakuniy `set-new-password` bosqichi uchun vaqtinchalik token

    Eslatma:
    bu endpoint parolni hali o‘zgartirmaydi.
    """,
        request_body=VerifySMSCodeSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="SMS kod tasdiqlandi",
                examples={
                    "application/json": {
                        "success": True,
                        "data": {
                            "pre_reset_token": "eyJwaG9uZV9udW1iZXIiOiIrOTk4..."
                        }
                    }
                },
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Noto‘g‘ri SMS kod yoki noto‘g‘ri so‘rov"
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = VerifySMSCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = verify_sms_code_for_password_reset(
            phone_number=serializer.validated_data["phone_number"],
            sms_code_id=serializer.validated_data["sms_code_id"],
            sms_code=serializer.validated_data["sms_code"],
        )
        return Response(
            {"success": True, "data": data},
            status=status.HTTP_200_OK
        )


class SetNewPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Parolni tiklash"],
        operation_summary="Yangi parol o‘rnatish",
        operation_description="""
    Parol reset flow'ning yakuniy bosqichi.

    Frontend foydalanuvchidan yangi parol va uni tasdiqlash qiymatini olib yuboradi.
    Shuningdek, oldingi bosqichda tasdiqlangan reset token ham yuboriladi.

    Frontend uchun:
    - muvaffaqiyatli bo‘lsa foydalanuvchiga 'parol muvaffaqiyatli o‘zgartirildi' degan xabar ko‘rsating
    - so‘ng login sahifasiga yo‘naltiring yoki login flow'ni qayta boshlang

    Request:
    - `pre_reset_token`: oldingi reset bosqichidan olingan vaqtinchalik token
    - `password`: yangi parol
    - `repeat_password`: yangi parolni tasdiqlash

    Response:
    - `success`: so‘rov holati
    - `message`: foydalanuvchiga ko‘rsatish mumkin bo‘lgan muvaffaqiyat xabari
    - `data`: odatda bo‘sh obyekt yoki texnik ma’lumot

    Xatolik:
    - token eskirgan yoki noto‘g‘ri bo‘lsa 400 qaytishi mumkin
    - parollar mos kelmasa validation xatosi qaytadi
    """,
        request_body=SetNewPasswordSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Yangi parol muvaffaqiyatli o‘rnatildi",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Parol muvaffaqiyatli o‘zgartirildi.",
                        "data": {}
                    }
                },
            ),
            status.HTTP_400_BAD_REQUEST: openapi.Response(
                description="Noto‘g‘ri so‘rov"
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: openapi.Response(
                description="Kutilmagan ichki server xatoligi.",
                examples={"application/json": {
                    "success": False,
                    "message": "Ichki server xatoligi yuz berdi.",
                }},
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = SetNewPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = set_new_password_with_pre_token(
                pre_reset_token=serializer.validated_data["pre_reset_token"],
                password=serializer.validated_data["password"],
                repeat_password=serializer.validated_data["repeat_password"],
            )

            return Response(
                {
                    "success": True,
                    "message": "Parol muvaffaqiyatli o‘zgartirildi.",
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )

        except PreResetTokenError as e:
            return Response(
                {
                    "success": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except PDPAPIError as e:
            return Response(
                {
                    "success": False,
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "Ichki server xatoligi yuz berdi.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
