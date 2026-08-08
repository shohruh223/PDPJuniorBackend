from django.db.models import Count
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import Course
from app.serializers.catalog import CourseCatalogSerializer


course_catalog_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Kurs IDsi."),
        "name": openapi.Schema(type=openapi.TYPE_STRING, description="Kurs nomi."),
        "description": openapi.Schema(
            type=openapi.TYPE_STRING, description="Frontend katalog tavsifi."
        ),
        "image": openapi.Schema(
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_URI,
            description="Kurs rasmi URL manzili; rasm bo‘lmasa bo‘sh satr.",
        ),
        "module_count": openapi.Schema(
            type=openapi.TYPE_INTEGER, description="Kursdagi modullar soni."
        ),
        "lesson_count": openapi.Schema(
            type=openapi.TYPE_INTEGER, description="Kursdagi darslar soni."
        ),
    },
)


class CourseCatalogAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Ochiq API / Kurslar"],
        operation_summary="Faol kurslar katalogi",
        operation_description=(
            "Frontend kurslar katalogi uchun bazadagi faqat `is_active=True` kurslarni "
            "`sort_order`, nom va ID bo‘yicha tartiblab qaytaradi. Modul va dars sonlari "
            "har bir kurs uchun dinamik hisoblanadi. Endpoint ochiq, token talab qilinmaydi."
        ),
        responses={
            200: openapi.Response(
                description="Faol kurslar ro‘yxati. Faol kurs bo‘lmasa bo‘sh massiv.",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY, items=course_catalog_schema
                ),
                examples={
                    "application/json": [
                        {
                            "id": 1,
                            "name": "Frontend",
                            "description": "Web dasturlash kursi",
                            "image": "https://example.uz/frontend.png",
                            "module_count": 4,
                            "lesson_count": 36,
                        }
                    ]
                },
            )
        },
    )
    def get(self, request, *args, **kwargs):
        courses = (
            Course.objects.filter(is_active=True)
            .annotate(
                module_count=Count("modules", distinct=True),
                lesson_count=Count("lessons", distinct=True),
            )
            .order_by("sort_order", "name", "id")
        )
        return Response(CourseCatalogSerializer(courses, many=True).data)
