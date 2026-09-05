from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django.conf import settings

from app.services.portal import cache_layer
from app.models import Branch
from app.serializers.branch import BranchSerializer


class BranchListAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Branches"],
        operation_summary="Filiallar ro‘yxatini olish",
        operation_description="""
Bu endpoint barcha foydalanuvchilar uchun ochiq.

Authorization token yuborish shart emas.
Faqat active filiallar qaytadi.

`GET /api/branches/?isOpened=opened` ko‘rinishida chaqiring.
`isOpened` yuborilmasa barcha faol filiallar qaytariladi.
""",
        manual_parameters=[
            openapi.Parameter(
                name="isOpened",
                in_=openapi.IN_QUERY,
                description="Filial statusi bo‘yicha filterlash. Masalan: opened yoki closed",
                type=openapi.TYPE_STRING,
                enum=["opened", "closed"],
                required=False,
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Filiallar ro‘yxati muvaffaqiyatli olindi.",
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
                                    "address": openapi.Schema(type=openapi.TYPE_STRING),
                                    "phone": openapi.Schema(type=openapi.TYPE_STRING),
                                    "mapUrl": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI),
                                    "isOpened": openapi.Schema(
                                        type=openapi.TYPE_STRING, enum=["opened", "closed"]
                                    ),
                                    "album": openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "type": openapi.Schema(type=openapi.TYPE_STRING),
                                                "url": openapi.Schema(
                                                    type=openapi.TYPE_STRING, format=openapi.FORMAT_URI
                                                ),
                                            },
                                        ),
                                    ),
                                },
                            ),
                        ),
                    },
                ),
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Filiallar ro‘yxati",
                        "data": [
                            {
                                "id": 1,
                                "name": "Xadra filiali",
                                "address": "Ташкент, Шайхантахурский район, ул. Заркайнар, 3Б",
                                "phone": "+998555084747",
                                "mapUrl": "https://yandex.uz/maps/-/CPCGb-M-",
                                "isOpened": "opened",
                                "album": [
                                    {
                                        "type": "image",
                                        "url": "http://127.0.0.1:8000/media/branches/album/xadra.jpg",
                                    },
                                    {
                                        "type": "video",
                                        "url": "http://127.0.0.1:8000/media/branches/album/xadra.mp4",
                                    },
                                ],
                            }
                        ],
                    }
                },
            )
        },
    )
    def get(self, request, *args, **kwargs):
        branches = Branch.objects.filter(is_active=True)

        is_opened = request.query_params.get("isOpened")

        if is_opened:
            branches = branches.filter(is_opened=is_opened)

        data = cache_layer.cached_call(
            cache_layer.make_key("branches", opened=is_opened or "-",
                                 host=cache_layer.request_host(request)),
            getattr(settings, "CACHE_TTL_PUBLIC", 300),
            lambda: BranchSerializer(
                branches, many=True, context={"request": request}
            ).data,
        )

        return Response(
            {
                "success": True,
                "message": "Filiallar ro‘yxati",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )