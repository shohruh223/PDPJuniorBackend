from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django.conf import settings

from app.services.portal import cache_layer
from app.models import Portfolio
from app.serializers.portfolio import PortfolioSerializer


class PortfolioListAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Portfolios"],
        operation_summary="Portfoliolar ro‘yxatini olish",
        operation_description="""
Bu endpoint barcha foydalanuvchilar uchun ochiq.

Authorization token yuborish shart emas.
Faqat active portfoliolar qaytadi.
`GET /api/portfolios/` so‘rovini parametrsiz yuboring.
""",
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Portfoliolar ro‘yxati muvaffaqiyatli olindi.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=["success", "message", "data"],
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                    "url": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI),
                                    "image": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        format=openapi.FORMAT_URI,
                                        x_nullable=True,
                                    ),
                                    "desc": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                        ),
                    },
                ),
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Portfoliolar ro‘yxati",
                        "data": [
                            {
                                "id": 1,
                                "name": "Sardor A.",
                                "url": "https://example.com/sardor",
                                "image": "http://127.0.0.1:8000/media/portfolios/sardor.jpg",
                                "desc": "Portfolio sayt",
                            }
                        ],
                    }
                },
            )
        },
    )
    def get(self, request, *args, **kwargs):
        portfolios = Portfolio.objects.filter(is_active=True)

        data = cache_layer.cached_call(
            cache_layer.make_key("portfolios", host=cache_layer.request_host(request)),
            getattr(settings, "CACHE_TTL_PUBLIC", 300),
            lambda: PortfolioSerializer(
                portfolios, many=True, context={"request": request}
            ).data,
        )

        return Response(
            {
                "success": True,
                "message": "Portfoliolar ro‘yxati",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )