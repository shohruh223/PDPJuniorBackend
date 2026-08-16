from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from app.models import Mentor
from app.serializers.mentor import MentorSerializer


class MentorListAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Mentors"],
        operation_summary="Mentorlar ro‘yxatini olish",
        operation_description="""
Bu endpoint barcha foydalanuvchilar uchun ochiq.

Authorization token yuborish shart emas.
Faqat active mentorlar va active filialga tegishli mentorlar qaytadi.

Masalan, `GET /api/mentors/?branch=2&role=Frontend` chaqiruvi 2-filialdagi
Frontend mentorlarini qaytaradi. Parametrlar yuborilmasa barcha mos mentorlar olinadi.
""",
        manual_parameters=[
            openapi.Parameter(
                name="branch",
                in_=openapi.IN_QUERY,
                description="Filial ID bo‘yicha filterlash",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                name="role",
                in_=openapi.IN_QUERY,
                description="Yo‘nalish bo‘yicha filterlash. Masalan: Frontend",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Mentorlar ro‘yxati muvaffaqiyatli olindi.",
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
                                    "role": openapi.Schema(type=openapi.TYPE_STRING),
                                    "branch": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "exp": openapi.Schema(type=openapi.TYPE_STRING),
                                    "studentsCount": openapi.Schema(type=openapi.TYPE_STRING),
                                    "workingPeriodStart": openapi.Schema(
                                        type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE
                                    ),
                                    "avatar": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        format=openapi.FORMAT_URI,
                                        x_nullable=True,
                                    ),
                                },
                            ),
                        ),
                    },
                ),
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Mentorlar ro‘yxati",
                        "data": [
                            {
                                "id": 1,
                                "name": "Asadbek Erkinov",
                                "role": "Frontend",
                                "branch": 2,
                                "exp": "2+ yil",
                                "studentsCount": "120+",
                                "workingPeriodStart": "2022-02-03",
                                "avatar": "http://127.0.0.1:8000/media/mentors/asadbek.jpg",
                            }
                        ],
                    }
                },
            )
        },
    )
    def get(self, request, *args, **kwargs):
        mentors = Mentor.objects.filter(
            is_active=True,
            branch__is_active=True,
        ).select_related("branch")

        branch = request.query_params.get("branch")
        role = request.query_params.get("role")

        if branch:
            mentors = mentors.filter(branch_id=branch)

        if role:
            mentors = mentors.filter(role__iexact=role)

        serializer = MentorSerializer(
            mentors,
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "success": True,
                "message": "Mentorlar ro‘yxati",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )