from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from app.permissions import IsStudentUserRole
from app.models.news import News
from app.serializers.news import NewsSerializer


news_list_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["success", "message", "data"],
    properties={
        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
        "message": openapi.Schema(type=openapi.TYPE_STRING, example="Yangiliklar ro‘yxati."),
        "data": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                    "title": openapi.Schema(type=openapi.TYPE_STRING),
                    "date": openapi.Schema(type=openapi.TYPE_STRING),
                    "type": openapi.Schema(type=openapi.TYPE_STRING),
                    "description": openapi.Schema(type=openapi.TYPE_STRING),
                    "color": openapi.Schema(type=openapi.TYPE_STRING),
                    "icon": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        ),
    },
)


class NewsListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Student / News"],
        operation_summary="Student uchun yangiliklar ro‘yxati",
        operation_description=(
            "Faol yangiliklarni eng yangisidan boshlab qaytaradi. "
            "Bearer token bilan student sifatida autentifikatsiya qiling; so‘rov parametrlari talab qilinmaydi."
        ),
        responses={
            200: openapi.Response("Yangiliklar muvaffaqiyatli olindi.", news_list_response),
            401: openapi.Response("Autentifikatsiya ma’lumotlari berilmagan yoki yaroqsiz."),
            403: openapi.Response("Foydalanuvchi student roliga ega emas."),
        },
    )
    def get(self, request, *args, **kwargs):
        return _news_list_response(request)


class PublicNewsListAPIView(APIView):
    """Galereya/yangiliklar sahifasi uchun ochiq endpoint."""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Public / News"],
        operation_summary="Ochiq yangiliklar ro‘yxati",
        operation_description=(
            "Barcha faol yangiliklarni eng yangisidan boshlab qaytaradi. "
            "Endpoint ochiq: Authorization sarlavhasi va query parametrlari kerak emas."
        ),
        responses={
            200: openapi.Response("Yangiliklar muvaffaqiyatli olindi.", news_list_response),
        },
    )
    def get(self, request, *args, **kwargs):
        return _news_list_response(request)


def _news_list_response(request):
    news = (
        News.objects
        .filter(is_active=True)
        .order_by("-created_at")
    )

    serializer = NewsSerializer(news, many=True, context={"request": request})

    return Response(
        {
            "success": True,
            "message": "Yangiliklar ro‘yxati.",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )