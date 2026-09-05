from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from app.services.portal import cache_layer
from app.services.portal.heroes_service import build_heroes_portal


class HeroesPortalAPIView(APIView):
    """Frontend heroes-portal.js — oy qahramonlari portali."""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Portal / Heroes"],
        operation_summary="Oy qahramonlari portali",
        operation_description=(
            "Mavjud oylar, faol oy va tanlangan ko‘rinishdagi qahramonlarni bitta portal payloadida qaytaradi. "
            "`month`ni `YYYY-MM` ko‘rinishida, `view`ni all/directions/branches qiymatlaridan biri sifatida yuboring. "
            "`q` qahramon ismi, kursi, filiali, mentori yoki kategoriyasi bo‘yicha faol oy ichida qidiradi. "
            "Noma’lum oy berilsa eng yangi mavjud oy ishlatiladi. Endpoint ochiq."
        ),
        manual_parameters=[
            openapi.Parameter("month", openapi.IN_QUERY, type=openapi.TYPE_STRING, pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Oy identifikatori. Masalan: 2026-08"),
            openapi.Parameter("view", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=["all", "directions", "branches"], default="all"),
            openapi.Parameter("q", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Qidiruv matni. `query` aliasi ham qabul qilinadi."),
        ],
        responses={
            200: openapi.Response(
                "Qahramonlar portali ma’lumotlari.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "filters": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "month": openapi.Schema(type=openapi.TYPE_STRING, x_nullable=True),
                                "view": openapi.Schema(type=openapi.TYPE_STRING),
                                "query": openapi.Schema(type=openapi.TYPE_STRING),
                            },
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "months": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        description=(
                                            "Oy obyekti: id, label, short hamda featured, directions va "
                                            "branches qahramon massivlarini saqlaydi."
                                        ),
                                    ),
                                ),
                                "active_month": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    x_nullable=True,
                                    description="Tanlangan yoki eng yangi oy obyekti.",
                                ),
                                "view": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    enum=["all", "directions", "branches"],
                                ),
                                "heroes": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                                            "course": openapi.Schema(type=openapi.TYPE_STRING),
                                            "branch": openapi.Schema(type=openapi.TYPE_STRING),
                                            "mentor": openapi.Schema(type=openapi.TYPE_STRING),
                                            "points": openapi.Schema(type=openapi.TYPE_INTEGER),
                                            "image": openapi.Schema(type=openapi.TYPE_STRING),
                                            "avatar": openapi.Schema(type=openapi.TYPE_STRING),
                                            "category": openapi.Schema(type=openapi.TYPE_STRING),
                                        },
                                    ),
                                ),
                            },
                        ),
                    },
                ),
            )
        },
    )
    def get(self, request, *args, **kwargs):
        month = request.query_params.get("month")
        view = request.query_params.get("view", "all")
        query = request.query_params.get("q") or request.query_params.get("query", "")

        cache_key = cache_layer.make_key(
            "heroes",
            month=month or "-", view=view, q=query,
            host=cache_layer.request_host(request),
        )
        payload = cache_layer.cached_call(
            cache_key,
            getattr(settings, "CACHE_TTL_HEROES", 300),
            lambda: build_heroes_portal(
                month=month,
                view=view,
                query=query,
                request=request,
            ),
        )

        return Response(
            {
                "success": True,
                "message": "Oy qahramonlari portali.",
                "filters": {"month": month, "view": view, "query": query},
                "data": payload,
            },
            status=status.HTTP_200_OK,
        )
