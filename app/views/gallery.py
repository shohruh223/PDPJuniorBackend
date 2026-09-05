from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.db.models import F

from app.services.portal import cache_layer
from app.services.portal.gallery_service import get_gallery_posts, serialize_gallery_post
from app.models.gallery import GalleryPost


gallery_post_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
        "category": openapi.Schema(type=openapi.TYPE_OBJECT),
        "icon": openapi.Schema(type=openapi.TYPE_STRING),
        "date": openapi.Schema(type=openapi.TYPE_STRING),
        "views": openapi.Schema(type=openapi.TYPE_STRING),
        "views_count": openapi.Schema(type=openapi.TYPE_INTEGER),
        "image": openapi.Schema(type=openapi.TYPE_STRING),
        "contain": openapi.Schema(type=openapi.TYPE_BOOLEAN),
        "bg": openapi.Schema(type=openapi.TYPE_STRING),
        "title": openapi.Schema(type=openapi.TYPE_OBJECT),
        "description": openapi.Schema(type=openapi.TYPE_OBJECT),
        "media": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                description="Media obyekti; odatda type, src, contain va bg maydonlarini saqlaydi.",
            ),
        ),
    },
)


class GalleryListAPIView(APIView):
    """Frontend gallery-page.js — yangiliklar va galereya."""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Portal / Gallery"],
        operation_summary="Galereya postlari ro‘yxati",
        operation_description=(
            "Barcha faol galereya postlarini `sort_order`, so‘ng yaratilgan sana bo‘yicha qaytaradi. "
            "Endpoint ochiq va parametrsiz chaqiriladi."
        ),
        responses={
            200: openapi.Response(
                "Galereya postlari olindi.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "items": openapi.Schema(
                                    type=openapi.TYPE_ARRAY, items=gallery_post_schema
                                ),
                                "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                            },
                        ),
                    },
                ),
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        items = cache_layer.cached_call(
            cache_layer.make_key("gallery", host=cache_layer.request_host(request)),
            getattr(settings, "CACHE_TTL_GALLERY", 300),
            lambda: get_gallery_posts(request),
        )
        return Response(
            {
                "success": True,
                "message": "Galereya postlari.",
                "data": {"items": items, "count": len(items)},
            },
            status=status.HTTP_200_OK,
        )


class GalleryDetailAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Portal / Gallery"],
        operation_summary="Galereya posti tafsilotlari",
        operation_description=(
            "URL dagi `post_id` UUID bo‘yicha faol postni qaytaradi va muvaffaqiyatli ko‘rilganda "
            "`views_count` qiymatini bittaga oshiradi. Endpoint ochiq."
        ),
        manual_parameters=[
            openapi.Parameter(
                "post_id",
                openapi.IN_PATH,
                description="Galereya postining UUID identifikatori.",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        responses={
            200: openapi.Response(
                "Post topildi.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": gallery_post_schema,
                    },
                ),
            ),
            404: openapi.Response(
                "Faol post topilmadi.",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "Post topilmadi.",
                    }
                },
            ),
        },
    )
    def get(self, request, post_id, *args, **kwargs):
        try:
            post = GalleryPost.objects.get(pk=post_id, is_active=True)
        except GalleryPost.DoesNotExist:
            return Response(
                {"success": False, "message": "Post topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # F() ifodasi bilan atomik o'sish: ilgari o'qish-o'zgartirish-yozish
        # edi va parallel ochilishlar bir-birini bosib ketardi.
        GalleryPost.objects.filter(pk=post.pk).update(views_count=F("views_count") + 1)
        post.views_count = (post.views_count or 0) + 1

        return Response(
            {
                "success": True,
                "message": "Galereya posti.",
                "data": serialize_gallery_post(post, request),
            },
            status=status.HTTP_200_OK,
        )
