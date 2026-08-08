from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from app.models.month_hero import MonthHero
from app.serializers.month_hero import MonthHeroSerializer, MONTH_NAMES


class MonthHeroListAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Public / Month heroes"],
        operation_summary="Oy qahramonlari ro‘yxati",
        operation_description=(
            "Tanlangan yil va oydagi faol qahramonlarni umumiy ball bo‘yicha saralab qaytaradi. "
            "Endpoint ochiq. Masalan: `GET /api/month-heroes/?year=2026&month=8&branch_id=1`. "
            "`year` yoki `month` yuborilmasa joriy yil/oy olinadi; branch va course filtrlari ixtiyoriy."
        ),
        manual_parameters=[
            openapi.Parameter(
                name="year",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Yil bo‘yicha filter. Masalan: 2026. Yuborilmasa joriy yil olinadi.",
            ),
            openapi.Parameter(
                name="month",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="1–12 oralig‘idagi oy. Yuborilmasa joriy oy olinadi.",
            ),
            openapi.Parameter(
                name="branch_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Branch ID bo‘yicha filter. Masalan: 1",
            ),
            openapi.Parameter(
                name="course_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Course ID bo‘yicha filter. Masalan: 2",
            ),
        ],
        responses={
            200: openapi.Response(
                "Qahramonlar ro‘yxati.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    required=["success", "message", "filters", "data"],
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "filters": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "year": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "month": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "month_name": openapi.Schema(type=openapi.TYPE_STRING),
                                "branch_id": openapi.Schema(type=openapi.TYPE_INTEGER, x_nullable=True),
                                "course_id": openapi.Schema(type=openapi.TYPE_INTEGER, x_nullable=True),
                            },
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                description="MonthHeroSerializer maydonlari.",
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                    "course_id": openapi.Schema(type=openapi.TYPE_INTEGER, x_nullable=True),
                                    "course": openapi.Schema(type=openapi.TYPE_OBJECT, x_nullable=True),
                                    "branch_id": openapi.Schema(type=openapi.TYPE_INTEGER, x_nullable=True),
                                    "branch": openapi.Schema(type=openapi.TYPE_OBJECT, x_nullable=True),
                                    "score": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "period": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                    "year": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "month": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "month_name": openapi.Schema(type=openapi.TYPE_STRING),
                                    "avatar": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        format=openapi.FORMAT_URI,
                                        x_nullable=True,
                                    ),
                                    "rank": openapi.Schema(type=openapi.TYPE_INTEGER),
                                },
                            ),
                        ),
                    },
                ),
            ),
            400: openapi.Response(
                "year, month, branch_id yoki course_id formati noto‘g‘ri.",
                examples={
                    "application/json": {
                        "success": False,
                        "message": "month 1 dan 12 gacha bo‘lishi kerak.",
                    }
                },
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        now = timezone.now()

        year = request.query_params.get("year") or now.year
        month = request.query_params.get("month") or now.month
        branch_id = request.query_params.get("branch_id")
        course_id = request.query_params.get("course_id")

        try:
            year = int(year)
        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "message": "year noto‘g‘ri formatda. Masalan: 2026",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if month:
            try:
                month = int(month)
            except (TypeError, ValueError):
                return Response(
                    {
                        "success": False,
                        "message": "month noto‘g‘ri formatda. Masalan: 1-12",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if month < 1 or month > 12:
                return Response(
                    {
                        "success": False,
                        "message": "month 1 dan 12 gacha bo‘lishi kerak.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if branch_id:
            try:
                branch_id = int(branch_id)
            except (TypeError, ValueError):
                return Response(
                    {
                        "success": False,
                        "message": "branch_id noto‘g‘ri formatda.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if course_id:
            try:
                course_id = int(course_id)
            except (TypeError, ValueError):
                return Response(
                    {
                        "success": False,
                        "message": "course_id noto‘g‘ri formatda.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        queryset = (
            MonthHero.objects
            .select_related(
                "student_profile",
                "student_profile__user",
                "student_profile__course",
                "student_profile__branch",
            )
            .filter(
                period__year=year,
                is_active=True,
            )
        )

        if month:
            queryset = queryset.filter(period__month=month)

        if branch_id:
            queryset = queryset.filter(student_profile__branch_id=branch_id)

        if course_id:
            queryset = queryset.filter(student_profile__course_id=course_id)

        queryset = queryset.order_by(
            "-student_profile__total_score",
            "student_profile__user__first_name",
        )

        heroes = list(queryset)

        ranks = {
            hero.id: index + 1
            for index, hero in enumerate(heroes)
        }

        serializer = MonthHeroSerializer(
            heroes,
            many=True,
            context={
                "request": request,
                "ranks": ranks,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Oy qahramonlari ro‘yxati.",
                "filters": {
                    "year": year,
                    "month": month,
                    "month_name": MONTH_NAMES.get(month),
                    "branch_id": branch_id,
                    "course_id": course_id,
                },
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )