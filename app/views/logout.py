"""Chiqish (logout) endpointi.

Ilgari loyihada logout umuman yo'q edi: access token 30 kun amal qilardi
va o'g'irlangan tokenni bekor qilishning imkoni yo'q edi. `token_blacklist`
ilovasi ulangan bo'lsa-da, hech kim undan foydalanmasdi.

Bu endpoint refresh tokenni qora ro'yxatga kiritadi. Access token o'z
muddati tugagunicha (default 2 soat) amal qilishda davom etadi — bu
JWT'ning tabiati; shuning uchun muddat qisqartirilgan.
"""

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class LogoutAPIView(APIView):
    """POST /auth/logout — refresh tokenni bekor qiladi."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Frontend / Autentifikatsiya"],
        operation_summary="Tizimdan chiqish",
        operation_description=(
            "Login vaqtida olingan `refresh_token` ni yuboring — u qora "
            "ro‘yxatga kiritiladi va boshqa yangi access token bera olmaydi.\n\n"
            "Mijoz tomonda saqlangan `access_token` va `refresh_token` ni "
            "ham o‘chiring."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh_token"],
            properties={
                "refresh_token": openapi.Schema(type=openapi.TYPE_STRING),
            },
            example={"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOi..."},
        ),
        responses={
            200: openapi.Response(
                description="Token bekor qilindi.",
                examples={"application/json": {"success": True, "message": "Chiqildi."}},
            ),
            400: openapi.Response(description="refresh_token yuborilmagan yoki yaroqsiz."),
        },
    )
    def post(self, request, *args, **kwargs):
        raw = request.data.get("refresh_token") or request.data.get("refresh")
        if not raw:
            return Response(
                {"success": False, "message": "refresh_token yuborilishi shart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            RefreshToken(str(raw)).blacklist()
        except TokenError:
            # Allaqachon bekor qilingan yoki muddati tugagan — mijoz uchun
            # natija bir xil, shuning uchun muvaffaqiyat deb qaytaramiz.
            pass
        except Exception:
            logger.exception("Logout: tokenni qora ro'yxatga kiritib bo'lmadi")
            return Response(
                {"success": False, "message": "Chiqishda xatolik yuz berdi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"success": True, "message": "Chiqildi."},
            status=status.HTTP_200_OK,
        )
