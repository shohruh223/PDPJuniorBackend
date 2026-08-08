from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from app.models.coin import CoinProduct
from app.permissions import IsStudentUserRole
from app.serializers.coin import CoinProductSerializer


coin_product_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "description": openapi.Schema(type=openapi.TYPE_STRING),
        "price": openapi.Schema(type=openapi.TYPE_INTEGER),
        "category": openapi.Schema(type=openapi.TYPE_STRING),
        "stock": openapi.Schema(type=openapi.TYPE_INTEGER),
        "emoji": openapi.Schema(type=openapi.TYPE_STRING),
        "bg_gradient": openapi.Schema(type=openapi.TYPE_STRING),
        "image": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, x_nullable=True),
        "in_stock": openapi.Schema(type=openapi.TYPE_BOOLEAN),
    },
)


class StudentCoinProductListAPIView(ListAPIView):
    serializer_class = CoinProductSerializer
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    def get_queryset(self):
        return CoinProduct.objects.filter(is_active=True).order_by("price")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @swagger_auto_schema(
        tags=["Student / Coin products"],
        operation_summary="Faol coin mahsulotlari ro‘yxati",
        operation_description=(
            "Student coin bilan olishi mumkin bo‘lgan faol mahsulotlarni narx bo‘yicha o‘sish tartibida qaytaradi. "
            "Bearer token bilan student sifatida autentifikatsiya qiling."
        ),
        responses={
            200: openapi.Response(
                "Mahsulotlar ro‘yxati.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_ARRAY, items=coin_product_schema),
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
        },
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "message": "Coin mahsulotlari ro‘yxati.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class StudentCoinProductDetailAPIView(RetrieveAPIView):
    serializer_class = CoinProductSerializer
    permission_classes = [IsAuthenticated, IsStudentUserRole]
    lookup_field = "id"

    def get_queryset(self):
        return CoinProduct.objects.filter(is_active=True)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @swagger_auto_schema(
        tags=["Student / Coin products"],
        operation_summary="Coin mahsuloti tafsilotlari",
        operation_description=(
            "URL dagi `id` UUID bo‘yicha bitta faol coin mahsulotini qaytaradi. "
            "Bearer token bilan student sifatida autentifikatsiya qiling."
        ),
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_PATH,
                description="Coin mahsulotining UUID identifikatori.",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response(
                "Mahsulot topildi.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": coin_product_schema,
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
            404: openapi.Response("Faol mahsulot topilmadi."),
        },
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Coin mahsulot ma'lumotlari.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )