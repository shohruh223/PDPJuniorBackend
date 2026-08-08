from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.permissions import IsStudentUserRole
from app.services.portal.ranking_service import get_ranking_list


ranking_student_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "course": openapi.Schema(type=openapi.TYPE_STRING),
        "branch": openapi.Schema(type=openapi.TYPE_STRING),
        "mentor": openapi.Schema(type=openapi.TYPE_STRING),
        "avatar": openapi.Schema(type=openapi.TYPE_STRING),
        "totalPoints": openapi.Schema(type=openapi.TYPE_INTEGER),
        "monthlyPoints": openapi.Schema(type=openapi.TYPE_INTEGER),
        "streak": openapi.Schema(type=openapi.TYPE_INTEGER),
        "level": openapi.Schema(type=openapi.TYPE_STRING),
        "score": openapi.Schema(type=openapi.TYPE_INTEGER),
    },
)


class RankingListAPIView(APIView):
    """Frontend ranking-page.js — o‘quvchilar reytingi."""

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Portal / Ranking"],
        operation_summary="O‘quvchilar reytingi",
        operation_description=(
            "Studentlarni ball bo‘yicha saralab, ko‘pi bilan 100 ta natija qaytaradi. "
            "`scope=course` yoki `scope=branch` ishlatilsa `context`ga mos kurs/filial nomini yuboring. "
            "`period=month` oylik, `total` umumiy ballni ishlatadi; `q` ism, guruh, kurs va filialdan qidiradi. "
            "Endpoint ochiq."
        ),
        manual_parameters=[
            openapi.Parameter("scope", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=["all", "course", "branch"], default="all"),
            openapi.Parameter("period", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=["total", "month"], default="total"),
            openapi.Parameter("context", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Kurs yoki filialning aniq nomi."),
            openapi.Parameter("q", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Erkin matnli qidiruv. `query` aliasi ham qabul qilinadi."),
        ],
        responses={
            200: openapi.Response(
                "Reyting ro‘yxati.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "filters": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "students": openapi.Schema(type=openapi.TYPE_ARRAY, items=ranking_student_schema),
                                "count": openapi.Schema(type=openapi.TYPE_INTEGER),
                            },
                        ),
                    },
                ),
            )
        },
    )
    def get(self, request, *args, **kwargs):
        scope = request.query_params.get("scope", "all")
        period = request.query_params.get("period", "total")
        context = request.query_params.get("context", "")
        query = request.query_params.get("q") or request.query_params.get("query", "")

        students = get_ranking_list(
            scope=scope,
            period=period,
            context=context,
            query=query,
            request=request,
        )

        return Response(
            {
                "success": True,
                "message": "Reyting ro‘yxati.",
                "filters": {
                    "scope": scope,
                    "period": period,
                    "context": context,
                    "query": query,
                },
                "data": {
                    "students": students,
                    "count": len(students),
                },
            },
            status=status.HTTP_200_OK,
        )


class StudentRankingMeAPIView(APIView):
    """Login qilgan o‘quvchining shaxsiy reyting pozitsiyasi."""

    permission_classes = [IsAuthenticated, IsStudentUserRole]

    @swagger_auto_schema(
        tags=["Portal / Ranking"],
        operation_summary="Joriy studentning reyting o‘rni",
        operation_description=(
            "Autentifikatsiya qilingan student uchun tanlangan reytingdagi o‘rnini va student ma’lumotlarini "
            "qaytaradi. `scope=course` yoki `branch` bo‘lsa `context` nomini yuboring. Student dastlabki "
            "500 natijaga kirmasa `rank` null bo‘ladi."
        ),
        manual_parameters=[
            openapi.Parameter("scope", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=["all", "course", "branch"], default="all"),
            openapi.Parameter("period", openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=["total", "month"], default="total"),
            openapi.Parameter("context", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Kurs yoki filialning aniq nomi."),
        ],
        responses={
            200: openapi.Response(
                "Shaxsiy reyting.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "rank": openapi.Schema(type=openapi.TYPE_INTEGER, x_nullable=True),
                                "student": ranking_student_schema,
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
        profile = request.user.student_profile
        scope = request.query_params.get("scope", "all")
        period = request.query_params.get("period", "total")
        context = request.query_params.get("context", "")

        students = get_ranking_list(
            scope=scope,
            period=period,
            context=context,
            request=request,
            limit=500,
        )
        my_id = str(profile.id)
        rank = next((index + 1 for index, item in enumerate(students) if item["id"] == my_id), None)

        from app.services.portal.ranking_service import serialize_ranking_student

        return Response(
            {
                "success": True,
                "message": "Shaxsiy reyting.",
                "data": {
                    "rank": rank,
                    "student": serialize_ranking_student(profile, request, period),
                },
            },
            status=status.HTTP_200_OK,
        )
