from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.throttling import ShopWriteThrottle
from app.permissions import IsStudentUserRole
from app.services.portal.shop_service import (
    get_shop_catalog,
    get_student_balance,
    purchase_product,
    serialize_order,
    serialize_shop_product,
)
from app.models.coin import CoinOrder, CoinProduct


shop_product_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
        "title": openapi.Schema(type=openapi.TYPE_STRING),
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "description": openapi.Schema(type=openapi.TYPE_STRING),
        "price": openapi.Schema(type=openapi.TYPE_INTEGER),
        "category": openapi.Schema(type=openapi.TYPE_STRING),
        "cat": openapi.Schema(type=openapi.TYPE_STRING),
        "stock": openapi.Schema(type=openapi.TYPE_INTEGER),
        "emoji": openapi.Schema(type=openapi.TYPE_STRING),
        "bg_gradient": openapi.Schema(type=openapi.TYPE_STRING),
        "image": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, x_nullable=True),
        "in_stock": openapi.Schema(type=openapi.TYPE_BOOLEAN),
    },
)

shop_order_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
        "title": openapi.Schema(type=openapi.TYPE_STRING),
        "price": openapi.Schema(type=openapi.TYPE_INTEGER),
        "status": openapi.Schema(type=openapi.TYPE_STRING),
        "date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
    },
)


class ShopCatalogAPIView(APIView):
    """Frontend shop.html — mahsulotlar katalogi."""

    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Shop"],
        operation_summary="Do‘kon katalogi",
        operation_description=(
            "Faol mahsulotlar, frontend kategoriyalari va joriy student coin balansini qaytaradi. "
            "`category` yuborilmasa yoki `all` bo‘lsa barcha mahsulotlar; boshqa qiymatda shu kategoriya olinadi. "
            "Bearer student tokeni talab qilinadi."
        ),
        manual_parameters=[
            openapi.Parameter(
                "category",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                enum=["all", "academy", "gadget", "book", "special"],
                default="all",
            ),
        ],
        responses={
            200: openapi.Response(
                "Katalog va balans.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "categories": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                                ),
                                "products": openapi.Schema(type=openapi.TYPE_ARRAY, items=shop_product_schema),
                                "balance": openapi.Schema(type=openapi.TYPE_INTEGER),
                            },
                        ),
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
        },
    )
    def get(self, request, *args, **kwargs):
        category = request.query_params.get("category", "all")
        catalog = get_shop_catalog(category=category, request=request)
        profile = request.user.student_profile

        return Response(
            {
                "success": True,
                "message": "Do‘kon katalogi.",
                "data": {
                    **catalog,
                    "balance": get_student_balance(profile),
                },
            },
            status=status.HTTP_200_OK,
        )


class ShopBalanceAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Shop"],
        operation_summary="Student coin balansi",
        operation_description=(
            "Autentifikatsiya qilingan studentning joriy jami coin balansini qaytaradi. "
            "Bearer student tokeni bilan parametrsiz chaqiring."
        ),
        responses={
            200: openapi.Response(
                "Joriy balans.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={"balance": openapi.Schema(type=openapi.TYPE_INTEGER)},
                        ),
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
        },
    )
    def get(self, request, *args, **kwargs):
        profile = request.user.student_profile
        return Response(
            {
                "success": True,
                "message": "Coin balansi.",
                "data": {"balance": get_student_balance(profile)},
            },
            status=status.HTTP_200_OK,
        )


class ShopProductDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Shop"],
        operation_summary="Do‘kon mahsuloti tafsilotlari",
        operation_description=(
            "URL dagi `product_id` UUID bo‘yicha bitta faol mahsulotni qaytaradi. "
            "Bearer student tokeni talab qilinadi."
        ),
        manual_parameters=[
            openapi.Parameter(
                "product_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
                description="Mahsulot UUIDsi.",
            )
        ],
        responses={
            200: openapi.Response(
                "Mahsulot topildi.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": shop_product_schema,
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
            404: openapi.Response(
                "Faol mahsulot topilmadi.",
                examples={"application/json": {"success": False, "message": "Mahsulot topilmadi."}},
            ),
        },
    )
    def get(self, request, product_id, *args, **kwargs):
        try:
            product = CoinProduct.objects.get(pk=product_id, is_active=True)
        except CoinProduct.DoesNotExist:
            return Response(
                {"success": False, "message": "Mahsulot topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "message": "Mahsulot ma'lumotlari.",
                "data": serialize_shop_product(product, request),
            },
            status=status.HTTP_200_OK,
        )


class ShopOrderListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Shop"],
        operation_summary="Student buyurtmalari",
        operation_description=(
            "Joriy studentning eng so‘nggi 50 ta do‘kon buyurtmasini yangi sanadan boshlab qaytaradi. "
            "Bearer student tokeni bilan parametrsiz chaqiring."
        ),
        responses={
            200: openapi.Response(
                "Buyurtmalar ro‘yxati.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(type=openapi.TYPE_ARRAY, items=shop_order_schema),
                    },
                ),
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
        },
    )
    def get(self, request, *args, **kwargs):
        profile = request.user.student_profile
        orders = CoinOrder.objects.filter(student_profile=profile).order_by("-created_at")[:50]
        return Response(
            {
                "success": True,
                "message": "Buyurtmalar ro‘yxati.",
                "data": [serialize_order(order) for order in orders],
            },
            status=status.HTTP_200_OK,
        )


class ShopOrderCreateAPIView(APIView):
    throttle_classes = [ShopWriteThrottle]
    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Shop"],
        operation_summary="Mahsulot sotib olish",
        operation_description=(
            "JSON bodyda faol mahsulotning `product_id` UUIDsini yuboradi. Yetarli coin va ombor qoldig‘i bo‘lsa "
            "coin yechiladi, qoldiq bittaga kamayadi va completed buyurtma yaratiladi. Bearer student tokeni talab qilinadi."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["product_id"],
            properties={"product_id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID)},
        ),
        responses={
            201: openapi.Response(
                "Buyurtma yaratildi.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "order": shop_order_schema,
                                "balance": openapi.Schema(type=openapi.TYPE_INTEGER),
                            },
                        ),
                    },
                ),
            ),
            400: openapi.Response(
                "product_id yo‘q/yaroqsiz, mahsulot tugagan yoki coin yetarli emas.",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Coin yetarli emas.",
                    }
                },
            ),
            401: openapi.Response("Autentifikatsiya talab qilinadi."),
            403: openapi.Response("Faqat studentlar uchun."),
        },
    )
    def post(self, request, *args, **kwargs):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response(
                {"success": False, "message": "product_id yuborilishi shart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = request.user.student_profile
        order, error = purchase_product(profile=profile, product_id=product_id)
        if error:
            return Response({"success": False, "message": error}, status=status.HTTP_400_BAD_REQUEST)

        profile.refresh_from_db()
        return Response(
            {
                "success": True,
                "message": "Buyurtma qabul qilindi.",
                "data": {
                    "order": serialize_order(order),
                    "balance": get_student_balance(profile),
                },
            },
            status=status.HTTP_201_CREATED,
        )
