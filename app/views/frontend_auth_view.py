from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from app.throttling import AuthEndpointThrottle, SmsThrottle
from app.serializers.auth import (
    CheckSMSCodeSerializer,
    EnterPasswordSerializer,
    ForgotPasswordSerializer,
    SetNewPasswordSerializer,
    VerifySMSCodeSerializer,
)
from app.services.auth_external_api import PDPAPIError
from app.services.auth_service import (
    check_sms_code_and_sync_user,
    enter_password_via_external_api,
    forgot_password_via_external_api,
    set_new_password_with_pre_token,
    verify_sms_code_for_password_reset,
)
from app.services.password_reset_token import PreResetTokenError
from app.utils.frontend_adapters import (
    auth_forgot_verify_response,
    auth_login_verify_response,
    auth_sms_response,
    pick_sms_code_id,
)


class FrontendLoginAPIView(APIView):
    """Frontend: POST /auth/login — telefon va parol, SMS kod yuborish."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    @swagger_auto_schema(
        tags=["Frontend / Autentifikatsiya"],
        operation_summary="Telefon va parol orqali loginni boshlash",
        operation_description=(
            "Frontend login jarayonining 1-bosqichi. `phone_number` (`+998XXXXXXXXX`) "
            "va parol yuboriladi; ma’lumotlar to‘g‘ri bo‘lsa PDP servis SMS yuboradi. "
            "Javobdagi `sms_code_id` ni telefon raqami bilan saqlang va keyingi bosqichda "
            "`POST /auth/login/verify` ga yuboring. Bu endpoint hali access token bermaydi."
        ),
        request_body=EnterPasswordSerializer,
        responses={
            200: openapi.Response(
                description="Parol tekshirildi va SMS yuborildi.",
                examples={"application/json": {
                    "message": "SMS kodni tasdiqlang!",
                    "sms_code_id": "291b3c96-1d95-4013-9ad8-ef24849a37c5",
                }},
            ),
            400: openapi.Response(
                description="Validatsiya xatosi yoki telefon/parol noto‘g‘ri.",
                examples={"application/json": {
                    "message": "Telefon raqam yoki parol xato kiritildi."
                }},
            ),
            502: openapi.Response(
                description="Tashqi servis javobida sms_code_id yo‘q.",
                examples={"application/json": {
                    "message": "Server javobida sms_code_id topilmadi."
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
        except PDPAPIError:
            return Response(
                {"message": "Telefon raqam yoki parol xato kiritildi."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return Response(
                {"message": "Parolni tekshirishda xatolik yuz berdi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = auth_sms_response(data, message="SMS kodni tasdiqlang!")
        if not pick_sms_code_id(data):
            return Response(
                {"message": "Server javobida sms_code_id topilmadi."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(body, status=status.HTTP_200_OK)


class FrontendVerifyLoginAPIView(APIView):
    """Frontend: POST /auth/login/verify — SMS kodni tasdiqlash va token olish."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    @swagger_auto_schema(
        tags=["Frontend / Autentifikatsiya"],
        operation_summary="Login SMS kodini tasdiqlash va token olish",
        operation_description=(
            "Frontend login jarayonining 2-yakuniy bosqichi. `/auth/login` dan olingan "
            "`sms_code_id`, o‘sha `phone_number` va foydalanuvchi kiritgan `sms_code` "
            "yuboriladi. Muvaffaqiyatli javobdan `access_token` ni Bearer token sifatida, "
            "`refresh_token` ni token yangilash uchun saqlang; keyin himoyalangan student "
            "endpointlarini chaqiring."
        ),
        request_body=CheckSMSCodeSerializer,
        responses={
            200: openapi.Response(
                description="SMS tasdiqlandi, lokal foydalanuvchi sinxronlandi va tokenlar berildi.",
                examples={"application/json": {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOi...",
                    "token_type": "Bearer",
                    "user": {
                        "id": "c97a5d85-2d93-4f0d-b6c4-8d9d3a7d4e33",
                        "name": "Ali Valiyev",
                        "phone_number": "+998901234567",
                        "full_name": "Ali Valiyev",
                        "first_name": "Ali",
                        "last_name": "Valiyev",
                        "group_name": "N89",
                    },
                    "pdp_token": "Bearer external-token",
                }},
            ),
            400: openapi.Response(
                description="Validatsiya xatosi, SMS kod noto‘g‘ri yoki login ma’lumoti yaroqsiz.",
                examples={"application/json": {"message": "SMS kod noto‘g‘ri."}},
            ),
            502: openapi.Response(
                description="PDP auth servisi ishlamadi yoki access_token qaytarmadi.",
                examples={"application/json": {
                    "message": "Tashqi PDP auth servisida xatolik bor. Birozdan keyin qayta urinib ko‘ring."
                }},
            ),
            500: openapi.Response(
                description="Kutilmagan ichki server xatoligi.",
                examples={"application/json": {"message": "Ichki server xatoligi yuz berdi."}},
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
        except PDPAPIError:
            return Response(
                {"message": "Tashqi PDP auth servisida xatolik bor. Birozdan keyin qayta urinib ko‘ring."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"message": "Ichki server xatoligi yuz berdi."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        body = auth_login_verify_response(data)
        if not body.get("access_token"):
            return Response(
                {"message": "Server javobida access_token topilmadi."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(body, status=status.HTTP_200_OK)


class FrontendForgotPasswordAPIView(APIView):
    """Frontend: POST /auth/forgot-password."""

    permission_classes = [AllowAny]
    throttle_classes = [SmsThrottle]

    @swagger_auto_schema(
        tags=["Frontend / Parolni tiklash"],
        operation_summary="Parolni tiklash uchun SMS yuborish",
        operation_description=(
            "Parolni tiklash jarayonining 1-bosqichi. Foydalanuvchining "
            "`phone_number` qiymatini `+998XXXXXXXXX` formatida yuboring. Javobdagi "
            "`sms_code_id` ni saqlang va telefon raqami hamda SMS kod bilan "
            "`POST /auth/forgot-password/verify` endpointiga o‘ting."
        ),
        request_body=ForgotPasswordSerializer,
        responses={
            200: openapi.Response(
                description="Tiklash SMS kodi yuborildi.",
                examples={"application/json": {
                    "message": "SMS kodi yuborildi",
                    "sms_code_id": "291b3c96-1d95-4013-9ad8-ef24849a37c5",
                }},
            ),
            400: openapi.Response(
                description="Telefon formati noto‘g‘ri yoki PDP servisi so‘rovni rad etdi.",
                examples={"application/json": {"message": "Telefon raqami topilmadi."}},
            ),
            502: openapi.Response(
                description="Tashqi servis sms_code_id qaytarmadi.",
                examples={"application/json": {
                    "message": "Server javobida sms_code_id topilmadi."
                }},
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = forgot_password_via_external_api(
                phone_number=serializer.validated_data["phone_number"],
            )
        except PDPAPIError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        body = auth_sms_response(data, message="SMS kodi yuborildi")
        if not pick_sms_code_id(data):
            return Response(
                {"message": "Server javobida sms_code_id topilmadi."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(body, status=status.HTTP_200_OK)


class FrontendVerifyForgotPasswordAPIView(APIView):
    """Frontend: POST /auth/forgot-password/verify."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    @swagger_auto_schema(
        tags=["Frontend / Parolni tiklash"],
        operation_summary="Parolni tiklash SMS kodini tasdiqlash",
        operation_description=(
            "Parolni tiklash jarayonining 2-bosqichi. Oldingi endpointdan olingan "
            "`sms_code_id`, ayni `phone_number` va foydalanuvchi kiritgan `sms_code` ni "
            "yuboring. Javobdagi qisqa muddatli `pre_reset_token` ni saqlab, "
            "`POST /auth/reset-password` so‘rovida ishlating. Bu bosqich parolni o‘zgartirmaydi."
        ),
        request_body=VerifySMSCodeSerializer,
        responses={
            200: openapi.Response(
                description="SMS tasdiqlandi va parolni almashtirish tokeni berildi.",
                examples={"application/json": {
                    "pre_reset_token": "eyJ0eXAiOiJKV1QiLCJhbGciOi..."
                }},
            ),
            400: openapi.Response(
                description="Validatsiya xatosi yoki SMS kodi noto‘g‘ri.",
                examples={"application/json": {"message": "SMS kod noto‘g‘ri."}},
            ),
            502: openapi.Response(
                description="Tasdiqlash javobida pre_reset_token yo‘q.",
                examples={"application/json": {
                    "message": "Server javobida pre_reset_token topilmadi."
                }},
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = VerifySMSCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = verify_sms_code_for_password_reset(
                phone_number=serializer.validated_data["phone_number"],
                sms_code_id=serializer.validated_data["sms_code_id"],
                sms_code=serializer.validated_data["sms_code"],
            )
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        body = auth_forgot_verify_response(data)
        if not body.get("pre_reset_token"):
            return Response(
                {"message": "Server javobida pre_reset_token topilmadi."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(body, status=status.HTTP_200_OK)


class FrontendResetPasswordAPIView(APIView):
    """Frontend: POST /auth/reset-password."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    @swagger_auto_schema(
        tags=["Frontend / Parolni tiklash"],
        operation_summary="Tasdiqlangan token bilan yangi parol o‘rnatish",
        operation_description=(
            "Parolni tiklash jarayonining 3-yakuniy bosqichi. SMS tasdiqlashdan olingan "
            "`pre_reset_token`, kamida 6 belgili `password` va unga aynan teng "
            "`repeat_password` yuboriladi. Muvaffaqiyatdan so‘ng tokenni o‘chirib, "
            "foydalanuvchini login ekraniga yo‘naltiring."
        ),
        request_body=SetNewPasswordSerializer,
        responses={
            200: openapi.Response(
                description="Parol muvaffaqiyatli yangilandi.",
                examples={"application/json": {
                    "success": True,
                    "message": "Parol muvaffaqiyatli yangilandi",
                }},
            ),
            400: openapi.Response(
                description="Parollar mos emas, token yaroqsiz/eskirgan yoki PDP servisi so‘rovni rad etdi.",
                examples={"application/json": {"message": "Reset token eskirgan."}},
            ),
            500: openapi.Response(
                description="Kutilmagan ichki server xatoligi.",
                examples={"application/json": {"message": "Ichki server xatoligi yuz berdi."}},
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = SetNewPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            set_new_password_with_pre_token(
                pre_reset_token=serializer.validated_data["pre_reset_token"],
                password=serializer.validated_data["password"],
                repeat_password=serializer.validated_data["repeat_password"],
            )
        except PreResetTokenError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except PDPAPIError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {"message": "Ichki server xatoligi yuz berdi."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"success": True, "message": "Parol muvaffaqiyatli yangilandi"},
            status=status.HTTP_200_OK,
        )


class FrontendResendSmsAPIView(APIView):
    """Frontend: POST /auth/sms/resend — SMS kodni qayta yuborish."""

    permission_classes = [AllowAny]
    throttle_classes = [SmsThrottle]

    @swagger_auto_schema(
        tags=["Frontend / Autentifikatsiya"],
        operation_summary="SMS tasdiqlash kodini qayta yuborish",
        operation_description=(
            "Login yoki parolni tiklashda SMS kelmasa ishlatiladi. Avvalgi bosqichdan "
            "olingan `sms_code_id` va o‘sha `phone_number` ni JSON bodyda yuboring. "
            "Javobdagi `sms_code_id` ni keyingi tasdiqlash so‘rovida ishlating; PDP servisida "
            "alohida resend mavjud bo‘lmasa ham amaldagi ID qaytariladi."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["sms_code_id", "phone_number"],
            properties={
                "sms_code_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Oldingi SMS yuborish bosqichidan olingan identifikator.",
                ),
                "phone_number": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="SMS yuboriladigan telefon raqami, masalan +998901234567.",
                ),
            },
            example={
                "sms_code_id": "291b3c96-1d95-4013-9ad8-ef24849a37c5",
                "phone_number": "+998901234567",
            },
        ),
        responses={
            200: openapi.Response(
                description="Yangi kod yuborildi yoki mavjud SMS identifikatori qaytarildi.",
                examples={"application/json": {
                    "message": "Yangi kod yuborildi",
                    "sms_code_id": "291b3c96-1d95-4013-9ad8-ef24849a37c5",
                }},
            ),
            400: openapi.Response(
                description="Majburiy maydonlardan biri yuborilmagan.",
                examples={"application/json": {
                    "message": "sms_code_id va phone_number yuborilishi shart."
                }},
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        sms_code_id = request.data.get("sms_code_id")
        phone_number = request.data.get("phone_number")

        if not sms_code_id or not phone_number:
            return Response(
                {"message": "sms_code_id va phone_number yuborilishi shart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from app.services.auth_external_api import PDPAuthAPIClient

        client = PDPAuthAPIClient()
        try:
            payload = client.resend_sms(
                sms_code_id=str(sms_code_id),
                phone_number=str(phone_number),
            )
            data = payload.get("data", {}) or {}
        except PDPAPIError:
            # Ba'zi PDP versiyalarida alohida resend yo'q — mavjud sms_code_id ni qaytaramiz.
            data = {"sms_code_id": str(sms_code_id)}

        body = auth_sms_response(data, message="Yangi kod yuborildi")
        if not pick_sms_code_id(data):
            body["sms_code_id"] = str(sms_code_id)
        return Response(body, status=status.HTTP_200_OK)
